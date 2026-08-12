"""
Document metadata + freshness helpers for production ingestion.

Every ingested chunk carries governance metadata so the assistant only answers
from documents that are approved and currently in effect:

  version         document version label
  effective_date  when the document takes effect (ISO YYYY-MM-DD)
  expiry_date     when it is superseded / must not be used after (ISO)
  review_date     next scheduled review (ISO, operational)
  approval_status "approved" | "draft" | "retired"
  access_level    coarse access tag (e.g., "general", "physician", "pharmacy")
  expiry_ts       epoch seconds derived from expiry_date (for range filtering);
                  a far-future sentinel when there is no expiry.
"""
from datetime import datetime, timezone

NO_EXPIRY_TS = 4102444800  # 2100-01-01 UTC — "no expiry" sentinel


def parse_date_ts(date_str):
    """Parse a date string to epoch seconds (UTC). Returns None if unparseable/empty."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(str(date_str).strip(), fmt).replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except ValueError:
            continue
    return None


def now_ts():
    return int(datetime.now(timezone.utc).timestamp())


def build_doc_meta(version="1", effective_date=None, expiry_date=None,
                   review_date=None, approval_status="approved", access_level="general"):
    """Return the governance metadata dict merged into each chunk's payload."""
    exp_ts = parse_date_ts(expiry_date)
    return {
        "version": str(version or "1"),
        "effective_date": (effective_date or None),
        "expiry_date": (expiry_date or None),
        "review_date": (review_date or None),
        "approval_status": (approval_status or "approved").strip().lower(),
        "access_level": (access_level or "general").strip().lower(),
        "expiry_ts": exp_ts if exp_ts is not None else NO_EXPIRY_TS,
    }
