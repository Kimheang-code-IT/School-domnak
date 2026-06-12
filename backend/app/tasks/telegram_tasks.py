"""Telegram alert tasks (Celery)."""

from __future__ import annotations

import asyncio
import logging

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.student import Student
from app.services.telegram_activity_service import format_new_student_message

logger = logging.getLogger(__name__)


async def _broadcast_html(text: str) -> None:
    from app.services.telegram_bot_service import _allowed_chat_ids, send_message

    chats = _allowed_chat_ids()
    if not chats:
        logger.warning("Telegram alert skipped: TELEGRAM_CHAT_ID not set")
        return
    for chat_id in chats:
        try:
            await send_message(chat_id, text)
        except Exception:
            logger.exception("Telegram alert failed for chat_id=%s", chat_id)


@celery_app.task(name="telegram.send_student_register_alert", bind=True, max_retries=3)
def send_student_register_telegram_alert_task(
    self,
    student_id: int,
    registered_by: str | None = None,
) -> dict[str, str | int]:
    db = SessionLocal()
    try:
        student = db.get(Student, student_id)
        if not student:
            logger.warning("Student %s not found for Telegram alert", student_id)
            return {"status": "skipped", "student_id": student_id}
        text = format_new_student_message(student, registered_by=registered_by)
        asyncio.run(_broadcast_html(text))
        return {"status": "sent", "student_id": student_id}
    except Exception as exc:
        logger.exception("Telegram student alert task failed")
        raise self.retry(exc=exc, countdown=30) from exc
    finally:
        db.close()
