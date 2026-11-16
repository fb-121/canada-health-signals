#!/usr/bin/env python3
"""Records whether today's briefing build succeeded, and stops an old briefing passing for today's.

Run by the workflow after every other step, with each step's outcome in the environment:
  critical  TESTS (fixture unit tests), BUILD (docs/briefing.* written)
  optional  PROBE, AI_EVIDENCE, RULES, MONEY, SITE, AI_PAGE (source collection and the older pages)

Critical success: data/briefing/build_state.json says ok, and verify_live.py later checks the public copies.
Critical failure: the workflow has already restored docs/briefing.* to the last good build. This script
then marks those files, at the top, as an earlier briefing that is not today's, and writes the failure into
docs/status.json, so neither the page nor the status file can be read as current. The job then fails.
Optional failures never block publishing. They are listed, and each source's own live state shows them.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CRITICAL = ("TESTS", "BUILD")
OPTIONAL = ("PROBE", "AI_EVIDENCE", "RULES", "MONEY", "SITE", "AI_PAGE")
MARK = "<!--build-failed-->"


def state_from_env(env, now):
    crit = {k.lower(): env.get(k, "unknown") for k in CRITICAL}
    opt = {k.lower(): env.get(k, "unknown") for k in OPTIONAL}
    ok = all(v == "success" for v in crit.values())
    run = (f"{env.get('GITHUB_SERVER_URL', 'https://github.com')}/{env.get('GITHUB_REPOSITORY')}/actions/runs/"
           f"{env.get('GITHUB_RUN_ID')}") if env.get("GITHUB_RUN_ID") else None
    return {"status": "ok" if ok else "failed", "run_utc": now.strftime("%Y-%m-%dT%H:%MZ"), "run_url": run,
            "critical": crit, "optional_collection": opt,
            "optional_failed": sorted(k for k, v in opt.items() if v not in ("success", "skipped", "unknown"))}


def mark_stale(docs, state):
    """Puts a not-current notice at the top of the restored, earlier briefing. Idempotent."""
    try:
        old = json.loads((docs / "briefing.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        old = {}
    gen = (old.get("build") or {}).get("generated_utc") or old.get("generated_utc") or "an earlier run"
    why = ", ".join(f"{k} {v}" for k, v in state["critical"].items() if v != "success")
    note = (f"The briefing build failed ({why}) at {state['run_utc']}. What follows is the earlier briefing generated "
            f"{gen}, not the one this run should have produced.")
    state["published"] = {"is_current": False, "shown_briefing_generated_utc": gen,
                          "shown_content_id": (old.get("build") or {}).get("content_id")}
    if old:
        old["build_failed"] = {"notice": note, **state}
        (docs / "briefing.json").write_text(json.dumps(old, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    md = docs / "briefing.md"
    if md.exists() and MARK not in md.read_text(encoding="utf-8"):
        md.write_text(f"{MARK}\n> **NOT CURRENT.** {note}\n\n" + md.read_text(encoding="utf-8"), encoding="utf-8")
    page = docs / "briefing.html"
    if page.exists():
        text = page.read_text(encoding="utf-8")
        if MARK not in text and '<main class="wrap">' in text:
            banner = (f'<main class="wrap">{MARK}<p class="empty" role="alert" style="border-style:solid;'
                      f'color:var(--warn);background:var(--warn-bg)"><b>Not current.</b> {note}</p>')
            page.write_text(text.replace('<main class="wrap">', banner, 1), encoding="utf-8")
    return note


SOURCE_STEPS = {"RULES": ("openfda_510k", "fda_ai_device_list"), "MONEY": ("sec_form_d",)}


def mark_failed_sources(env, root=ROOT):
    """Run before the build. A collection step that crashed never wrote its own status, so the source would
    still show the last run's live state. This marks those sources failed for this run, keeping their old
    check time, so a crash cannot pass as a successful source check."""
    path = root / "data" / "briefing" / "status.json"
    try:
        status = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        status = {}
    marked = []
    for step, sources in SOURCE_STEPS.items():
        if env.get(step) not in ("failure", "cancelled"):
            continue
        for src in sources:
            s = status.setdefault(src, {})
            s["live"] = "failed"
            s["live_detail"] = (f"collection step failed this run; figures are from the last completed check "
                                f"({s.get('checked_at', 'none')})")
            marked.append(src)
    if marked:
        path.write_text(json.dumps(status, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        print("- marked failed this run: " + ", ".join(marked))
    return marked


def main(env=os.environ, root=ROOT, now=None):
    now = now or datetime.now(timezone.utc)
    state = state_from_env(env, now)
    docs, data = root / "docs", root / "data" / "briefing"
    if state["status"] == "ok":
        b = json.loads((docs / "briefing.json").read_text(encoding="utf-8")).get("build", {})
        state["published"] = {"is_current": True, "generated_utc": b.get("generated_utc"), "content_id": b.get("content_id")}
        print(f"- critical steps passed; build {b.get('content_id')} generated {b.get('generated_utc')}")
    else:
        print("- CRITICAL FAILURE: " + mark_stale(docs, state))
        status_path = docs / "status.json"
        try:
            status = json.loads(status_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            status = {}
        status.update({"checked_utc": state["run_utc"], "build": state,
                       "public_copies": {"not_checked": "today's build failed; the public briefing is an earlier one, marked not current"}})
        status_path.write_text(json.dumps(status, indent=1) + "\n", encoding="utf-8")
    if state["optional_failed"]:
        print("- optional steps failed (publishing not blocked): " + ", ".join(state["optional_failed"]))
    data.mkdir(parents=True, exist_ok=True)
    (data / "build_state.json").write_text(json.dumps(state, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    if "--sources" in sys.argv:
        mark_failed_sources(os.environ)
        sys.exit(0)
    sys.exit(main())
