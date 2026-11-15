# Health Tech Morning Brief, November 15, 2026

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

- SEC Form D daily index: newest data 2026-11-13, checked 2026-11-15T20:16Z
- openFDA 510(k) clearances: newest data 2026-10-30, checked 2026-11-15T20:12Z
- FDA AI-enabled device list: newest data 2026-06-29, checked 2026-11-15T20:12Z
- FDA 510(k) summaries: newest data n/a, checked 2026-11-15T20:12Z

## Today (15 records in 14 stories)

1. **FDA clears EFAI NEUROSUITE CTA LVO ASSESSMENT SYSTEM (LVO-CTA-100) (Ever Fortune.Ai, Co., Ltd.)** (rules)
   - FDA clears EFAI NEUROSUITE CTA LVO ASSESSMENT SYSTEM (LVO-CTA-100) (Ever Fortune.Ai, Co., Ltd.) [recent | manufacturer_reported]
     Product code QAS. The device or company name says AI. Not yet checked against FDA documents.
     Dates: event 2026-10-30, filed None, detected 2026-11-15. Record K263109: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K263109
2. **Avicenna.Ai: 2 FDA clearances** (rules)
   - FDA clears CINA-Aneurysm+ (Avicenna.Ai) [recent | manufacturer_reported]
     Product code QIH. The device or company name says AI. Not yet checked against FDA documents.
     Dates: event 2026-10-19, filed None, detected 2026-11-15. Record K262147: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K262147
   - FDA clears CINA-Aneurysm (Avicenna.Ai) [recent | manufacturer_reported]
     Product code QBS. The device or company name says AI. Not yet checked against FDA documents.
     Dates: event 2026-10-20, filed None, detected 2026-11-15. Record K262062: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K262062
3. **FDA clears STAR Apollo Mapping System (Rhythm AI, Ltd.)** (rules)
   - FDA clears STAR Apollo Mapping System (Rhythm AI, Ltd.) [recent | manufacturer_reported]
     Product code DQK. The device or company name says AI. Not yet checked against FDA documents.
     Dates: event 2026-10-23, filed None, detected 2026-11-15. Record K263380: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K263380
4. **FDA clears DS Core Detect (Dentsply Sirona, Inc.)** (rules)
   - FDA clears DS Core Detect (Dentsply Sirona, Inc.) [recent | inferred]
     Product code MYN. Not on FDA's AI list. Guess from product code MYN, where 95% of clearances since 2016 are AI.
     Dates: event 2026-10-30, filed None, detected 2026-11-15. Record K261072: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K261072
5. **Transformer TX Holdings, LLC reports $4.1M sold in a equity round** (money)
   - Transformer TX Holdings, LLC reports $4.1M sold in a equity round [new | official filing | equity round | no listing or SEC reporting found (not verified private)]
     First sale 2026-11-02, filed 2026-11-09. Sold $4.1M of $319.1M offering to 53 investors. Securities: equity. Ownership: no listing or SEC reporting found (not verified private).
     Dates: event 2026-11-02, filed 2026-11-09, detected 2026-11-15. Record Form D 0001123292-26-001498: https://www.sec.gov/Archives/edgar/data/1926580/000112329226001498/0001123292-26-001498-index.htm
6. **Nanopath Inc reports $29.9M sold in a mixed equity and debt** (money)
   - Nanopath Inc reports $29.9M sold in a mixed equity and debt [recent | official filing | mixed equity and debt | no listing or SEC reporting found (not verified private) | filed 7 days late]
     First sale 2026-10-22, filed 2026-11-13, 7 days after the 2026-11-06 deadline. Sold $29.9M of $36.8M offering to 21 investors. Securities: equity, debt. Ownership: no listing or SEC reporting found (not verified private).
     Dates: event 2026-10-22, filed 2026-11-13, detected 2026-11-15. Record Form D 0001940981-26-000003: https://www.sec.gov/Archives/edgar/data/1940981/000194098126000003/0001940981-26-000003-index.htm
   - ANALYSIS (interpretation by Claude, 2026-11-15, not reviewed): why it matters: The filing reports $29.9M sold of a $36.8M offering, tagged as both equity and debt, and it does not say how much was which. Calling it an equity raise would overstate what is known. It was filed 7 days after the 15-day deadline, which is a fact to note and not evidence of a problem. For a founder benchmarking round sizes, treat the number as total capital in a mixed offering, not as an equity valuation signal. Watch next: Whether Nanopath announces the round with investors and the instrument split. A Form D names no investors; the four related persons listed are the company's own officers and directors.
7. **AngioInsight, Inc. reports $16.3M sold in a SAFE (per filer note)** (money)
   - AngioInsight, Inc. reports $16.3M sold in a SAFE (per filer note) [historical | official filing | SAFE (per filer note) | no listing or SEC reporting found (not verified private) | filed 382 days late]
     First sale 2025-10-09, filed 2026-11-10, 382 days after the 2025-10-24 deadline. Sold $16.3M of $20.0M offering to 94 investors. Securities: option to acquire. Sales commissions $760,900 to Cedar Point Capital, LLC. Ownership: no listing or SEC reporting found (not verified private).
     Dates: event 2025-10-09, filed 2026-11-10, detected 2026-11-15. Record Form D 0002164579-26-000001: https://www.sec.gov/Archives/edgar/data/2164579/000216457926000001/0002164579-26-000001-index.htm
   - ANALYSIS (interpretation by Claude, 2026-11-15, not reviewed): why it matters: This is a startup financing, not debt: the filing tags it as an option to acquire and the broker note describes the securities as SAFEs. It reports $16.3M sold to 94 investors, and the company says a placement agent (Cedar Point Capital) earned a 10% fee on the SAFEs it sold, which implies roughly $7.6M came through that broker (derived: $760,900 divided by 10%). The first sale was 2025-10-09 and the form was signed 2026-11-10, 382 days past the 15-day deadline, so this is a year of cumulative SAFE sales reported at once, not a new raise this week. Whether the lateness has any legal consequence is a question for counsel. Watch next: Whether an amended Form D or a priced equity round follows, since SAFEs convert at the next priced round. The company's own announcements are the place to look; this pipeline does not track them.
8. **Orcosa Inc. reports $6.0M sold in a equity round** (money)
   - Orcosa Inc. reports $6.0M sold in a equity round [historical | official filing | equity round | no listing or SEC reporting found (not verified private) | filed 105 days late]
     First sale 2026-07-15, filed 2026-11-12, 105 days after the 2026-07-30 deadline. Sold $6.0M of $11.5M offering to 25 investors. Securities: equity. Ownership: no listing or SEC reporting found (not verified private).
     Dates: event 2026-07-15, filed 2026-11-12, detected 2026-11-15. Record Form D 0000950157-26-001237: https://www.sec.gov/Archives/edgar/data/1852165/000095015726001237/0000950157-26-001237-index.htm
9. **Zai Lab Ltd reports $249.9M sold in a public-company private placement** (money)
   - Zai Lab Ltd reports $249.9M sold in a public-company private placement [recent | official filing | public-company private placement | listed (Nasdaq: ZLAB)]
     First sale 2026-10-27, filed 2026-11-09. Sold $249.9M of $249.9M offering to 25 investors. Securities: equity. Sales commissions $7.5M to LEERINK PARTNERS LLC. Ownership: listed (Nasdaq: ZLAB).
     Dates: event 2026-10-27, filed 2026-11-09, detected 2026-11-15. Record Form D 0001704292-26-000038: https://www.sec.gov/Archives/edgar/data/1704292/000170429226000038/0001704292-26-000038-index.htm
   - ANALYSIS (interpretation by Claude, 2026-11-15, not reviewed): why it matters: Zai Lab has an exchange ticker (Nasdaq: ZLAB) and files 10-Qs, so this is a private placement by a public company, sold in full to 25 investors with a $7.5M placement fee to Leerink Partners (3.0% of the amount sold). It is not a startup financing and should not be used as a benchmark for early-stage rounds. It is more useful as a signal of how much capital institutional investors are putting into a listed biotech. Watch next: Any 8-K or press release describing the terms and use of proceeds. This pipeline does not read those yet.
10. **ABVC BIOPHARMA, INC. reports $3.4M sold in a public-company private placement** (money)
   - ABVC BIOPHARMA, INC. reports $3.4M sold in a public-company private placement [recent | official filing | public-company private placement | listed (Nasdaq, OTC: ABVC, ECOC)]
     First sale 2026-10-30, filed 2026-11-10. Sold $3.4M of $3.4M offering to 9 investors. Securities: debt. Sales commissions $237,125 to WallachBeth Capital, LLC. Ownership: listed (Nasdaq, OTC: ABVC, ECOC).
     Dates: event 2026-10-30, filed 2026-11-10, detected 2026-11-15. Record Form D 0001213900-26-118072: https://www.sec.gov/Archives/edgar/data/1173313/000121390026118072/0001213900-26-118072-index.htm
11. **InSitu Biologics, Inc. amended its offering: $15.0M sold (other securities)** (money)
   - InSitu Biologics, Inc. amended its offering: $15.0M sold (other securities) [historical | official filing | other securities | no listing or SEC reporting found (not verified private) | filed 1471 days late]
     First sale 2022-10-14, filed 2026-11-10, 1471 days after the 2022-10-31 deadline. Sold $15.0M of $19.8M offering to 27 investors. Securities: debt, option to acquire. Amendment to an earlier offering; the earlier amount is not in this pipeline's records. Ownership: no listing or SEC reporting found (not verified private).
     Dates: event 2022-10-14, filed 2026-11-10, detected 2026-11-15. Record Form D 0001723443-26-000008: https://www.sec.gov/Archives/edgar/data/1723443/000172344326000008/0001723443-26-000008-index.htm
12. **Palomar Labs Holdings LLC amended its offering: $4.4M sold (equity round)** (money)
   - Palomar Labs Holdings LLC amended its offering: $4.4M sold (equity round) [historical | official filing | equity round | no listing or SEC reporting found (not verified private) | filed 129 days late]
     First sale 2026-06-22, filed 2026-11-13, 129 days after the 2026-07-07 deadline. Sold $4.4M of $4.4M offering to 13 investors. Securities: equity. Amendment to an earlier offering; the earlier amount is not in this pipeline's records. Ownership: no listing or SEC reporting found (not verified private).
     Dates: event 2026-06-22, filed 2026-11-13, detected 2026-11-15. Record Form D 0002061065-26-000006: https://www.sec.gov/Archives/edgar/data/2061065/000206106526000006/0002061065-26-000006-index.htm
13. **FDA clears BlineSlide (Deep Breathe, Inc.)** (rules)
   - FDA clears BlineSlide (Deep Breathe, Inc.) [recent | inferred]
     Product code POK. Not on FDA's AI list. Guess from product code POK, where 92% of clearances since 2016 are AI.
     Dates: event 2026-10-23, filed None, detected 2026-11-15. Record K261679: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K261679
   - ANALYSIS (interpretation by Claude, 2026-11-15, not reviewed): why it matters: FDA's own summary calls BlineSlide an AI-assisted tool but lists its algorithm methodology as computer vision, not machine learning, so 'AI device' needs that qualifier. It is a reading aid for lung ultrasound (absent pleural line motion), cleared against a fetal-ultrasound predicate (Sonio Suspect, K243614) under a product code FDA names for cancer-lesion diagnostic software. The summary also cites the company's earlier BlineSlide clearance (K252007, product code QIH). The applicant's address is London, CA with a Canadian-format postal code. For a founder, it is a worked example of clearing an ultrasound AI tool through a predicate from a different specialty, and of a Canadian company doing so. Watch next: Whether FDA adds K261679 to its AI-enabled device list at the next update, and whether the summary's performance figures (standalone sensitivity 0.94, specificity 0.87 on 818 cines; reader study aided AUC 0.922 vs 0.855 unaided) show up in the company's own claims.
14. **FDA clears AVIEW Aorta Metrics (Coreline Soft Co., Ltd.)** (rules)
   - FDA clears AVIEW Aorta Metrics (Coreline Soft Co., Ltd.) [recent | inferred]
     Product code JAK. Not on FDA's AI list. Guess from product code JAK, where 35% of clearances since 2016 are AI.
     Dates: event 2026-10-16, filed None, detected 2026-11-15. Record K260391: https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID=K260391

## Past week

History builds as daily runs accumulate. Everything above was first detected today.

## Data quality

76 of 76 checks passed.

Generated 2026-11-15T20:16Z from public records. Machine-readable version: briefing.json.
