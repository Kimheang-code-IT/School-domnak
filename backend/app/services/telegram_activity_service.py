"""Telegram alerts for student registration and class enrollment."""

from __future__ import annotations

import asyncio
import html
import logging
from datetime import date
from decimal import Decimal
from typing import Any

from app.core.config import settings
from app.models.class_model import SchoolClass
from app.models.enrollment import Enrollment
from app.models.invoice import Invoice
from app.models.student import Student
from app.schemas.student import format_student_code
from app.utils.enrollment_dates import parse_duration_months

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    return bool(settings.telegram_bot_token.strip()) and bool(settings.telegram_activity_alerts_enabled)


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=False)


def _fmt_date(value: date | None) -> str:
    return value.isoformat() if value else "—"


def _fmt_money(value: Decimal | float | int | None) -> str:
    return f"${float(value or 0):,.2f}"


def _fmt_duration(enrollment: Enrollment, school_class: SchoolClass) -> str:
    months = parse_duration_months(enrollment.duration_months)
    if months is None:
        months = parse_duration_months(school_class.class_duration)
    if months is None:
        return "—"
    if months == int(months):
        label = "month" if int(months) == 1 else "months"
        return f"{int(months)} {label}"
    return f"{months:g} months"


def _format_invoice_summary_lines(invoice: Invoice | None) -> list[str]:
    if invoice is None:
        return []
    return [
        "",
        "🧾 <b>Invoice</b>",
        f"No: <code>{_esc(invoice.invoice_no)}</code>",
        f"Subtotal: {_fmt_money(invoice.subtotal)}",
        f"Discount: {_fmt_money(invoice.discount_amount)}",
        f"Grand total: <b>{_fmt_money(invoice.total)}</b>",
    ]


def _resolve_class_names(student: Student, class_names: list[str] | None) -> list[str]:
    if class_names is not None:
        return [name.strip() for name in class_names if str(name).strip()]
    resolved: list[str] = []
    for enrollment in getattr(student, "enrollments", None) or []:
        school_class = getattr(enrollment, "school_class", None)
        name = getattr(school_class, "name", None) if school_class else None
        if name and str(name).strip():
            resolved.append(str(name).strip())
    # Preserve order, drop duplicates
    return list(dict.fromkeys(resolved))


def format_new_student_message(
    student: Student,
    *,
    registered_by: str | None = None,
    class_names: list[str] | None = None,
) -> str:
    code = format_student_code(student.id)
    lines = [
        "👤 <b>New Student Registered</b>",
        "",
        f"ID: <code>{_esc(code)}</code>",
        f"Name (KM): {_esc(student.name_km)}",
        f"Name (EN): {_esc(student.name_en)}",
    ]
    classes = _resolve_class_names(student, class_names)
    if classes:
        if len(classes) == 1:
            lines.append(f"Class: <b>{_esc(classes[0])}</b>")
        else:
            lines.append("Classes:")
            for class_name in classes:
                lines.append(f"  • {_esc(class_name)}")
    if student.phone:
        lines.append(f"Phone: {_esc(student.phone)}")
    if student.gender:
        lines.append(f"Gender: {_esc(student.gender)}")
    if student.province:
        lines.append(f"Province: {_esc(student.province)}")
    if student.birthdate:
        lines.append(f"Birthdate: {_esc(_fmt_date(student.birthdate))}")
    if registered_by:
        lines.append(f"\nBy: {_esc(registered_by)}")
    return "\n".join(lines)


def _format_enrollment_block(
    school_class: SchoolClass,
    enrollment: Enrollment,
    *,
    index: int | None = None,
) -> list[str]:
    teacher = school_class.teacher_name or (
        school_class.teacher.name if school_class.teacher else None
    )
    prefix = f"{index}. " if index is not None else ""
    lines = [f"<b>{prefix}{_esc(school_class.name)}</b>"]
    if teacher:
        lines.append(f"Teacher: {_esc(teacher)}")
    if school_class.course:
        lines.append(f"Course: {_esc(school_class.course.course_name)}")
    lines.extend(
        [
            f"Duration: <b>{_esc(_fmt_duration(enrollment, school_class))}</b>",
            f"Start: {_esc(_fmt_date(enrollment.start_date))}",
            f"End: {_esc(_fmt_date(enrollment.end_date))}",
        ]
    )
    return lines


def format_enrollment_message(
    student: Student,
    school_class: SchoolClass,
    enrollment: Enrollment,
    *,
    enrolled_by: str | None = None,
) -> str:
    code = format_student_code(student.id)
    lines = [
        "🏫 <b>Student Added to Class</b>",
        "",
        f"Student: {_esc(student.name_en)} ({_esc(student.name_km)})",
        f"ID: <code>{_esc(code)}</code>",
        "",
        *_format_enrollment_block(school_class, enrollment),
    ]
    if enrolled_by:
        lines.append(f"\nBy: {_esc(enrolled_by)}")
    return "\n".join(lines)


def format_registration_with_enrollments_message(
    student: Student,
    enrollments: list[tuple[Enrollment, SchoolClass]],
    *,
    is_new_student: bool = False,
    registered_by: str | None = None,
    invoice: Invoice | None = None,
) -> str:
    """Single Telegram message for new student + class enrollment(s) at checkout."""
    code = format_student_code(student.id)
    if is_new_student:
        title = f"👤 <b>{_esc('New Student & Enrollment')}</b>"
    elif len(enrollments) == 1:
        title = "🏫 <b>Student Added to Class</b>"
    else:
        title = "🏫 <b>Student Enrolled in Classes</b>"

    lines = [title, ""]
    if is_new_student:
        lines.extend(
            [
                f"ID: <code>{_esc(code)}</code>",
                f"Name (KM): {_esc(student.name_km)}",
                f"Name (EN): {_esc(student.name_en)}",
            ]
        )
        if student.phone:
            lines.append(f"Phone: {_esc(student.phone)}")
        if student.gender:
            lines.append(f"Gender: {_esc(student.gender)}")
        if student.province:
            lines.append(f"Province: {_esc(student.province)}")
        if student.birthdate:
            lines.append(f"Birthdate: {_esc(_fmt_date(student.birthdate))}")
    else:
        lines.extend(
            [
                f"Student: {_esc(student.name_en)} ({_esc(student.name_km)})",
                f"ID: <code>{_esc(code)}</code>",
            ]
        )

    for idx, (enrollment, school_class) in enumerate(enrollments, start=1):
        lines.append("")
        if len(enrollments) > 1:
            lines.extend(_format_enrollment_block(school_class, enrollment, index=idx))
        else:
            lines.extend(_format_enrollment_block(school_class, enrollment))

    lines.extend(_format_invoice_summary_lines(invoice))

    if registered_by:
        lines.append(f"\nBy: {_esc(registered_by)}")
    return "\n".join(lines)


def _schedule(coro) -> None:
    if not _enabled():
        return
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        asyncio.run(coro)
    except Exception:
        logger.exception("Could not schedule Telegram activity alert")


async def _broadcast(text: str) -> None:
    from app.services.telegram_bot_service import (
        _allowed_chat_ids,
        build_report_reply_keyboard,
        send_message,
    )

    chats = _allowed_chat_ids()
    if not chats:
        logger.warning("Telegram activity alert skipped: TELEGRAM_CHAT_ID not set")
        return
    keyboard = build_report_reply_keyboard()
    for chat_id in chats:
        try:
            await send_message(chat_id, text, reply_keyboard=keyboard)
        except Exception:
            logger.exception("Telegram activity alert failed for chat_id=%s", chat_id)


async def _send_new_student(
    student: Student,
    registered_by: str | None,
    *,
    class_names: list[str] | None = None,
) -> None:
    await _broadcast(
        format_new_student_message(
            student,
            registered_by=registered_by,
            class_names=class_names,
        )
    )


async def _send_enrollment(
    student: Student,
    school_class: SchoolClass,
    enrollment: Enrollment,
    enrolled_by: str | None,
) -> None:
    await _broadcast(
        format_enrollment_message(
            student,
            school_class,
            enrollment,
            enrolled_by=enrolled_by,
        )
    )


async def _send_registration_with_enrollments(
    student: Student,
    enrollments: list[tuple[Enrollment, SchoolClass]],
    *,
    is_new_student: bool,
    registered_by: str | None,
    invoice: Invoice | None = None,
) -> None:
    await _broadcast(
        format_registration_with_enrollments_message(
            student,
            enrollments,
            is_new_student=is_new_student,
            registered_by=registered_by,
            invoice=invoice,
        )
    )


def notify_new_student(
    student: Student,
    *,
    registered_by: str | None = None,
    class_names: list[str] | None = None,
) -> None:
    _schedule(_send_new_student(student, registered_by, class_names=class_names))


def notify_class_enrollment(
    student: Student,
    school_class: SchoolClass,
    enrollment: Enrollment,
    *,
    enrolled_by: str | None = None,
) -> None:
    _schedule(_send_enrollment(student, school_class, enrollment, enrolled_by))


def notify_registration_with_enrollments(
    student: Student,
    enrollments: list[tuple[Enrollment, SchoolClass]],
    *,
    is_new_student: bool = False,
    registered_by: str | None = None,
    invoice: Invoice | None = None,
) -> None:
    """One combined alert for checkout (new student + class enrollments)."""
    if not enrollments and not is_new_student:
        return
    if not enrollments and is_new_student:
        _schedule(_send_new_student(student, registered_by))
        return
    _schedule(
        _send_registration_with_enrollments(
            student,
            enrollments,
            is_new_student=is_new_student,
            registered_by=registered_by,
            invoice=invoice,
        )
    )
