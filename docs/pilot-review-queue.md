# Analysis review queue

Prepared 2026-11-16 for the pilot. Four analyses in `data/briefing/analysis.json` were written by Claude and are all `reviewed: false`. This queue lists what a human reviewer should check. Claude rechecked the arithmetic below on 2026-11-16 (it is consistent with the stored figures) but did not re-open the filings, and an AI check does not count as a review. Set `reviewed: true` only after a person has opened the official records and checked every item in the "verify" column.

## 1. Nanopath (cik:0001940981), Form D 0001940981-26-000003

**Interpretation.** $29.9M sold of a $36.8M offering, flagged as both equity and debt, with no split disclosed, so it should not be read as an equity round or a valuation signal. Filed 7 days after the deadline.

**Official evidence.** Form D security-type flags (equity and debt); offering $36,760,740; sold $29,891,706; remaining $6,869,034; 21 investors; first sale 2026-10-22; signed 2026-11-10; in EDGAR's daily index 2026-11-13.

**Verify.**
- The filing date. The pipeline uses the EDGAR index date (2026-11-13), not the filing's own acceptance timestamp.
- The deadline: 2026-10-22 plus 15 days is 2026-11-06, a Friday. 7 days late is arithmetic on the index date.
- The "watch" note that the four related persons are the company's own officers and directors. Not stated anywhere else in the pipeline's data.

**Uncertainties and counterarguments.** Equity plus debt flags often mean convertible notes, which behave like an early-stage venture financing, so "not an equity round" may undersell it. A filing a week late is common and is not evidence of anything wrong.

## 2. Zai Lab (cik:0001704292), Form D 0001704292-26-000038

**Interpretation.** A private placement by a public company (Nasdaq: ZLAB), not a startup round. $249.9M sold in full to 25 investors, with a 3.0% placement fee to Leerink Partners.

**Official evidence.** EDGAR company record: ticker ZLAB, Nasdaq, SIC 2834, large accelerated filer, 10-Q filed 2026-08-06. Form D: $249,933,600 offered and sold, $0 remaining, 25 investors, commissions $7,498,008 to Leerink Partners LLC; first sale 2026-10-27; filed 2026-11-09.

**Verify.**
- The 3.0% figure is derived: $7,498,008 divided by $249,933,600 (rechecked, exactly 3.0%).
- Ticker, exchange and filer category on the EDGAR company page.
- On time: 2026-10-27 plus 15 days is 2026-11-11, a federal holiday, and the filing on 2026-11-09 is earlier still.

**Uncertainties and counterarguments.** Zai Lab may also be listed outside the US, which this pipeline does not check. The claim that this "signals institutional investor appetite for a listed biotech" is interpretation: a Form D does not name the investors.

## 3. AngioInsight (cik:0002164579), Form D 0002164579-26-000001

**Interpretation.** A SAFE round, not debt. $16.3M sold to 94 investors, with roughly $7.6M through a broker earning a 10% fee. It was filed 382 days late, so it reports a year of cumulative sales, not a raise this week.

**Official evidence.** Form D security type: only "option to acquire"; offering $20,000,000; sold $16,314,000; 94 investors; commission $760,900 to Cedar Point Capital, LLC; filer note: "10% of the proceeds received from the sale of SAFEs by the Broker"; first sale 2025-10-09; signed and filed 2026-11-10.

**Verify.**
- The filer note wording, which is the only basis for "SAFE".
- About $7.6M through the broker is derived ($760,900 divided by 10%, rechecked). It assumes the 10% applied to every broker sale.
- 382 days late: the 2025-10-24 deadline to 2026-11-10 (rechecked).

**Uncertainties and counterarguments.** "Option to acquire" can also mean warrants or options. The lateness may reflect a filing made after counsel review, and its legal effect is a question for counsel, not this briefing. Sales are cumulative from the first sale date, so the timing of the money is unknown.

## 4. BlineSlide, Deep Breathe (fda:deep-breathe), FDA K261679

**Interpretation.** FDA's own 510(k) summary calls it AI-assisted (document-supported, human check pending). The method is not settled. It was cleared against a fetal-ultrasound predicate under a product code named for cancer-lesion software. The applicant appears to be Canadian. For a founder, it is an example of a cross-specialty predicate.

**Official evidence.** FDA record K261679: received 2026-05-21, decided 2026-10-23 (155 days, rechecked), traditional 510(k), product code POK, regulation 892.2060. 510(k) summary: "AI-assisted tool" wording; predicate Sonio Suspect K243614; reference device K252007. Manual review in `reviews.json`, status `document_supported`.

**Verify.**
- Open the PDF and confirm the three quotes and pages 3, 4, 5 and 7. This is the pending human verification.
- The performance figures in the "watch" note (sensitivity 0.94, specificity 0.87 on 818 cines; reader-study AUC 0.922 vs 0.855). They were not in the manual review's quotes.
- That product code POK's official name refers to cancer lesions, and that K252007's product code is QIH.
- "Canadian company": the FDA record shows London, CA with a postal code in Canadian format. That suggests London, Ontario, but "CA" is read here as Canada and not confirmed elsewhere.

**Uncertainties and counterarguments.** The comparison table lists both computer vision and machine-learning-based algorithms, and the column mapping is unclear. "Worked example for founders" is interpretation.
