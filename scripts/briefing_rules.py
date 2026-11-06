#!/usr/bin/env python3
"""Briefing, Rules section: FDA moves on AI devices. Standard library only.

Two sources, from slow and certain to fast and probable:
  1. FDA's AI-enabled device list (already saved daily by ai_evidence.py). A device that
     appears on it for the first time is a confirmed AI clearance. FDA refreshes this list
     only every few months, so this source is quiet most days.
  2. openFDA 510(k) clearances, refreshed weekly, kept only when the device is on the AI list,
     names AI in its device or company name, or sits in a code where MIN_SHARE+ of clearances
     are AI. Watched codes are those where FDA has
     already cleared at least MIN_AI_IN_CODE AI devices. These are possible AI devices,
     flagged months before the official list catches up. Labelled possible, never confirmed,
     because some of these codes (ultrasound systems, for example) also hold non-AI devices.
"""
import csv
import gzip
import json
import re
import sys
import urllib.parse
from collections import Counter
from datetime import datetime, timedelta

from briefing_common import ROOT, get, item, load_seen, save_seen, today, write_items

FDA_LIST = ROOT / "data" / "ai" / "fda_ai_devices.csv.gz"
LIST_URL = ("https://www.fda.gov/medical-devices/software-medical-device-samd/"
            "artificial-intelligence-enabled-medical-devices")
LOOKBACK_DAYS = 30        # openFDA window; the seen-set stops repeats inside it
FIRST_RUN_LIST_DAYS = 60  # on the very first run, only recent list entries count as news
CODES_PER_QUERY = 25
SHARE_SINCE = 2016        # compare AI clearances with all clearances from this year on
MIN_SHARE = 0.25          # a code counts as AI-heavy when a quarter of its clearances are AI
MIN_AI_IN_CODE = 5        # watch only codes with 5+ past AI clearances (42 codes, 86% of AI devices)


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
        out.append(item(
            "rules",
            f"FDA adds {r.get('Device', '').strip()} ({r.get('Company', '').strip()}) to its AI device list",
            f"Confirmed AI-enabled device. Panel: {r.get('Panel (Lead)', '').strip()}. "
            f"Decision {d.isoformat() if d else 'date unknown'}, {k}.",
            k_url(k), d.isoformat() if d else None, f"fda-list:{k}"))
    save_seen("rules_fda_list", seen)
    notes.append(f"FDA AI list: {len(rows)} devices, {len(out)} new to report"
                 + (" (first run: seeded)" if first_run else ""))
    return out


AI_WORDS = re.compile(r"\b(ai|a\.i\.|artificial intelligence|machine learning|deep learning|"
                      r"neural|algorithm\w*)\b", re.I)


def short(name, limit=90):
    """Model lists like 'System (A20); System (A20 Exp); ...' collapse to the first entry."""
    name = " ".join(name.split()).split(";")[0].strip()
    return name if len(name) <= limit else name[:limit - 1].rstrip() + "…"


def openfda(search, **extra):
    url = "https://api.fda.gov/device/510k.json?" + urllib.parse.urlencode({"search": search, **extra})
    status, body, err = get(url, pause=0.3)
    if status == 404:          # openFDA answers 404 when nothing matches
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
    out, skipped, fetched = [], [], 0
    for i in range(0, len(codes), CODES_PER_QUERY):
        batch = codes[i:i + CODES_PER_QUERY]
        results, err = openfda(f"decision_date:[{start} TO {today():%Y%m%d}] AND product_code:("
                               + " OR ".join(batch) + ")", limit=1000)
        if results is None:
            errors.append(err)
            continue
        fetched += len(results)
        for r in results:
            k = r.get("k_number", "")
            if not k or k in seen:
                continue
            seen.add(k)
            code = r.get("product_code", "")
            name, applicant = short(r.get("device_name", "")), " ".join(r.get("applicant", "").split())
            confirmed = k in on_list
            named = bool(AI_WORDS.search(f"{r.get('device_name', '')} {applicant}"))
            pct = share.get(code)
            pct_txt = f"{pct:.0%} of its clearances since {SHARE_SINCE} are AI" if pct is not None \
                else "AI share unknown"
            if not (confirmed or named or code in strong):
                skipped.append(f"{name} ({applicant}), {code}, {pct_txt}")
                continue
            why_flag = ("Already on FDA's AI list." if confirmed else
                        "AI named in the device or company." if named else
                        f"Not yet on FDA's AI list; inferred from product code {code}, where {pct_txt}.")
            out.append(item(
                "rules",
                f"FDA clears {name} ({applicant}), {'AI device' if confirmed else 'possible AI device'}",
                f"510(k) {k}, decided {r.get('decision_date', '')}. Product code {code}. {why_flag}",
                k_url(k), r.get("decision_date"), f"510k:{k}"))
    save_seen("rules_510k", seen)
    notes.append(f"openFDA 510(k): {len(codes)} watched codes, {len(strong)} at {MIN_SHARE:.0%}+ AI share, "
                 f"{fetched} clearances in the last {LOOKBACK_DAYS} days, {len(out)} kept, {len(skipped)} dropped"
                 + (f"; errors: {'; '.join(errors[:3])}" if errors else ""))
    notes.extend("SHARE: " + f"{c} {share[c]:.0%}" for c in sorted(share, key=share.get, reverse=True))
    notes.extend("DROPPED: " + s for s in skipped)
    return out


def main():
    rows = read_list()
    notes = []
    items = from_list(rows, notes) + from_openfda(rows, notes)
    write_items("rules", items, notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
