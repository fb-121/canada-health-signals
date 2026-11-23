# HealthSignal, November 23, 2026

North American Healthcare Technology Intelligence. US-first, Canada-aware.

HealthSignal is a source-linked healthcare technology intelligence briefing for founders, operators and people interested in the future of medicine. It is designed from a Canadian perspective and is US-first: current coverage is FDA clearances of AI-enabled medical devices and private financings by healthcare companies from SEC Form D filings, both US sources. It does not yet cover Canadian regulatory or financing data. Every record links to an official source. Facts come from those records. Analysis is written by a reviewer and labelled as interpretation. Nothing here is investment or legal advice.

## How to read the labels

- **fda_listed**: On FDA's AI-enabled device list.
- **document_verified**: FDA's 510(k) summary itself describes AI or machine learning. The summary may name the method (for example computer vision), which is recorded. When this rests on a manual review, verification_status says whether a person has checked the quotes against the PDF (human verified) or not yet (human check pending).
- **manufacturer_reported**: The manufacturer's own device or company name claims AI. Not checked against FDA documents.
- **inferred**: No document evidence. The FDA product code is AI-heavy, which is a guess.
- **unknown**: No evidence of AI either way.
- **financing categories**: Derived from the Form D's own security-type flags, plus an EDGAR lookup. public-company private placement: the issuer has an exchange ticker in EDGAR. equity round, debt financing, mixed equity and debt, option-based or SAFE (SAFE only when the filer's note says so), other. An amendment (D/A) is an update to an offering, not a new raise.
- **dates**: event_date: The underlying event: FDA decision date, or Form D first-sale date. filing_date: When the Form D was lodged with SEC (null for FDA records). signed_date: Date on the filer's signature (Form D). published_date: When the official source made it public, where the source says. Null when unknown. first_detected: The day this pipeline first saw the record. recency: new: event within 14 days of first detection. recent: 15 to 45 days. historical: older.

## Known gaps

- Many digital health startups file Form D under Other Technology, so they are missed.
- Form D asks for the amount sold to date. It does not say who invested or how the amount splits across securities.
- Form D deadline checks adjust for weekends but not federal holidays, so a filing one business day over may be on time.
- FDA's AI device list updates only every few months, so recent AI devices usually appear without that label.
- A 510(k) summary with no AI language does not prove the device has no AI. It is ranked last, not deleted.
- Only openFDA and SEC records are covered. There is no news, stock price or hiring data.
- Analysis is written for a few records so far and is not independently reviewed.

## Source freshness

Source data freshness (newest record) and pipeline freshness (last run) are separate. Live is whether the request worked.

- SEC Form D daily index: newest source record n/a; pipeline last ran 2026-11-23T22:39Z; live request unproven 0 filings read, 0 unreadable; no new index to read this run, so no filing was retrieved
- openFDA 510(k) clearances: newest source record 2026-11-06; pipeline last ran 2026-11-23T22:39Z; live request ok 21 clearances returned by the API
- FDA AI-enabled device list: newest source record 2026-06-29; pipeline last ran 2026-11-23T22:39Z; live request ok 1614 rows read from the FDA list
- FDA 510(k) summaries: newest source record n/a; pipeline last ran 2026-11-16T04:11Z; live request blocked FDA redirects scripts to an abuse-detection page; automated reading off, manual review in use
- Fixture unit tests (no network): 70 of 70 passed at 2026-11-23T22:39Z. This does not show any source is reachable.

## Today (0 records in 0 stories)

No new records today.

## Open data-quality issues

- [high] FDA 510(k) summaries (confirmed restriction, automated reading off): Confirmed 2026-11-16: from GitHub Actions, requests for FDA summary PDFs and even the FDA record page are redirected by FDA's bot-defence service (AkamaiGHost) to an abuse-detection page, with the project's honest user agent and 30 second pacing. The address itself is correct. FDA offers no official bulk route to summary text: openFDA and the downloadable 510(k) files carry metadata only. Automated reading is switched off while the probe sees this, it is not worked around, and document-verified labels come only from manual reviews. The probe re-checks once a day and reading resumes by itself if access opens.
- [medium] BlineSlide K261679 (open, human check pending): BlineSlide's review is document-supported, not human verified. Quotes and pages came from a text extraction and no person has compared them with the PDF. The AI-assisted label is kept. FDA's comparison table lists computer vision and machine-learning-based algorithms, and the extracted text does not show which device each belongs to, so the method is not settled.
- [low] FDA robots.txt (resolved 2026-11-16): FDA's robots.txt for accessdata.fda.gov names visiting hours of 23:00 to 05:00 Eastern and 30 seconds between requests. Reading and the access probe now run in a separate workflow at 05:23 UTC, the scripts refuse to contact accessdata.fda.gov outside 04:00 to 09:00 UTC (inside the window under both EDT and EST), and every request there, probe included, is spaced 30 seconds apart. Before the fix, test runs on 2026-11-15 20:12 UTC and 2026-11-16 03:21 and 03:31 UTC sent a few requests outside the window.
- [medium] Public outputs (investigated 2026-11-16): An outside retrieval showed an older Markdown file and JSON without build metadata. At 03:39 UTC on 2026-11-16 both canonical URLs (GitHub Pages and the raw file host, no query string) served the current build with its stamp, and every Pages deployment had succeeded. So the older copy came from a cache between the reader and GitHub, most likely the retrieving tool's own cache (Pages allows 10 minutes, the raw host 5, and some fetch tools keep copies for 15 minutes). The verify-live job now checks canonical and cache-busted URLs separately, records cache headers, labels any gap as cache or deployment, and publishes the result in docs/status.json.
- [medium] Why it matters / watch next (open): Analysis exists for four stories, all written by Claude and none independently reviewed.
- [medium] Company identity (open): FDA applicant IDs are name slugs, so spelling variants can split one company. The same company is not linked across FDA and SEC.
- [low] Form D lateness (open): Deadlines adjust for weekends, not federal holidays, so a filing one business day over may be on time.
- [medium] 510(k) summaries (open): Significant-modification analysis is not built. Only same-company reference devices and change-control-plan mentions are flagged.
- [medium] Git history (support request drafted, waiting for approval): The private email and AI-session URLs were removed from main and briefing-v0 by rewriting history. GitHub keeps pull request #1's original commits (refs/pull/1/head), which cannot be changed by a push, and old commit pages can stay reachable by their hash until GitHub garbage-collects them. Removing those needs a request to GitHub Support.
- [low] SEC Form D (explained 2026-11-16; corrected): The 'unreadable' item was EDGAR's daily index for 2026-11-11, which returned HTTP 403. EDGAR's 2026 QTR4 directory listing, checked in a browser on 2026-11-16, has no index for 2026-11-11 (Veterans Day) or 2026-10-12 (Columbus Day): EDGAR posts none on federal holidays and answers 403, not 404, for the missing file. This was a source limitation, not a parsing or retrieval fault. The collector now skips listed federal holidays, and the status separates index failures from unreadable filings. SEC stays 'unproven' until a run reads at least one filing. The first chance is the 2026-11-17 run, reading the 2026-11-16 index.
- [low] Public positioning (deferred to after the pilot (decision 2026-11-16)): The site root (index.html) is the earlier Canadian wastewater page, rebuilt daily by build_site.py, and does not link to HealthSignal, which lives at /briefing.html. Left unchanged for the pilot. After 2026-11-23 the direction is HealthSignal as the main offering, with the wastewater project kept as a separate archive. The GitHub repository description was set to the HealthSignal wording on 2026-11-16.

## Past week

### 2026-11-21
- Matchpoint Therapeutics Inc. reports $68.4M sold in a equity round (money): https://www.sec.gov/Archives/edgar/data/1950915/000195091526000002/0001950915-26-000002-index.htm
- Klothea Bio, Inc. amended its offering: $8.6M sold (other securities) (money): https://www.sec.gov/Archives/edgar/data/2042705/000204270526000007/0002042705-26-000007-index.htm

### 2026-11-20
- Laza Medical, Inc. reports $70.5M sold in a mixed equity and debt (money): https://www.sec.gov/Archives/edgar/data/2003996/000090514826005062/0000905148-26-005062-index.htm
- Spencer Investco, Inc. reports $10.0M sold in a equity round (money): https://www.sec.gov/Archives/edgar/data/2159762/000215976226000001/0002159762-26-000001-index.htm
- Mosaic Biosciences, Inc. reports $3.0M sold in a equity round (money): https://www.sec.gov/Archives/edgar/data/1526054/000152605426000004/0001526054-26-000004-index.htm
- Pathos AI, Inc. reports $237.5M sold in a equity round (money): https://www.sec.gov/Archives/edgar/data/1967854/000196785426000002/0001967854-26-000002-index.htm
- INFLAMMATIX, INC. reports $47.4M sold in a other securities (money): https://www.sec.gov/Archives/edgar/data/1801477/000123191926001616/0001231919-26-001616-index.htm
- Stereotaxis, Inc. reports $12.0M sold in a public-company private placement (money): https://www.sec.gov/Archives/edgar/data/1289340/000095013826000035/0000950138-26-000035-index.htm
- Anuncia Medical, Inc. amended its offering: $16.2M sold (other securities) (money): https://www.sec.gov/Archives/edgar/data/1889938/000188993826000002/0001889938-26-000002-index.htm
- RxWare, Inc. amended its offering: $6.3M sold (other securities) (money): https://www.sec.gov/Archives/edgar/data/1790134/000179013426000002/0001790134-26-000002-index.htm
- BFKW, LLC amended its offering: $2.6M sold (equity round) (money): https://www.sec.gov/Archives/edgar/data/1579495/000157949526000003/0001579495-26-000003-index.htm

### 2026-11-19
- Galvanize Therapeutics, Inc. reports $136.2M sold in a equity round (money): https://www.sec.gov/Archives/edgar/data/1659073/000165907326000004/0001659073-26-000004-index.htm
- Vesalius Longevity Labs Inc. reports $6.5M sold in a other securities (money): https://www.sec.gov/Archives/edgar/data/2131865/000106299326006173/0001062993-26-006173-index.htm
- Linnaeus Therapeutics, Inc. reports $3.7M sold in a equity round (money): https://www.sec.gov/Archives/edgar/data/1752026/000175202626000008/0001752026-26-000008-index.htm
- Ansa Biotechnologies, Inc. reports $54.4M sold in a equity round (money): https://www.sec.gov/Archives/edgar/data/1816722/000123191926001596/0001231919-26-001596-index.htm
- Rising Tide Dental Holdings, LLC reports $61.7M sold in a equity round (money): https://www.sec.gov/Archives/edgar/data/2159666/000215966626000001/0002159666-26-000001-index.htm
- Kura Oncology, Inc. reports $5.0M sold in a public-company private placement (money): https://www.sec.gov/Archives/edgar/data/1422143/000123191926001602/0001231919-26-001602-index.htm
- NewcelX Ltd. reports $2.9M sold in a public-company private placement (money): https://www.sec.gov/Archives/edgar/data/1783036/000121390026121840/0001213900-26-121840-index.htm

### 2026-11-18
- Human Biotech, Inc. reports $6.6M sold in a option-based (SAFE or warrant, not stated) (money): https://www.sec.gov/Archives/edgar/data/2126389/000212638926000004/0002126389-26-000004-index.htm
- Reach Neuro, Inc. reports $2.0M sold in a other securities (money): https://www.sec.gov/Archives/edgar/data/1942277/000194227726000004/0001942277-26-000004-index.htm
- Navierre Holdings, LLC reports $3.8M sold in a other securities (money): https://www.sec.gov/Archives/edgar/data/1909320/000190932026000008/0001909320-26-000008-index.htm

### 2026-11-17
- Cellphire, Inc. reports $6.5M sold in a equity round (money): https://www.sec.gov/Archives/edgar/data/1815181/000181518126000001/0001815181-26-000001-index.htm
- Graviton BioScience Corp reports $5.0M sold in a equity round (money): https://www.sec.gov/Archives/edgar/data/1847048/000184704826000004/0001847048-26-000004-index.htm
- Navierre Holdings, LLC reports $2.9M sold in a debt financing (money): https://www.sec.gov/Archives/edgar/data/1909320/000190932026000006/0001909320-26-000006-index.htm
- Park Dental Partners, Inc. reports $9.2M sold in a public-company private placement (money): https://www.sec.gov/Archives/edgar/data/2069604/000110465926128149/0001104659-26-128149-index.htm
- Pelthos Therapeutics Inc. reports $57.5M sold in a public-company private placement (money): https://www.sec.gov/Archives/edgar/data/1919246/000191924626000142/0001919246-26-000142-index.htm
- Adze Biotechnology Inc amended its offering: $9.3M sold (equity round) (money): https://www.sec.gov/Archives/edgar/data/1787508/000178750826000001/0001787508-26-000001-index.htm
- FDA clears PeekMed® web (Peek Health, S.A.) (rules): https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K262667
- FDA clears Clever One (Ewoosoft Co., Ltd.) (rules): https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K260372
- FDA clears CadAI-B Dx (BeamWorks, Inc.) (rules): https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K263749
- FDA clears ECG Buddy-LVD (EB-LVD-01) (ARPI, Inc.) (rules): https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K260436
- FDA clears MAGNETOM Free.XL (Siemens Healthineers AG) (rules): https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K262011


## Data quality

1 of 1 checks passed.

Build: content id a6e4a0a40b, schema 2, generated 2026-11-23T22:39Z, workflow commit 31f7fde. Copies fetched through a cache can be minutes behind; compare the content id. Machine-readable version: briefing.json.
