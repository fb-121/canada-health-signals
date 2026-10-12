#!/usr/bin/env python3
"""Builds docs/index.html from the latest archived data. Standard library only.

Reads:
  data/raw/*/phac_wastewater_aggregate.csv.gz   (latest copy)
  data/manual/qc_er_hourly_*.csv                (latest hand-saved Quebec ER hour)
Writes:
  docs/index.html   (self-contained: data is inlined, no fetches at view time)
"""
import csv
import gzip
import io
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATHOGENS = ("fluA", "covN2", "rsv", "fluB")
MIN_PRIOR_POINTS = 26  # a place needs about half a season of history to be compared


def season_year(d):
    return d.year if d.month >= 9 else d.year - 1


def sig3(x):
    return float(f"{x:.3g}")


def load_wastewater():
    files = sorted(ROOT.glob("data/raw/*/phac_wastewater_aggregate.csv.gz"))
    if not files:
        sys.exit("no wastewater snapshot found")
    with gzip.open(files[-1], "rt", encoding="utf-8", errors="ignore") as f:
        rows = list(csv.DictReader(f))

    parsed = []
    for r in rows:
        try:
            parsed.append((r["Location"], r["city"], r["province"], r["measureid"],
                           date.fromisoformat(r["weekstart"]), float(r["w_avg"])))
        except (ValueError, KeyError):
            continue
    latest = max(p[4] for p in parsed)
    current = season_year(latest)
    seasons = [current - 2, current - 1, current]
    start = date(seasons[0], 9, 1)

    groups = {}
    for loc, city, prov, m, wk, v in parsed:
        if m not in PATHOGENS or wk < start:
            continue
        if loc == "Canada":
            group = "Canada"
        elif prov and loc == prov and not city:
            group = "Province or territory"
        elif city and loc == city:
            group = "City"
        else:
            continue
        sy = season_year(wk)
        day = (wk - date(sy, 9, 1)).days
        place = groups.setdefault(loc, {"name": loc, "group": group, "series": {}})
        place["series"].setdefault(m, {}).setdefault(str(sy), []).append([day, sig3(v), wk.isoformat()])

    places = []
    for place in groups.values():
        for m in place["series"]:
            for sy in place["series"][m]:
                place["series"][m][sy].sort()
        cur_pts = [pt for m in place["series"] for pt in place["series"][m].get(str(current), [])]
        prior_a = place["series"].get("fluA", {})
        prior_n = sum(len(prior_a.get(str(s), [])) for s in seasons[:2])
        if not cur_pts or prior_n < MIN_PRIOR_POINTS:
            continue
        place["latest"] = max(pt[2] for pt in cur_pts)
        places.append(place)

    order = {"Canada": 0, "Province or territory": 1, "City": 2}
    places.sort(key=lambda p: (order[p["group"]], p["name"]))
    return {"latest": latest.isoformat(), "seasons": seasons, "current": current, "places": places}, files[-1]


SMALL = {"de", "du", "des", "la", "le", "les", "et", "en", "au", "aux"}
KEEP = {"CHUS", "CLSC", "CHSLD", "CHU", "CH"}


def nice_name(raw):
    out = []
    for i, tok in enumerate(raw.split()):
        if tok in KEEP:
            out.append(tok)
        elif i > 0 and tok.lower() in SMALL:
            out.append(tok.lower())
        else:
            out.append(tok.title())
    return " ".join(out)


def load_quebec():
    files = sorted(ROOT.glob("data/manual/qc_er_hourly_*.csv"))
    if not files:
        return None
    text = files[-1].read_bytes().decode("cp1252", errors="replace")
    rows = [r for r in csv.reader(io.StringIO(text)) if len(r) >= 9][1:]

    def num(x):
        try:
            return int(x)
        except ValueError:
            return None

    fac = []
    no_data = 0
    for r in rows:
        fun, occ = num(r[3]), num(r[4])
        if fun is None or occ is None:
            no_data += 1  # the file says "pas d'information disponible"
            continue
        if fun <= 0:
            continue  # facility with no functional stretchers, not part of the ratio
        fac.append({"name": nice_name(r[1].strip()), "occ": occ, "fun": fun,
                    "d24": num(r[5]) or 0, "d48": num(r[6]) or 0})
    stamp = datetime.fromisoformat(rows[0][8])
    top = sorted((f for f in fac if f["fun"] >= 10), key=lambda f: f["occ"] / f["fun"], reverse=True)[:10]
    return {
        "hour": rows[0][7][:5],
        "dateLabel": stamp.strftime("%b %d, %Y").replace(" 0", " "),
        "withData": len(fac),
        "noData": no_data,
        "over100": sum(1 for f in fac if f["occ"] > f["fun"]),
        "over24": sum(f["d24"] for f in fac),
        "top": [{"name": f["name"], "occ": f["occ"], "fun": f["fun"],
                 "pct": round(100 * f["occ"] / f["fun"])} for f in top],
    }


def main():
    data, src = load_wastewater()
    data["qc"] = load_quebec()
    data["built"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    template = (ROOT / "scripts" / "template.html").read_text(encoding="utf-8")
    if "__DATA__" not in template:
        sys.exit("template is missing the __DATA__ placeholder")
    out = ROOT / "docs" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(template.replace("__DATA__", payload), encoding="utf-8")
    print(f"built {out} from {src.name}: {len(data['places'])} places, {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
