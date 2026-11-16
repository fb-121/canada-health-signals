# HealthSignal seven-day pilot

The question is whether HealthSignal gives useful, accurate healthcare technology intelligence, not whether the software runs.

**Architecture freeze.** Commit `f8df353` (main, 2026-11-16) is the freeze reference. The pre-pilot operational fixes recorded in `docs/briefing-changelog.md` came after it. During the pilot, any commit touching `scripts/`, `tests/` or `.github/` must be a logged fix.

**Dates.** Seven briefings, Tuesday 2026-11-17 to Monday 2026-11-23. The briefing builds at 11:17 UTC (4:17 am Calgary). FDA documents are checked at 05:23 UTC.

**Reader and scorer.** Faaiz. Claude can prepare the operational checks and the official-record checks, but the relevance, usefulness and reading-time scores are Faaiz's.

## What may change during the pilot

Allowed: fixes for wrong data, broken runs, security or privacy problems. Each fix gets a changelog line saying which pilot day it affects. Manual reviews (`reviews.json`) and analysis (`analysis.json`) may be added or reviewed, since that is the review process under test.

Not allowed: new sources, new sections, new ranking rules, schema or layout changes. If a critical issue occurs, investigate and document it in the log. Do not change the system quietly to make a day look better.

## Daily procedure, about 15 minutes

1. **Run.** Check that the 11:17 UTC `signals` run (and the 05:23 `fda-docs` run) executed. Note the conclusion of each.
2. **Outputs.** Open `briefing.html`, `briefing.md` and `briefing.json`. Confirm they show the same content id and generation time, and that the generation time is this morning's.
3. **Status.** In `status.json`, record each source's live state, and the fixture test result separately. A source that read nothing is not a working source.
4. **Freshness.** Check the freshness table: source data age and pipeline age, separately.
5. **Records.** Note new records and records under Updated. Flag duplicates, and stories that are historical backfill rather than new events.
6. **Accuracy.** For each story shown, open the official record and check names, dates, amounts, evidence class and link. Check that interpretation is kept apart from facts.
7. **Relevance and usefulness.** Score each story, then the day.
8. **Problems.** Write down any operational problem.
9. **No changes.** No architecture or feature changes.

Log stories in `data/pilot/log.csv`, one row per story shown in Today and Updated records:

| Column | How to score |
|--------|--------------|
| `date`, `content_id` | Day and the content id in the page footer, so each score is tied to one build. |
| `story` | The story headline, or `RUN` for the day's operations row. |
| `accuracy` | `correct`, `minor` (wording or a secondary field off; needs a logged correction) or `wrong` (a classification, amount, date, company or link is wrong). |
| `relevance` | `0` irrelevant, `1` limited, `2` useful, `3` highly relevant, for health-tech founders, operators and people following medical innovation. |
| `fresh` | `new`, `backfill` (old event surfacing now) or `update` (an earlier record with new evidence). |
| `useful` | On the `RUN` row: `yes` if the day has at least one genuinely useful insight, otherwise `no`. Leave blank on story rows, or add a few words in `note`. |
| `minutes` | On the `RUN` row: time to read and understand the whole briefing. |
| `note` | Anything else: duplicates, unsupported claims, operational problems, things the briefing missed that day. |

The day's narrative goes in `docs/pilot-log.md`.

## Targets, judged on day 7

| Measure | Target |
|---------|--------|
| Accuracy | Zero known wrong records. Every `minor` has a documented correction. |
| Relevance | At least half of the stories shown score 2 or 3. |
| Freshness | All seven scheduled runs succeed. Backfill under 25% of stories shown after day 2. Pipeline success is recorded separately from source availability. |
| Usefulness | At least 3 of 7 days are `yes`. |
| Reading time | Median under 10 minutes. |

## Decision on 2026-11-23

The final evaluation covers accuracy, relevance, freshness, usefulness, reading time, operational reliability, source limitations, user experience and outstanding risks.

- **Accuracy fails:** fix accuracy before anything else.
- **Relevance or usefulness fails:** revisit filtering and ranking before adding sources.
- **Freshness fails:** fix the source or pipeline problem behind it.
- **All five met:** keep the design and consider the next source or coverage area.

Possible later directions, such as wider US coverage, Canadian health-tech intelligence and linking clearances to company activity, are not pilot work.
