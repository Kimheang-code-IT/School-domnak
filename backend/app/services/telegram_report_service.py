"""Report queries for Telegram bot (and other consumers)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.class_model import SchoolClass
from app.models.commission import Commission
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.invoice import Invoice, InvoiceLine
from app.models.student import Student
from app.models.user import User
from app.services.google_sheets_backup_service import BackupResult, run_google_sheets_backup
from app.utils.date_period import dates_to_range, format_period_label, get_date_range_by_period


def _money(value: Decimal | float | int | None) -> float:
    return float(value or 0)


def _apply_datetime_filter(column, start: datetime | None, end: datetime | None):
    clauses = []
    if start is not None:
        clauses.append(column >= start)
    if end is not None:
        clauses.append(column <= end)
    return clauses


def _enrollment_date_column():
    return cast(func.coalesce(Enrollment.register_date, cast(Enrollment.created_at, Date)), Date)


def resolve_period_range(
    period: str,
    *,
    custom_start: date | None = None,
    custom_end: date | None = None,
) -> tuple[datetime | None, datetime | None, str]:
    key = period.strip().lower().replace("-", "_")
    if key == "custom_range":
        if custom_start is None or custom_end is None:
            raise ValueError("Custom range requires start and end dates")
        start, end = dates_to_range(custom_start, custom_end)
        label = f"{custom_start.isoformat()} to {custom_end.isoformat()}"
        return start, end, label
    start, end = get_date_range_by_period(key)
    return start, end, format_period_label(key)


@dataclass
class StudentsSummary:
    total_students: int
    total_enrollments: int
    total_active_students: int
    total_inactive_students: int
    students_registered_in_period: int


def get_students_summary(
    db: Session,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> StudentsSummary:
    total_students = db.scalar(select(func.count(Student.id))) or 0

    enrollment_stmt = select(func.count(Enrollment.id))
    enroll_date = _enrollment_date_column()
    for clause in _apply_datetime_filter(enroll_date, start_date, end_date):
        enrollment_stmt = enrollment_stmt.where(clause)
    total_enrollments = db.scalar(enrollment_stmt) or 0

    active_stmt = (
        select(func.count(func.distinct(Enrollment.student_id)))
        .where(Enrollment.status == "Active", Enrollment.roster_active.is_(True))
    )
    for clause in _apply_datetime_filter(enroll_date, start_date, end_date):
        active_stmt = active_stmt.where(clause)
    total_active = db.scalar(active_stmt) or 0

    inactive_stmt = select(func.count(func.distinct(Enrollment.student_id))).where(
        (Enrollment.status != "Active") | (Enrollment.roster_active.is_(False))
    )
    for clause in _apply_datetime_filter(enroll_date, start_date, end_date):
        inactive_stmt = inactive_stmt.where(clause)
    total_inactive = db.scalar(inactive_stmt) or 0

    reg_stmt = select(func.count(Student.id))
    for clause in _apply_datetime_filter(Student.created_at, start_date, end_date):
        reg_stmt = reg_stmt.where(clause)
    registered_in_period = db.scalar(reg_stmt) or 0

    return StudentsSummary(
        total_students=total_students,
        total_enrollments=total_enrollments,
        total_active_students=total_active,
        total_inactive_students=total_inactive,
        students_registered_in_period=registered_in_period,
    )


@dataclass
class IncomeSummary:
    total_invoice: int
    subtotal: float
    discount: float
    total_income: float


def get_income_summary(
    db: Session,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> IncomeSummary:
    stmt = select(
        func.count(Invoice.id),
        func.coalesce(func.sum(Invoice.subtotal), 0),
        func.coalesce(func.sum(Invoice.discount_amount), 0),
        func.coalesce(func.sum(Invoice.total), 0),
    )
    for clause in _apply_datetime_filter(Invoice.created_at, start_date, end_date):
        stmt = stmt.where(clause)
    row = db.execute(stmt).one()
    return IncomeSummary(
        total_invoice=int(row[0] or 0),
        subtotal=_money(row[1]),
        discount=_money(row[2]),
        total_income=_money(row[3]),
    )


def _invoice_line_income_subquery(start_date: datetime | None, end_date: datetime | None):
    stmt = (
        select(
            InvoiceLine.class_id.label("class_id"),
            func.coalesce(func.sum(InvoiceLine.total), 0).label("income"),
        )
        .join(Invoice, Invoice.id == InvoiceLine.invoice_id)
        .where(InvoiceLine.class_id.isnot(None))
        .group_by(InvoiceLine.class_id)
    )
    for clause in _apply_datetime_filter(Invoice.created_at, start_date, end_date):
        stmt = stmt.where(clause)
    return stmt.subquery()


def _enrollment_counts_subquery(start_date: datetime | None, end_date: datetime | None):
    enroll_date = _enrollment_date_column()
    stmt = select(
        Enrollment.class_id.label("class_id"),
        func.count(func.distinct(Enrollment.student_id)).label("student_count"),
    ).group_by(Enrollment.class_id)
    for clause in _apply_datetime_filter(enroll_date, start_date, end_date):
        stmt = stmt.where(clause)
    return stmt.subquery()


def get_students_by_category(
    db: Session,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict[str, Any]]:
    income_sq = _invoice_line_income_subquery(start_date, end_date)
    enroll_sq = _enrollment_counts_subquery(start_date, end_date)
    stmt = (
        select(
            Category.id,
            Category.name,
            func.coalesce(func.sum(enroll_sq.c.student_count), 0),
            func.coalesce(func.sum(income_sq.c.income), 0),
        )
        .outerjoin(SchoolClass, SchoolClass.category_id == Category.id)
        .outerjoin(enroll_sq, enroll_sq.c.class_id == SchoolClass.id)
        .outerjoin(income_sq, income_sq.c.class_id == SchoolClass.id)
        .group_by(Category.id, Category.name)
        .order_by(func.coalesce(func.sum(enroll_sq.c.student_count), 0).desc())
    )
    rows = db.execute(stmt).all()
    return [
        {
            "category_id": row[0],
            "category_name": row[1],
            "total_students": int(row[2] or 0),
            "total_income": _money(row[3]),
        }
        for row in rows
    ]


def get_students_by_course(
    db: Session,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict[str, Any]]:
    income_sq = _invoice_line_income_subquery(start_date, end_date)
    enroll_sq = _enrollment_counts_subquery(start_date, end_date)
    stmt = (
        select(
            Course.id,
            Course.course_name,
            Course.course_name_km,
            func.coalesce(func.sum(enroll_sq.c.student_count), 0),
            func.coalesce(func.sum(income_sq.c.income), 0),
        )
        .outerjoin(SchoolClass, SchoolClass.course_id == Course.id)
        .outerjoin(enroll_sq, enroll_sq.c.class_id == SchoolClass.id)
        .outerjoin(income_sq, income_sq.c.class_id == SchoolClass.id)
        .group_by(Course.id, Course.course_name, Course.course_name_km)
        .order_by(func.coalesce(func.sum(enroll_sq.c.student_count), 0).desc())
    )
    rows = db.execute(stmt).all()
    return [
        {
            "course_id": row[0],
            "course_name": row[1],
            "course_name_km": row[2],
            "total_students": int(row[3] or 0),
            "total_income": _money(row[4]),
        }
        for row in rows
    ]


def get_students_by_class(
    db: Session,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict[str, Any]]:
    income_sq = _invoice_line_income_subquery(start_date, end_date)
    enroll_sq = _enrollment_counts_subquery(start_date, end_date)
    stmt = (
        select(
            SchoolClass.id,
            SchoolClass.name,
            SchoolClass.teacher_name,
            func.coalesce(enroll_sq.c.student_count, 0),
            func.coalesce(income_sq.c.income, 0),
        )
        .outerjoin(enroll_sq, enroll_sq.c.class_id == SchoolClass.id)
        .outerjoin(income_sq, income_sq.c.class_id == SchoolClass.id)
        .order_by(func.coalesce(enroll_sq.c.student_count, 0).desc())
    )
    rows = db.execute(stmt).all()
    return [
        {
            "class_id": row[0],
            "class_name": row[1],
            "teacher_name": row[2] or "—",
            "total_students": int(row[3] or 0),
            "total_income": _money(row[4]),
        }
        for row in rows
    ]


def get_students_by_teacher(
    db: Session,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict[str, Any]]:
    income_sq = _invoice_line_income_subquery(start_date, end_date)
    enroll_sq = _enrollment_counts_subquery(start_date, end_date)
    teacher_key = func.coalesce(User.name, SchoolClass.teacher_name, "Unknown")
    stmt = (
        select(
            User.id,
            teacher_key,
            func.coalesce(func.sum(enroll_sq.c.student_count), 0),
            func.coalesce(func.sum(income_sq.c.income), 0),
        )
        .select_from(SchoolClass)
        .outerjoin(User, User.id == SchoolClass.teacher_id)
        .outerjoin(enroll_sq, enroll_sq.c.class_id == SchoolClass.id)
        .outerjoin(income_sq, income_sq.c.class_id == SchoolClass.id)
        .group_by(User.id, teacher_key)
        .order_by(func.coalesce(func.sum(enroll_sq.c.student_count), 0).desc())
    )
    rows = db.execute(stmt).all()

    commission_stmt = select(
        Commission.teacher_name,
        func.coalesce(func.sum(Commission.commission), 0),
    ).group_by(Commission.teacher_name)
    for clause in _apply_datetime_filter(Commission.created_at, start_date, end_date):
        commission_stmt = commission_stmt.where(clause)
    commission_map = {name: _money(amount) for name, amount in db.execute(commission_stmt).all()}

    return [
        {
            "teacher_id": row[0],
            "teacher_name": row[1],
            "total_students": int(row[2] or 0),
            "total_income": _money(row[3]),
            "total_commission": commission_map.get(row[1], 0.0),
        }
        for row in rows
    ]


@dataclass
class RegistrationSummary:
    total_registrations: int
    active_registrations: int
    inactive_registrations: int
    total_registration_amount: float


def get_registration_summary(
    db: Session,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> RegistrationSummary:
    enroll_date = _enrollment_date_column()
    base = select(func.count(Enrollment.id))
    active = select(func.count(Enrollment.id)).where(
        Enrollment.status == "Active", Enrollment.roster_active.is_(True)
    )
    amount = select(func.coalesce(func.sum(Enrollment.price_after_discount), 0))
    for clause in _apply_datetime_filter(enroll_date, start_date, end_date):
        base = base.where(clause)
        active = active.where(clause)
        amount = amount.where(clause)
    total = db.scalar(base) or 0
    active_count = db.scalar(active) or 0
    return RegistrationSummary(
        total_registrations=total,
        active_registrations=active_count,
        inactive_registrations=max(total - active_count, 0),
        total_registration_amount=_money(db.scalar(amount)),
    )


def get_today_report(db: Session) -> str:
    start, end, label = resolve_period_range("today")
    students = get_students_summary(db, start, end)
    income = get_income_summary(db, start, end)
    registration = get_registration_summary(db, start, end)
    return (
        f"📅 <b>Today Report</b>\n"
        f"Period: {label}\n\n"
        f"<b>Students</b>\n"
        f"New students: {students.students_registered_in_period}\n"
        f"Enrollments: {students.total_enrollments}\n"
        f"Active: {students.total_active_students}\n\n"
        f"<b>Income</b>\n"
        f"Invoices: {income.total_invoice}\n"
        f"Total: ${income.total_income:,.2f}\n\n"
        f"<b>Registrations</b>\n"
        f"Count: {registration.total_registrations}\n"
        f"Amount: ${registration.total_registration_amount:,.2f}"
    )


def backup_now(db: Session) -> BackupResult:
    del db  # backup uses engine directly
    return run_google_sheets_backup()
