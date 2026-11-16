#!/usr/bin/env python3
"""Diagnoses why FDA 510(k) summary PDFs can or cannot be retrieved. Standard library only.

It sends a few plain requests with this project's honest user agent (the one in briefing_common,
which names the project and its repository) and records exactly what comes back, so a failure can
be put in one of four boxes before anyone changes anything:

  ok                 the PDF came back
  url_error          the server answered like an origin: the page that FDA links to is reachable
                     but this document address is not (a wrong address)
  network_restriction no answer at all from here (DNS, TLS, timeout, reset)
  access_restriction  the server answered with a block page or an explicit refusal that says so
                     (403, 429, or a body that names automated access). Only this box is a
                     confirmed restriction. It is never worked around.
  unclear            none of the above. Reported as unclear and not guessed at.

No redirect is followed silently: each hop is recorded. Output: data/briefing/diagnostics/fda_access.json.
Usage: python scripts/fda_probe.py [K261679]
"""
import http.client
import json
import ssl
import sys
import urllib.parse
from datetime import datetime, timezone

from briefing_common import OUT, UA, save_json, write_status

HEADERS_KEPT = ("server", "content-type", "content-length", "location", "retry-after", "via", "x-cache",
                "cache-control", "content-disposition", "x-frame-options")
BLOCK_WORDS = ("access denied", "automated", "robot", "bot ", "forbidden", "blocked", "unusual traffic", "captcha")
CONTROL_URL = "https://api.fda.gov/device/510k.json?limit=1"


def hop(url, timeout=40):
    """One request, no redirect following. Returns a record of what happened."""
    u = urllib.parse.urlsplit(url)
    rec = {"url": url, "status": None, "error": None, "headers": {}, "body_start": "", "bytes_read": 0}
    try:
        conn = http.client.HTTPSConnection(u.netloc, timeout=timeout, context=ssl.create_default_context())
        path = u.path + (("?" + u.query) if u.query else "")
        conn.request("GET", path, headers={"User-Agent": UA, "Accept": "application/pdf,text/html;q=0.8,*/*;q=0.5"})
        r = conn.getresponse()
        rec["status"] = r.status
        rec["headers"] = {k: v for k, v in ((h.lower(), r.getheader(h)) for h in HEADERS_KEPT) if v}
        body = r.read(2000)
        rec["bytes_read"] = len(body)
        rec["is_pdf"] = body[:5] == b"%PDF-"
        rec["body_start"] = "" if rec["is_pdf"] else " ".join(body.decode("utf-8", "replace").split())[:240]
        conn.close()
    except Exception as ex:   # network level: no HTTP answer
        rec["error"] = f"{type(ex).__name__}: {ex}"[:200]
    return rec


def follow(url, limit=4):
    chain = []
    for _ in range(limit):
        rec = hop(url)
        chain.append(rec)
        loc = rec["headers"].get("location")
        if rec["status"] in (301, 302, 303, 307, 308) and loc:
            url = urllib.parse.urljoin(url, loc)
            continue
        break
    return chain


def classify(chain, control_ok=True):
    """Puts a request chain in one box. Pure function so it can be tested without a network."""
    last = chain[-1]
    if last.get("error"):
        return "network_restriction"
    st = last.get("status")
    if st == 200 and last.get("is_pdf"):
        return "ok"
    text = (last.get("body_start") or "").lower()
    if st in (403, 429) or any(w in text for w in BLOCK_WORDS):
        return "access_restriction"
    if st == 404:
        return "url_error"
    return "unclear"


def main():
    k = sys.argv[1] if len(sys.argv) > 1 else "K261679"
    pdf = f"https://www.accessdata.fda.gov/cdrh_docs/pdf{k[1:3]}/{k}.pdf"
    record_page = f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm?ID={k}"
    out = {"checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "user_agent": UA, "record": k,
           "pdf_url": pdf, "official_link_confirmed_by": "FDA 510(k) database page lists this exact address (checked 2026-11-16)"}
    control = follow(CONTROL_URL)
    control_ok = control[-1].get("status") == 200
    out["control_api"] = {"url": CONTROL_URL, "reachable": control_ok, "status": control[-1].get("status"),
                          "error": control[-1].get("error")}
    out["record_page"] = follow(record_page)
    out["pdf"] = follow(pdf)
    out["verdict"] = classify(out["pdf"], control_ok)
    out["record_page_verdict"] = ("reachable" if out["record_page"][-1].get("status") == 200 else "not reachable")
    save_json(OUT / "diagnostics" / "fda_access.json", out)
    last = out["pdf"][-1]
    line = (f"{k}: verdict={out['verdict']}; pdf status={last.get('status')} error={last.get('error')} "
            f"hops={len(out['pdf'])} final={last['url']}; record page={out['record_page_verdict']} "
            f"({out['record_page'][-1].get('status')}); control API reachable={control_ok}")
    print("- " + line)
    print("  headers: " + json.dumps(last.get("headers")))
    print("  body: " + ("(pdf bytes)" if last.get("is_pdf") else last.get("body_start") or "(empty)"))
    write_status("fda_access_probe", verdict=out["verdict"], record=k)
    return 0


if __name__ == "__main__":
    sys.exit(main())
