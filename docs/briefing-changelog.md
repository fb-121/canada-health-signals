# Briefing changelog and validation notes

## Operational fixes before the pilot, 2026-11-16

Architecture freeze reference stays `f8df353`. These are operational fixes, not design changes: no new sources, features or ranking changes.

| # | Fix | Detail |
|---|-----|--------|
| 1 | FDA request spacing and hours, per request | One gate (`fda_gate` and `fda_done` in `briefing_common.py`) now sits in front of every request to accessdata.fda.gov from `fda_probe.py` (including each redirect hop) and `briefing_docs.py`. It waits until 30 seconds after the end of the previous FDA request by either script, using a clock file both steps share (`FDA_CLOCK_FILE` in `fda-docs.yml`), so the first request of the second script also waits. After the wait it checks visiting hours again and sends nothing if they have ended. The probe then keeps its previous diagnosis and the reader stops. Before, the probe spaced requests only within itself and the reader's first request had no wait. |
| 2 | Critical versus optional workflow steps | Fixture tests and the briefing build are critical. The build runs only if the tests pass. If either fails, `docs/briefing.*` are restored to the last good build, a "Not current" notice naming both times is put at the top of the HTML and Markdown and into the JSON, `docs/status.json` records the failure and drops any earlier "current" verdict, and the job fails, so `verify-live` does not run. Source collection (feed probe, AI evidence, Rules, Money) and the two older pages are optional: their failure is listed in `data/briefing/build_state.json` and never blocks publishing. Before, the first feed probe step had no `continue-on-error`, so a failure there skipped the build and left an old briefing and an old "current" status in place. `verify-live` now also fails when the build is not from this run (older than 6 hours or build state not ok). A manual failure drill (`drill_fail_tests` on manual runs) forces the tests to fail so the failure path can be tested on the live site. |
| 3 | Privacy residue in PR #1 | A GitHub Support request was drafted and is waiting for approval. It has not been sent. |

## Revision 3.1, 2026-11-16: pilot readiness (architecture frozen at commit `f8df353`)

No new sources and no new features.

| # | Request | What was done |
|---|---------|---------------|
| 1 | BlineSlide: document-supported versus human verified | Review statuses are now `document_supported`, `human_verified`, `rejected`, `inconclusive`. BlineSlide is `document_supported`: the AI-assisted classification stays, and the page, Markdown and JSON say "human check pending". `human_verified` is refused by the validator unless `verbatim_checked` is true and a named person and date are recorded. |
| 2 | FDA visiting hours | accessdata.fda.gov's robots.txt names 23:00 to 05:00 Eastern and 30 seconds between requests. The probe and the summary reader moved to `.github/workflows/fda-docs.yml` at 05:23 UTC. Both scripts refuse to contact accessdata.fda.gov outside 04:00 to 09:00 UTC, the hours inside the window under both EDT and EST, whatever triggered them. The probe now also waits 30 seconds between its own requests. The two workflows share a concurrency group so they never commit at the same time. |
| 3 | Public-output discrepancy | At 03:39 UTC both canonical URLs (Pages and raw, no query string) served the current build with its stamp, raw's headers showed `max-age=300`, and every Pages deployment had succeeded. So the older copy came from a cache between the reader and GitHub, not from deployment. `verify-live` now fetches canonical and cache-busted URLs separately, matches schema, content id and generation time, records cache headers, and labels any gap as "intermediary cache" or "deployment problem". |
| 4 | Fixture tests versus live checks, public | `docs/status.json` (published at `/status.json`, linked from the page) holds three separate blocks: fixture unit test results (55, no network), each source's live state, and the public-copy check. The briefing JSON and Markdown keep the same split. |
| 5 | Scope | Unchanged. |
| 6 | Git history | See below. |

### Git history clean-up

A full mirror backup and a bundle of every ref were made before rewriting. The private email appeared as author or committer on 6 commits on main (3 of them also on branch `briefing-v0`), and 20 commit messages carried AI-session URLs from two sessions. History on `main` and `briefing-v0` was rewritten: the email was replaced with the GitHub noreply address, and the `Claude-Session` lines were removed. Every commit hash changed. Future commits use the noreply address and carry no session URL. Pull request #1 still holds its original three commits on GitHub's side, which a push cannot change (see open issues).

---

## Revision 3, 2026-11-16: reliability

No new sources and no new features. Public URLs and the Markdown and JSON outputs are unchanged. JSON gains `build`, `tests`, `data_quality.open_issues` and `today.updated_records`.

| # | Request | Status | What was done and what is left |
|---|---------|--------|--------------------------------|
| A | Find out why FDA PDFs fail | Cause established: a confirmed access restriction | The address matches the link on FDA's own record page for K261679, and the same file loads through a separate fetch tool, so it is not a wrong address. From GitHub Actions, with the project's honest user agent (it names the repository) and FDA's requested 30 second pacing, FDA's bot-defence service (AkamaiGHost) redirects both the PDF and the FDA record page to `/apology_objects/abuse-detection-apology.html`. The control request to openFDA's API works, so it is not a general network block. FDA's robots.txt has no disallow rule for /cdrh_docs/, and FDA offers no official bulk route to summary text (openFDA and the downloadable 510(k) files are metadata only). Automated reading is therefore switched off while `scripts/fda_probe.py` sees the restriction, and it re-checks daily. Nothing is disguised or worked around. `data/briefing/diagnostics/fda_access.json` holds every hop, header and body start. |
| B | Manual evidence review | Done | `data/briefing/reviews.json` keeps, per record, the official document URL, short quotations, page numbers with how sure each page is, review date, reviewer, whether the reviewer was independent, whether the quotes were compared with the PDF, and caveats. The build applies it on top of automated results, automation cannot overrule it, and a completeness check runs in the tests and on every build. First case: BlineSlide K261679. |
| 1 | Public outputs reflect schema 2 | Verified, with a stamp added | Checked independently on 2026-11-16: github.io served schema 2 with 15 items generated 2026-11-15 20:16Z, and the raw file host matched. The schema 1 copy with 13 items was the build before that run, so a cached copy. Every output now carries a content id. A new `verify-live` job fetches each public URL with a cache-busting query after every run, retries for 12 minutes, and fails if any copy differs from the build. |
| 2 | Source freshness versus pipeline freshness | Done | The freshness table separates the newest source record (against that source's normal cadence) from when the pipeline last ran (stale after 36 hours). Each can be stale without the other. |
| 3 | Automated tests versus live integration | Done | Fixture unit tests (49, no network) are recorded in `tests.json`. Each source records a live state (ok, degraded, failed, unproven) from its real request. The page says plainly that passing tests does not show a source is reachable. |
| 4 | Resurfacing | Done | A record that gains evidence (summary read, manual review) keeps its first-detected date and gets an update entry. It reappears for 3 days under Updated records, labelled "Update, not a new event", and is never counted as a new clearance. Amendments are counted as amendments, not new financings. |
| 5 | Correction history, open issues | Done | `corrections.jsonl` stays append-only. Two entries added for BlineSlide. `known_issues.json` is shown on the page and in the JSON. |

### What was wrong in revision 2

- The 510(k) summary reader had never worked live. It returned 404 on all 7 PDFs. Revision 2 reported it as "built, not proven", which was accurate but easy to miss.
- The analysis said BlineSlide's summary lists computer vision "not machine learning". The summary's comparison table lists both, and the extracted text does not show which device each belongs to. The AI-assisted label is supported by the summary's own wording. The method is not settled. Corrected and logged.

### BlineSlide manual review (K261679)

Status: verified, not independent, quotes not yet compared with the PDF. Three quotations (AI-assisted wording, page 3; algorithm methodology row, page 7; indications for use, pages 4 to 5). Page numbers came from a text extraction and are approximate. A person should open the PDF and confirm them, then set `verbatim_checked`, and `independent` if someone other than the author checks.

---

Revision 2, 2026-11-15. Public URLs and the Markdown and JSON outputs are unchanged. The JSON now carries `schema_version: 2`, and `today.items` keeps its earlier fields plus new ones.

## What changed

| # | Request | Status | What was done and what is left |
|---|---------|--------|--------------------------------|
| 1 | Separate dates, flag backfills | Done | Every record carries event, filing, signed, published, first-detected and briefing dates. Unknown stays null. A recency band (new, recent, historical) compares the event date with first detection. Everything first detected on 2026-11-15 comes from the pipeline's initial lookback window. |
| 2 | Verify AI from FDA 510(k) summaries | Built, failing live (see revision 3) | The reader downloads each summary, records AI language, stated intended use, methods mentioned, predicate and reference devices, and mention of a change control plan. I checked K261679 by hand today. The code has unit tests but its first run against real PDFs happens in the workflow. Significant-modification analysis is not done: it only flags same-company reference devices and change control plan mentions. |
| 3 | Evidence-based classes | Done | fda_listed, document_verified, manufacturer_reported, inferred, unknown. Sentences about a predicate do not count as evidence about the subject device. A summary with no AI language lowers a record to unknown and ranks it last. It is not deleted. |
| 4 | Enrich Form D | Done, with limits | Security types, financing category, offering, amount sold, remaining, first sale, investors, commissions, filing lateness, and ownership from an EDGAR company lookup. Missing values stay unknown. Parent and subsidiary ownership is not covered. |
| 5 | Startups versus placements, amendments | Done | A listed issuer's private placement is its own category. Debt, mixed and SAFE rounds are separated. A D/A amendment is an update to an existing offering. The earlier amount is shown only when this pipeline stored the original (offerings are kept 400 days, so older ones read as unknown). |
| 6 | Profiles, identifiers, stories | Partly done | IDs are `cik:` for SEC and `fda:` plus a name slug for FDA applicants. Records of one company group into one story with each source record kept. EDGAR profiles are cached in `data/briefing/companies/`. FDA applicant IDs are name-based, so spelling variants may split one company, and the same company is not yet linked across FDA and SEC. |
| 7 | Why it matters, what to watch | Done by hand for four stories | Written in `data/briefing/analysis.json`, labelled as interpretation, with the evidence each rests on, and marked not yet reviewed. There is no automatic generation. The other stories have none. |
| 8 | Review, freshness, duplicates, corrections, tests | Done, with limits | Source freshness table, duplicate and consistency checks on every build, an append-only correction log, and 32 unit tests run in the daily workflow. Review is one person (see below). |
| 9 | Validation cases | Done | Below. |

## Validation cases

| Case | What the official record shows | What the earlier page got wrong |
|------|-------------------------------|---------------------------------|
| Nanopath | Form D 0001940981-26-000003. Securities offered: equity and debt. Offering $36,760,740, sold $29,891,706, remaining $6,869,034, 21 investors. First sale 2026-10-22, signed 2026-11-10, indexed 2026-11-13, which is 7 days past the 2026-11-06 deadline. | Said "raised $29.9M" and implied equity. The split between equity and debt is not disclosed. |
| Zai Lab | Form D 0001704292-26-000038. Cayman exempted company, $249,933,600 sold in full to 25 investors, $7,498,008 commission to Leerink Partners (3.0%). EDGAR company record: ticker ZLAB on Nasdaq, SIC 2834, large accelerated filer, 10-Q filed 2026-08-06. | Listed it as a biotech raise next to startups. It is a public company's private placement. |
| AngioInsight | Form D 0002164579-26-000001. Securities offered: option to acquire only. The commission note refers to SAFEs. Offering $20,000,000, sold $16,314,000, 94 investors. First sale 2025-10-09, signed and filed 2026-11-10, 382 days past the 2025-10-24 deadline. | Labelled it "not an equity raise (debt or other securities)". It is a SAFE round. It also looked like a new raise this week when it is a year of cumulative sales. |
| BlineSlide | FDA record K261679: received 2026-05-21, decided 2026-10-23, product code POK, traditional 510(k). The summary calls it an "AI-assisted tool", lists the algorithm methodology as computer vision, and names Sonio Suspect (K243614, machine learning based, fetal ultrasound) as predicate and its own K252007 as a reference device. | Labelled it a possible AI device from product-code statistics alone. The summary supports the AI label but with the method qualified. The product code's own name refers to cancer lesions while the device reads lung ultrasound, which is why the product-code guess is weak evidence. |

Sources: the SEC filings and EDGAR company record named above, the FDA database record and the FDA 510(k) summary for K261679, all read on 2026-11-15.

## Daily review process

1. After the 11:17 UTC run, open `briefing.json` and list stories where `analysis` is null.
2. For each story worth acting on, read the official record linked from it, then add an entry to `data/briefing/analysis.json` keyed by `company_id`, with `why`, `watch`, `basis` (the facts it rests on) and `reviewed: false`.
3. A second person sets `reviewed: true` only after checking the basis against the records.
4. Anything wrong in a published record is fixed at the source of the logic, and the change shows in `data/briefing/corrections.jsonl`.

## Source freshness

`status.json` records the newest data date and check time for each source. The page marks a source stale after 4 days (SEC index), 21 days (openFDA clearances) or 180 days (FDA AI list, which FDA updates every few months).

## Tests

Run `python -m unittest discover -s tests -v`. The workflow runs them every day before collecting. Fixtures are reconstructed from the fields read from the four validation cases and are not byte copies of the filings.

## Remaining limitations at revision 2 (the live list is data/briefing/known_issues.json)

- Only openFDA and SEC records are covered. No news, stock prices or hiring data.
- Startups that file Form D under Other Technology are missed.
- A Form D gives the amount sold to date, not the investors or how the amount splits by security.
- Deadline checks adjust for weekends but not federal holidays.
- A 510(k) summary without AI language is not proof of no AI.
- A 510(k) with only a statement and no summary cannot be read.
- Analysis exists for four stories and none is independently reviewed.
- Company IDs for FDA applicants are name-based and not authoritative.
