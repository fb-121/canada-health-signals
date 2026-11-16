"""Reliability tests: manual reviews, resurfacing, freshness, live versus unit status, access diagnosis.
Run: python -m unittest discover -s tests -v   (no network)"""
import json
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import briefing_common as bc          # noqa: E402
import briefing_docs as docs          # noqa: E402
import briefing_reviews as rv         # noqa: E402
import build_briefing as page         # noqa: E402
import fda_probe as probe             # noqa: E402
from datetime import datetime, timezone

REAL_WINDOW = bc.fda_window_open   # captured before any test replaces it


def rule(key="510k:K9", ev="inferred", **kw):
    base = bc.item("rules", "FDA clears X", "d", "https://x", "2026-11-01", key, evidence=ev,
                   record_id=key.split(":")[1], company_id="fda:x", company="X", **kw)
    return base


REVIEW = {"K9": {"status": "document_supported", "subject": "AI functionality", "claim": "Summary says AI-assisted.",
                 "document_url": "https://www.accessdata.fda.gov/cdrh_docs/pdf26/K9.pdf",
                 "evidence": [{"quote": "an AI-assisted tool", "page": 3, "page_basis": "tool-reported"}],
                 "reviewed_on": "2026-11-16", "reviewer": "Claude via fetch", "independent": False}}


class RealFiles(unittest.TestCase):
    def test_shipped_reviews_are_complete(self):
        reviews = rv.load(ROOT / "data" / "briefing" / "reviews.json")
        self.assertIn("K261679", reviews)
        self.assertEqual(rv.validate(reviews), [])
        r = reviews["K261679"]
        self.assertFalse(r["independent"])
        self.assertFalse(r["verbatim_checked"])      # must stay false until a person compares with the PDF
        self.assertTrue(r["caveats"])
        self.assertEqual(r["status"], "document_supported")   # not human verified until a person checks the PDF

    def test_human_verified_requires_a_person_and_a_verbatim_check(self):
        hv = {"K9": dict(REVIEW["K9"], status="human_verified")}
        problems = " | ".join(rv.validate(hv))
        self.assertIn("verbatim_checked", problems)
        self.assertIn("verified_by", problems)
        ok = {"K9": dict(REVIEW["K9"], status="human_verified", verbatim_checked=True, verified_by="Faaiz", verified_on="2026-11-17")}
        self.assertEqual(rv.validate(ok), [])

    def test_pending_review_is_shown_as_pending_not_verified(self):
        it = rule()
        rv.apply(it, REVIEW)
        html = page.chips(it) + page.review_html(it)
        self.assertIn("human check pending", html)
        self.assertIn("Human verification pending", html)

    def test_known_issues_have_what_the_page_needs(self):
        issues = json.loads((ROOT / "data" / "briefing" / "known_issues.json").read_text())
        ids = [x["id"] for x in issues]
        self.assertEqual(len(ids), len(set(ids)))
        for x in issues:
            for f in ("id", "opened", "severity", "area", "status", "text"):
                self.assertTrue(x.get(f), f"{x.get('id')}: {f}")


class Reviews(unittest.TestCase):
    def test_review_overrides_class_and_records_an_update(self):
        it = rule()
        self.assertTrue(rv.apply(it, REVIEW))
        self.assertEqual(it["evidence"], "document_verified")
        self.assertEqual(it["evidence_source"], "manual review")
        self.assertEqual(it["updates"][0]["kind"], "manual_review")
        rv.apply(it, REVIEW)
        self.assertEqual(len(it["updates"]), 1)           # applying twice does not duplicate

    def test_fda_listed_is_never_changed_and_rejected_means_unknown(self):
        listed = rule(ev="fda_listed")
        rv.apply(listed, REVIEW)
        self.assertEqual(listed["evidence"], "fda_listed")
        rej = dict(REVIEW["K9"], status="rejected")
        it = rule()
        rv.apply(it, {"K9": rej})
        self.assertEqual(it["evidence"], "unknown")
        inc = rule()
        rv.apply(inc, {"K9": dict(REVIEW["K9"], status="inconclusive")})
        self.assertEqual(inc["evidence"], "inferred")

    def test_review_survives_a_later_automated_document_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            bc.OUT = docs.OUT = Path(tmp)
            docs.REVIEWS_PATH = Path(tmp) / "reviews.json"
            docs.REVIEWS_PATH.write_text(json.dumps(REVIEW))
            it = rule()
            note = docs.apply_to_item(it, {"status": "read", "ai_language": False})
            self.assertIsNone(note)                      # automation would have said unknown; the review wins
            self.assertEqual(it["evidence"], "inferred")  # untouched here, and the build overlays the review
            page.DATA = Path(tmp)
            (Path(tmp) / bc.today().isoformat()).mkdir()
            (Path(tmp) / bc.today().isoformat() / "rules.json").write_text(json.dumps([it]))
            out = page.load_day(bc.today())
            self.assertEqual(out[0]["evidence"], "document_verified")
            self.assertEqual(out[0]["review"]["status"], "document_supported")
            self.assertEqual(out[0]["verification_status"], "human check pending")

    def test_review_survives_schema_upgrade_rewrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            bc.OUT = page.DATA = Path(tmp)
            (Path(tmp) / "reviews.json").write_text(json.dumps(REVIEW))
            day = Path(tmp) / bc.today().isoformat()
            day.mkdir()
            (day / "rules.json").write_text(json.dumps([{"key": "510k:K9", "section": "rules", "headline": "old",
                                                         "detail": "", "record_id": "K9", "first_detected": "2026-11-15"}]))
            bc.write_items("rules", [rule()], [])      # automated re-derivation says "inferred"
            out = page.load_day(bc.today())
            self.assertEqual(out[0]["evidence"], "document_verified")

    def test_validation_catches_weak_reviews(self):
        bad = {"K1": dict(REVIEW["K9"], document_url="https://example.com/x.pdf",
                          evidence=[{"quote": "word " * 31, "page": None}], reviewed_on="soon")}
        problems = " | ".join(rv.validate(bad))
        for needle in ("official host", "over 30 words", "no page and no note", "not a date"):
            self.assertIn(needle, problems)
        self.assertTrue(any("with no evidence" in p or "missing evidence" in p
                            for p in rv.validate({"K2": dict(REVIEW["K9"], evidence=[])})))


class Resurfacing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        bc.OUT = page.DATA = Path(self.tmp.name)
        self.today = bc.today()

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, days_ago, items):
        d = Path(self.tmp.name) / (self.today - timedelta(days=days_ago)).isoformat()
        d.mkdir(parents=True, exist_ok=True)
        (d / "rules.json").write_text(json.dumps(items))

    def test_old_record_with_new_evidence_resurfaces_as_update_only(self):
        it = rule()
        bc.note_update(it, "document_read", "FDA 510(k) summary read: evidence inferred to document_verified")
        self.put(1, [it])
        recs = page.updated_records(self.today)
        self.assertEqual(len(recs), 1)
        html = page.build(datetime.now(timezone.utc))
        self.assertIn("Updated records", html)
        self.assertIn("Update, not a new event", html)
        self.assertNotIn("<b>1</b> FDA clearances", html)   # not counted as a new clearance

    def test_stale_updates_and_todays_new_records_do_not_resurface(self):
        old = rule("510k:K1")
        bc.note_update(old, "document_read", "x", on=self.today - timedelta(days=5))
        new = rule("510k:K2")
        bc.note_update(new, "document_read", "y")
        self.put(2, [old])
        self.put(0, [new])
        self.assertEqual(page.updated_records(self.today), [])

    def test_amendments_are_counted_separately_from_new_financings(self):
        base = dict(company_id="cik:1", company="A", category="equity round", filing_date="2026-11-10", amount=5e6,
                    offering=6e6, record_id="D1", ownership="no listing found")
        new = bc.item("money", "A reports $5.0M sold", "d", "https://x", "2026-11-05", "formd:1", kind="new offering", **base)
        upd = bc.item("money", "A amended its offering", "d", "https://x", "2026-11-05", "formd:2", kind="update",
                      **dict(base, record_id="D2"))
        d = Path(self.tmp.name) / self.today.isoformat()
        d.mkdir(parents=True)
        (d / "money.json").write_text(json.dumps([new, upd]))
        html = page.build(datetime.now(timezone.utc))
        self.assertIn("<b>1</b> new financing filings", html)
        self.assertIn("<b>1</b> amendments to earlier offerings", html)

    def test_content_id_changes_when_evidence_changes(self):
        self.put(0, [rule()])
        a = page.content_id(self.today)
        self.assertEqual(a, page.content_id(self.today))
        self.put(0, [rule(ev="document_verified")])
        self.assertNotEqual(a, page.content_id(self.today))


class FreshnessAndLive(unittest.TestCase):
    NOW = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)

    def status(self, newest, ran, live="ok"):
        return {"sec_form_d": {"latest_index_date": newest, "checked_at": ran, "live": live, "live_detail": "detail here"}}

    def test_source_stale_is_not_pipeline_stale(self):
        html = page.freshness_html(self.status("2026-11-01", "2026-11-16T11:00Z"), self.NOW)
        self.assertIn("(source stale)", html)
        self.assertNotIn("(pipeline stale)", html)

    def test_pipeline_stale_is_not_source_stale(self):
        html = page.freshness_html(self.status("2026-11-15", "2026-11-10T11:00Z"), self.NOW)
        self.assertIn("(pipeline stale)", html)
        self.assertNotIn("(source stale)", html)

    def test_unit_tests_passing_is_stated_as_not_proving_live_access(self):
        st = self.status("2026-11-15", "2026-11-16T11:00Z", live="failed")
        html = page.freshness_html(st, self.NOW, {"passed": 40, "ran": 40, "ran_at": "2026-11-16T11:00Z"})
        self.assertIn("40 of 40 passed", html)
        self.assertIn("does not say any source is reachable", html)
        self.assertIn("failed", html)

    def test_download_failures_set_live_failed_even_though_nothing_crashed(self):
        with tempfile.TemporaryDirectory() as tmp:
            bc.OUT = docs.OUT = Path(tmp)
            docs.REVIEWS_PATH = Path(tmp) / "reviews.json"
            docs.PAUSE = 0
            day = Path(tmp) / bc.today().isoformat()
            day.mkdir()
            it = rule()
            it.update(source="openFDA 510(k)", summary_available=True)
            (day / "rules.json").write_text(json.dumps([it]))
            docs.get = lambda *a, **k: (404, b"", "HTTP 404")
            bc.fda_window_open = lambda now=None: True
            docs.main()
            st = json.loads((Path(tmp) / "status.json").read_text())["fda_510k_summaries"]
            self.assertEqual(st["live"], "failed")
            self.assertEqual(st["failed"], 1)
            self.assertIn("HTTP 404", st["live_detail"])


class AccessDiagnosis(unittest.TestCase):
    def chain(self, status=None, body="", error=None, pdf=False):
        return [{"url": "u", "status": status, "error": error, "headers": {}, "body_start": body, "is_pdf": pdf}]

    def test_boxes(self):
        c = probe.classify
        self.assertEqual(c(self.chain(200, pdf=True)), "ok")
        self.assertEqual(c(self.chain(404, "Page not found")), "url_error")
        self.assertEqual(c(self.chain(403, "Access Denied")), "access_restriction")
        self.assertEqual(c(self.chain(200, "Request blocked: automated access")), "access_restriction")
        self.assertEqual(c(self.chain(error="TimeoutError")), "network_restriction")
        self.assertEqual(c(self.chain(500, "oops")), "unclear")

    def test_redirect_into_an_abuse_detection_page_is_a_confirmed_restriction(self):
        chain = [{"url": "https://www.accessdata.fda.gov/cdrh_docs/pdf26/K1.pdf", "status": 302, "error": None,
                  "headers": {"location": "/apology_objects/abuse-detection-apology.html"}, "body_start": ""},
                 {"url": "https://www.accessdata.fda.gov/apology_objects/abuse-detection-apology.html", "status": 404,
                  "error": None, "headers": {}, "body_start": "FDA Apology", "is_pdf": False}]
        self.assertEqual(probe.classify(chain), "access_restriction")


class BlockedReading(unittest.TestCase):
    def test_no_download_is_attempted_while_fda_blocks_scripts(self):
        with tempfile.TemporaryDirectory() as tmp:
            bc.OUT = docs.OUT = Path(tmp)
            docs.REVIEWS_PATH = Path(tmp) / "reviews.json"
            (Path(tmp) / "diagnostics").mkdir()
            (Path(tmp) / "diagnostics" / "fda_access.json").write_text(json.dumps({"verdict": "access_restriction"}))
            day = Path(tmp) / bc.today().isoformat()
            day.mkdir()
            it = rule()
            it.update(source="openFDA 510(k)", summary_available=True)
            (day / "rules.json").write_text(json.dumps([it]))
            calls = []
            bc.fda_window_open = lambda now=None: True
            docs.get = lambda *a, **k: calls.append(a) or (200, b"", "")
            docs.main()
            self.assertEqual(calls, [])
            st = json.loads((Path(tmp) / "status.json").read_text())["fda_510k_summaries"]
            self.assertEqual(st["live"], "blocked")


class VisitingHours(unittest.TestCase):
    def test_window_is_inside_both_eastern_readings(self):
        at = lambda h: REAL_WINDOW(datetime(2026, 11, 16, h, 30, tzinfo=timezone.utc))
        self.assertEqual([h for h in range(24) if at(h)], [4, 5, 6, 7, 8])

    def test_nothing_is_sent_to_fda_outside_the_window(self):
        bc.fda_window_open = lambda now=None: False
        calls = []
        probe.hop = lambda *a, **k: calls.append(a) or {}
        docs.get = lambda *a, **k: calls.append(a) or (200, b"", "")
        self.assertEqual(probe.main(), 0)
        self.assertEqual(docs.main(), 0)
        self.assertEqual(calls, [])


class CorrectionHistory(unittest.TestCase):
    def test_log_is_append_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            bc.OUT = Path(tmp)
            bc.log_correction("k", "evidence", "a", "b", "r1")
            bc.log_correction("k", "evidence", "b", "c", "r2")
            rows = (Path(tmp) / "corrections.jsonl").read_text().splitlines()
            self.assertEqual([json.loads(r)["reason"] for r in rows], ["r1", "r2"])


if __name__ == "__main__":
    unittest.main()
