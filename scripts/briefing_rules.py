#!/usr/bin/env python3
"""Briefing, Rules section: FDA moves on AI devices. Standard library only.

Two sources, from slow and certain to fast and probable:
  1. FDA's AI-enabled device list (saved daily by ai_evidence.py). A device appearing on it
     for the first time is a clearance FDA itself calls AI-enabled. The list updates only every
     few months.
  2. openFDA 510(k) clearances, refreshed weekly. A clearance is kept as a candidate when it is
     on the list, names AI in the device or company name, or sits in a product code where
     MIN_SHARE+ of clearances since 2016 are on the AI list.

Evidence classes (strongest first). briefing_docs.py may raise or lower a class after reading
the FDA 510(k) summary:
  fda_listed             on FDA's AI-enabled device list
  document_verified      the FDA 510(k) summary itself describes AI or machine learning
  manufacturer_reported  the manufacturer's own device or company name claims AI; not yet checked
  inferred               no document evidence; the product code is AI-heavy, which is a guess
  unknown                no evidence either way
"""
import csv
import gzip
import json
import re
import sys
import urllib.parse
from collections import Counter
from datetime import datetime, timedelta

from briefing_common import (ROOT, get, iso, item, load_seen, pdate, save_seen, slug, today, write_items,
                             write_status)

FDA_LIST = ROOT / "data" / "ai" / "fda_ai_devices.csv.gz"
LOOKBACK_DAYS = 30
FIRST_RUN_LIST_DAYS = 60
CODES_PER_QUERY = 25
SHARE_SINCE = 2016
MIN_SHARE = 0.25
MIN_AI_IN_CODE = 5
AI_WORDS = re.compile(r"\b(ai|a\.i\.|artificial intelligence|machine learning|deep learning|"
                      r"neural|algorithm\w*)\b", re.I)
EVIDENCE = ("fda_listed", "document_verified", "manufacturer_reported", "inferred", "unknown")


def k_url(k):
    return f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID={k}"


def read_list():
    if not FDA_LIST.exists():
        return []
    with gzip.open(FDA_LIST, "rt", encoding="utf-8-sig", errors="ignore") as f:
        return list(csv.DictReader(f))


def parse_us_date(s):
    try:
        return datetime.strptime(s.strip(), "%m/%d/%Y").date()
    except ValueError:
        return None


def classify_evidence(on_list, named, share):
    """Pure. The class from what is known before reading any FDA document."""
    if on_list:
        return "fda_listed"
    if named:
        return "manufacturer_reported"
    if share is not None and share >= MIN_SHARE:
        return "inferred"
    return "unknown"


def short(name, limit=90):
    """Model lists like 'System (A20); System (A20 Exp); ...' collapse to the first entry."""
    name = " ".join((name or "").split()).split(";")[0].strip()
    return name if len(name) <= limit else name[:limit - 1].rstrip() + "…"


def from_list(rows, notes):
    seen = load_seen("rules_fda_list")
    first_run = not seen
    out = []
    for r in rows:
        k = (r.get("Submission Number") or "").strip()
        if not k or k in seen:
            continue
        seen.add(k)
        d = parse_us_date(r.get("Date of Final Decision", ""))
        if first_run and (d is None or (today() - d).days > FIRST_RUN_LIST_DAYS):
            continue
        company = (r.get("Company") or "").strip()
        out.append(item(
            "rules", f"FDA lists {short(r.get('Device'))} ({company}) as AI-enabled",
            f"On FDA's AI-enabled device list. Specialty: {(r.get('Panel (Lead)') or '').strip()}. Product code "
            f"{(r.get('Primary Product Code') or '').strip()}.",
            k_url(k), d, f"fda-list:{k}", company_id=f"fda:{slug(company)}", company=company,
            evidence="fda_listed", specialty=(r.get("Panel (Lead)") or "").strip(),
            product_code=(r.get("Primary Product Code") or "").strip(), record_id=k,
            source="FDA AI device list"))
    save_seen("rules_fda_list", seen)
    notes.append(f"FDA AI list: {len(rows)} devices, {len(out)} new to report"
                 + (" (first run: seeded)" if first_run else ""))
    return out


def openfda(search, **extra):
    url = "https://api.fda.gov/device/510k.json?" + urllib.parse.urlencode({"search": search, **extra})
    status, body, err = get(url, pause=0.3)
    if status == 404:
        return [], ""
    if status != 200:
        return None, err or f"HTTP {status}"
    try:
        return json.loads(body).get("results", []), ""
    except ValueError as e:
        return None, f"parse: {e}"


def ai_share(rows, codes, errors):
    """Share of each code's 510(k) clearances since SHARE_SINCE that are on FDA's AI list."""
    ai = Counter()
    for r in rows:
        d = parse_us_date(r.get("Date of Final Decision", ""))
        if d and d.year >= SHARE_SINCE:
            ai[(r.get("Primary Product Code") or "").strip()] += 1
    totals = {}
    for i in range(0, len(codes), CODES_PER_QUERY):
        batch = codes[i:i + CODES_PER_QUERY]
        res, err = openfda(f"decision_date:[{SHARE_SINCE}0101 TO {today():%Y%m%d}] AND product_code:("
                           + " OR ".join(batch) + ")", count="product_code")
        if res is None:
            errors.append(f"share counts: {err}")
            continue
        for t in res:
            totals[str(t.get("term", "")).upper()] = t.get("count", 0)
    return {c: ai[c] / totals[c] for c in codes if totals.get(c)}


def build_item(r, on_list, share):  # on_list: True when this clearance is on FDA's AI list
    """One openFDA 510(k) record to an item. Pure."""
    k = r.get("k_number", "")
    code = r.get("product_code", "")
    applicant = " ".join((r.get("applicant") or "").split())
    name = short(r.get("device_name"))
    named = bool(AI_WORDS.search(f"{r.get('device_name', '')} {applicant}"))
    evidence = classify_evidence(bool(on_list), named, share.get(code))
    decided, received = pdate(r.get("decision_date")), pdate(r.get("date_received"))
    review_days = (decided - received).days if decided and received else None
    pct = share.get(code)
    basis = {"fda_listed": "On FDA's AI-enabled device list.",
             "manufacturer_reported": "The device or company name says AI. Not yet checked against FDA documents.",
             "inferred": (f"Not on FDA's AI list. Guess from product code {code}, where "
                          f"{pct:.0%} of clearances since {SHARE_SINCE} are AI.") if pct is not None else "",
             "unknown": "No evidence of AI either way."}[evidence]
    return item("rules", f"FDA clears {name} ({applicant})",
                f"Product code {code}. {basis}", k_url(k), decided, f"510k:{k}",
                company_id=f"fda:{slug(applicant)}", company=applicant, evidence=evidence, record_id=k,
                product_code=code, code_ai_share=round(pct, 3) if pct is not None else None,
                specialty=(r.get("advisory_committee_description") or "").strip() or None,
                received_date=iso(received), review_days=review_days,
                applicant_country=(r.get("country_code") or "").strip() or None,
                clearance_type=(r.get("clearance_type") or "").strip() or None,
                summary_available=(r.get("statement_or_summary") or "").strip().lower() == "summary",
                source="openFDA 510(k)")


def from_openfda(rows, notes):
    on_list = {(r.get("Submission Number") or "").strip() for r in rows}
    code_counts = Counter((r.get("Primary Product Code") or "").strip() for r in rows)
    code_counts.pop("", None)
    codes = sorted(c for c, n in code_counts.items() if n >= MIN_AI_IN_CODE)
    if not codes:
        notes.append("openFDA: skipped, no product codes (FDA list missing)")
        return []
    errors = []
    share = ai_share(rows, codes, errors)
    strong = {c for c, v in share.items() if v >= MIN_SHARE}
    seen = load_seen("rules_510k")
    start = (today() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y%m%d")
    out, skipped, fetched, latest = [], [], 0, None
    for i in range(0, len(codes), CODES_PER_QUERY):
        batch = codes[i:i + CODES_PER_QUERY]
        results, err = openfda(f"decision_date:[{start} TO {today():%Y%m%d}] AND product_code:("
                               + " OR ".join(batch) + ")", limit=1000)
        if results is None:
            errors.append(err)
            continue
        fetched += len(results)
        for r in results:
            d = pdate(r.get("decision_date"))
            latest = max(latest, d) if latest and d else (d or latest)
            k = r.get("k_number", "")
            if not k or k in seen:
                continue
            seen.add(k)
            it = build_item(r, k in on_list, share)
            if it["evidence"] == "unknown" or (it["evidence"] == "inferred" and it["product_code"] not in strong):
                skipped.append(f"{k} {it['headline']}")
                continue
            out.append(it)
    save_seen("rules_510k", seen)
    notes.append(f"openFDA 510(k): {len(codes)} watched codes, {len(strong)} at {MIN_SHARE:.0%}+ AI share, "
                 f"{fetched} clearances in the last {LOOKBACK_DAYS} days, {len(out)} kept, {len(skipped)} dropped"
                 + (f"; errors: {'; '.join(errors[:3])}" if errors else ""))
    notes.extend("DROPPED: " + s for s in skipped)
    write_status("openfda_510k", latest_decision_date=iso(latest), fetched=fetched, errors=len(errors),
                 live="failed" if errors else "ok" if fetched else "unproven",
                 live_detail=("; ".join(errors[:2]) if errors else f"{fetched} clearances returned by the API"))
    return out


def main():
    rows = read_list()
    notes = []
    dates = [parse_us_date(r.get("Date of Final Decision", "")) for r in rows]
    write_status("fda_ai_device_list", latest_decision_date=iso(max((d for d in dates if d), default=None)),
                 devices=len(rows), live="ok" if rows else "failed",
                 live_detail=f"{len(rows)} rows read from the FDA list" if rows else "no rows read")
    items = from_list(rows, notes) + from_openfda(rows, notes)
    write_items("rules", items, notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
