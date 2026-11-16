# HealthSignal

**North American Healthcare Technology Intelligence.** US-first, Canada-aware.

HealthSignal is a source-linked healthcare technology intelligence briefing designed to help founders, operators and people interested in the future of medicine understand developments across the healthcare technology industry.

Current coverage:

1. FDA clearances of AI-enabled medical devices (openFDA, FDA's AI-enabled device list, and manual review of FDA 510(k) summaries).
2. Private financings by healthcare companies, from SEC Form D filings.

It is designed from a Canadian perspective but currently relies on US regulatory and financing data. It does not yet cover Canadian sources such as Health Canada device licences or Canadian financings.

Every record links to its official source. Facts and interpretation are kept apart, and each FDA record carries an evidence class (FDA-listed, document-verified, manufacturer-reported, inferred, unknown). Nothing here is investment or legal advice.

## Read it

- Briefing: https://fb-121.github.io/canada-health-signals/briefing.html
- Markdown: https://fb-121.github.io/canada-health-signals/briefing.md
- JSON: https://fb-121.github.io/canada-health-signals/briefing.json
- Run status (fixture tests, live source checks, public-copy check kept apart): https://fb-121.github.io/canada-health-signals/status.json

## How it runs

- `.github/workflows/signals.yml`, daily at 11:17 UTC: optional source collection (`briefing_rules.py`, `briefing_money.py`), then the critical steps (fixture tests, then `build_briefing.py`), then a live check of the public copies (`verify_live.py`). If a critical step fails, the last good briefing stays published, marked not current.
- `.github/workflows/fda-docs.yml`, daily at 05:23 UTC, inside FDA's stated visiting hours: an access probe and the 510(k) summary reader. FDA currently redirects scripted requests to an abuse-detection page, so automated reading is off and manual review (`data/briefing/reviews.json`) is used.
- Change history and known limitations: `docs/briefing-changelog.md` and `data/briefing/known_issues.json`. Pilot plan: `docs/pilot.md`.
- Tests: `python scripts/run_tests.py` (fixtures, no network).

The repository keeps its original name, `canada-health-signals`, so that existing links keep working.

## Also in this repository: Canada Health Signals archive (separate, earlier project)

The site's front page (`docs/index.html`, built by `scripts/build_site.py`) is an earlier, separate project: a respiratory-season page built from Canadian wastewater data. `docs/ai.html` (built by `scripts/build_ai.py`) compares FDA AI device approvals with clinical trial counts. Both keep running unchanged and are not part of HealthSignal.

That archive saves a daily snapshot of public Canadian health feeds, so history builds up where the sources only show today's value. `scripts/probe.py` requests each source once, logs the result to `data/probe_log.csv`, and saves raw snapshots under `data/raw/YYYY-MM-DD/`. Sources, as listed in `scripts/probe.py`: Health Canada Drug Product Database and recalls, PHAC wastewater and respiratory surveillance, Environment Canada air quality (AQHI, Calgary), Quebec hourly ER data, and US comparison feeds (CDC NHSN and wastewater, PubMed, ClinicalTrials.gov, openFDA, FDA's AI device page). Each source remains subject to its own terms of use and licence.
