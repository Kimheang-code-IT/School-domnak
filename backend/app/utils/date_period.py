"""Date period helpers for reports and Telegram bot."""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.core.config import settings

CUSTOM_RANGE_PATTERN = re.compile(
    r"^\s*(\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})\s*$",
    re.IGNORECASE,
)


def get_app_timezone() -> ZoneInfo:
    try:
        return ZoneInfo(settings.backup_timezone)
    except Exception:
        return ZoneInfo("UTC")


def _start_of_day(d: date, tz: ZoneInfo) -> datetime:
    return datetime.combine(d, time.min, tzinfo=tz)


def _end_of_day(d: date, tz: ZoneInfo) -> datetime:
    return datetime.combine(d, time.max, tzinfo=tz)


def get_date_range_by_period(period: str) -> tuple[datetime | None, datetime | None]:
    """
    Return inclusive (start, end) datetimes in app timezone.
    all_time -> (None, None)
    custom_range -> raises ValueError; use parse_custom_date_range + dates_to_range instead.
    """
    normalized = period.strip().lower().replace("-", "_")
    if normalized in ("all_time", "all"):
        return None, None
    if normalized == "custom_range":
        raise ValueError("custom_range requires explicit start and end dates")

    tz = get_app_timezone()
    now = datetime.now(tz)
    today = now.date()

    if normalized == "today":
        return _start_of_day(today, tz), _end_of_day(today, tz)
    if normalized == "yesterday":
        day = today - timedelta(days=1)
        return _start_of_day(day, tz), _end_of_day(day, tz)
    if normalized == "this_week":
        start_day = today - timedelta(days=today.weekday())
        return _start_of_day(start_day, tz), _end_of_day(today, tz)
    if normalized == "this_month":
        start_day = today.replace(day=1)
        return _start_of_day(start_day, tz), _end_of_day(today, tz)
    if normalized == "last_month":
        first_this_month = today.replace(day=1)
        last_day_prev = first_this_month - timedelta(days=1)
        start_day = last_day_prev.replace(day=1)
        return _start_of_day(start_day, tz), _end_of_day(last_day_prev, tz)
    if normalized == "this_year":
        start_day = today.replace(month=1, day=1)
        return _start_of_day(start_day, tz), _end_of_day(today, tz)

    raise ValueError(f"Unknown period: {period}")


def dates_to_range(start: date, end: date) -> tuple[datetime, datetime]:
    if end < start:
        raise ValueError("End date must be on or after start date")
    tz = get_app_timezone()
    return _start_of_day(start, tz), _end_of_day(end, tz)


def parse_custom_date_range(text: str) -> tuple[date, date]:
    match = CUSTOM_RANGE_PATTERN.match(text or "")
    if not match:
        raise ValueError(
            "Invalid date range. Please use format:\nYYYY-MM-DD to YYYY-MM-DD"
        )
    start = date.fromisoformat(match.group(1))
    end = date.fromisoformat(match.group(2))
    if end < start:
        raise ValueError(
            "Invalid date range. Please use format:\nYYYY-MM-DD to YYYY-MM-DD"
        )
    return start, end


def format_period_label(period: str) -> str:
    labels = {
        "today": "Today",
        "yesterday": "Yesterday",
        "this_week": "This Week",
        "this_month": "This Month",
        "last_month": "Last Month",
        "this_year": "This Year",
        "all_time": "All Time",
        "custom_range": "Custom Range",
    }
    key = period.strip().lower().replace("-", "_")
    return labels.get(key, period.replace("_", " ").title())
