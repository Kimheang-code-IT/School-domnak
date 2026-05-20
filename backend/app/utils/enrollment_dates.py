import calendar
import re
from datetime import date, timedelta
from decimal import Decimal


def parse_duration_months(value: str | float | int | Decimal | None) -> float | None:
    """Parse month count (`3`, `1.5`, `3 months`, etc.)."""
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        months = float(value)
        return months if months > 0 else None
    raw = str(value).strip().replace(",", ".")
    if not raw:
        return None
    match = re.match(r"^(\d+(?:\.\d+)?)", raw)
    if not match:
        return None
    months = float(match.group(1))
    return months if months > 0 else None


def add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(start.day, last_day))


def compute_end_date(start: date, duration_months: float) -> date:
    whole = int(duration_months)
    fraction = duration_months - whole
    end = add_months(start, whole) if whole > 0 else start
    if fraction > 0:
        end = end + timedelta(days=int(round(fraction * 30)))
    return end


def resolve_enrollment_start_date(value: date | str | None, *, fallback: date | None = None) -> date:
    """Parse checkout start date; default to today."""
    if isinstance(value, date):
        return value
    if value:
        raw = str(value).strip()[:10]
        try:
            parts = raw.split("-")
            if len(parts) == 3:
                return date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (TypeError, ValueError):
            pass
    return fallback or date.today()


def prorate_class_price(
    out_price: Decimal,
    *,
    student_months: float,
    class_months: float,
) -> Decimal:
    """Scale class tuition by enrollment length vs full class duration."""
    if class_months <= 0:
        return out_price
    ratio = Decimal(str(student_months)) / Decimal(str(class_months))
    if ratio <= 0:
        return Decimal("0")
    if ratio >= 1:
        return out_price
    return (out_price * ratio).quantize(Decimal("0.01"))


def is_expiring_soon(end: date | None, *, today: date | None = None, within_days: int = 3) -> bool:
    """True when end date is today or within `within_days` (inclusive)."""
    if end is None:
        return False
    today = today or date.today()
    if end < today:
        return False
    return (end - today).days <= within_days
