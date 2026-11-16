# Health Tech Morning Brief, November 16, 2026

A daily, source-linked briefing of two kinds of public health-tech signals: FDA clearances of AI-enabled medical devices, and private financings by health companies. Built for one reader (a non-technical founder tracking US health tech). Every record links to an official source. Facts come from those records. Analysis is written by a reviewer and labelled as interpretation. Nothing here is investment or legal advice.

## How to read the labels

- **fda_listed**: On FDA's AI-enabled device list.
- **document_verified**: FDA's 510(k) summary itself describes AI or machine learning. The summary may name the method (for example computer vision), which is recorded.
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

- SEC Form D daily index: newest source record n/a; pipeline last ran 2026-11-16T03:24Z; live request unproven 0 filings read, 1 unreadable
- openFDA 510(k) clearances: newest source record 2026-10-30; pipeline last ran 2026-11-16T03:21Z; live request ok 20 clearances returned by the API
- FDA AI-enabled device list: newest source record 2026-06-29; pipeline last ran 2026-11-16T03:21Z; live request ok 1614 rows read from the FDA list
- FDA 510(k) summaries: newest source record n/a; pipeline last ran 2026-11-16T03:24Z; live request failed 0 downloaded, 7 failed (HTTP 404)
- Fixture unit tests (no network): 49 of 49 passed at 2026-11-16T03:21Z. This does not show any source is reachable.

## Today (0 records in 0 stories)

No new records today.

## Updated records (1; updates, not new events)

- FDA clears BlineSlide (Deep Breathe, Inc.) (K261679), first reported 2026-11-15: 2026-11-16 manual_review: AI functionality: verified by Claude, reading the FDA PDF through a text fetch tool
  Manual review (verified, Claude, reading the FDA PDF through a text fetch tool, independent=False, verbatim checked=False): FDA's 510(k) summary for BlineSlide (Deep Breathe, Inc.) describes the device as an AI-assisted tool.
  - "an AI-assisted tool for detecting the absence of pleural line motion (lung sliding or lung pulse) in LUS cines" page 3 (510(k) Summary, device overview. Page number reported by a text fetch tool; not confirmed in a PDF viewer.)
  - "Algorithm Methodology: Computer vision; Machine Learning-Based Algorithms" page 7 (Comparison table. The table is flattened in extracted text, so it is not known which column (subject, predicate or reference device) each method belongs to.)
  - "BlineSlide is intended for use as a concurrent reading aid to assist interpreting physicians" page 4 (Indications for use. Continues onto page 5. Page reported by a text fetch tool.)
  - Caveat: The first quote supports an AI label for the subject device. The method is not settled: the table lists both computer vision and machine learning and the column mapping is unclear.
  - Caveat: Quotes and page numbers came from a text extraction, not from comparing with the PDF itself. A person should open the PDF and confirm pages 3, 4, 5 and 7.
  - Caveat: An earlier analysis said the summary lists computer vision 'not machine learning'. That was too strong and was corrected on 2026-11-16.
  Document: https://www.accessdata.fda.gov/cdrh_docs/pdf26/K261679.pdf

## Open data-quality issues

- [high] FDA 510(k) summaries (investigating): The automated reader got HTTP 404 on all 7 summary PDFs in GitHub Actions although the address matches the link on FDA's own record page. A diagnostic now records redirects, headers and body (data/briefing/diagnostics/fda_access.json). Until it is explained, document-verified labels come only from manual reviews.
- [medium] BlineSlide K261679 (open): FDA's comparison table lists computer vision and machine-learning-based algorithms, and the extracted text does not show which device each belongs to. The AI-assisted label is supported; the method is not settled. Quotes and page numbers are not yet compared with the PDF by a person.
- [low] FDA robots.txt (open): FDA's robots.txt asks for 30 seconds between requests, which the reader now follows, and names visiting hours of 23:00 to 05:00 Eastern. The daily run is at 11:17 UTC, outside those hours. The file lists no disallow rule for /cdrh_docs/.
- [medium] Public outputs (mitigated): An outside fetch of the public files returned an older version. GitHub Pages and the raw file host cache for several minutes. Each output now carries a build stamp and a content id, and a workflow job compares the live files with the built ones after every run.
- [medium] Why it matters / watch next (open): Analysis exists for four stories, all written by Claude and none independently reviewed.
- [medium] Company identity (open): FDA applicant IDs are name slugs, so spelling variants can split one company. The same company is not linked across FDA and SEC.
- [low] Form D lateness (open): Deadlines adjust for weekends, not federal holidays, so a filing one business day over may be on time.
- [medium] 510(k) summaries (open): Significant-modification analysis is not built. Only same-company reference devices and change-control-plan mentions are flagged.

## Past week

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

1 of 1 checks passed.

Build: content id dbe4df7710, schema 2, generated 2026-11-16T03:24Z, workflow commit fc9caad. Copies fetched through a cache can be minutes behind; compare the content id. Machine-readable version: briefing.json.
