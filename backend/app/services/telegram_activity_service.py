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
from app.models.student import Student
from app.schemas.student import format_student_code

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    return bool(settings.telegram_bot_token.strip()) and bool(settings.telegram_activity_alerts_enabled)


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=False)


def _fmt_date(value: date | None) -> str:
    return value.isoformat() if value else "—"


def _fmt_money(value: Decimal | float | int | None) -> str:
    return f"${float(value or 0):,.2f}"


def format_new_student_message(student: Student, *, registered_by: str | None = None) -> str:
    code = format_student_code(student.id)
    lines = [
        "👤 <b>New Student Registered</b>",
        "",
        f"ID: <code>{_esc(code)}</code>",
        f"Name (KM): {_esc(student.name_km)}",
        f"Name (EN): {_esc(student.name_en)}",
    ]
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


def format_enrollment_message(
    student: Student,
    school_class: SchoolClass,
    enrollment: Enrollment,
    *,
    enrolled_by: str | None = None,
) -> str:
    code = format_student_code(student.id)
    teacher = school_class.teacher_name or (
        school_class.teacher.name if school_class.teacher else None
    )
    lines = [
        "🏫 <b>Student Added to Class</b>",
        "",
        f"Student: {_esc(student.name_en)} ({_esc(student.name_km)})",
        f"ID: <code>{_esc(code)}</code>",
        f"Class: {_esc(school_class.name)}",
    ]
    if teacher:
        lines.append(f"Teacher: {_esc(teacher)}")
    if school_class.course:
        lines.append(f"Course: {_esc(school_class.course.course_name)}")
    lines.extend(
        [
            f"Start: {_esc(_fmt_date(enrollment.start_date))}",
            f"End: {_esc(_fmt_date(enrollment.end_date))}",
            f"Fee: {_fmt_money(enrollment.price_after_discount)}",
            f"Status: {_esc(enrollment.status)}",
        ]
    )
    if enrolled_by:
        lines.append(f"\nBy: {_esc(enrolled_by)}")
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
    from app.services.telegram_bot_service import _allowed_chat_ids, send_message

    chats = _allowed_chat_ids()
    if not chats:
        logger.warning("Telegram activity alert skipped: TELEGRAM_CHAT_ID not set")
        return
    for chat_id in chats:
        try:
            await send_message(chat_id, text)
        except Exception:
            logger.exception("Telegram activity alert failed for chat_id=%s", chat_id)


async def _send_new_student(student: Student, registered_by: str | None) -> None:
    await _broadcast(format_new_student_message(student, registered_by=registered_by))


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


def notify_new_student(student: Student, *, registered_by: str | None = None) -> None:
    _schedule(_send_new_student(student, registered_by))


def notify_class_enrollment(
    student: Student,
    school_class: SchoolClass,
    enrollment: Enrollment,
    *,
    enrolled_by: str | None = None,
) -> None:
    _schedule(_send_enrollment(student, school_class, enrollment, enrolled_by))
