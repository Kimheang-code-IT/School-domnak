import calendar
import re
from datetime import date


def parse_duration_months(value: str | None) -> int | None:
    """Parse month count from class duration (`3`, `23`, `3 months`, etc.)."""
    raw = str(value or "").strip()
    if not raw:
        return None
    match = re.match(r"^(\d+)", raw)
    if not match:
        return None
    months = int(match.group(1))
    return months if months > 0 else None


def add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(start.day, last_day))


def compute_end_date(start: date, duration_months: int) -> date:
    return add_months(start, duration_months)


def is_expiring_soon(end: date | None, *, today: date | None = None, within_days: int = 3) -> bool:
    """True when end date is today or within `within_days` (inclusive)."""
    if end is None:
        return False
    today = today or date.today()
    if end < today:
        return False
    return (end - today).days <= within_days
