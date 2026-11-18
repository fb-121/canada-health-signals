# HealthSignal, November 18, 2026

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

- SEC Form D daily index: newest source record 2026-11-17; pipeline last ran 2026-11-18T19:26Z; live request ok 238 filings read, 0 unreadable
- openFDA 510(k) clearances: newest source record 2026-11-06; pipeline last ran 2026-11-18T19:25Z; live request ok 32 clearances returned by the API
- FDA AI-enabled device list: newest source record 2026-06-29; pipeline last ran 2026-11-18T19:25Z; live request ok 1614 rows read from the FDA list
- FDA 510(k) summaries: newest source record n/a; pipeline last ran 2026-11-16T04:11Z; live request blocked FDA redirects scripts to an abuse-detection page; automated reading off, manual review in use
- Fixture unit tests (no network): 70 of 70 passed at 2026-11-18T19:25Z. This does not show any source is reachable.

## Today (3 records in 3 stories)

1. **Human Biotech, Inc. reports $6.6M sold in a option-based (SAFE or warrant, not stated)** (money)
   - Human Biotech, Inc. reports $6.6M sold in a option-based (SAFE or warrant, not stated) [recent | official filing | option-based (SAFE or warrant, not stated) | no listing or SEC reporting found (not verified private)]
     First sale 2026-11-02, filed 2026-11-17. Sold $6.6M of $10.0M offering to 3 investors. Securities: option to acquire. Ownership: no listing or SEC reporting found (not verified private).
     Dates: event 2026-11-02, filed 2026-11-17, detected 2026-11-18. Record Form D 0002126389-26-000004: https://www.sec.gov/Archives/edgar/data/2126389/000212638926000004/0002126389-26-000004-index.htm
2. **Reach Neuro, Inc. reports $2.0M sold in a other securities** (money)
   - Reach Neuro, Inc. reports $2.0M sold in a other securities [recent | official filing | other securities | no listing or SEC reporting found (not verified private) | filed 1 days late]
     First sale 2026-10-30, filed 2026-11-17, 1 days after the 2026-11-16 deadline. Sold $2.0M of $2.0M offering to 12 investors. Securities: equity, other (Conversion of SAFE's). Ownership: no listing or SEC reporting found (not verified private).
     Dates: event 2026-10-30, filed 2026-11-17, detected 2026-11-18. Record Form D 0001942277-26-000004: https://www.sec.gov/Archives/edgar/data/1942277/000194227726000004/0001942277-26-000004-index.htm
3. **Navierre Holdings, LLC reports $3.8M sold in a other securities** (money)
   - Navierre Holdings, LLC reports $3.8M sold in a other securities [historical | official filing | other securities | no listing or SEC reporting found (not verified private) | filed 1441 days late]
     First sale 2022-11-22, filed 2026-11-17, 1441 days after the 2022-12-07 deadline. Sold $3.8M of $3.8M offering to 27 investors. Securities: other (Simple Agreement for Future Equity (SAFE)). Ownership: no listing or SEC reporting found (not verified private).
     Dates: event 2022-11-22, filed 2026-11-17, detected 2026-11-18. Record Form D 0001909320-26-000008: https://www.sec.gov/Archives/edgar/data/1909320/000190932026000008/0001909320-26-000008-index.htm

## Updated records (1; updates, not new events)

- FDA clears BlineSlide (Deep Breathe, Inc.) (K261679), first reported 2026-11-15: 2026-11-16 manual_review: AI functionality: document supported (human check pending), reviewed by Claude, reading the FDA PDF through a text fetch tool
  Manual review (document_supported; human check pending; Claude, reading the FDA PDF through a text fetch tool; independent=False; verbatim checked=False): FDA's 510(k) summary for BlineSlide (Deep Breathe, Inc.) describes the device as an AI-assisted tool.
  - "an AI-assisted tool for detecting the absence of pleural line motion (lung sliding or lung pulse) in LUS cines" page 3 (510(k) Summary, device overview. Page number reported by a text fetch tool; not confirmed in a PDF viewer.)
  - "Algorithm Methodology: Computer vision; Machine Learning-Based Algorithms" page 7 (Comparison table. The table is flattened in extracted text, so it is not known which column (subject, predicate or reference device) each method belongs to.)
  - "BlineSlide is intended for use as a concurrent reading aid to assist interpreting physicians" page 4 (Indications for use. Continues onto page 5. Page reported by a text fetch tool.)
  - Caveat: The first quote supports an AI label for the subject device. The method is not settled: the table lists both computer vision and machine learning and the column mapping is unclear.
  - Caveat: Quotes and page numbers came from a text extraction, not from comparing with the PDF itself. A person should open the PDF and confirm pages 3, 4, 5 and 7.
  - Caveat: An earlier analysis said the summary lists computer vision 'not machine learning'. That was too strong and was corrected on 2026-11-16.
  Document: https://www.accessdata.fda.gov/cdrh_docs/pdf26/K261679.pdf

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

### 2026-11-15
- Transformer TX Holdings, LLC reports $4.1M sold in a equity round (money): https://www.sec.gov/Archives/edgar/data/1926580/000112329226001498/0001123292-26-001498-index.htm
- Nanopath Inc reports $29.9M sold in a mixed equity and debt (money): https://www.sec.gov/Archives/edgar/data/1940981/000194098126000003/0001940981-26-000003-index.htm
- AngioInsight, Inc. reports $16.3M sold in a SAFE (per filer note) (money): https://www.sec.gov/Archives/edgar/data/2164579/000216457926000001/0002164579-26-000001-index.htm
- Orcosa Inc. reports $6.0M sold in a equity round (money): https://www.sec.gov/Archives/edgar/data/1852165/000095015726001237/0000950157-26-001237-index.htm
- Zai Lab Ltd reports $249.9M sold in a public-company private placement (money): https://www.sec.gov/Archives/edgar/data/1704292/000170429226000038/0001704292-26-000038-index.htm
- ABVC BIOPHARMA, INC. reports $3.4M sold in a public-company private placement (money): https://www.sec.gov/Archives/edgar/data/1173313/000121390026118072/0001213900-26-118072-index.htm
- InSitu Biologics, Inc. amended its offering: $15.0M sold (other securities) (money): https://www.sec.gov/Archives/edgar/data/1723443/000172344326000008/0001723443-26-000008-index.htm
- Palomar Labs Holdings LLC amended its offering: $4.4M sold (equity round) (money): https://www.sec.gov/Archives/edgar/data/2061065/000206106526000006/0002061065-26-000006-index.htm
- FDA clears BlineSlide (Deep Breathe, Inc.) (rules): https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K261679
- FDA clears EFAI NEUROSUITE CTA LVO ASSESSMENT SYSTEM (LVO-CTA-100) (Ever Fortune.Ai, Co., Ltd.) (rules): https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K263109
- FDA clears CINA-Aneurysm+ (Avicenna.Ai) (rules): https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K262147
- FDA clears CINA-Aneurysm (Avicenna.Ai) (rules): https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K262062
- FDA clears STAR Apollo Mapping System (Rhythm AI, Ltd.) (rules): https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K263380
- FDA clears DS Core Detect (Dentsply Sirona, Inc.) (rules): https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K261072
- FDA clears AVIEW Aorta Metrics (Coreline Soft Co., Ltd.) (rules): https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K260391


## Data quality

19 of 19 checks passed.

Build: content id 5a5c316b1e, schema 2, generated 2026-11-18T19:26Z, workflow commit e0794ac. Copies fetched through a cache can be minutes behind; compare the content id. Machine-readable version: briefing.json.
