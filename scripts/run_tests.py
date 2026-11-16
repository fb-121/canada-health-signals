#!/usr/bin/env python3
"""Runs the fixture unit tests and records the result in data/briefing/tests.json.

These tests use reconstructed records and make no network requests. A pass here says the logic is
right on those fixtures. It says nothing about whether SEC, openFDA or FDA's document server work
today. That is what the per-source "live" state in status.json is for.
"""
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))


def main():
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    res = unittest.TextTestRunner(verbosity=1).run(suite)
    rec = {"kind": "fixture unit tests, no network", "ran": res.testsRun, "failures": len(res.failures),
           "errors": len(res.errors), "passed": res.testsRun - len(res.failures) - len(res.errors),
           "ran_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")}
    out = ROOT / "data" / "briefing" / "tests.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(rec))
    return 0 if res.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
