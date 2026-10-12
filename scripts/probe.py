#!/usr/bin/env python3
"""Canada Health Signals: daily probe and archive of open public feeds.

Standard library only. Each run does three things:
  1. Requests every source once, politely, with a descriptive User-Agent.
  2. Appends one row per source to data/probe_log.csv (status, size, hash, links found).
  3. Saves the raw response under data/raw/YYYY-MM-DD/ for sources marked archive=True.

Sources marked archive=False are probed only (status logged, nothing stored). Flip a
source to True once you have read its terms of use and confirmed archiving is allowed.
"""
import csv
import hashlib
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY", "your-username/canada-health-signals")
USER_AGENT = f"CanadaHealthSignals/0.1 (open-data research project; https://github.com/{REPO})"
TIMEOUT = 30
MAX_BYTES = 5_000_000

# name, url, ext, archive, note
SOURCES = [
    {
        "name": "dpd_drugproduct_sample",
        "url": "https://health-products.canada.ca/api/drug/drugproduct/?lang=en&type=json&din=02242963",
        "ext": "json",
        "archive": True,
        "note": "Drug Product Database API, documented, no key. Sample DIN to confirm it responds.",
    },
    {
        "name": "hc_recalls_opendata",
        "url": "https://recalls-rappels.canada.ca/sites/default/files/opendata-donneesouvertes/HCRSAMOpenData.json",
        "ext": "json",
        "archive": True,
        "note": "Candidate URL for the recalls open data file. Unverified, a 404 here is useful information.",
    },
    {
        "name": "hc_recalls_api_page",
        "url": "https://recalls-rappels.canada.ca/en/api",
        "ext": "html",
        "archive": True,
        "note": "Documentation page, to find the real feed address if the candidate above fails.",
    },
    {
        "name": "drug_shortages_home",
        "url": "https://www.drugshortagescanada.ca/",
        "ext": "html",
        "archive": False,
        "note": "No API or bulk download found. Probe only until terms of use are reviewed.",
    },
    {
        "name": "phac_wastewater_page",
        "url": "https://health-infobase.canada.ca/covid-19/wastewater/",
        "ext": "html",
        "archive": True,
        "note": "PHAC dashboard page. Updates Tuesdays and Fridays. Script lists any csv/json links it finds.",
    },
    {
        "name": "aqhi_calgary_bbox",
        "url": "https://api.weather.gc.ca/collections/aqhi-observations-realtime/items?f=json&limit=20&bbox=-114.5,50.8,-113.8,51.3",
        "ext": "json",
        "archive": True,
        "note": "Environment Canada OGC API, air quality observations around Calgary.",
    },
    {
        "name": "ahs_er_wait_times",
        "url": "https://www.albertahealthservices.ca/waittimes/waittimes.aspx",
        "ext": "html",
        "archive": False,
        "note": "Probe only. Review AHS terms of use before archiving. This is the signal with no public history.",
    },
]

LINK_RE = re.compile(r"""href=["']([^"']+\.(?:csv|json|xlsx|zip))["']""", re.IGNORECASE)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read(MAX_BYTES)
            return resp.status, resp.headers.get("Content-Type", ""), body, ""
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", "") if e.headers else "", b"", f"HTTP {e.code}"
    except Exception as e:  # network errors, timeouts, DNS, TLS
        return 0, "", b"", f"{type(e).__name__}: {e}"[:200]


def main():
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")
    data_dir = Path("data")
    raw_dir = data_dir / "raw" / day
    raw_dir.mkdir(parents=True, exist_ok=True)
    log_path = data_dir / "probe_log.csv"
    new_log = not log_path.exists()

    rows = []
    for src in SOURCES:
        status, ctype, body, error = fetch(src["url"])
        digest = hashlib.sha256(body).hexdigest()[:12] if body else ""
        links = ""
        if body and src["ext"] == "html":
            text = body.decode("utf-8", errors="ignore")
            found = []
            for link in LINK_RE.findall(text):
                if link not in found:
                    found.append(link)
            links = "|".join(found[:5])
        archived = False
        if status == 200 and body and src["archive"]:
            (raw_dir / f"{src['name']}.{src['ext']}").write_bytes(body)
            archived = True
        rows.append({
            "ts_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "name": src["name"],
            "status": status,
            "bytes": len(body),
            "content_type": ctype.split(";")[0],
            "sha256_12": digest,
            "archived": archived,
            "data_links": links,
            "error": error,
        })
        time.sleep(2)  # be polite

    with log_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        if new_log:
            writer.writeheader()
        writer.writerows(rows)

    lines = ["| source | status | bytes | archived | data links | error |", "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(
            f"| {r['name']} | {r['status']} | {r['bytes']} | {r['archived']} | {r['data_links'] or '-'} | {r['error'] or '-'} |"
        )
    summary = "\n".join(lines)
    print(summary)
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a", encoding="utf-8") as f:
            f.write(f"## Probe results {day}\n\n{summary}\n")
    return 0  # never fail the workflow: a dead feed is a result, not an error


if __name__ == "__main__":
    sys.exit(main())
