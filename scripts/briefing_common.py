"""Shared helpers for the briefing collectors. Standard library only.

Each collector writes the day's items to data/briefing/YYYY-MM-DD/<section>.json and keeps
what it has already reported under data/briefing/state/, so an item is reported once.
"""
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "briefing"
STATE = OUT / "state"
REPO = os.environ.get("GITHUB_REPOSITORY", "fb-121/canada-health-signals")
UA = f"CanadaHealthSignals/0.4 briefing (open-data research; +https://github.com/{REPO})"


def today():
    return datetime.now(timezone.utc).date()


def get(url, ua=UA, limit=50_000_000, pause=0.0):
    """Returns (status, body bytes, error text). Never raises."""
    if pause:
        time.sleep(pause)
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read(limit + 1), ""
    except urllib.error.HTTPError as e:
        return e.code, b"", f"HTTP {e.code}"
    except Exception as e:
        return 0, b"", f"{type(e).__name__}: {e}"[:160]


def load_seen(name):
    p = STATE / f"{name}.txt"
    return set(p.read_text().split()) if p.exists() else set()


def save_seen(name, seen):
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / f"{name}.txt").write_text("\n".join(sorted(seen)) + "\n")


def item(section, headline, detail, source_url, event_date, key):
    """One briefing item. 'why' stays empty until the why-line step exists."""
    return {"section": section, "headline": headline, "detail": detail,
            "source_url": source_url, "event_date": event_date, "key": key, "why": None}


def write_items(section, items, notes):
    """Appends to today's file for this section (a re-run the same day never drops items)."""
    day = OUT / today().isoformat()
    day.mkdir(parents=True, exist_ok=True)
    path = day / f"{section}.json"
    existing = json.loads(path.read_text()) if path.exists() else []
    keys = {i["key"] for i in existing}
    merged = existing + [i for i in items if i["key"] not in keys]
    if merged:
        path.write_text(json.dumps(merged, indent=1, ensure_ascii=False) + "\n")
    text = "\n".join(f"- {n}" for n in notes)
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"## Briefing: {section}\n\n{text}\n")
