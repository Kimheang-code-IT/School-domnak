"""Queue Celery tasks after successful DB commits; fall back to in-process alerts."""

from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def _celery_available() -> bool:
    if not settings.use_celery_tasks:
        return False
    try:
        from app.core.celery_app import celery_app

        celery_app.connection().ensure_connection(max_retries=1)
        return True
    except Exception:
        return False


def dispatch_new_student_alerts(student_id: int, *, registered_by: str | None = None) -> None:
    if _celery_available():
        try:
            from app.tasks.telegram_tasks import send_student_register_telegram_alert_task

            send_student_register_telegram_alert_task.delay(student_id, registered_by=registered_by)
            return
        except Exception:
            logger.exception("Celery student alert dispatch failed; using in-process fallback")

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.core.database import SessionLocal
    from app.models.enrollment import Enrollment
    from app.models.student import Student
    from app.services.telegram_activity_service import notify_new_student

    db = SessionLocal()
    try:
        student = db.scalar(
            select(Student)
            .options(selectinload(Student.enrollments).selectinload(Enrollment.school_class))
            .where(Student.id == student_id)
        )
        if student:
            notify_new_student(student, registered_by=registered_by)
    finally:
        db.close()


def dispatch_google_sheets_backup() -> None:
    if not settings.google_sheets_backup_enabled:
        return
    if _celery_available():
        try:
            from app.tasks.google_sheet_tasks import backup_all_to_google_sheets_task

            backup_all_to_google_sheets_task.delay()
            return
        except Exception:
            logger.exception("Celery backup dispatch failed; running synchronously")

    from app.services.google_sheets_backup_service import run_google_sheets_backup
    from app.services.telegram_notify import notify_backup_completed

    result = run_google_sheets_backup()
    notify_backup_completed(result)
