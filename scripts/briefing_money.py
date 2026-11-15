#!/usr/bin/env python3
"""Briefing, Money section: private financings in health, from SEC Form D. Standard library only.

A company selling securities privately in the US files a Form D within 15 days of the first
sale. Steps:
  1. Read EDGAR's daily form index for each recent business day not yet processed (D and D/A).
  2. For each new filing read primary_doc.xml and keep health industry groups, drop pooled
     funds, keep offerings with at least MIN_SOLD dollars sold.
  3. Classify the financing from the filing's own security-type flags, and look the company up
     in EDGAR (ticker, exchange, SIC, SEC reporting) to tell listed companies from the rest.
  4. A D/A amendment is an update to an existing offering, not a new raise.

Nothing is guessed. A field the filing leaves out stays None and shows as unknown.
Known blind spot: many digital health startups file under "Other Technology".
Set the repository secret SEC_USER_AGENT to "Your Name your@email" so SEC can identify the bot.
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from briefing_common import (OUT, days_late, form_d_deadline, get, item, iso, load_json, load_seen, pdate,
                             run_start, save_json, save_seen, today, write_items, write_status)

HEALTH_GROUPS = {"Biotechnology", "Health Insurance", "Hospitals and Physicians",
                 "Pharmaceuticals", "Other Health Care"}
MIN_SOLD = 2_000_000
DAYS_BACK = 7
MAX_FILINGS_PER_RUN = 1500
PROFILE_MAX_AGE_DAYS = 30
UA = os.environ.get("SEC_USER_AGENT") or \
    "CanadaHealthSignals research bot https://github.com/fb-121/canada-health-signals"
PAUSE = 0.15
ROW = re.compile(r"^(D/A|D)\s{2,}(.+?)\s{2,}(\d+)\s+(\d{8})\s+(edgar/\S+\.txt)\s*$")
PERIODIC = {"10-K", "10-Q", "8-K", "20-F", "6-K", "40-F", "10-KT"}

SECURITY_FLAGS = {"isEquityType": "equity", "isDebtType": "debt", "isOptionToAcquireType": "option to acquire",
                  "isSecurityToBeAcquiredUponExerciseOfOptionToAcquireType": "security from option exercise",
                  "isPooledInvestmentFundType": "pooled fund", "isTenantInCommonType": "tenant in common",
                  "isMineralPropertyType": "mineral property", "isOtherType": "other"}


def index_url(d):
    q = (d.month - 1) // 3 + 1
    return f"https://www.sec.gov/Archives/edgar/daily-index/{d.year}/QTR{q}/form.{d:%Y%m%d}.idx"


def parse_index(text):
    """Yields (form, company, cik, date_filed, filename) for Form D and D/A rows."""
    for line in text.splitlines():
        m = ROW.match(line)
        if m:
            yield m.group(1), m.group(2).strip(), m.group(3), m.group(4), m.group(5)


def doc_urls(cik, filename):
    acc = filename.rsplit("/", 1)[-1].removesuffix(".txt")
    folder = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}"
    return acc, f"{folder}/primary_doc.xml", f"{folder}/{acc}-index.htm"


def strip_ns(root):
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return root


def num(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def fmt(v):
    if v is None:
        return "unknown"
    if v >= 1e9:
        return f"${v / 1e9:.1f}B"
    if v >= 1e6:
        return f"${v / 1e6:.1f}M"
    return f"${v:,.0f}"


def parse_form_d(xml_bytes):
    """Every field the page uses, straight from the filing. Missing stays None."""
    root = strip_ns(ET.fromstring(xml_bytes))
    t = lambda path: (root.findtext(path) or "").strip() or None
    flag = lambda path: {"true": True, "false": False}.get((root.findtext(path) or "").strip().lower())
    types = [label for tag, label in SECURITY_FLAGS.items()
             if (root.findtext(f"offeringData/typesOfSecuritiesOffered/{tag}") or "").strip().lower() == "true"]
    other = t("offeringData/typesOfSecuritiesOffered/descriptionOfOtherType")
    if other and "other" in types:
        types[types.index("other")] = f"other ({other})"
    clar = [(el.text or "").strip() for el in root.iter("clarificationOfResponse") if (el.text or "").strip()]
    brokers = [(el.findtext("recipientName") or "").strip() for el in root.iter("recipient")]
    return {
        "name": t("primaryIssuer/entityName"),
        "entity_type": t("primaryIssuer/entityType"),
        "jurisdiction": t("primaryIssuer/jurisdictionOfInc"),
        "state": t("primaryIssuer/issuerAddress/stateOrCountry"),
        "state_name": t("primaryIssuer/issuerAddress/stateOrCountryDescription"),
        "group": t("offeringData/industryGroup/industryGroupType"),
        "fund": t("offeringData/industryGroup/investmentFundInfo/investmentFundType"),
        "pooled": bool(flag("offeringData/typesOfSecuritiesOffered/isPooledInvestmentFundType")),
        "amendment": bool(flag("offeringData/typeOfFiling/newOrAmendment/isAmendment")),
        "previous_accession": t("offeringData/typeOfFiling/newOrAmendment/previousAccessionNumber"),
        "first_sale": iso(t("offeringData/typeOfFiling/dateOfFirstSale/value")),
        "yet_to_occur": flag("offeringData/typeOfFiling/dateOfFirstSale/yetToOccur"),
        "security_types": types,
        "offering_raw": t("offeringData/offeringSalesAmounts/totalOfferingAmount"),
        "offering": num(t("offeringData/offeringSalesAmounts/totalOfferingAmount")),
        "sold": num(t("offeringData/offeringSalesAmounts/totalAmountSold")),
        "remaining": num(t("offeringData/offeringSalesAmounts/totalRemaining")),
        "investors": num(t("offeringData/investors/totalNumberAlreadyInvested")),
        "non_accredited": flag("offeringData/investors/hasNonAccreditedInvestors"),
        "exemptions": [(el.text or "").strip() for el in root.iter("item")
                       if re.fullmatch(r"\d\w?\w?|3C(\.\d+)?|06b|04\w?", (el.text or "").strip() or "x")],
        "commission": num(t("offeringData/salesCommissionsFindersFees/salesCommissions/dollarAmount")),
        "brokers": [b for b in brokers if b],
        "clarifications": clar,
        "signed": iso(t("signatureBlock/signature/signatureDate")),
        "revenue_range": t("offeringData/issuerSize/revenueRange"),
        "over_five_years": flag("primaryIssuer/yearOfInc/overFiveYears"),
    }


def financing_category(f, listed):
    """The financing type, from the filing's own security-type flags. Order matters:
    a listed company's private placement is its own category whatever the security."""
    types = set(x.split(" (")[0] for x in f.get("security_types", []))
    safe = any(re.search(r"\bSAFEs?\b|simple agreement", c, re.I) for c in f.get("clarifications", []))
    if listed:
        return "public-company private placement"
    if not types:
        return "unknown"
    if types <= {"option to acquire", "security from option exercise"}:
        return "SAFE (per filer note)" if safe else "option-based (SAFE or warrant, not stated)"
    if types == {"equity"}:
        return "equity round"
    if types == {"debt"}:
        return "debt financing"
    if "equity" in types and "debt" in types:
        return "mixed equity and debt"
    return "other securities"


def profile_from_submissions(data, cik10):
    """Pulls the few EDGAR facts we use from a data.sec.gov submissions record."""
    tickers = [t for t in data.get("tickers", []) if t]
    exchanges = [e for e in data.get("exchanges", []) if e]
    forms = set((data.get("filings", {}).get("recent", {}) or {}).get("form", []))
    return {"cik": cik10, "name": data.get("name"), "tickers": tickers, "exchanges": exchanges,
            "sic": data.get("sic"), "sic_description": data.get("sicDescription"),
            "state_of_incorporation": data.get("stateOfIncorporation"),
            "files_periodic_reports": bool(forms & PERIODIC),
            "fetched": today().isoformat()}


def ownership(profile):
    """Listed, SEC-reporting, or no listing found. 'Not verified private': absence of a listing
    in EDGAR is not proof a company is private."""
    if not profile:
        return "unknown (EDGAR lookup failed)"
    if profile["tickers"]:
        return f"listed ({', '.join(profile['exchanges'] or ['exchange n/a'])}: {', '.join(profile['tickers'])})"
    if profile["files_periodic_reports"]:
        return "SEC reporting company (no ticker found)"
    return "no listing or SEC reporting found (not verified private)"


def get_profile(cik, notes):
    cik10 = f"{int(cik):010d}"
    path = OUT / "companies" / f"{cik10}.json"
    cached = load_json(path, None)
    if cached and (today() - (pdate(cached.get("fetched")) or today())).days < PROFILE_MAX_AGE_DAYS:
        return cached
    status, body, err = get(f"https://data.sec.gov/submissions/CIK{cik10}.json", ua=UA, pause=PAUSE)
    if status != 200:
        notes.append(f"EDGAR company lookup failed for CIK {cik10}: {err or status}")
        return cached
    try:
        profile = profile_from_submissions(json.loads(body), cik10)
    except ValueError:
        return cached
    save_json(path, profile)
    return profile


def build_item(f, form, cik, filed, acc, page_url, profile, ledger):
    """Turns one parsed filing into a briefing item. Pure: no network."""
    listed = bool(profile and profile.get("tickers"))
    category = financing_category(f, listed)
    own = ownership(profile)
    late = days_late(f["first_sale"], filed)
    deadline = form_d_deadline(f["first_sale"])
    prev = ledger.get(f["previous_accession"]) if f["amendment"] and f["previous_accession"] else None
    types_txt = ", ".join(f["security_types"]) or "not stated"

    bits = []
    if f["first_sale"]:
        bits.append(f"First sale {f['first_sale']}, filed {iso(filed)}")
        if late:
            bits[-1] += f", {late} days after the {deadline.isoformat()} deadline"
        bits[-1] += "."
    else:
        bits.append(f"Filed {iso(filed)}; first-sale date not stated.")
    bits.append(f"Sold {fmt(f['sold'])} of {'an open-ended' if (f['offering_raw'] or '').lower() == 'indefinite' else fmt(f['offering'])} offering"
                + (f" to {int(f['investors'])} investors" if f["investors"] else "") + f". Securities: {types_txt}.")
    if f["commission"]:
        who = f" to {', '.join(f['brokers'])}" if f["brokers"] else ""
        bits.append(f"Sales commissions {fmt(f['commission'])}{who}.")
    if f["amendment"]:
        if prev and prev.get("sold") is not None and f["sold"] is not None:
            bits.append(f"Amendment: sold was {fmt(prev['sold'])} in the earlier filing ({fmt(f['sold'] - prev['sold'])} change).")
        else:
            bits.append("Amendment to an earlier offering; the earlier amount is not in this pipeline's records.")
    bits.append(f"Ownership: {own}.")

    if f["amendment"]:
        headline = f"{f['name']} amended its offering: {fmt(f['sold'])} sold ({category})"
    else:
        headline = f"{f['name']} reports {fmt(f['sold'])} sold in a {category}"
    it = item("money", headline, " ".join(bits), page_url, f["first_sale"], f"formd:{acc}",
              company_id=f"cik:{int(cik):010d}", company=f["name"], category=category, ownership=own,
              kind="update" if f["amendment"] else "new offering", amount=f["sold"], offering=f["offering"],
              remaining=f["remaining"], investors=f["investors"], industry=f["group"],
              security_types=f["security_types"], late_days=late, deadline=iso(deadline),
              entity_type=f["entity_type"], jurisdiction=f["jurisdiction"], state=f["state_name"] or f["state"],
              previous_accession=f["previous_accession"], source="SEC Form D", form=form, accession=acc,
              evidence="official filing")
    it["filing_date"] = iso(filed)
    it["published_date"] = iso(filed)
    it["signed_date"] = f["signed"]
    return it


def main():
    notes, items = [], []
    start = run_start("money")
    done_days = load_seen("money_days")
    seen = load_seen("money_seen")
    ledger = load_json(OUT / "state" / "offerings.json", {})
    days = [today() - timedelta(days=n) for n in range(DAYS_BACK, 0, -1)]
    days = [d for d in days if d.isoformat() not in done_days]

    checked = failed = 0
    last_index = None
    for d in days:
        if d.weekday() >= 5:
            done_days.add(d.isoformat())
            continue
        status, body, err = get(index_url(d), ua=UA, pause=PAUSE)
        if status == 404:
            notes.append(f"{d}: no index (holiday or not posted yet)")
            continue
        if status != 200:
            notes.append(f"{d}: index failed, {err or status}")
            failed += 1
            continue
        last_index = d
        rows = list(parse_index(body.decode("latin-1")))
        day_kept = day_failed = 0
        for form, company, cik, filed, filename in rows:
            acc, xml_url, page_url = doc_urls(cik, filename)
            tag = f"{d.isoformat()}:{acc}"
            if tag in seen or checked >= MAX_FILINGS_PER_RUN:
                continue
            s, xb, e = get(xml_url, ua=UA, pause=PAUSE)
            checked += 1
            if s != 200:
                day_failed += 1
                continue
            seen.add(tag)
            try:
                f = parse_form_d(xb)
            except ET.ParseError:
                continue
            if f["sold"] is not None and not f["pooled"]:
                ledger[acc] = {"cik": cik, "name": f["name"], "first_sale": f["first_sale"], "sold": f["sold"],
                               "offering": f["offering"], "filed": iso(filed)}
            if (f["group"] not in HEALTH_GROUPS or f["pooled"] or f["fund"] or (f["sold"] or 0) < MIN_SOLD):
                continue
            items.append(build_item(f, form, cik, filed, acc, page_url, get_profile(cik, notes), ledger))
            day_kept += 1
        if checked < MAX_FILINGS_PER_RUN and day_failed == 0:
            done_days.add(d.isoformat())
        failed += day_failed
        notes.append(f"{d}: {len(rows)} Form D/D-A filings, {day_kept} health offerings of {fmt(MIN_SOLD)}+"
                     + (f", {day_failed} unreadable (will retry)" if day_failed else ""))

    cutoff = (today() - timedelta(days=DAYS_BACK + 1)).isoformat()
    save_seen("money_days", {x for x in done_days if x >= cutoff})
    save_seen("money_seen", {x for x in seen if x[:10] >= cutoff})
    keep = (today() - timedelta(days=400)).isoformat()
    save_json(OUT / "state" / "offerings.json", {a: v for a, v in ledger.items() if (v.get("filed") or "9") >= keep})
    notes.append(f"Checked {checked} filings, {len(items)} items; pipeline first ran {start}")
    write_status("sec_form_d", latest_index_date=iso(last_index), filings_read=checked, unreadable=failed,
                 items=len(items))
    write_items("money", items, notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
