# Briefing changelog and validation notes

Revision 2, 2026-11-15. Public URLs and the Markdown and JSON outputs are unchanged. The JSON now carries `schema_version: 2`, and `today.items` keeps its earlier fields plus new ones.

## What changed

| # | Request | Status | What was done and what is left |
|---|---------|--------|--------------------------------|
| 1 | Separate dates, flag backfills | Done | Every record carries event, filing, signed, published, first-detected and briefing dates. Unknown stays null. A recency band (new, recent, historical) compares the event date with first detection. Everything first detected on 2026-11-15 comes from the pipeline's initial lookback window. |
| 2 | Verify AI from FDA 510(k) summaries | Built, not yet proven on live PDFs | The reader downloads each summary, records AI language, stated intended use, methods mentioned, predicate and reference devices, and mention of a change control plan. I checked K261679 by hand today. The code has unit tests but its first run against real PDFs happens in the workflow. Significant-modification analysis is not done: it only flags same-company reference devices and change control plan mentions. |
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

## Remaining limitations

- Only openFDA and SEC records are covered. No news, stock prices or hiring data.
- Startups that file Form D under Other Technology are missed.
- A Form D gives the amount sold to date, not the investors or how the amount splits by security.
- Deadline checks adjust for weekends but not federal holidays.
- A 510(k) summary without AI language is not proof of no AI.
- A 510(k) with only a statement and no summary cannot be read.
- Analysis exists for four stories and none is independently reviewed.
- Company IDs for FDA applicants are name-based and not authoritative.
