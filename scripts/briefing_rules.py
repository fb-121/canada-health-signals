#!/usr/bin/env python3
"""Briefing, Rules section: FDA moves on AI devices. Standard library only.

Two sources, from slow and certain to fast and probable:
  1. FDA's AI-enabled device list (already saved daily by ai_evidence.py). A device that
     appears on it for the first time is a confirmed AI clearance. FDA refreshes this list
     only every few months, so this source is quiet most days.
  2. openFDA 510(k) clearances, refreshed weekly, limited to product codes where FDA has
     already cleared at least MIN_AI_IN_CODE AI devices. These are possible AI devices,
     flagged months before the official list catches up. Labelled possible, never confirmed,
     because some of these codes (ultrasound systems, for example) also hold non-AI devices.
"""
import csv
import gzip
import json
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


def from_openfda(rows, notes):
    on_list = {(r.get("Submission Number") or "").strip() for r in rows}
    code_counts = Counter((r.get("Primary Product Code") or "").strip() for r in rows)
    code_counts.pop("", None)
    codes = sorted(c for c, n in code_counts.items() if n >= MIN_AI_IN_CODE)
    if not codes:
        notes.append("openFDA: skipped, no product codes (FDA list missing)")
        return []
    seen = load_seen("rules_510k")
    start = (today() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y%m%d")
    end = today().strftime("%Y%m%d")
    out, fetched, errors = [], 0, []
    for i in range(0, len(codes), CODES_PER_QUERY):
        batch = codes[i:i + CODES_PER_QUERY]
        search = (f"decision_date:[{start} TO {end}] AND product_code:("
                  + " OR ".join(batch) + ")")
        url = "https://api.fda.gov/device/510k.json?" + urllib.parse.urlencode(
            {"search": search, "limit": 1000})
        status, body, err = get(url, pause=0.3)
        if status == 404:      # openFDA answers 404 when nothing matches
            continue
        if status != 200:
            errors.append(err or f"HTTP {status}")
            continue
        try:
            results = json.loads(body).get("results", [])
        except ValueError as e:
            errors.append(f"parse: {e}")
            continue
        fetched += len(results)
        for r in results:
            k = r.get("k_number", "")
            if not k or k in seen:
                continue
            seen.add(k)
            code = r.get("product_code", "")
            confirmed = k in on_list
            label = "AI device" if confirmed else "possible AI device"
            n_ai = code_counts.get(code, 0)
            out.append(item(
                "rules",
                f"FDA clears {r.get('device_name', '').strip()} ({r.get('applicant', '').strip()}), {label}",
                f"510(k) {k}, decided {r.get('decision_date', '')}. Product code {code}, "
                f"where FDA has cleared {n_ai} AI device{'s' if n_ai != 1 else ''} before. "
                + ("Already on FDA's AI list." if confirmed
                   else "Not yet on FDA's AI list, so AI use is inferred from the product code."),
                k_url(k), r.get("decision_date"), f"510k:{k}"))
    save_seen("rules_510k", seen)
    notes.append(f"openFDA 510(k): {len(codes)} AI product codes, {fetched} clearances in "
                 f"the last {LOOKBACK_DAYS} days, {len(out)} new to report"
                 + (f"; errors: {'; '.join(errors[:3])}" if errors else ""))
    return out


def main():
    rows = read_list()
    notes = []
    items = from_list(rows, notes) + from_openfda(rows, notes)
    write_items("rules", items, notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
