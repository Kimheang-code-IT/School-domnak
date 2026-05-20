from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.class_model import SchoolClass
from app.models.enrollment import Enrollment
from app.models.student import Student
from app.schemas.enrollment import ClassEnrollmentRead
from app.schemas.student import format_student_code
from app.utils.enrollment_dates import (
    compute_end_date,
    is_expiring_soon,
    parse_duration_months,
)


def _resolve_start_date(enrollment: Enrollment, *, today: date) -> date:
    return enrollment.start_date or enrollment.register_date or today


def apply_enrollment_end_date(
    enrollment: Enrollment,
    school_class: SchoolClass,
    *,
    today: date | None = None,
) -> bool:
    """Set missing start/end dates from class duration. Returns True if enrollment changed."""
    today = today or date.today()
    changed = False

    if not enrollment.start_date:
        enrollment.start_date = _resolve_start_date(enrollment, today=today)
        changed = True

    if enrollment.end_date:
        return changed

    months = parse_duration_months(school_class.class_duration)
    if not months:
        return changed

    start = _resolve_start_date(enrollment, today=today)
    enrollment.end_date = compute_end_date(start, months)
    return True


def expire_past_roster_enrollments(
    db: Session,
    *,
    class_id: int | None = None,
    today: date | None = None,
) -> int:
    """Deactivate roster enrollments whose end date is before today."""
    today = today or date.today()
    statement = select(Enrollment).where(
        Enrollment.roster_active.is_(True),
        Enrollment.end_date.isnot(None),
        Enrollment.end_date < today,
    )
    if class_id is not None:
        statement = statement.where(Enrollment.class_id == class_id)

    expired = list(db.scalars(statement).all())
    for enrollment in expired:
        enrollment.roster_active = False
        enrollment.status = "Expired"
    if expired:
        db.flush()
    return len(expired)


def sync_class_roster_enrollments(
    db: Session,
    class_id: int,
    school_class: SchoolClass,
    *,
    today: date | None = None,
) -> None:
    """Backfill end dates, then remove expired students from the active roster."""
    today = today or date.today()
    active = list(
        db.scalars(
            select(Enrollment).where(
                Enrollment.class_id == class_id,
                Enrollment.roster_active.is_(True),
            )
        ).all()
    )
    changed = False
    for enrollment in active:
        if apply_enrollment_end_date(enrollment, school_class, today=today):
            changed = True
    if changed:
        db.flush()
    expire_past_roster_enrollments(db, class_id=class_id, today=today)


def to_class_enrollment_read(
    enrollment: Enrollment,
    student: Student,
    *,
    today: date | None = None,
) -> ClassEnrollmentRead:
    today = today or date.today()
    status = enrollment.status or "Active"
    expires_soon = status.lower() == "active" and is_expiring_soon(enrollment.end_date, today=today)
    return ClassEnrollmentRead(
        id=enrollment.id,
        student_id=student.id,
        student_code=format_student_code(student.id),
        student_name=student.name_en,
        name_km=student.name_km,
        name_en=student.name_en,
        gender=student.gender,
        phone=student.phone,
        birthdate=student.birthdate,
        province=student.province,
        start_date=enrollment.start_date,
        end_date=enrollment.end_date,
        startdate=enrollment.start_date,
        enddate=enrollment.end_date,
        status=status,
        expires_soon=expires_soon,
        duration_months=enrollment.duration_months,
        total_price=enrollment.total_price or Decimal("0"),
        discount_price=enrollment.discount_price or Decimal("0"),
        price_after_discount=enrollment.price_after_discount or Decimal("0"),
    )
