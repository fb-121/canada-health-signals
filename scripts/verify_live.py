#!/usr/bin/env python3
"""Checks that the public copies of the briefing are the ones this run just built.

For each public URL (GitHub Pages and the raw file host) it fetches with a cache-busting query, reads
the schema version and content id stamped into the file, and compares them with docs/ in the checkout.
Pages and the raw host cache for several minutes, so it retries for up to WAIT_MINUTES before it calls a
copy stale. A stale or mismatching copy fails the job, which is the point: a green data job must not hide
a public file that still shows an older version.
"""
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = os.environ.get("GITHUB_REPOSITORY", "fb-121/canada-health-signals")
PAGES = f"https://{REPO.split('/')[0]}.github.io/{REPO.split('/')[1]}"
RAW = f"https://raw.githubusercontent.com/{REPO}/main/docs"
WAIT_MINUTES = 12
UA = f"CanadaHealthSignals/0.5 live-check (+https://github.com/{REPO})"


def fetch(url):
    req = urllib.request.Request(f"{url}?cb={int(time.time())}", headers={"User-Agent": UA, "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception as ex:
        return 0, f"{type(ex).__name__}: {ex}"[:150]


def stamp(kind, text):
    """Returns (schema, content_id, records_today) as stamped in the file, or Nones."""
    try:
        if kind == "json":
            b = json.loads(text).get("build", {})
            return json.loads(text).get("schema_version"), b.get("content_id"), b.get("records_today")
        if kind == "md":
            m = re.search(r"content id (\w+), schema (\d+)", text)
            return (int(m.group(2)), m.group(1), None) if m else (None, None, None)
        m = re.search(r'data-content-id="(\w+)" data-schema="(\d+)"', text)
        return (int(m.group(2)), m.group(1), None) if m else (None, None, None)
    except ValueError:
        return None, None, None


def main():
    local = json.loads((ROOT / "docs" / "briefing.json").read_text(encoding="utf-8"))
    want = (local["schema_version"], local["build"]["content_id"])
    targets = [("pages json", f"{PAGES}/briefing.json", "json"), ("pages md", f"{PAGES}/briefing.md", "md"),
               ("pages html", f"{PAGES}/briefing.html", "html"), ("raw json", f"{RAW}/briefing.json", "json"),
               ("raw md", f"{RAW}/briefing.md", "md")]
    deadline = time.time() + WAIT_MINUTES * 60
    results, pending = {}, list(targets)
    while pending:
        still = []
        for name, url, kind in pending:
            status, text = fetch(url)
            schema, cid, n = stamp(kind, text) if status == 200 else (None, None, None)
            ok = status == 200 and (schema, cid) == want
            results[name] = {"url": url, "http": status, "schema": schema, "content_id": cid, "ok": ok,
                             "note": "" if status == 200 else text}
            if not ok:
                still.append((name, url, kind))
        pending = still
        if pending and time.time() < deadline:
            time.sleep(45)
        else:
            break
    lines = [f"Expected schema {want[0]}, content id {want[1]} (from docs/briefing.json, generated {local['build']['generated_utc']})", ""]
    for name, r in results.items():
        lines.append(f"- {name}: {'MATCH' if r['ok'] else 'MISMATCH'} (http {r['http']}, schema {r['schema']}, content id {r['content_id']}) {r['note']}")
    text = "\n".join(lines)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("## Live output check\n\n" + text + "\n")
    return 0 if all(r["ok"] for r in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
