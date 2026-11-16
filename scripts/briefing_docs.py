#!/usr/bin/env python3
"""Briefing, document check: reads each candidate's FDA 510(k) summary and records what it says.

For every FDA item whose 510(k) has a published summary, this downloads the summary PDF from
accessdata.fda.gov, extracts the text, and records short facts: whether the document itself
describes AI or machine learning, the stated intended use, the algorithm method it names, the
predicate and reference devices, and whether a predetermined change control plan is mentioned.
Only these short facts are saved (data/briefing/docs/K######.json), never the PDF.

Evidence rules after reading:
  fda_listed stays fda_listed.
  Strong AI language in the summary raises manufacturer_reported or inferred to document_verified.
  A summary with no AI language lowers manufacturer_reported or inferred to unknown. Absence of
  AI language in the summary is not proof the device has no AI, so the item stays in the
  record and the page ranks it last instead of deleting it.
A summary that cannot be downloaded or read changes nothing. The item keeps its class.

Needs the pypdf package (the workflow installs it); falls back to the pdftotext command.
"""
import json
import re
import subprocess
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

import briefing_reviews as reviews
from briefing_common import OUT, get, load_json, log_correction, note_update, save_json, today, write_status

STRONG_AI = re.compile(
    r"artificial intelligence|machine[- ]learning|deep[- ]learning|neural network|convolutional|"
    r"\bAI[- ](?:assisted|enabled|based|powered|driven|algorithm|model|software|device|tool)\b|"
    r"\bML[- ](?:based|enabled|model|algorithm)\b", re.I)
BARE_AI = re.compile(r"\bAI\b")
METHODS = ("computer vision", "machine learning", "deep learning", "neural network", "rule-based",
           "signal processing", "image processing", "classical")
PAUSE = 30.0        # FDA's robots.txt asks for 30 seconds between requests
MAX_FETCH = 8       # per run, so a run stays under about four minutes
REVIEWS_PATH = OUT / "reviews.json"


def pdf_url(k):
    return f"https://www.accessdata.fda.gov/cdrh_docs/pdf{k[1:3]}/{k}.pdf"


def extract_text(data):
    """Text from PDF bytes, or None. pypdf first, then the pdftotext command."""
    try:
        import io
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
    except Exception:
        pass
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            f.write(data)
            f.flush()
            out = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, timeout=60)
            return out.stdout.decode("utf-8", "ignore") if out.returncode == 0 else None
    except Exception:
        return None


def sentence_around(text, pos, width=240):
    start = max(0, text.rfind(". ", 0, pos) + 2)
    end = text.find(". ", pos)
    end = len(text) if end == -1 else end + 1
    return text[start:end][:width].strip()


def analyze_summary(raw_text, k, applicant=""):
    """Pure. Short facts from the summary text. Anything not found stays None or empty."""
    text = re.sub(r"\s+", " ", raw_text or "").strip()
    if len(text) < 200:
        return {"status": "unreadable", "chars": len(text)}
    # AI language only counts when it is about the subject device. A sentence that mentions a
    # predicate often describes the predicate's method, not this device's.
    sentences = re.split(r"(?<=[.!?])\s+", text)
    subject = [x for x in sentences if STRONG_AI.search(x) and "predicate" not in x.lower()]
    terms = sorted({m.group(0).lower() for x in subject for m in STRONG_AI.finditer(x)})[:8]
    predicate_only = sorted({m.group(0).lower() for x in sentences if "predicate" in x.lower()
                             for m in STRONG_AI.finditer(x)} - set(terms))[:8]
    bare = len(BARE_AI.findall(" ".join(x for x in sentences if "predicate" not in x.lower())))
    ai_language = bool(subject) or bare >= 3

    methods = [m for m in METHODS if m in text.lower()]
    indications = None
    m = re.search(r"(?:indications? for use|intended use)\W{1,6}", text, re.I)
    if m:
        chunk = text[m.end():m.end() + 500]
        cut = chunk.find(". ", 80)
        indications = (chunk[:cut + 1] if cut != -1 else chunk[:350]).strip()[:350]

    predicates, references, same_company = [], [], []
    app_word = (applicant or "").split(" ")[0].lower().strip(",.")
    for km in re.finditer(r"\bK\d{6}\b", text):
        num = km.group(0)
        if num == k:
            continue
        before = text[max(0, km.start() - 120):km.start()].lower()
        after = text[km.end():km.end() + 80].lower()
        lp, lr = before.rfind("predicate"), before.rfind("reference")
        bucket = predicates if lp > lr else references if lr >= 0 else None
        if bucket is not None and num not in bucket:
            bucket.append(num)
        if app_word and len(app_word) > 2 and app_word in after and num not in same_company:
            same_company.append(num)
    return {
        "status": "read", "chars": len(text),
        "ai_language": ai_language, "ai_terms": terms, "bare_ai_mentions": bare,
        "ai_terms_predicate_only": predicate_only,
        "ai_sentence": subject[0][:240] if subject else None,
        "algorithm_methods": methods, "intended_use": indications,
        "predicates": predicates[:5], "reference_devices": references[:5],
        "same_company_devices": same_company[:5],
        "pccp_mentioned": "predetermined change control plan" in text.lower(),
        "pdf_url": pdf_url(k),
    }


def apply_to_item(it, facts):
    """Updates an item's evidence class from document facts. Returns a note, or None."""
    it["document"] = facts
    if facts.get("status") != "read":
        return None
    if reviews.review_for(it, reviews.load(REVIEWS_PATH)):
        return None      # a manual review decides this item's class; automation does not overrule it
    old = it.get("evidence")
    new = old
    if old != "fda_listed":
        if facts["ai_language"]:
            new = "document_verified"
        elif old in ("manufacturer_reported", "inferred"):
            new = "unknown"
    if new != old:
        log_correction(it["key"], "evidence", old, new,
                       "FDA 510(k) summary " + ("describes AI" if new == "document_verified" else "has no AI language"))
        it["evidence"] = new
        note_update(it, "document_read", f"FDA 510(k) summary read: evidence {old} to {new}")
        return f"{it['record_id']}: {old} -> {new}"
    return None


def main():
    cache_dir = OUT / "docs"
    changed, fetched, failed, cached, notes = 0, 0, 0, 0, []
    first_error = None
    for n in range(0, 7):
        path = OUT / (today() - timedelta(days=n)).isoformat() / "rules.json"
        items = load_json(path, None)
        if not items:
            continue
        touched = False
        for it in items:
            if it.get("source") != "openFDA 510(k)" or not it.get("summary_available") or it.get("document"):
                continue
            k = it["record_id"]
            facts = load_json(cache_dir / f"{k}.json", None)
            if facts is not None:
                cached += 1
            if facts is None:
                if fetched + failed >= MAX_FETCH:
                    notes.append(f"{k}: left for the next run (limit of {MAX_FETCH} downloads per run)")
                    continue
                status, body, err = get(pdf_url(k), pause=PAUSE if fetched + failed else 0, limit=25_000_000)
                if status != 200:
                    failed += 1
                    first_error = first_error or (err or str(status))
                    notes.append(f"{k}: summary PDF not retrieved ({err or status})")
                    continue
                text = extract_text(body)
                facts = analyze_summary(text, k, it.get("company", ""))
                fetched += 1
                if facts["status"] == "read":
                    save_json(cache_dir / f"{k}.json", facts)
            note = apply_to_item(it, facts)
            touched = True
            if note:
                changed += 1
                notes.append(note)
            notes.append(f"{k}: {facts['status']}, ai_language={facts.get('ai_language')}, terms={facts.get('ai_terms')}, "
                         f"methods={facts.get('algorithm_methods')}, predicates={facts.get('predicates')}")
        if touched:
            save_items = json.dumps(items, indent=1, ensure_ascii=False) + "\n"
            path.write_text(save_items, encoding="utf-8")
    live = "unproven" if not (fetched or failed or cached) else "failed" if failed and not (fetched or cached) \
        else "degraded" if failed else "ok"
    write_status("fda_510k_summaries", read=fetched, failed=failed, from_cache=cached, evidence_changed=changed,
                 live=live, live_detail=(f"{fetched} downloaded, {failed} failed" + (f" ({first_error})" if first_error else "")))
    print("\n".join("- " + n for n in notes) or "- nothing to check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
