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
import build_state                    # noqa: E402
import briefing_money as money        # noqa: E402
from datetime import datetime, timezone

import email.message
import urllib.error


class _Resp:
    def __init__(self, status, body=b""):
        self.status, self._b = status, body

    def read(self, n=-1):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_open(calls, plan):
    """Stands in for one HTTP request with redirects not followed. plan: (status, Location) per request."""
    def _o(url, ua, timeout=60):
        calls.append(url)
        st, loc = plan[min(len(calls) - 1, len(plan) - 1)]
        if st == 200:
            return _Resp(200, b"%PDF-1.4")
        h = email.message.Message()
        if loc:
            h["Location"] = loc
        raise urllib.error.HTTPError(url, st, "x", h, None)
    return _o


REAL_WINDOW = bc.fda_window_open   # captured before any test replaces it
bc.FDA_CLOCK = Path(tempfile.mkdtemp()) / "fda_clock"   # never share the real runner clock with tests
bc._sleep = lambda s: None


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
            bc._open = fake_open([], [(404, None)])
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
            bc._open = fake_open(calls, [(200, None)])
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
        bc._open = fake_open(calls, [(200, None)])
        self.assertEqual(probe.main(), 0)
        self.assertEqual(docs.main(), 0)
        self.assertEqual(calls, [])


class FDARequestGate(unittest.TestCase):
    def setUp(self):
        self.t = [1000.0]
        self.slept = []
        bc._now = lambda: self.t[0]
        bc._sleep = lambda s: (self.slept.append(round(s, 3)), self.t.__setitem__(0, self.t[0] + s))
        bc.FDA_CLOCK = Path(tempfile.mkdtemp()) / "clock"
        bc.fda_window_open = lambda now=None: True

    def tearDown(self):
        import time as _t
        bc._now = _t.time
        bc._sleep = lambda s: None

    def test_spacing_is_measured_from_the_end_of_the_previous_request(self):
        bc.fda_gate()
        self.t[0] += 5          # the request itself takes 5 s
        bc.fda_done()
        bc.fda_gate()
        self.assertEqual(self.slept, [30.0])

    def test_first_request_of_a_second_script_still_waits(self):
        bc.fda_gate(); bc.fda_done()             # last request of the probe
        self.t[0] += 12
        bc.fda_gate()                            # first request of the reader, a separate process sharing the clock file
        self.assertEqual(self.slept, [18.0])

    def test_hours_are_checked_after_the_wait_before_each_request(self):
        bc.fda_gate(); bc.fda_done()
        bc.fda_window_open = lambda now=None: False     # 09:00 UTC passed while waiting
        with self.assertRaises(bc.FDAWindowClosed):
            bc.fda_gate()

    def test_probe_sends_nothing_when_the_gate_closes(self):
        bc.fda_window_open = lambda now=None: False
        rec = probe.hop("https://www.accessdata.fda.gov/cdrh_docs/pdf26/K1.pdf")
        self.assertTrue(rec["not_sent"])
        self.assertIsNone(rec["status"])

    def test_reader_stops_when_hours_end_mid_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            bc.OUT = docs.OUT = Path(tmp)
            docs.REVIEWS_PATH = Path(tmp) / "reviews.json"
            day = Path(tmp) / bc.today().isoformat()
            day.mkdir()
            its = []
            for n in (1, 2, 3):
                it = rule(f"510k:K{n}")
                it.update(source="openFDA 510(k)", summary_available=True)
                its.append(it)
            (day / "rules.json").write_text(json.dumps(its))
            opens = iter([True, True, True, False, False, False])   # start check, gate 1, gate 2, then closed
            bc.fda_window_open = lambda now=None: next(opens)
            calls = []
            bc._open = fake_open(calls, [(404, None)])
            docs.main()
            self.assertEqual(len(calls), 2)
            self.assertEqual(self.slept, [30.0, 30.0])   # waited before request 2, and before the refused third


class BuildReliability(unittest.TestCase):
    def setup_docs(self, tmp):
        docs = Path(tmp) / "docs"
        docs.mkdir()
        (docs / "briefing.json").write_text(json.dumps({"schema_version": 2, "build": {"generated_utc": "2026-11-16T11:20Z", "content_id": "abc"}}))
        (docs / "briefing.md").write_text("# Brief\n")
        (docs / "briefing.html").write_text('<main class="wrap"><h1>Brief</h1></main>')
        (docs / "status.json").write_text(json.dumps({"public_copies": {"pages json": {"verdict": "current"}}}))
        return docs

    ENV_OK = {"TESTS": "success", "BUILD": "success", "PROBE": "success", "RULES": "failure", "MONEY": "success"}

    def test_failed_tests_mark_the_old_briefing_not_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs = self.setup_docs(tmp)
            env = dict(self.ENV_OK, TESTS="failure", BUILD="skipped")
            build_state.main(env, Path(tmp), datetime(2026, 11, 17, 11, 25, tzinfo=timezone.utc))
            self.assertIn("Not current.", (docs / "briefing.html").read_text())
            self.assertIn("NOT CURRENT", (docs / "briefing.md").read_text())
            j = json.loads((docs / "briefing.json").read_text())
            self.assertFalse(j["build_failed"]["published"]["is_current"])
            st = json.loads((docs / "status.json").read_text())
            self.assertEqual(st["build"]["status"], "failed")
            self.assertNotIn("pages json", st["public_copies"])       # no stale "current" verdict survives
            build_state.main(env, Path(tmp), datetime(2026, 11, 17, 11, 25, tzinfo=timezone.utc))
            self.assertEqual((docs / "briefing.html").read_text().count("Not current."), 1)   # idempotent

    def test_optional_failure_does_not_block_publishing(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs = self.setup_docs(tmp)
            build_state.main(self.ENV_OK, Path(tmp), datetime(2026, 11, 16, 11, 25, tzinfo=timezone.utc))
            st = json.loads((Path(tmp) / "data" / "briefing" / "build_state.json").read_text())
            self.assertEqual(st["status"], "ok")
            self.assertEqual(st["optional_failed"], ["rules"])
            self.assertTrue(st["published"]["is_current"])
            self.assertNotIn("Not current", (docs / "briefing.html").read_text())

    def test_crashed_collection_step_is_never_shown_as_a_live_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "data" / "briefing"
            p.mkdir(parents=True)
            (p / "status.json").write_text(json.dumps({
                "sec_form_d": {"live": "ok", "checked_at": "2026-11-16T11:20Z"},
                "openfda_510k": {"live": "ok", "checked_at": "2026-11-16T11:18Z"}}))
            marked = build_state.mark_failed_sources({"RULES": "success", "MONEY": "failure"}, Path(tmp))
            st = json.loads((p / "status.json").read_text())
            self.assertEqual(marked, ["sec_form_d"])
            self.assertEqual(st["sec_form_d"]["live"], "failed")
            self.assertEqual(st["sec_form_d"]["checked_at"], "2026-11-16T11:20Z")   # old check time kept
            self.assertEqual(st["openfda_510k"]["live"], "ok")

    def test_failed_build_counts_as_critical(self):
        s = build_state.state_from_env(dict(self.ENV_OK, BUILD="failure"), datetime(2026, 11, 16, tzinfo=timezone.utc))
        self.assertEqual(s["status"], "failed")


class RedirectHops(unittest.TestCase):
    """Every redirect hop to accessdata.fda.gov is its own request through the gate."""
    def setUp(self):
        self.t = [1000.0]
        self.slept = []
        bc._now = lambda: self.t[0]
        bc._sleep = lambda s: (self.slept.append(round(s, 3)), self.t.__setitem__(0, self.t[0] + s))
        bc.FDA_CLOCK = Path(tempfile.mkdtemp()) / "clock"
        bc.fda_window_open = lambda now=None: True

    def tearDown(self):
        import time as _t
        bc._now = _t.time
        bc._sleep = lambda s: None

    PDF = "https://www.accessdata.fda.gov/cdrh_docs/pdf26/K1.pdf"

    def test_redirect_hop_waits_30_seconds(self):
        calls = []
        bc._open = fake_open(calls, [(302, "/apology_objects/abuse-detection-apology.html"), (404, None)])
        status, body, err, hops = bc.fda_fetch(self.PDF)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1], "https://www.accessdata.fda.gov/apology_objects/abuse-detection-apology.html")
        self.assertEqual(self.slept, [30.0])
        self.assertEqual((status, [h[1] for h in hops]), (404, [302, 404]))

    def test_hours_rechecked_before_the_redirect_hop(self):
        opens = iter([True, False])
        bc.fda_window_open = lambda now=None: next(opens)
        calls = []
        bc._open = fake_open(calls, [(302, "/next"), (200, None)])
        with self.assertRaises(bc.FDAWindowClosed):
            bc.fda_fetch(self.PDF)
        self.assertEqual(len(calls), 1)          # the hop was not sent

    def test_redirect_to_another_host_is_not_followed(self):
        calls = []
        bc._open = fake_open(calls, [(302, "https://elsewhere.example/x.pdf")])
        status, body, err, hops = bc.fda_fetch(self.PDF)
        self.assertEqual(len(calls), 1)
        self.assertIn("another host", err)

    def test_redirect_loop_is_bounded(self):
        calls = []
        bc._open = fake_open(calls, [(302, "/again")])
        status, body, err, hops = bc.fda_fetch(self.PDF, max_hops=3)
        self.assertEqual(len(calls), 4)
        self.assertIn("more than 3 redirects", err)

    def test_reader_sends_redirect_hops_through_the_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            bc.OUT = docs.OUT = Path(tmp)
            docs.REVIEWS_PATH = Path(tmp) / "reviews.json"
            day = Path(tmp) / bc.today().isoformat()
            day.mkdir()
            it = rule()
            it.update(source="openFDA 510(k)", summary_available=True)
            (day / "rules.json").write_text(json.dumps([it]))
            calls = []
            bc._open = fake_open(calls, [(302, "/apology_objects/abuse-detection-apology.html"), (404, None)])
            docs.main()
            self.assertEqual(len(calls), 2)
            self.assertEqual(self.slept, [30.0])
            st = json.loads((Path(tmp) / "status.json").read_text())["fda_510k_summaries"]
            self.assertEqual(st["live"], "failed")


class SECIndex(unittest.TestCase):
    def test_federal_holiday_index_is_not_requested_or_counted_as_a_failure(self):
        from datetime import date
        with tempfile.TemporaryDirectory() as tmp:
            bc.OUT = money.OUT = Path(tmp)
            bc.STATE = Path(tmp) / "state"
            real_today = money.today
            money.today = lambda: date(2026, 11, 17)
            asked = []

            def fake_get(url, **k):
                asked.append(url)
                return 403, b"", "HTTP 403"
            real_get, money.get = money.get, fake_get
            try:
                money.main()
            finally:
                money.get, money.today = real_get, real_today
            self.assertFalse(any("20261111" in u for u in asked))
            st = json.loads((Path(tmp) / "status.json").read_text())["sec_form_d"]
            self.assertEqual(st["live"], "unproven")              # nothing read is never called a success
            self.assertIn("daily index not retrieved", st["live_detail"])
            self.assertNotIn("2026-11-11", st["live_detail"])


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
