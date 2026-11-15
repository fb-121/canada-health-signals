#!/usr/bin/env python3
"""Builds docs/briefing.html from data/briefing/. Standard library only, no fetches at view time.

The page shows today's items ranked (at most TOP_N up front, the rest one click away), then
the past week. Every item links to its official record.

  python scripts/build_briefing.py                     writes docs/briefing.html
  python scripts/build_briefing.py --fragment PATH     also writes the page body alone (for previews)
"""
import html
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "briefing"
OUT = ROOT / "docs" / "briefing.html"
TOP_N = 7
QUOTA = {"rules": 4, "money": 3}   # first pass per section; leftovers fill the remaining slots
WEEK = 7

SECTION = {"rules": ("FDA", "Rules"), "money": ("Raise", "Money")}
CONF = {"confirmed": ("Confirmed AI", "conf"), "named": ("AI named", "named"),
        "inferred": ("Possible AI", "inf")}


# ---------- loading ----------

def load_day(d):
    items = []
    for sec in ("rules", "money"):
        p = DATA / d.isoformat() / f"{sec}.json"
        if p.exists():
            try:
                items += json.loads(p.read_text(encoding="utf-8"))
            except ValueError:
                pass
    return [fill(i) for i in items]


def fill(i):
    """Older items carry facts only in their text; recover them so ranking still works."""
    if i["section"] == "rules" and "confidence" not in i:
        d = i.get("detail", "")
        i["confidence"] = ("confirmed" if "Already on FDA's AI list" in d or "Confirmed AI" in d
                           else "named" if "AI named" in d else "inferred")
        m = re.search(r"where (\d+)% of its clearances", d)
        i["share"] = int(m.group(1)) / 100 if m else None
    if i["section"] == "money" and "amount" not in i:
        m = re.search(r"raised \$([\d.]+)([MBK])", i.get("headline", ""))
        i["amount"] = float(m.group(1)) * {"K": 1e3, "M": 1e6, "B": 1e9}[m.group(2)] if m else 0
    return i


def rank_key(i):
    if i["section"] == "rules":
        order = {"confirmed": 0, "named": 1, "inferred": 2}.get(i.get("confidence"), 3)
        return (order, -(i.get("share") or 0))
    return (0, -(i.get("amount") or 0))


def pick(items):
    by = {s: sorted([i for i in items if i["section"] == s], key=rank_key) for s in QUOTA}
    top = []
    for s, n in QUOTA.items():
        top += by[s][:n]
    rest = [i for s in QUOTA for i in by[s][QUOTA[s]:]]
    rest.sort(key=lambda i: (i["section"] != "money", rank_key(i)))
    while len(top) < TOP_N and rest:
        top.append(rest.pop(0))
    order = list(QUOTA)
    top.sort(key=lambda i: (order.index(i["section"]), rank_key(i)))
    return top, rest


# ---------- rendering ----------

CTRL = re.compile(r"[\x00-\x1f\x7f-\x9f￼�]")


def e(s):
    """Escape for HTML and drop stray control characters that some FDA records carry."""
    return html.escape(CTRL.sub("", str(s)))


def clean_headline(i):
    """The chips already say how sure we are, so the headline doesn't repeat it."""
    return re.sub(r", (possible )?AI device$", "", i.get("headline", ""))


def clean_detail(i):
    """The footer already shows the record number and date, so drop them from the detail."""
    d = i.get("detail", "")
    d = re.sub(r"^510\(k\) K\d+, decided [\d-]+\. ", "", d)
    d = re.sub(r"^Form D filed [\d-]+\. ", "", d)
    d = re.sub(r"Based in ([A-Z ,.]+)\.", lambda m: f"Based in {m.group(1).title()}.", d)
    return d


def nice_date(s):
    try:
        d = date.fromisoformat(str(s)[:10])
    except ValueError:
        return e(str(s or ""))
    return f"{d:%b} {d.day}"


def money_fmt(v):
    if not v:
        return ""
    return f"${v / 1e9:.1f}B" if v >= 1e9 else f"${v / 1e6:.1f}M" if v >= 1e6 else f"${v:,.0f}"


def ident(i):
    k = i.get("key", "")
    if k.startswith("510k:") or k.startswith("fda-list:"):
        return k.split(":", 1)[1]
    if k.startswith("formd:"):
        return "Form D " + k.split(":", 1)[1]
    return k


def chips(i):
    tag, _ = SECTION.get(i["section"], (i["section"], ""))
    out = [f'<span class="chip sec-{e(i["section"])}">{e(tag)}</span>']
    if i["section"] == "rules":
        label, cls = CONF.get(i.get("confidence"), ("", ""))
        if label:
            out.append(f'<span class="chip {cls}">{label}</span>')
    if i["section"] == "money" and i.get("amount"):
        out.append(f'<span class="chip amt">{money_fmt(i["amount"])}</span>')
    return "".join(out)


def card(i):
    why = i.get("why")
    why_html = (f'<p class="why"><span class="why-label">Why it matters (Claude\'s read)</span>{e(why)}</p>'
                if why else "")
    return f"""<li class="item">
  <div class="chips">{chips(i)}</div>
  <h3>{e(clean_headline(i))}</h3>
  <p class="detail">{e(clean_detail(i))}</p>
  {why_html}
  <p class="meta"><span class="id">{e(ident(i))}</span><span>{"Cleared" if i["section"] == "rules" else "Filed"} {nice_date(i.get("event_date"))}</span><a href="{e(i.get("source_url", ""))}" target="_blank" rel="noopener">Official record</a></p>
</li>"""


def row(i):
    return (f'<li><span class="chip sec-{e(i["section"])}">{e(SECTION[i["section"]][0])}</span>'
            f'<a href="{e(i.get("source_url", ""))}" target="_blank" rel="noopener">{e(clean_headline(i))}</a></li>')


STYLE = """
<title>Health Tech Morning Brief</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
/* Layout: one narrow reading column, a docket of ranked items, the week below as a ledger. */
:root{
  --bg:#f5f7f9; --surface:#ffffff; --ink:#15202b; --muted:#5b6876; --line:#dbe2e9;
  --accent:#1f5f8b; --fda:#1f5f8b; --fda-bg:#e3eef7; --money:#7a5a12; --money-bg:#f6eedb;
  --conf:#1d6b46; --conf-bg:#ddf1e6; --inf:#6b5a8e; --inf-bg:#ece7f6;
  --display:"IBM Plex Sans Condensed","Arial Narrow",system-ui,sans-serif;
  --body:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#0f151b; --surface:#161e26; --ink:#e4eaf0; --muted:#97a5b3; --line:#26323d;
  --accent:#7fb6dd; --fda:#9cc7e6; --fda-bg:#18324a; --money:#e3c27a; --money-bg:#3a2f15;
  --conf:#8fd3ad; --conf-bg:#173528; --inf:#c2b3e6; --inf-bg:#2b2440; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#0f151b; --surface:#161e26; --ink:#e4eaf0; --muted:#97a5b3; --line:#26323d;
  --accent:#7fb6dd; --fda:#9cc7e6; --fda-bg:#18324a; --money:#e3c27a; --money-bg:#3a2f15;
  --conf:#8fd3ad; --conf-bg:#173528; --inf:#c2b3e6; --inf-bg:#2b2440; color-scheme:dark}
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
  display:flex;flex-direction:column;gap:6px;min-width:0}
.item h3{font-size:16px;font-weight:600;line-height:1.35;margin:0;overflow-wrap:anywhere}
.detail{margin:0;color:var(--muted);overflow-wrap:anywhere}
.why{margin:4px 0 0;padding-top:8px;border-top:1px dashed var(--line);display:flex;flex-direction:column;gap:2px}
.why-label{font-family:var(--mono);font-size:11px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}
.meta{margin:2px 0 0;display:flex;flex-wrap:wrap;gap:6px 16px;font-size:13px;color:var(--muted)}
.id{font-family:var(--mono);font-size:12.5px;font-variant-numeric:tabular-nums}
a{color:var(--accent);text-underline-offset:2px}
a:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:3px}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{font-family:var(--mono);font-size:11.5px;font-weight:500;padding:2px 8px;border-radius:4px;letter-spacing:.02em;white-space:nowrap}
.sec-rules{color:var(--fda);background:var(--fda-bg)}
.sec-money{color:var(--money);background:var(--money-bg)}
.conf,.named{color:var(--conf);background:var(--conf-bg)}
.inf{color:var(--inf);background:transparent;border:1px dashed var(--inf)}
.amt{color:var(--ink);background:transparent;border:1px solid var(--line);font-variant-numeric:tabular-nums}
details{border-top:1px solid var(--line);padding-top:12px}
summary{cursor:pointer;color:var(--accent);font-weight:500}
.rows{display:flex;flex-direction:column;gap:8px;margin-top:12px}
.rows li{display:flex;gap:10px;align-items:baseline;min-width:0}
.rows a{overflow-wrap:anywhere}
.day{display:grid;grid-template-columns:72px 1fr;gap:12px;padding-block:10px;border-top:1px solid var(--line)}
.day:first-child{border-top:0}
.day-date{font-family:var(--mono);font-size:13px;color:var(--muted);font-variant-numeric:tabular-nums}
.day .rows{margin:0}
.empty{background:var(--surface);border:1px dashed var(--line);border-radius:8px;padding:18px;color:var(--muted);margin:0}
.notes{font-size:13px;color:var(--muted);display:flex;flex-direction:column;gap:6px}
.notes p{margin:0;max-width:65ch}
@media (max-width:480px){.day{grid-template-columns:1fr;gap:6px}.item{padding:14px}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
"""


def build(now=None):
    now = now or datetime.now(timezone.utc)
    today = now.date()
    items = load_day(today)
    top, rest = pick(items)
    n_rules = sum(i["section"] == "rules" for i in items)
    n_money = sum(i["section"] == "money" for i in items)

    if items:
        summary = (f"<b>{len(items)}</b> new {'item' if len(items) == 1 else 'items'} passed the filter today: "
                   f"<b>{n_rules}</b> FDA, <b>{n_money}</b> private {'raise' if n_money == 1 else 'raises'}."
                   + (f" Showing the top {len(top)}." if rest else ""))
        today_html = f'<ol class="items">{"".join(card(i) for i in top)}</ol>'
        if rest:
            today_html += (f'<details><summary>{len(rest)} more from today</summary>'
                           f'<ul class="rows">{"".join(row(i) for i in rest)}</ul></details>')
    else:
        summary = "Nothing new passed the filter today."
        today_html = ('<p class="empty">No new FDA AI clearances or health raises were found since the last run. '
                      'Quiet days are normal: FDA posts clearances weekly and raises come in clumps.</p>')

    days = []
    for n in range(1, WEEK + 1):
        d = today - timedelta(days=n)
        its = load_day(d)
        if its:
            its.sort(key=lambda i: (i["section"] != "money", rank_key(i)))
            days.append(f'<li class="day"><span class="day-date">{d:%a} {d:%b} {d.day}</span>'
                        f'<ul class="rows">{"".join(row(i) for i in its)}</ul></li>')
    week_html = (f'<ol>{"".join(days)}</ol>' if days
                 else '<p class="empty">The past week fills in as the daily runs build up history.</p>')

    body = f"""{STYLE}
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
  <section class="notes" aria-label="How this is built">
    <p><b>FDA</b> items come from openFDA 510(k) clearances and FDA's AI device list. Confirmed AI means the device is on FDA's list. AI named means the device or company name says AI. Possible AI means it sits in a product category where a quarter or more of clearances since 2016 are AI, so check the record.</p>
    <p><b>Raise</b> items come from SEC Form D filings in health industry groups with at least $2M sold, excluding funds and amendments. Startups that file under Other Technology are missed.</p>
    <p>Built {now:%Y-%m-%d %H:%M} UTC from public records. Each item appears once, on the day it was first seen.</p>
  </section>
</main>
"""
    return body


METHOD = {
    "what_this_is": "A daily, source-linked briefing of two kinds of public health-tech signals: FDA clearances of AI-enabled medical devices, and private fundraising by health companies. Built for one reader (a non-technical founder tracking US health tech). Every item links to an official record. Nothing here is investment advice.",
    "sections": {
        "rules": "FDA 510(k) clearances from openFDA, plus new entries on FDA's AI-enabled device list. confidence=confirmed means the device is on FDA's AI list. named means the device or company name says AI. inferred means FDA's own data puts it in a product code where 25%+ of clearances since 2016 are AI, so AI use is a guess to verify at the record.",
        "money": "SEC Form D filings in health industry groups with at least $2M sold. Pooled investment funds and amendments are excluded. Some are debt, not equity (equity=false).",
    },
    "known_gaps": [
        "Many digital health startups file Form D under Other Technology, so they are missed.",
        "FDA's AI device list updates only every few months, so recent AI devices usually appear as inferred.",
        "No news, stock prices or hiring data yet. Only the two official feeds above.",
        "Why-it-matters lines are not written yet, so the why field is empty.",
    ],
    "source_systems": ["openFDA device 510(k) API", "FDA AI-enabled medical devices list", "SEC EDGAR Form D"],
}


def public(i, rank=None, shown=None):
    out = {"rank": rank, "shown_on_page": shown, "section": i["section"],
           "headline": clean_headline(i), "detail": clean_detail(i),
           "event_date": i.get("event_date"), "record_id": ident(i),
           "source_url": i.get("source_url"), "why": i.get("why")}
    for k in ("confidence", "share", "product_code", "amount", "industry", "equity"):
        if i.get(k) is not None:
            out[k] = i[k]
    return out


def export(now):
    today = now.date()
    items = load_day(today)
    top, rest = pick(items)
    ranked = [public(i, n + 1, True) for n, i in enumerate(top)] + \
             [public(i, len(top) + n + 1, False) for n, i in enumerate(rest)]
    week = []
    for n in range(1, WEEK + 1):
        d = today - timedelta(days=n)
        its = load_day(d)
        if its:
            its.sort(key=lambda i: (i["section"] != "money", rank_key(i)))
            week.append({"date": d.isoformat(), "items": [public(i) for i in its]})
    data = {"title": "Health Tech Morning Brief", "generated_utc": now.strftime("%Y-%m-%dT%H:%MZ"),
            "date": today.isoformat(), "method": METHOD,
            "today": {"count": len(items), "items": ranked}, "past_week": week}
    (ROOT / "docs" / "briefing.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    md = [f"# Health Tech Morning Brief, {today:%B} {today.day}, {today.year}", "",
          METHOD["what_this_is"], "", "## How to read the labels", ""]
    md += [f"- **{k}**: {v}" for k, v in METHOD["sections"].items()]
    md += ["", "## Known gaps", ""] + [f"- {g}" for g in METHOD["known_gaps"]]
    md += ["", f"## Today ({len(items)} items)", ""]
    for r in ranked:
        extra = " | ".join(x for x in (r.get("confidence"), money_fmt(r.get("amount")) or None, r.get("industry")) if x)
        md += [f"{r['rank']}. **{r['headline']}** ({r['section']}{', ' + extra if extra else ''})",
               f"   {r['detail']} Date: {r['event_date']}. Record {r['record_id']}: {r['source_url']}"]
    if not ranked:
        md.append("No new items today.")
    md += ["", "## Past week", ""]
    for day in week:
        md.append(f"### {day['date']}")
        md += [f"- {r['headline']} ({r['section']}): {r['source_url']}" for r in day["items"]]
        md.append("")
    if not week:
        md.append("History builds as daily runs accumulate.")
    md += ["", f"Generated {data['generated_utc']} from public records. Machine-readable version: briefing.json."]
    (ROOT / "docs" / "briefing.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("- wrote docs/briefing.json and docs/briefing.md")


def main():
    body = build()
    page = body.split(STYLE, 1)[1]   # title, fonts and styles belong in the head of the full page
    full = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            + STYLE + '</head><body style="margin:0">' + page + '</body></html>\n')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(full, encoding="utf-8")
    print(f"- wrote {OUT.relative_to(ROOT)} ({len(full):,} bytes)")
    export(datetime.now(timezone.utc))
    if "--fragment" in sys.argv:
        Path(sys.argv[sys.argv.index("--fragment") + 1]).write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
