"""Datetime and ISO timestamp normalization utilities."""

from datetime import datetime, timezone
from typing import Union
from dateutil import parser


def utc_now() -> datetime:
    """Return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def parse_iso_timestamp(ts: Union[str, datetime]) -> datetime:
    """Safely parse an ISO string or ensure timezone awareness."""
    if isinstance(ts, datetime):
        return ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)
    parsed = parser.isoparse(ts)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def format_iso(dt: datetime) -> str:
    """Format datetime to ISO 8601 string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()

