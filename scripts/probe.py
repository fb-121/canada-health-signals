#!/usr/bin/env python3
"""Canada Health Signals: daily probe and archive of open public feeds.

Standard library only. Each run does three things:
  1. Requests every source once, politely, with a descriptive User-Agent.
  2. Appends one row per source to data/probe_log.csv (status, size, hash, links found).
  3. Saves the raw response (gzipped) under data/raw/YYYY-MM-DD/ for sources marked
     archive=True, but only when the content changed since the last saved copy.

Sources marked archive=False are probed only (status logged, nothing stored). Flip a
source to True once you have read its terms of use and confirmed archiving is allowed.
"""
import csv
import gzip
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
USER_AGENT = f"Mozilla/5.0 (compatible; CanadaHealthSignals/0.3; open-data research; +https://github.com/{REPO})"
TIMEOUT = 60
MAX_BYTES = 80_000_000

WW = "https://health-infobase.canada.ca/src/data"
AQHI_BBOX = "bbox=-114.5,50.8,-113.8,51.3"

SOURCES = [
    {
        "name": "dpd_brand_advil",
        "url": "https://health-products.canada.ca/api/drug/drugproduct/?lang=en&type=json&brandname=advil",
        "ext": "json",
        "archive": True,
        "note": "Drug Product Database API (documented, no key). Brand name search to confirm real results.",
    },
    {
        "name": "dpd_ingredient_acetaminophen",
        "url": "https://health-products.canada.ca/api/drug/activeingredient/?lang=en&type=json&ingredientname=acetaminophen",
        "ext": "json",
        "archive": True,
        "note": "Second DPD check, by active ingredient.",
    },
    {
        "name": "hc_recalls_opendata",
        "url": "https://recalls-rappels.canada.ca/sites/default/files/opendata-donneesouvertes/HCRSAMOpenData.json",
        "ext": "json",
        "archive": True,
        "note": "All Health Canada recalls and safety alerts. Has an Organization field for filtering to health products.",
    },
    {
        "name": "phac_wastewater_aggregate",
        "url": f"{WW}/wastewater/wastewater_aggregate.csv",
        "ext": "csv",
        "archive": True,
        "note": "PHAC wastewater surveillance, aggregate. Link found on the dashboard page. Updates Tue and Fri.",
    },
    {
        "name": "phac_wastewater_covid_trend",
        "url": f"{WW}/covidLive/wastewater/covid19-wastewater-trend.csv",
        "ext": "csv",
        "archive": True,
        "note": "PHAC COVID wastewater trend. Link found on the dashboard page.",
    },
    {
        "name": "phac_wastewater_page",
        "url": "https://health-infobase.canada.ca/covid-19/wastewater/",
        "ext": "html",
        "archive": False,
        "note": "Dashboard page. Probe only, used to notice if the CSV links change.",
    },
    {
        "name": "aqhi_calgary_bbox",
        "url": f"https://api.weather.gc.ca/collections/aqhi-observations-realtime/items?f=json&limit=100&{AQHI_BBOX}",
        "ext": "json",
        "archive": True,
        "note": "Environment Canada OGC API, air quality observations around Calgary.",
    },
    {
        "name": "qc_er_dataset_meta",
        "url": "https://www.donneesquebec.ca/recherche/api/3/action/package_show?id=fichier-horaire-des-donnees-de-la-situation-a-l-urgence",
        "ext": "json",
        "archive": True,
        "note": "Donnees Quebec (CC-BY 4.0) hourly ER situation by facility. Metadata call, used to find the real CSV URLs.",
    },
    {
        "name": "qc_er_resource_page",
        "url": "https://www.donneesquebec.ca/recherche/dataset/fichier-horaire-des-donnees-de-la-situation-a-l-urgence/resource/a9272cc9-8234-40d1-9806-9f6b4c75c20d",
        "ext": "html",
        "archive": False,
        "note": "Fallback for finding the CSV link if the metadata call fails.",
    },
    {
        "name": "qc_er_hourly_7day",
        "url": "https://www.msss.gouv.qc.ca/professionnels/statistiques/documents/urgences/Releve_horaire_urgences_7jours.csv",
        "ext": "csv",
        "archive": True,
        "note": "Quebec ER situation by facility, hourly, rolling 7 days (CC-BY 4.0). A daily run captures every hour.",
    },
    {
        "name": "qc_er_hourly_7day_headcount",
        "url": "https://www.msss.gouv.qc.ca/professionnels/statistiques/documents/urgences/Releve_horaire_urgences_7jours_nbpers.csv",
        "ext": "csv",
        "archive": True,
        "note": "Same, with the number of people present (CC-BY 4.0).",
    },
    # AHS (Alberta) ER wait times removed: their terms of use do not allow automated collection.
]

LINK_RE = re.compile(r"""href=["']([^"']+\.(?:csv|json|xlsx|zip))["']""", re.IGNORECASE)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read(MAX_BYTES + 1)
            return resp.status, resp.headers.get("Content-Type", ""), body, ""
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", "") if e.headers else "", b"", f"HTTP {e.code}"
    except Exception as e:  # network errors, timeouts, DNS, TLS
        return 0, "", b"", f"{type(e).__name__}: {e}"[:200]


def last_saved_hashes(log_path):
    """Map source name to the hash of its most recently saved snapshot."""
    hashes = {}
    if not log_path.exists():
        return hashes
    with log_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("archived") in ("True", "unchanged") and row.get("sha256_12"):
                hashes[row["name"]] = row["sha256_12"]
    return hashes


def main():
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")
    data_dir = Path("data")
    raw_dir = data_dir / "raw" / day
    raw_dir.mkdir(parents=True, exist_ok=True)
    log_path = data_dir / "probe_log.csv"
    new_log = not log_path.exists()
    previous = last_saved_hashes(log_path)

    rows = []
    for src in SOURCES:
        status, ctype, body, error = fetch(src["url"])
        too_big = len(body) > MAX_BYTES
        if too_big:
            body, error = b"", f"over {MAX_BYTES} byte cap"
        digest = hashlib.sha256(body).hexdigest()[:12] if body else ""
        links = ""
        if body and src["ext"] == "html":
            text = body.decode("utf-8", errors="ignore")
            found = []
            for link in LINK_RE.findall(text):
                if link not in found:
                    found.append(link)
            links = ";".join(found[:5])
        archived = "False"
        if status == 200 and body and src["archive"]:
            if previous.get(src["name"]) == digest:
                archived = "unchanged"
            else:
                path = raw_dir / f"{src['name']}.{src['ext']}.gz"
                with gzip.open(path, "wb") as f:
                    f.write(body)
                archived = "True"
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

    def cell(value):
        return str(value).replace("|", "/") if str(value) else "-"

    lines = ["| source | status | bytes | saved | links found | error |", "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(
            f"| {r['name']} | {r['status']} | {r['bytes']} | {r['archived']} | {cell(r['data_links'])} | {cell(r['error'])} |"
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
