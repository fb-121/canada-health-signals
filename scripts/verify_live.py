#!/usr/bin/env python3
"""Live integration check of the public outputs, and the public status file.

For each public file it fetches two ways:
  canonical  the exact URL a reader uses, no query string, so it sees what caches serve
  busted     the same URL with a cache-busting query, so it sees what the origin serves
and reads the schema version, content id and generation time stamped into the file. If the busted copy
matches the build and the canonical copy does not, the difference is an intermediary cache. If neither
matches after WAIT_MINUTES, it is a deployment problem. Cache headers are recorded for both.

It then writes docs/status.json: fixture unit test results, the live state of each source, and this
check, kept apart so a passing test suite is never read as proof that live sources or public files work.
Exit code 1 when any copy is wrong after the wait.
"""
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = os.environ.get("GITHUB_REPOSITORY", "fb-121/canada-health-signals")
OWNER, NAME = REPO.split("/")
PAGES = f"https://{OWNER}.github.io/{NAME}"
RAW = f"https://raw.githubusercontent.com/{REPO}/main/docs"
WAIT_MINUTES = 12
UA = f"CanadaHealthSignals/0.5 live-check (+https://github.com/{REPO})"
KEEP = ("cache-control", "age", "x-cache", "last-modified", "etag", "expires", "x-served-by")


def fetch(url, bust):
    full = f"{url}?cb={int(time.time())}" if bust else url
    headers = {"User-Agent": UA}
    if bust:
        headers["Cache-Control"] = "no-cache"
    try:
        with urllib.request.urlopen(urllib.request.Request(full, headers=headers), timeout=40) as r:
            h = {k: r.headers.get(k) for k in KEEP if r.headers.get(k)}
            return r.status, r.read().decode("utf-8", "replace"), h
    except Exception as ex:
        return 0, f"{type(ex).__name__}: {ex}"[:150], {}


def stamp(kind, text):
    """(schema, content_id, generated) as stamped in the file, or Nones."""
    try:
        if kind == "json":
            d = json.loads(text)
            b = d.get("build") or {}
            return d.get("schema_version"), b.get("content_id"), b.get("generated_utc")
        m = re.search(r"content id (\w+), schema (\d+)[^\n]*?generated (\S+?)[,.]", text) if kind == "md" else \
            re.search(r'data-content-id="(\w+)" data-schema="(\d+)"[^<]*?generated (\S+?)[,.]', text)
        return (int(m.group(2)), m.group(1), m.group(3)) if m else (None, None, None)
    except ValueError:
        return None, None, None


def check(targets, want):
    results = {}
    pending = [(n, u, k, b) for n, u, k in targets for b in (False, True)]
    deadline = time.time() + WAIT_MINUTES * 60
    while pending:
        still = []
        for name, url, kind, bust in pending:
            status, text, headers = fetch(url, bust)
            got = stamp(kind, text) if status == 200 else (None, None, None)
            ok = status == 200 and got == want
            results[(name, "busted" if bust else "canonical")] = {
                "url": url, "http": status, "schema": got[0], "content_id": got[1], "generated_utc": got[2],
                "ok": ok, "headers": headers, "error": "" if status == 200 else text}
            if not ok:
                still.append((name, url, kind, bust))
        pending = still
        if pending and time.time() < deadline:
            time.sleep(45)
        else:
            break
    return results


def diagnose(results, name):
    c, b = results[(name, "canonical")], results[(name, "busted")]
    if c["ok"] and b["ok"]:
        return "current"
    if b["ok"]:
        return "intermediary cache (origin is current, the canonical URL is not yet)"
    return "deployment problem (the origin itself does not serve this build)"


def main():
    local = json.loads((ROOT / "docs" / "briefing.json").read_text(encoding="utf-8"))
    want = (local["schema_version"], local["build"]["content_id"], local["build"]["generated_utc"])
    targets = [("pages json", f"{PAGES}/briefing.json", "json"), ("pages md", f"{PAGES}/briefing.md", "md"),
               ("pages html", f"{PAGES}/briefing.html", "html"), ("raw json", f"{RAW}/briefing.json", "json"),
               ("raw md", f"{RAW}/briefing.md", "md")]
    results = check(targets, want)
    verdicts = {n: diagnose(results, n) for n, _, _ in targets}
    lines = [f"Expected schema {want[0]}, content id {want[1]}, generated {want[2]}", ""]
    for n, _, _ in targets:
        c, b = results[(n, "canonical")], results[(n, "busted")]
        lines.append(f"- {n}: {verdicts[n]}. canonical: {c['content_id']} {c['generated_utc']} "
                     f"(age {c['headers'].get('age', '?')}, {c['headers'].get('cache-control', '?')}); "
                     f"busted: {b['content_id']} {b['generated_utc']}")
    text = "\n".join(lines)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("## Live output check\n\n" + text + "\n")

    data = ROOT / "data" / "briefing"
    load = lambda p, d: json.loads(p.read_text(encoding="utf-8")) if p.exists() else d
    sources = load(data / "status.json", {})
    status = {
        "checked_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "build_checked": {"schema_version": want[0], "content_id": want[1], "generated_utc": want[2]},
        "fixture_unit_tests": {**(load(data / "tests.json", {}) or {}),
                               "meaning": "Logic checked on reconstructed records with no network. Says nothing about live sources."},
        "live_sources": {k: {f: v.get(f) for f in ("live", "live_detail", "checked_at")} for k, v in sources.items()},
        "public_copies": {n: {"verdict": verdicts[n],
                              "canonical": {k: results[(n, "canonical")][k] for k in ("url", "http", "content_id", "generated_utc", "headers")},
                              "origin": {k: results[(n, "busted")][k] for k in ("http", "content_id", "generated_utc")}}
                          for n, _, _ in targets},
        "note": "Pages caches for up to 10 minutes and the raw host for 5. A canonical copy may lag the origin by that much.",
    }
    (ROOT / "docs" / "status.json").write_text(json.dumps(status, indent=1) + "\n", encoding="utf-8")
    return 0 if all(r["ok"] for r in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
