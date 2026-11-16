"""Persistent manual evidence reviews. Standard library only.

data/briefing/reviews.json holds judgements a person (or Claude, labelled as such) made by reading an
official document. It is hand-maintained and never rewritten by the daily scripts, and the build applies
it on top of whatever the automated steps derived, so a reviewed classification survives every rerun.

One review, keyed by record id (for example an FDA K number):
  status         verified      the document supports the claim  -> evidence class document_verified
                 rejected      the document does not support it  -> evidence class unknown
                 inconclusive  read, but nothing can be concluded -> automated class is left alone
  subject        what was checked (for example "AI functionality")
  claim          the one sentence being verified
  document_url   the official document (must be on an official host)
  evidence       list of {quote, page, page_basis}: short verbatim wording, the page, and how sure the page is
  reviewed_on    date of the review
  reviewer       who read the document
  independent    true only if someone other than the author of the pipeline checked it
  caveats        anything that limits the conclusion
  verbatim_checked  true only if the quotes were compared with the PDF itself
"""
from briefing_common import load_json, pdate

STATUS_TO_EVIDENCE = {"verified": "document_verified", "rejected": "unknown", "inconclusive": None}
OFFICIAL_HOSTS = ("https://www.accessdata.fda.gov/", "https://www.sec.gov/", "https://api.fda.gov/")
REQUIRED = ("status", "subject", "claim", "document_url", "evidence", "reviewed_on", "reviewer", "independent")


def load(path):
    return load_json(path, {})


def validate(reviews):
    """Returns a list of problems. Empty means every review is complete."""
    problems = []
    for rid, r in reviews.items():
        for f in REQUIRED:
            if r.get(f) in (None, "", []):
                problems.append(f"{rid}: missing {f}")
        if r.get("status") not in STATUS_TO_EVIDENCE:
            problems.append(f"{rid}: status must be one of {sorted(STATUS_TO_EVIDENCE)}")
        if not str(r.get("document_url", "")).startswith(OFFICIAL_HOSTS):
            problems.append(f"{rid}: document_url is not on an official host")
        if pdate(r.get("reviewed_on")) is None:
            problems.append(f"{rid}: reviewed_on is not a date")
        for n, ev in enumerate(r.get("evidence") or []):
            q = (ev.get("quote") or "").strip()
            if not q:
                problems.append(f"{rid}: evidence {n + 1} has no quote")
            elif len(q.split()) > 30:
                problems.append(f"{rid}: evidence {n + 1} quote is over 30 words")
            if ev.get("page") is None and not ev.get("page_basis"):
                problems.append(f"{rid}: evidence {n + 1} has no page and no note on why")
        if r.get("status") == "verified" and not r.get("evidence"):
            problems.append(f"{rid}: verified with no evidence")
    return problems


def review_for(item, reviews):
    rid = item.get("record_id")
    return reviews.get(rid) if rid else None


def apply(item, reviews):
    """Overlays a review on an item. Sets item['review'], overrides the evidence class for FDA items when
    the review is conclusive, and records the review as an update to an already-reported item.
    Returns True if the evidence class was overridden."""
    r = review_for(item, reviews)
    if not r:
        return False
    item["review"] = r
    ups = item.setdefault("updates", [])
    upd = {"date": r["reviewed_on"], "kind": "manual_review",
           "detail": f"{r['subject']}: {r['status']} by {r['reviewer']}"}
    if upd not in ups:
        ups.append(upd)
    forced = STATUS_TO_EVIDENCE.get(r["status"])
    if item.get("section") == "rules" and forced and item.get("evidence") not in (forced, "fda_listed"):
        item["evidence"] = forced
        item["evidence_source"] = "manual review"
        return True
    return False
