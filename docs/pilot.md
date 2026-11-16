# Seven-day internal pilot

The architecture is frozen at commit `f8df353` (main, 2026-11-16) for the pilot. Any later commit that touches `scripts/`, `tests/` or `.github/` must be a fix logged in the changelog. The question is whether the real daily briefings are accurate, relevant, fresh and useful, before any expansion.

**Dates.** Seven briefings, Tuesday 2026-11-17 to Monday 2026-11-23. The briefing builds at 11:17 UTC (4:17 am Calgary). FDA documents are checked at 05:23 UTC.

**Reader.** Faaiz. Claude can prepare the official-record checks, but the scores are Faaiz's.

## What may change during the pilot

Allowed: fixes for wrong data, broken runs, security or privacy problems. Each fix gets a line in `docs/briefing-changelog.md` saying which pilot day it affects. Manual reviews (`reviews.json`) and analysis (`analysis.json`) may be added, since that is the review process under test.

Not allowed: new sources, new sections, new ranking rules, layout changes.

## Daily check, about 15 minutes

Open `briefing.html` and score each story shown in Today and Updated records. Log one row per story in `data/pilot/log.csv`.

| Column | How to score |
|--------|--------------|
| `accuracy` | Open the official record link. `correct`, `minor` (wording or a secondary field off) or `wrong` (a classification, amount, date or company is wrong). |
| `relevance` | `1` noise, `2` worth knowing, `3` would act on it or tell someone. |
| `fresh` | `yes` if the event is recent enough to matter to you. `backfill` if it is old news resurfacing. |
| `useful` | `yes` if it changed what you think or plan to do, otherwise `no`. Add a few words in `note`. |
| `minutes` | Reading time for the whole briefing (on the first row of the day only). |

Once per day also record, in a row with `story` set to `RUN`:
- whether the run happened on time and the freshness table shows no stale source or pipeline;
- the content id in the page footer, so the score is tied to one build;
- one thing you know happened in health tech that day that the briefing missed, if any (this is a coverage probe, not a new source).

## Decision at the end of day 7

| Measure | Target to keep the design |
|---------|---------------------------|
| Accuracy | No `wrong` rows. `minor` rows each have a fix logged. |
| Relevance | At least half of the shown stories score 2 or 3. |
| Freshness | Runs on time all 7 days. Backfill is under a quarter of shown stories after day 2. |
| Usefulness | At least 3 days with a `yes`. |
| Cost | Median reading time under 10 minutes. |

Meet all five: keep the design and choose the next source. Miss accuracy: fix before anything else. Miss relevance or usefulness: change ranking and filters before adding sources.
