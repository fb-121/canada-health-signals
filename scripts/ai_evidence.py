#!/usr/bin/env python3
"""AI approvals versus evidence: daily collector. Standard library only.

Saves, under data/ai/:
  fda_ai_devices.csv.gz     latest copy of the FDA AI-enabled device list (only when it changed)
  year_counts.csv           per-year counts, rewritten each run:
                              pubmed_ai_all   PubMed records on AI/ML/deep learning (MeSH), by publication year
                              pubmed_ai_rct   same, limited to randomized controlled trials
                              ctgov_ai        ClinicalTrials.gov studies mentioning artificial intelligence, by start year
Every request is polite (pause between calls) and uses a descriptive User-Agent.
"""
import csv
import gzip
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY", "your-username/canada-health-signals")
UA = f"Mozilla/5.0 (compatible; CanadaHealthSignals/0.3; open-data research; +https://github.com/{REPO})"
FDA_CSV = "https://www.fda.gov/media/178541/download?attachment"
FIRST_YEAR = 2010
OUT = Path("data/ai")

AI_MESH = '("artificial intelligence"[MeSH Terms] OR "machine learning"[MeSH Terms] OR "deep learning"[MeSH Terms])'
RCT = 'randomized controlled trial[Publication Type]'


def get(url, limit=60_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read(limit + 1), ""
    except urllib.error.HTTPError as e:
        return e.code, b"", f"HTTP {e.code}"
    except Exception as e:
        return 0, b"", f"{type(e).__name__}: {e}"[:160]


def pubmed_count(term, year):
    q = urllib.parse.urlencode({"db": "pubmed", "retmode": "json", "rettype": "count",
                                "term": term, "datetype": "pdat", "mindate": year, "maxdate": year})
    status, body, err = get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + q)
    if status != 200:
        return None, err
    try:
        return int(json.loads(body)["esearchresult"]["count"]), ""
    except Exception as e:
        return None, f"parse: {e}"


def ctgov_count(year):
    adv = f"AREA[StartDate]RANGE[{year}-01-01,{year}-12-31]"
    q = urllib.parse.urlencode({"query.term": "artificial intelligence", "filter.advanced": adv,
                                "pageSize": 1, "countTotal": "true"})
    status, body, err = get("https://clinicaltrials.gov/api/v2/studies?" + q)
    if status != 200:
        return None, err
    try:
        return int(json.loads(body)["totalCount"]), ""
    except Exception as e:
        return None, f"parse: {e}"


def save_fda():
    status, body, err = get(FDA_CSV)
    if status != 200 or not body:
        return f"FDA list: status {status} {err}"
    digest = hashlib.sha256(body).hexdigest()[:12]
    path = OUT / "fda_ai_devices.csv.gz"
    marker = OUT / "fda_ai_devices.sha"
    if marker.exists() and marker.read_text().strip() == digest:
        return f"FDA list: unchanged ({len(body)} bytes)"
    with gzip.open(path, "wb") as f:
        f.write(body)
    marker.write_text(digest + "\n")
    return f"FDA list: saved {len(body)} bytes, hash {digest}"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    notes = [save_fda()]
    this_year = datetime.now(timezone.utc).year
    rows, failures = [], 0
    for y in range(FIRST_YEAR, this_year + 1):
        row = {"year": y}
        for key, fn in (("pubmed_ai_all", lambda: pubmed_count(AI_MESH, y)),
                        ("pubmed_ai_rct", lambda: pubmed_count(AI_MESH + " AND " + RCT, y)),
                        ("ctgov_ai", lambda: ctgov_count(y))):
            val, err = fn()
            if val is None:
                failures += 1
                notes.append(f"{key} {y}: {err}")
            row[key] = "" if val is None else val
            time.sleep(0.5)
        rows.append(row)
    # Keep the old file if the run was mostly failures, so one bad day never erases history.
    if failures <= len(rows):
        with (OUT / "year_counts.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["year", "pubmed_ai_all", "pubmed_ai_rct", "ctgov_ai"])
            w.writeheader()
            w.writerows(rows)
        notes.append(f"year_counts.csv written: {len(rows)} years, {failures} failed lookups")
    else:
        notes.append(f"year_counts.csv NOT rewritten: {failures} failed lookups")
    text = "\n".join(f"- {n}" for n in notes)
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("## AI evidence collector\n\n" + text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
