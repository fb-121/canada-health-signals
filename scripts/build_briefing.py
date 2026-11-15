#!/usr/bin/env python3
"""Builds docs/briefing.html, docs/briefing.md and docs/briefing.json from data/briefing/.

Standard library only, no fetches at view time. Everything on the page is either
  facts     read from an official record (the detail text, dates, amounts, document facts), or
  analysis  written by a reviewer and labelled as interpretation (data/briefing/analysis.json).

  python scripts/build_briefing.py                     writes the three files in docs/
  python scripts/build_briefing.py --fragment PATH     also writes the page body alone (for previews)
"""
import html
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from briefing_common import load_json, pdate

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "briefing"
DOCS = ROOT / "docs"
TOP_N = 7
QUOTA = {"rules": 4, "money": 3}
WEEK = 7
SCHEMA = 2

EV_LABEL = {"fda_listed": ("FDA-listed AI", "conf"), "document_verified": ("Document-verified", "conf"),
            "manufacturer_reported": ("Manufacturer-reported", "named"), "inferred": ("Inferred", "inf"),
            "unknown": ("AI unknown", "unk")}
EV_ORDER = {k: n for n, k in enumerate(EV_LABEL)}
REC_LABEL = {"new": "New", "recent": "Recent", "historical": "Historical"}
REC_ORDER = {"new": 0, "recent": 1, "historical": 2}
SECTION_TAG = {"rules": "FDA", "money": "Financing"}
FRESH = {  # source -> (status field, label, days before it counts as stale, why that long)
    "sec_form_d": ("latest_index_date", "SEC Form D daily index", 4, "posted each business day"),
    "openfda_510k": ("latest_decision_date", "openFDA 510(k) clearances", 21, "refreshed weekly, lags the FDA decision"),
    "fda_ai_device_list": ("latest_decision_date", "FDA AI-enabled device list", 180, "FDA updates it every few months"),
    "fda_510k_summaries": (None, "FDA 510(k) summaries", None, "read on demand"),
}

METHOD = {
    "what_this_is": "A daily, source-linked briefing of two kinds of public health-tech signals: FDA clearances of AI-enabled medical devices, and private financings by health companies. Built for one reader (a non-technical founder tracking US health tech). Every record links to an official source. Facts come from those records. Analysis is written by a reviewer and labelled as interpretation. Nothing here is investment or legal advice.",
    "evidence_classes": {
        "fda_listed": "On FDA's AI-enabled device list.",
        "document_verified": "FDA's 510(k) summary itself describes AI or machine learning. The summary may name the method (for example computer vision), which is recorded.",
        "manufacturer_reported": "The manufacturer's own device or company name claims AI. Not checked against FDA documents.",
        "inferred": "No document evidence. The FDA product code is AI-heavy, which is a guess.",
        "unknown": "No evidence of AI either way.",
    },
    "dates": {
        "event_date": "The underlying event: FDA decision date, or Form D first-sale date.",
        "filing_date": "When the Form D was lodged with SEC (null for FDA records).",
        "signed_date": "Date on the filer's signature (Form D).",
        "published_date": "When the official source made it public, where the source says. Null when unknown.",
        "first_detected": "The day this pipeline first saw the record.",
        "recency": "new: event within 14 days of first detection. recent: 15 to 45 days. historical: older.",
    },
    "financing_categories": "Derived from the Form D's own security-type flags, plus an EDGAR lookup. public-company private placement: the issuer has an exchange ticker in EDGAR. equity round, debt financing, mixed equity and debt, option-based or SAFE (SAFE only when the filer's note says so), other. An amendment (D/A) is an update to an offering, not a new raise.",
    "known_gaps": [
        "Many digital health startups file Form D under Other Technology, so they are missed.",
        "Form D asks for the amount sold to date. It does not say who invested or how the amount splits across securities.",
        "Form D deadline checks adjust for weekends but not federal holidays, so a filing one business day over may be on time.",
        "FDA's AI device list updates only every few months, so recent AI devices usually appear without that label.",
        "A 510(k) summary with no AI language does not prove the device has no AI. It is ranked last, not deleted.",
        "Only openFDA and SEC records are covered. There is no news, stock price or hiring data.",
        "Analysis is written for a few records so far and is not independently reviewed.",
    ],
    "source_systems": ["openFDA device 510(k) API", "FDA 510(k) summary PDFs", "FDA AI-enabled medical devices list",
                       "SEC EDGAR Form D", "SEC EDGAR company submissions"],
}

CTRL = re.compile(r"[\x00-\x1f\x7f-\x9f￼�]")


def e(s):
    """Escape for HTML and drop stray control characters that some FDA records carry."""
    return html.escape(CTRL.sub("", str(s if s is not None else "")))


# ---------- loading ----------

def load_day(d):
    items = []
    for sec in ("rules", "money"):
        items += load_json(DATA / d.isoformat() / f"{sec}.json", [])
    return [upgrade(i) for i in items]


def upgrade(i):
    """Items stored before schema 2 lack evidence, recency and dates. Fill what can be derived."""
    if i.get("schema", 1) >= 2:
        return i
    i = dict(i)
    if i["section"] == "rules":
        c = i.get("confidence")
        i.setdefault("evidence", {"confirmed": "fda_listed", "named": "manufacturer_reported"}.get(c, "inferred"))
    i.setdefault("first_detected", None)
    return i


def clean_headline(i):
    return re.sub(r", (possible )?AI device$", "", i.get("headline", ""))


def ident(i):
    if i.get("record_id"):
        return i["record_id"]
    k = i.get("key", "")
    return ("Form D " + k.split(":", 1)[1]) if k.startswith("formd:") else k.split(":", 1)[-1]


def money_fmt(v):
    if v is None:
        return "unknown"
    return f"${v / 1e9:.1f}B" if v >= 1e9 else f"${v / 1e6:.1f}M" if v >= 1e6 else f"${v:,.0f}"


def nice_date(s):
    d = pdate(s)
    return f"{d:%b} {d.day}, {d.year}" if d else "unknown"


def listed(i):
    return str(i.get("ownership", "")).startswith("listed")


def item_rank(i):
    rec = REC_ORDER.get(i.get("recency"), 3)
    if i["section"] == "rules":
        return (EV_ORDER.get(i.get("evidence"), 5), rec, -(i.get("code_ai_share") or 0))
    return (i.get("kind") == "update", listed(i), rec, -(i.get("amount") or 0))


# ---------- stories: one company, one editorial unit, individual records preserved ----------

def make_stories(items, analysis):
    groups = {}
    for i in items:
        groups.setdefault((i["section"], i.get("company_id") or i["key"]), []).append(i)
    stories = []
    for (sec, cid), its in groups.items():
        its.sort(key=item_rank)
        lead = its[0]
        name = lead.get("company") or clean_headline(lead)
        if len(its) == 1:
            headline = clean_headline(lead)
        elif sec == "rules":
            headline = f"{name}: {len(its)} FDA clearances"
        else:
            headline = f"{name}: {len(its)} filings for the same company"
        stories.append({"company_id": cid, "section": sec, "company": name, "headline": headline,
                        "records": its, "lead": lead, "analysis": analysis.get(cid)})
    stories.sort(key=lambda s: item_rank(s["lead"]))
    return stories


def pick(stories):
    top = []
    for sec, n in QUOTA.items():
        top += [s for s in stories if s["section"] == sec][:n]
    rest = [s for s in stories if s not in top]
    while len(top) < TOP_N and rest:
        top.append(rest.pop(0))
    order = list(QUOTA)
    top.sort(key=lambda s: (order.index(s["section"]), item_rank(s["lead"])))
    return top, rest


# ---------- data-quality checks ----------

def quality(items):
    """Returns (checks_run, issues). Runs on every build and is published in briefing.json."""
    issues, n = [], 0

    def check(ok, msg):
        nonlocal n
        n += 1
        if not ok:
            issues.append(msg)

    seen = {}
    for i in items:
        rid = ident(i)
        check(rid not in seen, f"duplicate record {rid}")
        seen[rid] = True
        check(bool(i.get("source_url")), f"{rid}: no source link")
        check(pdate(i.get("event_date")) is not None, f"{rid}: no event date")
        if i["section"] == "rules":
            check(i.get("evidence") in EV_LABEL, f"{rid}: unknown evidence class {i.get('evidence')}")
        if i["section"] == "money":
            check(i.get("amount") is None or i.get("offering") is None or i["amount"] <= i["offering"] * 1.001,
                  f"{rid}: sold exceeds offering")
            check(bool(i.get("category")), f"{rid}: no financing category")
            check(pdate(i.get("filing_date")) is not None, f"{rid}: no filing date")
    return n, issues


# ---------- html ----------

def chips(i):
    out = [f'<span class="chip sec-{e(i["section"])}">{e(SECTION_TAG.get(i["section"], i["section"]))}</span>']
    if i.get("recency"):
        out.append(f'<span class="chip rec-{e(i["recency"])}">{REC_LABEL[i["recency"]]}</span>')
    if i["section"] == "rules" and i.get("evidence") in EV_LABEL:
        label, cls = EV_LABEL[i["evidence"]]
        out.append(f'<span class="chip {cls}">{label}</span>')
    if i["section"] == "money":
        if i.get("kind") == "update":
            out.append('<span class="chip upd">Amendment</span>')
        if i.get("category"):
            out.append(f'<span class="chip cat">{e(i["category"])}</span>')
        if listed(i):
            out.append('<span class="chip lst">Listed company</span>')
        if i.get("late_days"):
            out.append(f'<span class="chip late">Filed {i["late_days"]} days late</span>')
        if i.get("amount") is not None:
            out.append(f'<span class="chip amt">{money_fmt(i["amount"])} sold</span>')
    return "".join(out)


def dates_line(i):
    if i["section"] == "rules":
        parts = [("Cleared", i.get("event_date")), ("Received by FDA", i.get("received_date")),
                 ("Detected", i.get("first_detected"))]
    else:
        parts = [("First sale", i.get("event_date")), ("Filed", i.get("filing_date")),
                 ("Signed", i.get("signed_date")), ("Detected", i.get("first_detected"))]
    return "".join(f'<span><span class="dl">{l}</span> {e(nice_date(v))}</span>' for l, v in parts if v)


def doc_facts(i):
    d = i.get("document") or {}
    if d.get("status") != "read":
        return ""
    rows = []
    if d.get("intended_use"):
        rows.append(f"<li><b>Intended use:</b> {e(d['intended_use'])}</li>")
    if d.get("ai_language"):
        rows.append(f"<li><b>AI language in the summary:</b> {e(', '.join(d.get('ai_terms') or ['AI']))}</li>")
    else:
        rows.append("<li><b>AI language in the summary:</b> none found</li>")
    if d.get("algorithm_methods"):
        rows.append(f"<li><b>Methods mentioned (may describe the predicate):</b> {e(', '.join(d['algorithm_methods']))}</li>")
    preds = ", ".join(d.get("predicates") or []) or "not found"
    refs = ", ".join(d.get("reference_devices") or [])
    same = d.get("same_company_devices") or []
    rows.append(f"<li><b>Predicate:</b> {e(preds)}" + (f" · <b>Reference:</b> {e(refs)}" if refs else "")
                + (f" · same company: {e(', '.join(same))}" if same else "") + "</li>")
    if d.get("pccp_mentioned"):
        rows.append("<li>Mentions a predetermined change control plan</li>")
    return (f'<div class="docfacts"><span class="label">From the FDA 510(k) summary</span><ul>{"".join(rows)}</ul>'
            f'<a href="{e(d.get("pdf_url", ""))}" target="_blank" rel="noopener">Read the summary</a></div>')


def analysis_html(a):
    if not a:
        return ""
    basis = "".join(f"<li>{e(b)}</li>" for b in a.get("basis", []))
    return (f'<div class="analysis"><span class="label">Analysis by {e(a.get("author", "Claude"))}, {e(a.get("written", ""))}. '
            f'Interpretation, not verified fact. {"Reviewed." if a.get("reviewed") else "Not yet reviewed."}</span>'
            f'<p><b>Why it matters.</b> {e(a.get("why", ""))}</p>'
            f'<p><b>Watch next.</b> {e(a.get("watch", ""))}</p>'
            + (f'<details><summary>Evidence it rests on</summary><ul>{basis}</ul></details>' if basis else "")
            + "</div>")


def record_html(i, lead=True):
    return f"""<div class="record">
  <div class="chips">{chips(i)}</div>
  {'' if lead else f'<h4>{e(clean_headline(i))}</h4>'}
  <p class="detail">{e(i.get("detail", ""))}</p>
  {doc_facts(i)}
  <p class="meta"><span class="id">{e(ident(i))}</span>{dates_line(i)}<a href="{e(i.get("source_url", ""))}" target="_blank" rel="noopener">Official record</a></p>
</div>"""


def story_card(s):
    if len(s["records"]) == 1:
        body = record_html(s["lead"])
    else:
        body = "".join(record_html(r, lead=False) for r in s["records"])
    return f'<li class="item"><h3>{e(s["headline"])}</h3>{body}{analysis_html(s["analysis"])}</li>'


def row(s):
    chip = f'<span class="chip sec-{e(s["section"])}">{e(SECTION_TAG[s["section"]])}</span>'
    return f'<li>{chip}<a href="{e(s["lead"].get("source_url", ""))}" target="_blank" rel="noopener">{e(s["headline"])}</a></li>'


def freshness_html(status, now):
    rows = []
    for src, (field, label, limit, why) in FRESH.items():
        s = status.get(src)
        if not s:
            rows.append(f"<tr><td>{e(label)}</td><td>no run recorded</td><td></td><td>{e(why)}</td></tr>")
            continue
        latest = pdate(s.get(field)) if field else None
        age = (now.date() - latest).days if latest else None
        flag = "" if age is None or limit is None else ("ok" if age <= limit else "stale")
        rows.append(f'<tr><td>{e(label)}</td><td>{e(nice_date(latest) if latest else "n/a")}</td>'
                    f'<td class="{flag}">{"" if age is None else f"{age} days old"}{" (stale)" if flag == "stale" else ""}</td>'
                    f'<td>{e(why)}</td></tr>')
    return ('<div class="scroll"><table><thead><tr><th>Source</th><th>Newest data</th><th>Age</th><th>Normal cadence</th>'
            f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def corrections_html(rows):
    if not rows:
        return '<p class="empty">No corrections logged yet.</p>'
    cut = lambda v: e((str(v)[:90] + "…") if len(str(v)) > 90 else v)
    lis = "".join(f"<li><span class='id'>{e(r['date'])}</span> {e(r['key'])}: {e(r['field'])} changed from "
                  f"{cut(r['old'])} to {cut(r['new'])}. {e(r['reason'])}.</li>" for r in rows[-12:][::-1])
    return f'<ul class="rows corr">{lis}</ul>'


STYLE = """
<title>Health Tech Morning Brief</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
/* Layout: one narrow reading column, a docket of ranked stories, the week below as a ledger. */
:root{
  --bg:#f5f7f9; --surface:#ffffff; --ink:#15202b; --muted:#5b6876; --line:#dbe2e9;
  --accent:#1f5f8b; --fda:#1f5f8b; --fda-bg:#e3eef7; --money:#7a5a12; --money-bg:#f6eedb;
  --conf:#1d6b46; --conf-bg:#ddf1e6; --inf:#6b5a8e; --inf-bg:#ece7f6; --warn:#9a4a12; --warn-bg:#fbe9d8;
  --analysis-bg:#eef2f7;
  --display:"IBM Plex Sans Condensed","Arial Narrow",system-ui,sans-serif;
  --body:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#0f151b; --surface:#161e26; --ink:#e4eaf0; --muted:#97a5b3; --line:#26323d;
  --accent:#7fb6dd; --fda:#9cc7e6; --fda-bg:#18324a; --money:#e3c27a; --money-bg:#3a2f15;
  --conf:#8fd3ad; --conf-bg:#173528; --inf:#c2b3e6; --inf-bg:#2b2440; --warn:#f0b585; --warn-bg:#40291a;
  --analysis-bg:#1b2530; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#0f151b; --surface:#161e26; --ink:#e4eaf0; --muted:#97a5b3; --line:#26323d;
  --accent:#7fb6dd; --fda:#9cc7e6; --fda-bg:#18324a; --money:#e3c27a; --money-bg:#3a2f15;
  --conf:#8fd3ad; --conf-bg:#173528; --inf:#c2b3e6; --inf-bg:#2b2440; --warn:#f0b585; --warn-bg:#40291a;
  --analysis-bg:#1b2530; color-scheme:dark}
body{background:var(--bg);color:var(--ink);font-family:var(--body);font-size:15px;line-height:1.5}
.wrap{max-width:720px;margin:0 auto;padding-block:28px 56px;
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));
  display:flex;flex-direction:column;gap:28px}
header{display:flex;flex-direction:column;gap:6px}
.kicker{font-family:var(--mono);font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
h1{font-family:var(--display);font-weight:600;font-size:clamp(28px,6vw,38px);line-height:1.1;margin:0;text-wrap:balance}
.summary{color:var(--muted);margin:0}
.summary b{color:var(--ink);font-weight:600}
h2{font-family:var(--display);font-weight:600;font-size:20px;margin:0}
section{display:flex;flex-direction:column;gap:12px}
ol,ul{list-style:none;margin:0;padding:0}
.items{display:flex;flex-direction:column;gap:12px}
.item{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:16px 18px;
  display:flex;flex-direction:column;gap:10px;min-width:0}
.item h3{font-size:16px;font-weight:600;line-height:1.35;margin:0;overflow-wrap:anywhere}
.record{display:flex;flex-direction:column;gap:6px;min-width:0}
.record+.record{border-top:1px solid var(--line);padding-top:10px}
.record h4{font-size:14.5px;font-weight:600;margin:0;overflow-wrap:anywhere}
.detail{margin:0;color:var(--muted);overflow-wrap:anywhere}
.label{font-family:var(--mono);font-size:11px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}
.docfacts{display:flex;flex-direction:column;gap:4px;font-size:13.5px}
.docfacts ul{display:flex;flex-direction:column;gap:3px;color:var(--muted)}
.docfacts b{color:var(--ink);font-weight:500}
.analysis{background:var(--analysis-bg);border-radius:6px;padding:12px 14px;display:flex;flex-direction:column;gap:6px;font-size:14px}
.analysis p{margin:0}
.analysis details{border-top:0;padding-top:0}
.analysis ul{display:flex;flex-direction:column;gap:3px;margin-top:6px;color:var(--muted);font-size:13px;list-style:disc;padding-left:18px}
.meta{margin:2px 0 0;display:flex;flex-wrap:wrap;gap:4px 14px;font-size:13px;color:var(--muted)}
.meta .dl{font-family:var(--mono);font-size:11px;text-transform:uppercase;letter-spacing:.03em}
.id{font-family:var(--mono);font-size:12.5px;font-variant-numeric:tabular-nums}
a{color:var(--accent);text-underline-offset:2px}
a:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:3px}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{font-family:var(--mono);font-size:11.5px;font-weight:500;padding:2px 8px;border-radius:4px;letter-spacing:.02em}
.sec-rules{color:var(--fda);background:var(--fda-bg)}
.sec-money{color:var(--money);background:var(--money-bg)}
.conf,.named{color:var(--conf);background:var(--conf-bg)}
.inf{color:var(--inf);background:transparent;border:1px dashed var(--inf)}
.unk{color:var(--muted);background:transparent;border:1px dashed var(--line)}
.rec-new{color:var(--conf);border:1px solid var(--conf)}
.rec-recent,.rec-historical,.amt,.cat,.upd,.lst{color:var(--muted);border:1px solid var(--line)}
.late{color:var(--warn);background:var(--warn-bg)}
.amt{font-variant-numeric:tabular-nums}
details{border-top:1px solid var(--line);padding-top:12px}
summary{cursor:pointer;color:var(--accent);font-weight:500}
.rows{display:flex;flex-direction:column;gap:8px;margin-top:12px}
.rows li{display:flex;gap:10px;align-items:baseline;min-width:0;flex-wrap:wrap}
.rows a{overflow-wrap:anywhere}
.corr li{display:block;font-size:13px;color:var(--muted)}
.day{display:grid;grid-template-columns:72px 1fr;gap:12px;padding-block:10px;border-top:1px solid var(--line)}
.day:first-child{border-top:0}
.day-date{font-family:var(--mono);font-size:13px;color:var(--muted);font-variant-numeric:tabular-nums}
.day .rows{margin:0}
.empty{background:var(--surface);border:1px dashed var(--line);border-radius:8px;padding:18px;color:var(--muted);margin:0}
.notes{font-size:13px;color:var(--muted);display:flex;flex-direction:column;gap:8px}
.notes p{margin:0;max-width:65ch}
.scroll{overflow-x:auto}
table{border-collapse:collapse;font-size:13px;min-width:480px;width:100%}
th,td{text-align:left;padding:6px 10px 6px 0;border-bottom:1px solid var(--line);vertical-align:top}
th{font-family:var(--mono);font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);font-weight:500}
td.ok{color:var(--conf)} td.stale{color:var(--warn);font-weight:600}
@media (max-width:480px){.day{grid-template-columns:1fr;gap:6px}.item{padding:14px}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
"""


def build(now=None):
    now = now or datetime.now(timezone.utc)
    today = now.date()
    analysis = load_json(DATA / "analysis.json", {})
    status = load_json(DATA / "status.json", {})
    corrections = [json.loads(l) for l in (DATA / "corrections.jsonl").read_text().splitlines() if l.strip()] \
        if (DATA / "corrections.jsonl").exists() else []
    items = load_day(today)
    stories = make_stories(items, analysis)
    top, rest = pick(stories)
    n_checks, issues = quality(items)
    n_new = sum(i.get("recency") == "new" for i in items)
    n_rules = sum(i["section"] == "rules" for i in items)
    n_money = sum(i["section"] == "money" for i in items)
    n_with_analysis = sum(1 for s in stories if s["analysis"])

    if items:
        summary = (f"<b>{len(items)}</b> records in <b>{len(stories)}</b> stories: <b>{n_rules}</b> FDA, "
                   f"<b>{n_money}</b> financing filings. <b>{n_new}</b> are new (event within 14 days of detection); "
                   f"the rest are recent or historical. Analysis written for <b>{n_with_analysis}</b> stories.")
        today_html = f'<ol class="items">{"".join(story_card(s) for s in top)}</ol>'
        if rest:
            today_html += (f'<details><summary>{len(rest)} more stories from today</summary>'
                           f'<ul class="rows">{"".join(row(s) for s in rest)}</ul></details>')
    else:
        summary = "Nothing new passed the filter today."
        today_html = '<p class="empty">No new FDA AI clearances or health financings were found since the last run.</p>'

    days = []
    for n in range(1, WEEK + 1):
        d = today - timedelta(days=n)
        its = load_day(d)
        if its:
            rows = "".join(row(s) for s in make_stories(its, analysis))
            days.append(f'<li class="day"><span class="day-date">{d:%a} {d:%b} {d.day}</span><ul class="rows">{rows}</ul></li>')
    week_html = (f'<ol>{"".join(days)}</ol>' if days
                 else '<p class="empty">The past week fills in as the daily runs build up history. Everything above was first detected today, so it includes the initial lookback.</p>')
    qual = (f"{n_checks - len(issues)} of {n_checks} data checks passed." if not issues
            else f"{len(issues)} of {n_checks} data checks flagged: " + "; ".join(issues[:4]))

    return f"""{STYLE}
<main class="wrap">
  <header>
    <span class="kicker">{today:%A}, {today:%B} {today.day}, {today.year}</span>
    <h1>Health Tech Morning Brief</h1>
    <p class="summary">{summary}</p>
  </header>
  <section aria-labelledby="t-today">
    <h2 id="t-today">Today</h2>
    {today_html}
  </section>
  <section aria-labelledby="t-week">
    <h2 id="t-week">Past week</h2>
    {week_html}
  </section>
  <section aria-labelledby="t-fresh">
    <h2 id="t-fresh">Source freshness</h2>
    {freshness_html(status, now)}
  </section>
  <section aria-labelledby="t-corr">
    <h2 id="t-corr">Corrections and changes</h2>
    {corrections_html(corrections)}
  </section>
  <section class="notes" aria-label="How this is built">
    <p><b>Facts versus analysis.</b> Everything outside the shaded analysis boxes comes from an official record. Analysis boxes are interpretation, written by a reviewer, labelled with who wrote them and whether they were reviewed.</p>
    <p><b>FDA labels.</b> FDA-listed: on FDA's AI-enabled device list. Document-verified: the FDA 510(k) summary describes AI or machine learning (the summary may name a method such as computer vision). Manufacturer-reported: the device or company name claims AI, unchecked. Inferred: a guess from an AI-heavy product code. AI unknown: no evidence either way.</p>
    <p><b>Financing labels.</b> Derived from the Form D's own security-type flags and an EDGAR lookup. A listed company's private placement is not a startup round. An amendment updates an existing offering and is not a new raise. Late means more than 15 days after the first sale, adjusted for weekends only. Startups that file under Other Technology are missed.</p>
    <p>{e(qual)} Built {now:%Y-%m-%d %H:%M} UTC from public records. Each record appears once, on the day it was first detected.</p>
  </section>
</main>
"""


# ---------- exports ----------

PUBLIC_DROP = {"schema", "briefing_date"}


def public_record(i):
    return {k: v for k, v in i.items() if k not in PUBLIC_DROP}


def export(now):
    today = now.date()
    analysis = load_json(DATA / "analysis.json", {})
    status = load_json(DATA / "status.json", {})
    items = load_day(today)
    stories = make_stories(items, analysis)
    top, rest = pick(stories)
    shown = {id(s) for s in top}
    n_checks, issues = quality(items)
    out_stories = []
    for n, s in enumerate(top + rest, 1):
        out_stories.append({"rank": n, "shown_on_page": id(s) in shown, "company_id": s["company_id"],
                            "section": s["section"], "headline": s["headline"], "analysis": s["analysis"],
                            "records": [public_record(r) for r in s["records"]]})
    flat = [{**public_record(r), "rank": st["rank"], "shown_on_page": st["shown_on_page"]}
            for st in out_stories for r in st["records"]]
    week = []
    for n in range(1, WEEK + 1):
        d = today - timedelta(days=n)
        its = load_day(d)
        if its:
            week.append({"date": d.isoformat(), "items": [public_record(i) for i in sorted(its, key=item_rank)]})
    data = {"title": "Health Tech Morning Brief", "schema_version": SCHEMA,
            "generated_utc": now.strftime("%Y-%m-%dT%H:%MZ"), "date": today.isoformat(), "method": METHOD,
            "source_freshness": status,
            "data_quality": {"checks_run": n_checks, "issues": issues},
            "today": {"count": len(items), "story_count": len(stories), "stories": out_stories, "items": flat},
            "past_week": week}
    (DOCS / "briefing.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    md = [f"# Health Tech Morning Brief, {today:%B} {today.day}, {today.year}", "", METHOD["what_this_is"], "",
          "## How to read the labels", ""]
    md += [f"- **{k}**: {v}" for k, v in METHOD["evidence_classes"].items()]
    md += [f"- **financing categories**: {METHOD['financing_categories']}"]
    md += [f"- **dates**: " + " ".join(f"{k}: {v}" for k, v in METHOD["dates"].items()), "",
           "## Known gaps", ""] + [f"- {g}" for g in METHOD["known_gaps"]]
    md += ["", f"## Source freshness", ""]
    for src, (field, label, limit, why) in FRESH.items():
        s = status.get(src, {})
        md.append(f"- {label}: newest data {s.get(field) or 'n/a'}, checked {s.get('checked_at', 'never')}")
    md += ["", f"## Today ({len(items)} records in {len(stories)} stories)", ""]
    for st in out_stories:
        md.append(f"{st['rank']}. **{st['headline']}** ({st['section']})")
        for r in st["records"]:
            tags = " | ".join(x for x in (r.get("recency"), r.get("evidence"), r.get("category"), r.get("ownership"),
                                          f"filed {r['late_days']} days late" if r.get("late_days") else None) if x)
            md.append(f"   - {r['headline']} [{tags}]")
            md.append(f"     {r['detail']}")
            md.append(f"     Dates: event {r.get('event_date')}, filed {r.get('filing_date')}, detected {r.get('first_detected')}. "
                      f"Record {ident(r)}: {r['source_url']}")
            d = r.get("document") or {}
            if d.get("status") == "read":
                md.append(f"     FDA summary: AI language={d.get('ai_language')} {d.get('ai_terms')}; methods={d.get('algorithm_methods')}; "
                          f"predicates={d.get('predicates')}; intended use: {d.get('intended_use')}")
        a = st["analysis"]
        if a:
            md.append(f"   - ANALYSIS (interpretation by {a.get('author')}, {a.get('written')}, "
                      f"{'reviewed' if a.get('reviewed') else 'not reviewed'}): why it matters: {a.get('why')} Watch next: {a.get('watch')}")
    if not out_stories:
        md.append("No new records today.")
    md += ["", "## Past week", ""]
    for day in week:
        md.append(f"### {day['date']}")
        md += [f"- {r['headline']} ({r['section']}): {r['source_url']}" for r in day["items"]]
        md.append("")
    if not week:
        md.append("History builds as daily runs accumulate. Everything above was first detected today.")
    md += ["", f"## Data quality", "", f"{n_checks - len(issues)} of {n_checks} checks passed." + (" Flagged: " + "; ".join(issues) if issues else ""),
           "", f"Generated {data['generated_utc']} from public records. Machine-readable version: briefing.json."]
    (DOCS / "briefing.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("- wrote docs/briefing.json and docs/briefing.md")


def main():
    now = datetime.now(timezone.utc)
    body = build(now)
    page = body.split(STYLE, 1)[1]
    full = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            + STYLE + '</head><body style="margin:0">' + page + '</body></html>\n')
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "briefing.html").write_text(full, encoding="utf-8")
    print(f"- wrote docs/briefing.html ({len(full):,} bytes)")
    export(now)
    if "--fragment" in sys.argv:
        Path(sys.argv[sys.argv.index("--fragment") + 1]).write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
