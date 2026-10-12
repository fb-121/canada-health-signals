# Canada Health Signals

A daily archive of public Canadian health signals, built entirely on open data.

Most of these feeds only show today's number. This project saves a snapshot every day, so the history builds up into a dataset that does not exist anywhere else. The first question it aims to answer: do wastewater virus levels lead ER wait times, and by how many days?

## How it works

- `scripts/probe.py` requests each source once, logs the result to `data/probe_log.csv`, and saves raw snapshots under `data/raw/YYYY-MM-DD/`.
- `.github/workflows/signals.yml` runs it daily and commits the new data.
- Sources marked `archive: False` in the script are probed only. Flip one to `True` after reading that source's terms of use.

## Data sources

Health Canada Drug Product Database, Health Canada recalls, PHAC wastewater surveillance, Environment Canada air quality (AQHI), Drug Shortages Canada, Alberta Health Services ER wait times. Each source remains subject to its own terms of use and licence.
