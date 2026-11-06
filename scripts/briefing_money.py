#!/usr/bin/env python3
"""Briefing, Money section: private raises in health, from SEC Form D. Standard library only.

A company raising money privately in the US files a Form D within 15 days of the first sale.
These filings often show a raise before any press release. Steps:
  1. Read EDGAR's daily form index for each recent business day not yet processed.
  2. For every new Form D (not D/A amendments), read its primary_doc.xml.
  3. Keep health industry groups, drop pooled investment funds, keep raises at or above
     MIN_SOLD dollars actually sold.

Known blind spot: many digital health startups file under "Other Technology", not a health
group, so they are missed here. The watchlist step will cover named companies.

SEC asks automated clients to identify themselves with a contact. Set the repository secret
SEC_USER_AGENT to something like "Your Name your@email" if SEC starts refusing requests.
"""
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import timedelta

from briefing_common import get, item, load_seen, save_seen, today, write_items

HEALTH_GROUPS = {"Biotechnology", "Health Insurance", "Hospitals and Physicians",
                 "Pharmaceuticals", "Other Health Care"}
MIN_SOLD = 2_000_000
DAYS_BACK = 7            # look at most a week back; older days are dropped, not retried forever
FIRST_RUN_DAYS = 3       # the first run only looks at the last few business days
MAX_FILINGS_PER_RUN = 1500
UA = os.environ.get("SEC_USER_AGENT") or \
    "CanadaHealthSignals research bot https://github.com/fb-121/canada-health-signals"
PAUSE = 0.15             # SEC's limit is 10 requests a second; stay well under it
ROW = re.compile(r"^D\s{2,}(.+?)\s{2,}(\d+)\s+(\d{8})\s+(edgar/\S+\.txt)\s*$")


def index_url(d):
    q = (d.month - 1) // 3 + 1
    return f"https://www.sec.gov/Archives/edgar/daily-index/{d.year}/QTR{q}/form.{d:%Y%m%d}.idx"


def parse_index(text):
    """Yields (company, cik, filename) for plain Form D rows."""
    for line in text.splitlines():
        m = ROW.match(line)
        if m:
            yield m.group(1).strip(), m.group(2), m.group(4)


def doc_urls(cik, filename):
    acc = filename.rsplit("/", 1)[-1].removesuffix(".txt")
    folder = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}"
    return acc, f"{folder}/primary_doc.xml", f"{folder}/{acc}-index.htm"


def strip_ns(root):
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return root


def money(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fmt(v):
    if v is None:
        return "undisclosed"
    if v >= 1e9:
        return f"${v / 1e9:.1f}B"
    if v >= 1e6:
        return f"${v / 1e6:.1f}M"
    return f"${v:,.0f}"


def parse_form_d(xml_bytes):
    root = strip_ns(ET.fromstring(xml_bytes))
    t = lambda path: (root.findtext(path) or "").strip()
    return {
        "name": t("primaryIssuer/entityName"),
        "state": t("primaryIssuer/issuerAddress/stateOrCountryDescription")
                 or t("primaryIssuer/issuerAddress/stateOrCountry"),
        "group": t("offeringData/industryGroup/industryGroupType"),
        "fund": t("offeringData/industryGroup/investmentFundInfo/investmentFundType"),
        "pooled": t("offeringData/typesOfSecuritiesOffered/isPooledInvestmentFundType").lower() == "true",
        "amendment": t("offeringData/typeOfFiling/newOrAmendment/isAmendment").lower() == "true",
        "first_sale": t("offeringData/typeOfFiling/dateOfFirstSale/value"),
        "offering": t("offeringData/offeringSalesAmounts/totalOfferingAmount"),
        "sold": money(t("offeringData/offeringSalesAmounts/totalAmountSold")),
        "investors": t("offeringData/investors/totalNumberAlreadyInvested"),
        "equity": t("offeringData/typesOfSecuritiesOffered/isEquityType").lower() == "true",
    }


def main():
    notes, items = [], []
    done_days = load_seen("money_days")
    seen = load_seen("money_seen")
    first_run = not done_days
    span = FIRST_RUN_DAYS if first_run else DAYS_BACK
    days = [today() - timedelta(days=n) for n in range(span, 0, -1)]
    days = [d for d in days if d.isoformat() not in done_days]

    checked = kept = 0
    for d in days:
        if d.weekday() >= 5:          # EDGAR posts no index on weekends
            done_days.add(d.isoformat())
            continue
        status, body, err = get(index_url(d), ua=UA, pause=PAUSE)
        if status == 404:
            notes.append(f"{d}: no index yet (holiday, or not posted)")
            continue
        if status != 200:
            notes.append(f"{d}: index failed, {err or status}")
            continue
        rows = list(parse_index(body.decode("latin-1")))
        day_kept = day_failed = 0
        for company, cik, filename in rows:
            acc, xml_url, page_url = doc_urls(cik, filename)
            tag = f"{d.isoformat()}:{acc}"
            if tag in seen or checked >= MAX_FILINGS_PER_RUN:
                continue
            s, xb, e = get(xml_url, ua=UA, pause=PAUSE)
            checked += 1
            if s != 200:
                day_failed += 1             # left unseen, so the next run tries it again
                continue
            seen.add(tag)
            try:
                f = parse_form_d(xb)
            except ET.ParseError:
                continue
            if (f["group"] not in HEALTH_GROUPS or f["pooled"] or f["fund"]
                    or f["amendment"] or (f["sold"] or 0) < MIN_SOLD):
                continue
            offering = money(f["offering"])
            offer_txt = "open-ended" if f["offering"].lower() == "indefinite" else fmt(offering)
            items.append(item(
                "money",
                f"{f['name'] or company} raised {fmt(f['sold'])} ({f['group']})",
                f"Form D filed {d}. Sold {fmt(f['sold'])} of a {offer_txt} offering"
                + (f" to {f['investors']} investors" if f["investors"] else "")
                + (f", first sale {f['first_sale']}" if f["first_sale"] else "")
                + (f". Based in {f['state']}." if f["state"] else ".")
                + ("" if f["equity"] else " Not an equity raise (debt or other securities)."),
                page_url, d.isoformat(), f"formd:{acc}"))
            day_kept += 1
        kept += day_kept
        # A day counts as done only if every filing was read; failures get retried next run.
        if checked < MAX_FILINGS_PER_RUN and day_failed == 0:
            done_days.add(d.isoformat())
        notes.append(f"{d}: {len(rows)} Form D filings, {day_kept} health raises of {fmt(MIN_SOLD)}+"
                     + (f", {day_failed} could not be read (will retry)" if day_failed else ""))

    # Forget days and filings outside the window so the state files stay small.
    cutoff = (today() - timedelta(days=DAYS_BACK + 1)).isoformat()
    done_days = {x for x in done_days if x >= cutoff}
    seen = {x for x in seen if x[:10] >= cutoff}
    save_seen("money_days", done_days)
    save_seen("money_seen", seen)
    notes.append(f"Checked {checked} filings, {kept} items" + (" (first run)" if first_run else ""))
    write_items("money", items, notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
