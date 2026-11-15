"""Briefing data-integrity tests. Run: python -m unittest discover -s tests -v

Fixtures for the Form D cases are reconstructed from the fields read on 2026-11-15 from the
SEC filings for Nanopath (0001940981-26-000003), Zai Lab (0001704292-26-000038) and
AngioInsight (0002164579-26-000001), and the FDA 510(k) summary and record for BlineSlide
(K261679). They are not byte copies of those filings. The tests pin down the validation cases.
"""
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import briefing_common as bc          # noqa: E402
import briefing_docs as docs          # noqa: E402
import briefing_money as money        # noqa: E402
import briefing_rules as rules        # noqa: E402
import build_briefing as page         # noqa: E402

bc.OUT = Path(tempfile.mkdtemp())     # no test may write into the real data folder
bc.STATE = bc.OUT / "state"


def form_d(name, group="Biotechnology", types=("isEquityType",), first_sale="2026-10-22", amend=False,
           prev=None, offering="36760740", sold="29891706", remaining="6869034", investors="21",
           clar=None, commission=None, broker=None, signed="2026-11-10", pooled=False):
    flags = "".join(f"<{t}>true</{t}>" for t in types)
    if pooled:
        flags += "<isPooledInvestmentFundType>true</isPooledInvestmentFundType>"
    sale = (f"<dateOfFirstSale><value>{first_sale}</value></dateOfFirstSale>" if first_sale else "")
    clar_xml = f"<clarificationOfResponse>{clar}</clarificationOfResponse>" if clar else ""
    comp = (f"<salesCommissionsFindersFees><salesCommissions><dollarAmount>{commission}</dollarAmount>"
            f"</salesCommissions></salesCommissionsFindersFees>") if commission else ""
    recip = f"<salesCompensationList><recipient><recipientName>{broker}</recipientName></recipient></salesCompensationList>" if broker else ""
    sold_x = f"<totalAmountSold>{sold}</totalAmountSold>" if sold is not None else ""
    rem_x = f"<totalRemaining>{remaining}</totalRemaining>" if remaining is not None else ""
    prev_x = f"<previousAccessionNumber>{prev}</previousAccessionNumber>" if prev else ""
    return f"""<?xml version="1.0"?><edgarSubmission><primaryIssuer><entityName>{name}</entityName>
<entityType>Corporation</entityType><jurisdictionOfInc>DELAWARE</jurisdictionOfInc>
<issuerAddress><stateOrCountry>MA</stateOrCountry><stateOrCountryDescription>MASSACHUSETTS</stateOrCountryDescription></issuerAddress>
</primaryIssuer><offeringData><industryGroup><industryGroupType>{group}</industryGroupType></industryGroup>
<typeOfFiling><newOrAmendment><isAmendment>{str(amend).lower()}</isAmendment>{prev_x}</newOrAmendment>{sale}</typeOfFiling>
<typesOfSecuritiesOffered>{flags}</typesOfSecuritiesOffered>
<offeringSalesAmounts><totalOfferingAmount>{offering}</totalOfferingAmount>{sold_x}{rem_x}{clar_xml}</offeringSalesAmounts>
<investors><hasNonAccreditedInvestors>false</hasNonAccreditedInvestors><totalNumberAlreadyInvested>{investors}</totalNumberAlreadyInvested></investors>
{comp}{recip}</offeringData><signatureBlock><signature><signatureDate>{signed}</signatureDate></signature></signatureBlock></edgarSubmission>""".encode()


PRIVATE = {"cik": "0001940981", "tickers": [], "exchanges": [], "files_periodic_reports": False}
ZAI = {"cik": "0001704292", "tickers": ["ZLAB"], "exchanges": ["Nasdaq"], "files_periodic_reports": True}


class Dates(unittest.TestCase):
    def test_weekend_deadline_rolls_to_monday(self):
        self.assertEqual(bc.form_d_deadline("2026-10-17"), date(2026, 11, 2))   # day 15 is a Sunday

    def test_weekday_deadline_stays(self):
        self.assertEqual(bc.form_d_deadline("2026-10-22"), date(2026, 11, 6))

    def test_late_filing_counts(self):
        self.assertEqual(bc.days_late("2026-10-22", "2026-11-13"), 7)      # Nanopath
        self.assertGreater(bc.days_late("2025-10-09", "2026-11-10"), 365)  # AngioInsight
        self.assertEqual(bc.days_late("2026-10-22", "2026-11-06"), 0)

    def test_unknown_dates_stay_unknown(self):
        self.assertIsNone(bc.days_late(None, "2026-11-10"))
        self.assertIsNone(bc.form_d_deadline("not a date"))
        self.assertIsNone(bc.recency(None, "2026-11-15"))

    def test_recency_bands(self):
        self.assertEqual(bc.recency("2026-11-10", "2026-11-15"), "new")
        self.assertEqual(bc.recency("2026-10-23", "2026-11-15"), "recent")
        self.assertEqual(bc.recency("2025-10-09", "2026-11-15"), "historical")

    def test_parse_dates(self):
        self.assertEqual(bc.pdate("20261023"), date(2026, 10, 23))
        self.assertEqual(bc.pdate("10/23/2026"), date(2026, 10, 23))
        self.assertIsNone(bc.pdate(""))


class FormD(unittest.TestCase):
    def build(self, xml, profile, cik="1940981", filed="20261113", ledger=None, form="D"):
        f = money.parse_form_d(xml)
        return f, money.build_item(f, form, cik, filed, "0001-26-000001", "https://sec.example/x", profile, ledger or {})

    def test_index_rows(self):
        idx = ("D                Acme Health AI, Inc.      1900001     20261113    edgar/data/1900001/0001900001-26-000001.txt\n"
               "D/A              Acme Amend Inc            1900004     20261113    edgar/data/1900004/0001900004-26-000002.txt\n"
               "SC 13D           Someone                   1900005     20261113    edgar/data/1900005/0001900005-26-000003.txt\n")
        rows = list(money.parse_index(idx))
        self.assertEqual([r[0] for r in rows], ["D", "D/A"])

    def test_nanopath_is_mixed_equity_and_debt_and_late(self):
        xml = form_d("Nanopath Inc", types=("isEquityType", "isDebtType"), clar=None)
        f, it = self.build(xml, PRIVATE)
        self.assertEqual(f["security_types"], ["equity", "debt"])
        self.assertEqual(it["category"], "mixed equity and debt")
        self.assertEqual(it["late_days"], 7)
        self.assertEqual(it["filing_date"], "2026-11-13")
        self.assertEqual(it["signed_date"], "2026-11-10")
        self.assertNotIn("equity round", it["headline"])

    def test_zai_lab_is_public_company_placement(self):
        xml = form_d("Zai Lab Ltd", first_sale="2026-10-27", offering="249933600", sold="249933600",
                     remaining="0", investors="25", commission="7498008", broker="LEERINK PARTNERS LLC",
                     signed="2026-11-09")
        f, it = self.build(xml, ZAI, cik="1704292", filed="20261109")
        self.assertEqual(it["category"], "public-company private placement")
        self.assertIn("ZLAB", it["ownership"])
        self.assertEqual(f["brokers"], ["LEERINK PARTNERS LLC"])
        self.assertAlmostEqual(f["commission"] / f["sold"], 0.03, places=4)
        self.assertEqual(it["late_days"], 0)

    def test_angioinsight_is_safe_and_very_late(self):
        xml = form_d("AngioInsight, Inc.", group="Other Health Care", types=("isOptionToAcquireType",),
                     first_sale="2025-10-09", offering="20000000", sold="16314000", remaining="3686000",
                     investors="94", clar="10% of the proceeds received from the sale of SAFEs by the Broker",
                     commission="760900", broker="Cedar Point Capital, LLC")
        f, it = self.build(xml, PRIVATE, cik="2164579", filed="20261110")
        self.assertEqual(it["category"], "SAFE (per filer note)")
        self.assertGreater(it["late_days"], 365)
        self.assertEqual(it["recency"], "historical")
        self.assertNotIn("debt", it["category"])

    def test_option_based_without_safe_note_is_not_called_safe(self):
        f, it = self.build(form_d("X Corp", types=("isOptionToAcquireType",)), PRIVATE)
        self.assertEqual(it["category"], "option-based (SAFE or warrant, not stated)")

    def test_amendment_is_an_update_with_change_from_ledger(self):
        ledger = {"0001-25-000009": {"sold": 20_000_000.0}}
        xml = form_d("Nanopath Inc", amend=True, prev="0001-25-000009")
        f, it = self.build(xml, PRIVATE, ledger=ledger, form="D/A")
        self.assertEqual(it["kind"], "update")
        self.assertIn("amended", it["headline"])
        self.assertIn("$20.0M in the earlier filing", it["detail"])

    def test_amendment_without_ledger_says_unknown(self):
        f, it = self.build(form_d("Nanopath Inc", amend=True, prev="0001-25-000009"), PRIVATE, form="D/A")
        self.assertIn("not in this pipeline's records", it["detail"])

    def test_missing_values_stay_unknown(self):
        f, it = self.build(form_d("Gap Co", first_sale=None, sold=None, remaining=None), PRIVATE)
        self.assertIsNone(f["first_sale"])
        self.assertIsNone(f["sold"])
        self.assertIsNone(f["remaining"])
        self.assertIsNone(it["late_days"])
        self.assertIsNone(it["event_date"])
        self.assertIn("first-sale date not stated", it["detail"])

    def test_pooled_funds_are_flagged(self):
        self.assertTrue(money.parse_form_d(form_d("Fund LP", pooled=True))["pooled"])

    def test_ownership_wording_never_claims_private(self):
        self.assertIn("not verified private", money.ownership(PRIVATE))
        self.assertTrue(money.ownership(None).startswith("unknown"))


class Rules(unittest.TestCase):
    def test_evidence_classes(self):
        self.assertEqual(rules.classify_evidence(True, False, None), "fda_listed")
        self.assertEqual(rules.classify_evidence(False, True, 0.9), "manufacturer_reported")
        self.assertEqual(rules.classify_evidence(False, False, 0.92), "inferred")
        self.assertEqual(rules.classify_evidence(False, False, 0.10), "unknown")
        self.assertEqual(rules.classify_evidence(False, False, None), "unknown")

    def test_blineslide_record_is_inferred_with_dates(self):
        r = {"k_number": "K261679", "applicant": "Deep Breathe, Inc.", "device_name": "BlineSlide",
             "decision_date": "2026-10-23", "date_received": "2026-05-21", "product_code": "POK",
             "advisory_committee_description": "Radiology", "country_code": "CA", "statement_or_summary": "Summary"}
        it = rules.build_item(r, False, {"POK": 0.92})
        self.assertEqual(it["evidence"], "inferred")
        self.assertEqual(it["review_days"], 155)
        self.assertEqual(it["received_date"], "2026-05-21")
        self.assertTrue(it["summary_available"])
        self.assertEqual(it["company_id"], "fda:deep-breathe")


BLINE = """510(k) Summary K261679. Indications for Use: The device is a concurrent reading aid for physicians interpreting
lung ultrasound exams of adults. It detects absent pleural line motion. The subject device is an AI-assisted tool for
detecting the absence of pleural line motion. Predicate Device: Sonio Suspect (K243614), product code POK. The predicate
uses a machine learning-based algorithm. Reference device: BlineSlide (K252007) Deep Breathe Inc. product code QIH.
Technological characteristics: Algorithm methodology of the subject device is computer vision. Standalone testing used 818
cines. Predetermined Change Control Plan: not authorized for this device."""

NO_AI = """510(k) Summary K260001. Indications for Use: The system is a diagnostic ultrasound system intended for imaging of
the human body in clinical settings by trained operators. Predicate Device: Other Ultrasound (K200001). The device has the
same technological characteristics, acoustic output limits and transducers as the predicate. Performance testing covered
electrical safety, acoustic output and biocompatibility in accordance with applicable standards. No software algorithms
beyond standard image reconstruction are included in this submission, and no new risks were identified."""

PREDICATE_ONLY = """510(k) Summary K260002. Indications for Use: The software displays and measures images from a scanner
for use by clinicians. Predicate Device: Acme Reader (K210002) is a machine learning based tool for triage. The subject
device does not include any adaptive components and uses fixed measurement tools only. All performance testing was
completed on bench phantoms and compared with the predicate for measurement accuracy and repeatability across the range."""


class Documents(unittest.TestCase):
    def test_blineslide_summary(self):
        a = docs.analyze_summary(BLINE, "K261679", "Deep Breathe, Inc.")
        self.assertEqual(a["status"], "read")
        self.assertTrue(a["ai_language"])
        self.assertIn("ai-assisted", a["ai_terms"])
        self.assertIn("computer vision", a["algorithm_methods"])
        self.assertEqual(a["predicates"], ["K243614"])
        self.assertEqual(a["reference_devices"], ["K252007"])
        self.assertEqual(a["same_company_devices"], ["K252007"])
        self.assertIn("concurrent reading aid", a["intended_use"])

    def test_no_ai_language(self):
        a = docs.analyze_summary(NO_AI, "K260001")
        self.assertFalse(a["ai_language"])
        self.assertEqual(a["predicates"], ["K200001"])

    def test_ai_in_predicate_sentence_does_not_count(self):
        a = docs.analyze_summary(PREDICATE_ONLY, "K260002")
        self.assertFalse(a["ai_language"])
        self.assertIn("machine learning", " ".join(a["ai_terms_predicate_only"]))

    def test_too_short_is_unreadable_and_changes_nothing(self):
        a = docs.analyze_summary("short", "K1")
        self.assertEqual(a["status"], "unreadable")
        it = {"key": "510k:K1", "record_id": "K1", "evidence": "inferred"}
        self.assertIsNone(docs.apply_to_item(it, a))
        self.assertEqual(it["evidence"], "inferred")

    def _item(self, ev):
        return {"key": "510k:K9", "record_id": "K9", "evidence": ev}

    def test_evidence_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            bc.OUT = Path(tmp)
            yes = docs.analyze_summary(BLINE, "K9")
            no = docs.analyze_summary(NO_AI, "K9")
            a = self._item("inferred"); docs.apply_to_item(a, yes); self.assertEqual(a["evidence"], "document_verified")
            b = self._item("manufacturer_reported"); docs.apply_to_item(b, no); self.assertEqual(b["evidence"], "unknown")
            c = self._item("fda_listed"); docs.apply_to_item(c, no); self.assertEqual(c["evidence"], "fda_listed")
            log = [json.loads(l) for l in (Path(tmp) / "corrections.jsonl").read_text().splitlines()]
            self.assertEqual(len(log), 2)


class Storage(unittest.TestCase):
    def test_upgrade_in_place_logs_correction_and_keeps_first_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            bc.OUT = Path(tmp)
            day = Path(tmp) / bc.today().isoformat()
            day.mkdir(parents=True)
            old = {"key": "formd:A", "section": "money", "headline": "Nanopath raised $29.9M", "detail": "",
                   "first_detected": "2026-11-15"}
            (day / "money.json").write_text(json.dumps([old]))
            new = bc.item("money", "Nanopath reports $29.9M sold in a mixed equity and debt", "d", "u", "2026-10-22", "formd:A",
                          category="mixed equity and debt")
            new["first_detected"] = "2026-11-20"
            bc.write_items("money", [new], [])
            stored = json.loads((day / "money.json").read_text())
            self.assertEqual(len(stored), 1)
            self.assertEqual(stored[0]["schema"], bc.SCHEMA)
            self.assertEqual(stored[0]["first_detected"], "2026-11-15")
            log = [json.loads(l) for l in (Path(tmp) / "corrections.jsonl").read_text().splitlines()]
            self.assertEqual(log[0]["field"], "headline")

    def test_upgrade_finds_the_record_in_an_earlier_day(self):
        with tempfile.TemporaryDirectory() as tmp:
            bc.OUT = Path(tmp)
            earlier = Path(tmp) / "2000-01-01"          # outside the window: must NOT be matched
            from datetime import timedelta
            prev = Path(tmp) / (bc.today() - timedelta(days=3)).isoformat()
            prev.mkdir(parents=True)
            old = {"key": "510k:K5", "section": "rules", "headline": "old", "detail": "", "first_detected": "2026-11-12"}
            (prev / "rules.json").write_text(json.dumps([old]))
            new = bc.item("rules", "new headline", "d", "u", "2026-11-01", "510k:K5")
            bc.write_items("rules", [new], [])
            self.assertFalse((Path(tmp) / bc.today().isoformat() / "rules.json").exists())   # no duplicate today
            stored = json.loads((prev / "rules.json").read_text())
            self.assertEqual(stored[0]["headline"], "new headline")
            self.assertEqual(stored[0]["first_detected"], "2026-11-12")

    def test_same_schema_item_is_not_duplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            bc.OUT = Path(tmp)
            it = bc.item("rules", "h", "d", "u", "2026-10-22", "510k:K1")
            bc.write_items("rules", [it], [])
            bc.write_items("rules", [it], [])
            day = Path(tmp) / bc.today().isoformat() / "rules.json"
            self.assertEqual(len(json.loads(day.read_text())), 1)


def R(section, key, **kw):
    base = bc.item(section, kw.pop("headline", key), "d", "https://x", kw.pop("event", "2026-11-01"), key, **kw)
    return base


class PageLogic(unittest.TestCase):
    def test_same_company_records_become_one_story(self):
        a = R("rules", "510k:K1", company_id="fda:avicenna", company="Avicenna.Ai", evidence="manufacturer_reported", record_id="K1")
        b = R("rules", "510k:K2", company_id="fda:avicenna", company="Avicenna.Ai", evidence="manufacturer_reported", record_id="K2")
        c = R("rules", "510k:K3", company_id="fda:other", company="Other", evidence="inferred", record_id="K3")
        stories = page.make_stories([a, b, c], {})
        self.assertEqual(len(stories), 2)
        self.assertEqual(sorted(len(s["records"]) for s in stories), [1, 2])
        self.assertIn("2 FDA clearances", [s for s in stories if len(s["records"]) == 2][0]["headline"])

    def test_private_startup_outranks_public_placement_and_amendments(self):
        priv = R("money", "formd:1", amount=5e6, ownership="no listing found", kind="new offering", company_id="cik:1")
        pub = R("money", "formd:2", amount=250e6, ownership="listed (Nasdaq: ZLAB)", kind="new offering", company_id="cik:2")
        upd = R("money", "formd:3", amount=50e6, ownership="no listing found", kind="update", company_id="cik:3")
        order = [s["company_id"] for s in page.make_stories([pub, upd, priv], {})]
        self.assertEqual(order, ["cik:1", "cik:2", "cik:3"])

    def test_evidence_order_in_rules(self):
        items = [R("rules", f"510k:K{n}", company_id=f"fda:{n}", evidence=ev, record_id=f"K{n}")
                 for n, ev in enumerate(["inferred", "fda_listed", "unknown", "document_verified"])]
        order = [s["lead"]["evidence"] for s in page.make_stories(items, {})]
        self.assertEqual(order, ["fda_listed", "document_verified", "inferred", "unknown"])

    def test_quality_flags_duplicates_and_bad_values(self):
        a = R("money", "formd:1", amount=9e6, offering=5e6, category="x", filing_date="2026-11-01", record_id="D1")
        b = R("money", "formd:2", amount=1e6, offering=5e6, category="x", filing_date="2026-11-01", record_id="D1")
        n, issues = page.quality([a, b])
        self.assertTrue(any("duplicate record D1" in i for i in issues))
        self.assertTrue(any("sold exceeds offering" in i for i in issues))

    def test_quality_passes_clean_items(self):
        a = R("rules", "510k:K1", evidence="inferred", record_id="K1")
        n, issues = page.quality([a])
        self.assertEqual(issues, [])

    def test_page_builds_without_data_and_has_no_em_dash(self):
        with tempfile.TemporaryDirectory() as tmp:
            page.DATA = Path(tmp)
            bc.OUT = Path(tmp)
            html = page.build()
            self.assertIn("Health Tech Morning Brief", html)
            self.assertNotIn("—", html)


if __name__ == "__main__":
    unittest.main()
