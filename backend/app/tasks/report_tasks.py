"""Scheduled Telegram report tasks (Celery)."""

from __future__ import annotations

import asyncio
import logging

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.services import telegram_report_service as reports
logger = logging.getLogger(__name__)


async def _broadcast_html(text: str) -> None:
    from app.services.telegram_bot_service import _allowed_chat_ids, send_message

    for chat_id in _allowed_chat_ids():
        try:
            await send_message(chat_id, text)
        except Exception:
            logger.exception("Telegram report failed for chat_id=%s", chat_id)


@celery_app.task(name="reports.send_daily_summary")
def send_daily_summary_report_task() -> dict[str, str]:
    db = SessionLocal()
    try:
        text = reports.get_today_report(db)
        asyncio.run(_broadcast_html(text))
        return {"status": "sent", "type": "daily"}
    except Exception:
        logger.exception("Daily summary report task failed")
        raise
    finally:
        db.close()


@celery_app.task(name="reports.send_weekly_summary")
def send_weekly_summary_report_task() -> dict[str, str]:
    db = SessionLocal()
    try:
        start, end, label = reports.resolve_period_range("this_week")
        students = reports.get_students_summary(db, start, end)
        income = reports.get_income_summary(db, start, end)
        registration = reports.get_registration_summary(db, start, end)
        text = (
            f"📅 <b>Weekly Summary</b>\n"
            f"Period: {label}\n\n"
            f"<b>Students</b>\n"
            f"New: {students.students_registered_in_period}\n"
            f"Enrollments: {students.total_enrollments}\n\n"
            f"<b>Income</b>\n"
            f"Invoices: {income.total_invoice}\n"
            f"Total: ${income.total_income:,.2f}\n\n"
            f"<b>Registrations</b>\n"
            f"Count: {registration.total_registrations}\n"
            f"Amount: ${registration.total_registration_amount:,.2f}"
        )
        asyncio.run(_broadcast_html(text))
        return {"status": "sent", "type": "weekly"}
    except Exception:
        logger.exception("Weekly summary report task failed")
        raise
    finally:
        db.close()


@celery_app.task(name="reports.send_period_report")
def send_period_report_task(
    period: str = "today",
    report_action: str = "students_summary",
    *,
    custom_start: str | None = None,
    custom_end: str | None = None,
) -> dict[str, str]:
    from datetime import date

    from app.services.telegram_bot_service import (
        _format_registration_summary,
        _format_students_summary,
        run_report_for_action,
    )
    from app.services.telegram_state import get_user_state

    db = SessionLocal()
    try:
        state = get_user_state(0)
        state["period"] = period
        if period == "custom_range" and custom_start and custom_end:
            state["custom_start"] = date.fromisoformat(custom_start)
            state["custom_end"] = date.fromisoformat(custom_end)
            start, end, label = reports.resolve_period_range(
                period,
                custom_start=state["custom_start"],
                custom_end=state["custom_end"],
            )
        else:
            start, end, label = reports.resolve_period_range(period)
        if report_action in {"students_summary", "registration_summary"}:
            if report_action == "students_summary":
                data = reports.get_students_summary(db, start, end)
                text = _format_students_summary(label, data)
            else:
                data = reports.get_registration_summary(db, start, end)
                text = _format_registration_summary(label, data)
        else:
            state["filter_all_entities"] = True
            text = run_report_for_action(db, user_id=0, action=report_action)
        asyncio.run(_broadcast_html(text))
        return {"status": "sent", "period": period, "action": report_action}
    except Exception:
        logger.exception("Period report task failed")
        raise
    finally:
        db.close()
