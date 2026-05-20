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
from app.models.finance import Finance
from app.models.invoice import Invoice, InvoiceLine
from app.models.student import Student
from app.models.user import User
from app.services.finance_service import sync_finance_for_all_classes
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


def _student_created_in_period(
    created_at: datetime | None,
    start_date: datetime | None,
    end_date: datetime | None,
) -> bool:
    if created_at is None:
        return False
    if start_date is None and end_date is None:
        return True
    if start_date is not None and created_at < start_date:
        return False
    if end_date is not None and created_at > end_date:
        return False
    return True


def get_students_summary_by_class(
    db: Session,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict[str, Any]]:
    """Per-class student stats for the selected period."""
    enroll_date = _enrollment_date_column()
    stmt = (
        select(
            SchoolClass.id,
            SchoolClass.name,
            Enrollment.student_id,
            Enrollment.status,
            Enrollment.roster_active,
            Student.created_at,
        )
        .join(Enrollment, Enrollment.class_id == SchoolClass.id)
        .join(Student, Student.id == Enrollment.student_id)
    )
    for clause in _apply_datetime_filter(enroll_date, start_date, end_date):
        stmt = stmt.where(clause)

    grouped: dict[int, dict[str, Any]] = {}
    for row in db.execute(stmt).all():
        class_id = row[0]
        bucket = grouped.get(class_id)
        if bucket is None:
            bucket = {
                "class_id": class_id,
                "class_name": row[1] or "—",
                "active_student_ids": set(),
                "inactive_student_ids": set(),
                "new_student_ids": set(),
                "total_enrollments": 0,
            }
            grouped[class_id] = bucket

        student_id = row[2]
        if _is_active_enrollment(row[3] or "", bool(row[4])):
            bucket["active_student_ids"].add(student_id)
        else:
            bucket["inactive_student_ids"].add(student_id)
        bucket["total_enrollments"] += 1
        if _student_created_in_period(row[5], start_date, end_date):
            bucket["new_student_ids"].add(student_id)

    items: list[dict[str, Any]] = []
    for bucket in grouped.values():
        items.append(
            {
                "class_id": bucket["class_id"],
                "class_name": bucket["class_name"],
                "active_students": len(bucket["active_student_ids"]),
                "inactive_students": len(bucket["inactive_student_ids"]),
                "total_enrollments": bucket["total_enrollments"],
                "new_students_in_period": len(bucket["new_student_ids"]),
            }
        )
    items.sort(key=lambda row: row["class_name"])
    return items


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


def get_finance_report(
    db: Session,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    *,
    class_id: int | None = None,
) -> list[dict[str, Any]]:
    """Finance rows per class (same fields as the Finance page table)."""
    sync_finance_for_all_classes(db)
    stmt = (
        select(
            Finance.id,
            SchoolClass.name,
            Finance.electricity,
            Finance.water,
            Finance.internet,
            Finance.total_commission,
            Finance.facebook,
            Finance.other,
            Finance.amount,
            Finance.final_price,
        )
        .outerjoin(SchoolClass, SchoolClass.id == Finance.class_id)
        .where(Finance.class_id.isnot(None))
    )
    if class_id is not None:
        stmt = stmt.where(Finance.class_id == class_id)
    for clause in _apply_datetime_filter(Finance.created_at, start_date, end_date):
        stmt = stmt.where(clause)
    stmt = stmt.order_by(SchoolClass.name)

    items: list[dict[str, Any]] = []
    for row in db.execute(stmt).all():
        items.append(
            {
                "finance_id": row[0],
                "class_name": row[1] or "—",
                "electricity": _money(row[2]),
                "water": _money(row[3]),
                "internet": _money(row[4]),
                "total_commission": _money(row[5]),
                "facebook": _money(row[6]),
                "other": _money(row[7]),
                "amount": _money(row[8]),
                "final_price": _money(row[9]),
            }
        )
    return items


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


def _is_active_enrollment(status: str, roster_active: bool) -> bool:
    return status == "Active" and roster_active is True


def _course_display_name(course_name: str | None, course_name_km: str | None = None) -> str:
    base = (course_name or "").strip() or "—"
    km = (course_name_km or "").strip()
    if km:
        return f"{km} / {base}"
    return base


def _new_enrollment_detail_bucket(item_name: str) -> dict[str, Any]:
    return {
        "item_name": item_name or "—",
        "class_names": set(),
        "teacher_name": None,
        "active_student_ids": set(),
        "inactive_student_ids": set(),
        "subtotal": 0.0,
        "discount": 0.0,
        "grand_total": 0.0,
        "commission": 0.0,
    }


def _apply_enrollment_row_to_bucket(
    bucket: dict[str, Any],
    *,
    class_name: str | None,
    student_id: int,
    status: str,
    roster_active: bool,
    total_price: Any,
    discount_price: Any,
    price_after_discount: Any,
    teacher_name: str | None = None,
) -> None:
    name = (class_name or "").strip()
    if name:
        bucket["class_names"].add(name)
    if teacher_name and not bucket.get("teacher_name"):
        bucket["teacher_name"] = teacher_name
    if _is_active_enrollment(status or "", bool(roster_active)):
        bucket["active_student_ids"].add(student_id)
    else:
        bucket["inactive_student_ids"].add(student_id)
    bucket["subtotal"] += _money(total_price)
    bucket["discount"] += _money(discount_price)
    bucket["grand_total"] += _money(price_after_discount)


def _finalize_enrollment_detail_buckets(grouped: dict[Any, dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for bucket in grouped.values():
        items.append(
            {
                "item_name": bucket["item_name"],
                "class_names": sorted(bucket["class_names"]),
                "teacher_name": bucket.get("teacher_name"),
                "active_students": len(bucket["active_student_ids"]),
                "inactive_students": len(bucket["inactive_student_ids"]),
                "subtotal": bucket["subtotal"],
                "discount": bucket["discount"],
                "grand_total": bucket["grand_total"],
                "commission": bucket.get("commission", 0.0),
            }
        )
    items.sort(key=lambda row: (-row["grand_total"], row["item_name"]))
    return items


def list_all_categories(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(select(Category.id, Category.name).order_by(Category.name)).all()
    return [{"id": int(row[0]), "name": row[1] or "—"} for row in rows]


def list_all_courses(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        select(Course.id, Course.course_name, Course.course_name_km).order_by(Course.course_name)
    ).all()
    items: list[dict[str, Any]] = []
    for row in rows:
        name = row[1] or "—"
        if row[2]:
            name = f"{row[2]} / {name}"
        items.append({"id": int(row[0]), "name": name})
    return items


def list_all_classes(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(select(SchoolClass.id, SchoolClass.name).order_by(SchoolClass.name)).all()
    return [{"id": int(row[0]), "name": row[1] or "—"} for row in rows]


def list_all_teachers(db: Session) -> list[dict[str, Any]]:
    teacher_key = func.coalesce(User.name, SchoolClass.teacher_name, "Unknown")
    rows = db.execute(
        select(User.id, teacher_key)
        .select_from(SchoolClass)
        .outerjoin(User, User.id == SchoolClass.teacher_id)
        .group_by(User.id, teacher_key)
        .order_by(teacher_key)
    ).all()
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        name = str(row[1] or "Unknown")
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append({"id": int(row[0]) if row[0] is not None else None, "name": name})
    return items


def get_students_by_category_detail(
    db: Session,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    *,
    category_id: int | None = None,
) -> list[dict[str, Any]]:
    """Per-category class names, student counts, and enrollment totals for the period."""
    enroll_date = _enrollment_date_column()
    stmt = (
        select(
            Category.id,
            Category.name,
            SchoolClass.name,
            Enrollment.student_id,
            Enrollment.status,
            Enrollment.roster_active,
            Enrollment.total_price,
            Enrollment.discount_price,
            Enrollment.price_after_discount,
        )
        .join(SchoolClass, SchoolClass.category_id == Category.id)
        .join(Enrollment, Enrollment.class_id == SchoolClass.id)
    )
    if category_id is not None:
        stmt = stmt.where(Category.id == category_id)
    for clause in _apply_datetime_filter(enroll_date, start_date, end_date):
        stmt = stmt.where(clause)

    grouped: dict[int, dict[str, Any]] = {}
    for row in db.execute(stmt).all():
        group_id = row[0]
        if group_id not in grouped:
            grouped[group_id] = _new_enrollment_detail_bucket(row[1])
        _apply_enrollment_row_to_bucket(
            grouped[group_id],
            class_name=row[2],
            student_id=row[3],
            status=row[4] or "",
            roster_active=bool(row[5]),
            total_price=row[6],
            discount_price=row[7],
            price_after_discount=row[8],
        )
    return _finalize_enrollment_detail_buckets(grouped)


def get_students_by_course_detail(
    db: Session,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    *,
    course_id: int | None = None,
) -> list[dict[str, Any]]:
    enroll_date = _enrollment_date_column()
    stmt = (
        select(
            Course.id,
            Course.course_name,
            Course.course_name_km,
            SchoolClass.name,
            Enrollment.student_id,
            Enrollment.status,
            Enrollment.roster_active,
            Enrollment.total_price,
            Enrollment.discount_price,
            Enrollment.price_after_discount,
        )
        .join(SchoolClass, SchoolClass.course_id == Course.id)
        .join(Enrollment, Enrollment.class_id == SchoolClass.id)
    )
    if course_id is not None:
        stmt = stmt.where(Course.id == course_id)
    for clause in _apply_datetime_filter(enroll_date, start_date, end_date):
        stmt = stmt.where(clause)

    grouped: dict[int, dict[str, Any]] = {}
    for row in db.execute(stmt).all():
        group_id = row[0]
        if group_id not in grouped:
            grouped[group_id] = _new_enrollment_detail_bucket(
                _course_display_name(row[1], row[2])
            )
        _apply_enrollment_row_to_bucket(
            grouped[group_id],
            class_name=row[3],
            student_id=row[4],
            status=row[5] or "",
            roster_active=bool(row[6]),
            total_price=row[7],
            discount_price=row[8],
            price_after_discount=row[9],
        )
    return _finalize_enrollment_detail_buckets(grouped)


def get_students_by_class_detail(
    db: Session,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    *,
    class_id: int | None = None,
) -> list[dict[str, Any]]:
    enroll_date = _enrollment_date_column()
    teacher_label = func.coalesce(User.name, SchoolClass.teacher_name, "Unknown")
    stmt = (
        select(
            SchoolClass.id,
            SchoolClass.name,
            teacher_label,
            Enrollment.student_id,
            Enrollment.status,
            Enrollment.roster_active,
            Enrollment.total_price,
            Enrollment.discount_price,
            Enrollment.price_after_discount,
        )
        .join(Enrollment, Enrollment.class_id == SchoolClass.id)
        .outerjoin(User, User.id == SchoolClass.teacher_id)
    )
    if class_id is not None:
        stmt = stmt.where(SchoolClass.id == class_id)
    for clause in _apply_datetime_filter(enroll_date, start_date, end_date):
        stmt = stmt.where(clause)

    grouped: dict[int, dict[str, Any]] = {}
    for row in db.execute(stmt).all():
        group_id = row[0]
        if group_id not in grouped:
            bucket = _new_enrollment_detail_bucket(row[1])
            bucket["teacher_name"] = row[2] or "—"
            grouped[group_id] = bucket
        _apply_enrollment_row_to_bucket(
            grouped[group_id],
            class_name=None,
            student_id=row[3],
            status=row[4] or "",
            roster_active=bool(row[5]),
            total_price=row[6],
            discount_price=row[7],
            price_after_discount=row[8],
        )
    return _finalize_enrollment_detail_buckets(grouped)


def get_students_by_teacher_detail(
    db: Session,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    *,
    teacher_name: str | None = None,
) -> list[dict[str, Any]]:
    enroll_date = _enrollment_date_column()
    teacher_label = func.coalesce(User.name, SchoolClass.teacher_name, "Unknown")
    stmt = (
        select(
            teacher_label,
            SchoolClass.name,
            Enrollment.student_id,
            Enrollment.status,
            Enrollment.roster_active,
            Enrollment.total_price,
            Enrollment.discount_price,
            Enrollment.price_after_discount,
        )
        .select_from(SchoolClass)
        .join(Enrollment, Enrollment.class_id == SchoolClass.id)
        .outerjoin(User, User.id == SchoolClass.teacher_id)
    )
    if teacher_name:
        stmt = stmt.where(teacher_label == teacher_name)
    for clause in _apply_datetime_filter(enroll_date, start_date, end_date):
        stmt = stmt.where(clause)

    grouped: dict[str, dict[str, Any]] = {}
    for row in db.execute(stmt).all():
        group_key = str(row[0] or "Unknown")
        if group_key not in grouped:
            grouped[group_key] = _new_enrollment_detail_bucket(group_key)
        _apply_enrollment_row_to_bucket(
            grouped[group_key],
            class_name=row[1],
            student_id=row[2],
            status=row[3] or "",
            roster_active=bool(row[4]),
            total_price=row[5],
            discount_price=row[6],
            price_after_discount=row[7],
        )

    commission_stmt = select(
        Commission.teacher_name,
        func.coalesce(func.sum(Commission.commission), 0),
    ).group_by(Commission.teacher_name)
    for clause in _apply_datetime_filter(Commission.created_at, start_date, end_date):
        commission_stmt = commission_stmt.where(clause)
    commission_map = {
        str(name): _money(amount) for name, amount in db.execute(commission_stmt).all()
    }
    for key, bucket in grouped.items():
        bucket["commission"] = commission_map.get(key, 0.0)

    return _finalize_enrollment_detail_buckets(grouped)


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
    *,
    course_id: int | None = None,
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
    if course_id is not None:
        stmt = stmt.where(Course.id == course_id)
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
    *,
    class_id: int | None = None,
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
    if class_id is not None:
        stmt = stmt.where(SchoolClass.id == class_id)
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
    *,
    teacher_name: str | None = None,
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
    if teacher_name:
        stmt = stmt.where(teacher_key == teacher_name)
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
