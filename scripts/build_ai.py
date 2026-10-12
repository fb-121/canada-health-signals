#!/usr/bin/env python3
"""Builds docs/ai.html from data/ai/. Standard library only. Static SVG, no fetches at view time."""
import collections
import csv
import gzip
import html
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIRST = 2016
W, H = 480, 320
ML, MR, MT, MB = 40, 64, 18, 34


def load():
    with gzip.open(ROOT / "data/ai/fda_ai_devices.csv.gz", "rt", encoding="utf-8-sig") as f:
        devs = list(csv.DictReader(f))
    for d in devs:
        m, dd, y = d["Date of Final Decision"].split("/")
        d["date"] = date(int(y), int(m), int(dd))
    with (ROOT / "data/ai/year_counts.csv").open(newline="", encoding="utf-8") as f:
        counts = {int(r["year"]): r for r in csv.DictReader(f)}
    return devs, counts


def num(x):
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def line_chart(years, series, partial_year):
    """series: list of (label, css class, {year: value}). Last year drawn dashed (partial)."""
    ymax = max(v for _, _, s in series for v in s.values() if v is not None)
    top = 100 * -(-ymax // 100)
    x0, x1, y0, y1 = ML, W - MR, MT, H - MB

    def X(y):
        return x0 + (x1 - x0) * (y - years[0]) / (years[-1] - years[0])

    def Y(v):
        return y1 - (y1 - y0) * v / top

    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Line chart of FDA AI device clearances and AI randomized trials per year" class="chart">']
    for t in range(0, top + 1, 100):
        out.append(f'<line x1="{x0}" x2="{x1}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="grid"/>')
        out.append(f'<text x="{x0 - 8}" y="{Y(t) + 5:.1f}" class="tick" text-anchor="end">{t}</text>')
    for y in years:
        if (y - years[0]) % 2 == 0 or y == years[-1]:
            out.append(f'<text x="{X(y):.1f}" y="{H - 10}" class="tick" text-anchor="middle">{y}</text>')
    labels = []
    for label, cls, s in series:
        pts = [(y, s[y]) for y in years if s.get(y) is not None]
        full = pts[:-1] if pts[-1][0] == partial_year else pts
        d = " ".join(f"{'M' if i == 0 else 'L'}{X(y):.1f},{Y(v):.1f}" for i, (y, v) in enumerate(full))
        out.append(f'<path d="{d}" class="line {cls}"/>')
        if pts[-1][0] == partial_year and len(pts) > 1:
            (ya, va), (yb, vb) = pts[-2], pts[-1]
            out.append(f'<path d="M{X(ya):.1f},{Y(va):.1f} L{X(yb):.1f},{Y(vb):.1f}" class="line {cls} dash"/>')
        for y, v in full:
            out.append(f'<circle cx="{X(y):.1f}" cy="{Y(v):.1f}" r="3.5" class="dot {cls}"><title>{label}, {y}: {v}</title></circle>')
        y, v = pts[-1]
        out.append(f'<circle cx="{X(y):.1f}" cy="{Y(v):.1f}" r="3.5" class="dot hollow {cls}"><title>{label}, {y} (partial year): {v}</title></circle>')
        labels.append([Y(full[-1][1]), label, cls])
    labels.sort()
    for i in range(1, len(labels)):  # keep the two end labels from touching
        if labels[i][0] - labels[i - 1][0] < 18:
            labels[i][0] = labels[i - 1][0] + 18
    for ly, label, cls in labels:
        out.append(f'<text x="{x1 + 10}" y="{ly + 5:.1f}" class="endlabel {cls}">{html.escape(label)}</text>')
    out.append("</svg>")
    return "".join(out)


def bar_chart(items, total):
    row_h, left, right = 34, 118, 92
    h = row_h * len(items) + 8
    width = 440
    mx = max(v for _, v in items)
    out = [f'<svg viewBox="0 0 {width} {h}" role="img" aria-label="Bar chart of devices by FDA review panel" class="chart">']
    for i, (name, v) in enumerate(items):
        y = 4 + i * row_h
        bw = (width - left - right) * v / mx
        out.append(f'<text x="{left - 10}" y="{y + 20}" class="tick strong" text-anchor="end">{html.escape(name)}</text>')
        out.append(f'<rect x="{left}" y="{y + 5}" width="{bw:.1f}" height="22" rx="3" class="bar"><title>{name}: {v} devices ({100 * v / total:.0f}%)</title></rect>')
        out.append(f'<text x="{left + bw + 8:.1f}" y="{y + 21}" class="tick strong">{v:,} ({100 * v / total:.0f}%)</text>')
    out.append("</svg>")
    return "".join(out)


def main():
    devs, counts = load()
    latest = max(d["date"] for d in devs)
    cur_year = latest.year
    by_year = collections.Counter(d["date"].year for d in devs)
    years = list(range(FIRST, cur_year + 1))
    dev_s = {y: by_year.get(y, 0) for y in years}
    rct_s = {y: num(counts.get(y, {}).get("pubmed_ai_rct")) for y in years}
    all_s = {y: num(counts.get(y, {}).get("pubmed_ai_all")) for y in years}
    reg_s = {y: num(counts.get(y, {}).get("ctgov_ai")) for y in years}

    total = len(devs)
    k510 = sum(1 for d in devs if d["Submission Number"].startswith("K"))
    denovo = sum(1 for d in devs if d["Submission Number"].startswith("D"))
    pma = sum(1 for d in devs if d["Submission Number"].startswith("P"))
    panels = collections.Counter(d["Panel (Lead)"] for d in devs).most_common()
    top_panels = [(n.replace('Gastroenterology-Urology', 'Gastro-Urology'), v) for n, v in panels[:6]]
    other = sum(v for _, v in panels[6:])
    if other:
        top_panels.append(("All other panels", other))
    rad = dict(panels).get("Radiology", 0)

    full_prev = cur_year - 1
    base = 2018
    d_growth = dev_s[full_prev] / dev_s[base]
    r_growth = rct_s[full_prev] / rct_s[base]

    lede = (f"Since {base}, FDA clearances of AI-enabled devices grew {d_growth:.1f} times, from {dev_s[base]} to {dev_s[full_prev]} a year. "
            f"Published AI randomized trials grew {r_growth:.1f} times over the same period, from {rct_s[base]} to {rct_s[full_prev]}. "
            f"The two lines move together. What stands out is where the devices sit: {100 * k510 / total:.0f}% came through the 510(k) route, "
            f"and {100 * rad / total:.0f}% are radiology.")

    chart = line_chart(years, [
        ("Devices", "cur", dev_s),
        ("Trials", "prev", rct_s),
    ], cur_year)

    rows = "".join(
        f"<tr><td>{y}{' (partial)' if y == cur_year else ''}</td><td>{dev_s[y]}</td><td>{rct_s[y] if rct_s[y] is not None else '-'}</td>"
        f"<td>{all_s[y] if all_s[y] is not None else '-'}</td><td>{reg_s[y] if reg_s[y] is not None else '-'}</td></tr>"
        for y in years)

    built = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    page = TEMPLATE
    for k, v in {
        "__LEDE__": html.escape(lede),
        "__CHART__": chart,
        "__BARS__": bar_chart(top_panels, total),
        "__ROWS__": rows,
        "__TOTAL__": f"{total:,}",
        "__K510__": f"{100 * k510 / total:.0f}%",
        "__K510N__": f"{k510:,} 510(k), {denovo} De Novo, {pma} PMA",
        "__RAD__": f"{100 * rad / total:.0f}%",
        "__LATEST__": latest.strftime("%b %d, %Y").replace(" 0", " "),
        "__BUILT__": built,
        "__YEAR__": str(cur_year),
    }.items():
        page = page.replace(k, v)
    out = ROOT / "docs" / "ai.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"built {out}: {total} devices, latest decision {latest}, {len(years)} years")


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI in medicine: approvals and evidence</title>
<meta name="description" content="FDA AI-enabled device clearances per year next to published AI randomized trials, rebuilt daily from public data.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root { color-scheme: light; --surface:#fcfcfb; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781; --grid:#e1e0d9; --axis:#c3c2b7; --cur:#2a78d6; --prev:#6b6a65; }
@media (prefers-color-scheme: dark) { :root { color-scheme: dark; --surface:#1a1a19; --ink:#f0efec; --ink2:#c3c2b7; --muted:#898781; --grid:#2c2c2a; --axis:#383835; --cur:#3987e5; --prev:#a3a29a; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--surface); color:var(--ink); font-family:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif; font-size:16px; line-height:1.5; }
.wrap { max-width:880px; margin:0 auto; padding:36px 16px 72px; }
@media (min-width:700px) { .wrap { padding:56px 32px 96px; } }
.site { font-size:15px; font-weight:500; color:var(--ink2); margin:0 0 20px; }
.site a { color:inherit; }
h1 { font-size:clamp(27px,4.4vw,42px); line-height:1.16; font-weight:600; letter-spacing:-0.012em; margin:0 0 16px; max-width:20em; }
.lede { font-size:18px; color:var(--ink2); max-width:40em; margin:0 0 32px; }
.stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; margin:0 0 40px; }
.stat { border:1px solid var(--grid); border-radius:8px; padding:14px 16px; }
.stat b { display:block; font-size:28px; font-weight:600; letter-spacing:-0.01em; }
.stat span { font-size:14px; color:var(--ink2); }
h2 { font-size:20px; font-weight:600; margin:40px 0 4px; }
.sub { color:var(--ink2); font-size:15px; margin:0 0 12px; max-width:44em; }
.chart { width:100%; height:auto; display:block; overflow:visible; }
.grid { stroke:var(--grid); stroke-width:1; }
.tick { font-size:13px; fill:var(--muted); font-family:inherit; }
.tick.strong { fill:var(--ink2); font-size:14px; }
.line { fill:none; stroke-width:2.5; stroke-linecap:round; stroke-linejoin:round; }
.line.cur { stroke:var(--cur); } .line.prev { stroke:var(--prev); }
.line.dash { stroke-dasharray:4 5; }
.dot.cur { fill:var(--cur); } .dot.prev { fill:var(--prev); }
.dot.hollow { fill:var(--surface); stroke-width:2; } .dot.hollow.cur { stroke:var(--cur); } .dot.hollow.prev { stroke:var(--prev); }
.endlabel { font-size:14px; font-weight:600; font-family:inherit; } .endlabel.cur { fill:var(--cur); } .endlabel.prev { fill:var(--prev); }
.bar { fill:var(--cur); }
.key { font-size:14px; color:var(--ink2); margin:8px 0 0; }
details { margin-top:16px; } summary { cursor:pointer; font-weight:500; color:var(--ink2); }
table { border-collapse:collapse; width:100%; margin-top:12px; font-size:15px; font-variant-numeric:tabular-nums; }
th,td { text-align:right; padding:6px 8px; border-bottom:1px solid var(--grid); } th:first-child,td:first-child { text-align:left; }
th { font-weight:600; color:var(--ink2); }
.notes { margin-top:48px; font-size:14px; color:var(--ink2); max-width:46em; } .notes p { margin:0 0 10px; } .notes a { color:var(--cur); }
</style>
</head>
<body>
<div class="wrap">
<p class="site"><a href="index.html">Canada Health Signals</a> / Project two</p>
<h1>AI in medicine: approvals and evidence</h1>
<p class="lede">__LEDE__</p>

<div class="stats">
  <div class="stat"><b>__TOTAL__</b><span>AI-enabled devices on the FDA list</span></div>
  <div class="stat"><b>__K510__</b><span>cleared by 510(k) (__K510N__)</span></div>
  <div class="stat"><b>__RAD__</b><span>in radiology</span></div>
  <div class="stat"><b>__LATEST__</b><span>latest decision on the list</span></div>
</div>

<h2>Devices cleared and trials published, per year</h2>
<p class="sub">Dashed segment and hollow dots mark __YEAR__, which is a partial year. The FDA list runs to __LATEST__.</p>
__CHART__
<p class="key">Blue (Devices): FDA AI-enabled devices by decision year. Grey (Trials): PubMed randomized controlled trials indexed under artificial intelligence, machine learning or deep learning, by publication year.</p>
<details><summary>Show as a table</summary>
<table><thead><tr><th>Year</th><th>Devices cleared</th><th>AI trials (PubMed)</th><th>All AI papers (PubMed)</th><th>Registered studies mentioning AI</th></tr></thead><tbody>__ROWS__</tbody></table>
</details>

<h2>Where the devices are</h2>
<p class="sub">Lead FDA review panel for every device on the list.</p>
__BARS__

<div class="notes">
<p><b>What this does not show.</b> The trials counted here are about AI in medicine in general. They are not trials of the devices on the FDA list, and open data does not link the two. So this page cannot say how many cleared devices have trial evidence behind them.</p>
<p><b>Known limits.</b> PubMed counts rely on MeSH indexing, which lags for recent papers, so the latest years are likely undercounted. The FDA calls its list periodic and not comprehensive. A 510(k) clearance shows a device is substantially equivalent to an earlier one and usually does not need a clinical trial.</p>
<p>Sources: <a href="https://www.fda.gov/medical-devices/software-medical-device-samd/artificial-intelligence-enabled-medical-devices">FDA AI-enabled medical devices list</a>; <a href="https://pubmed.ncbi.nlm.nih.gov/">PubMed</a> via NCBI E-utilities; <a href="https://clinicaltrials.gov/">ClinicalTrials.gov</a> API. Built __BUILT__ from files archived in this repository.</p>
</div>
</div>
</body>
</html>
"""

if __name__ == "__main__":
    main()
