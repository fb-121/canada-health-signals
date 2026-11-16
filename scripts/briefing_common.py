"""Shared helpers for the briefing collectors. Standard library only.

Each collector writes the day's items to data/briefing/YYYY-MM-DD/<section>.json and keeps
what it has already reported under data/briefing/state/, so an item is reported once.

Date model (every item carries these, unknown stays None, never guessed):
  event_date      the underlying event: FDA decision date, or Form D first-sale date
  filing_date     when the filing was lodged (Form D, from EDGAR's daily index); None for FDA
  signed_date     date on the filer's signature (Form D)
  published_date  when the official source made it public, where the source says (Form D = filing_date)
  first_detected  the day this pipeline first saw it
  briefing_date   the day it appears in the briefing (same as first_detected)
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "briefing"
STATE = OUT / "state"
REPO = os.environ.get("GITHUB_REPOSITORY", "fb-121/canada-health-signals")
UA = f"CanadaHealthSignals/0.5 briefing (open-data research; +https://github.com/{REPO})"
SCHEMA = 2
TRACKED = ("headline", "evidence", "category", "ownership", "amount")  # changes here go to the correction log


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


# ---------- dates ----------

def pdate(s):
    """Parses 2026-10-23, 20261023 or 10/23/2026 into a date; anything else is None."""
    if isinstance(s, date):
        return s
    s = str(s or "").strip()
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s[:10] if fmt != "%Y%m%d" else s[:8], fmt).date()
        except ValueError:
            continue
    return None


def iso(d):
    d = pdate(d)
    return d.isoformat() if d else None


def form_d_deadline(first_sale):
    """Form D is due 15 calendar days after the first sale. A weekend deadline rolls to Monday.
    Federal holidays are not adjusted, so a filing one business day over may be on time."""
    d = pdate(first_sale)
    if not d:
        return None
    due = d + timedelta(days=15)
    while due.weekday() >= 5:
        due += timedelta(days=1)
    return due


def days_late(first_sale, filed):
    due, f = form_d_deadline(first_sale), pdate(filed)
    if not due or not f:
        return None
    return max(0, (f - due).days)


def recency(event, detected):
    """new: event within 14 days of detection. recent: 15 to 45. historical: older. None if unknown."""
    e, d = pdate(event), pdate(detected)
    if not e or not d:
        return None
    age = (d - e).days
    return "new" if age <= 14 else "recent" if age <= 45 else "historical"


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    s = re.sub(r"-(inc|llc|ltd|co|corp|corporation|limited|gmbh|sa|lp)$", "", s)
    return s or "unknown"


# ---------- state ----------

def load_seen(name):
    p = STATE / f"{name}.txt"
    return set(p.read_text().split()) if p.exists() else set()


def save_seen(name, seen):
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / f"{name}.txt").write_text("\n".join(sorted(seen)) + "\n")


def run_start(name):
    """The day this collector first ran. Items first detected that day are an initial backfill."""
    p = STATE / f"first_run_{name}.txt"
    if p.exists():
        return pdate(p.read_text().strip())
    STATE.mkdir(parents=True, exist_ok=True)
    p.write_text(today().isoformat() + "\n")
    return today()


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save_json(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def write_status(source, **facts):
    """Source freshness: one record per source, rewritten each run (data/briefing/status.json)."""
    path = OUT / "status.json"
    status = load_json(path, {})
    status[source] = {**facts, "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    save_json(path, status)


def note_update(it, kind, detail, on=None):
    """Records that an already-reported item gained material new evidence. The item keeps its
    first_detected date and counts as an update, never as a new clearance or financing event."""
    row = {"date": iso(on) or today().isoformat(), "kind": kind, "detail": detail}
    ups = it.setdefault("updates", [])
    if row not in ups:
        ups.append(row)


def log_correction(key, field, old, new, reason):
    """Append-only history of changes to something the page already said."""
    OUT.mkdir(parents=True, exist_ok=True)
    row = {"date": today().isoformat(), "key": key, "field": field, "old": old, "new": new, "reason": reason}
    with (OUT / "corrections.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---------- items ----------

def item(section, headline, detail, source_url, event_date, key, **facts):
    """One briefing item. why/watch stay empty until a reviewed analysis exists for it.
    facts are structured fields the page ranks and labels on."""
    d = today().isoformat()
    base = {"schema": SCHEMA, "section": section, "headline": headline, "detail": detail,
            "source_url": source_url, "event_date": iso(event_date), "key": key,
            "filing_date": None, "signed_date": None, "published_date": None,
            "first_detected": d, "briefing_date": d,
            "why": None, "watch": None}
    base.update(facts)
    base["recency"] = recency(base["event_date"], base["first_detected"])
    return base


def write_items(section, items, notes):
    """Writes this section's items. A record already stored in any of the last 8 days is never
    added a second time. If it was stored at an older schema it is upgraded in place, keeping its
    first_detected, and any change to a tracked field is recorded in the correction log."""
    files = {}   # path -> list of stored items, today's file first
    for n in range(0, 8):
        path = OUT / (today() - timedelta(days=n)).isoformat() / f"{section}.json"
        files[path] = load_json(path, [])
    index = {}
    for path, stored in files.items():
        for n, i in enumerate(stored):
            index.setdefault(i["key"], (path, n))
    today_path = OUT / today().isoformat() / f"{section}.json"
    added = upgraded = 0
    changed = set()
    for new in items:
        hit = index.get(new["key"])
        if hit is None:
            files[today_path].append(new)
            index[new["key"]] = (today_path, len(files[today_path]) - 1)
            changed.add(today_path)
            added += 1
            notes.append(f"NEW: {new['headline']}")
            continue
        path, n = hit
        old = files[path][n]
        if old.get("schema", 1) < new.get("schema", 1):
            for f in TRACKED:
                if old.get(f) != new.get(f) and old.get(f) is not None:
                    log_correction(new["key"], f, old.get(f), new.get(f), "schema upgrade, re-derived from the official record")
            new["first_detected"] = old.get("first_detected") or new["first_detected"]
            new["briefing_date"] = old.get("briefing_date") or new["briefing_date"]
            new["recency"] = recency(new["event_date"], new["first_detected"])
            if old.get("updates"):
                new["updates"] = old["updates"]
            files[path][n] = new
            changed.add(path)
            upgraded += 1
            notes.append(f"UPGRADED: {new['headline']}")
    for path in changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(files[path], indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if upgraded:
        notes.append(f"{upgraded} stored items upgraded to schema {SCHEMA}")
    text = "\n".join(f"- {n}" for n in notes)
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"## Briefing: {section}\n\n{text}\n")
    return added, upgraded
