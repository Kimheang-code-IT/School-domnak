"""Queue Celery tasks after successful DB commits; fall back without blocking requests."""

from __future__ import annotations

import logging
import threading
import time

from app.core.config import settings

logger = logging.getLogger(__name__)

_CELERY_CACHE_TTL_SECONDS = 30.0
_celery_available_cache: bool | None = None
_celery_checked_at: float = 0.0


def _probe_celery() -> bool:
    if not settings.use_celery_tasks:
        return False
    try:
        from app.core.celery_app import celery_app

        celery_app.connection().ensure_connection(max_retries=1)
        return True
    except Exception:
        return False


def celery_available_cached() -> bool:
    """Avoid blocking every dispatch with a broker connection check."""
    global _celery_available_cache, _celery_checked_at
    now = time.monotonic()
    if _celery_available_cache is not None and now - _celery_checked_at < _CELERY_CACHE_TTL_SECONDS:
        return _celery_available_cache
    _celery_available_cache = _probe_celery()
    _celery_checked_at = now
    return _celery_available_cache


def invalidate_celery_cache() -> None:
    global _celery_available_cache, _celery_checked_at
    _celery_available_cache = None
    _celery_checked_at = 0.0


def dispatch_new_student_alerts(student_id: int, *, registered_by: str | None = None) -> None:
    if celery_available_cached():
        try:
            from app.tasks.telegram_tasks import send_student_register_telegram_alert_task

            send_student_register_telegram_alert_task.delay(student_id, registered_by=registered_by)
            return
        except Exception:
            invalidate_celery_cache()
            logger.exception("Celery student alert dispatch failed; using background fallback")

    threading.Thread(
        target=_notify_new_student_sync,
        args=(student_id,),
        kwargs={"registered_by": registered_by},
        daemon=True,
        name="student-alert-fallback",
    ).start()


def _notify_new_student_sync(student_id: int, *, registered_by: str | None = None) -> None:
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


def dispatch_checkout_post_process(
    invoice_id: int,
    student_id: int,
    *,
    is_new_student: bool = False,
    registered_by: str | None = None,
    notify: bool = True,
    enrollment_ids: list[int] | None = None,
    invoice_no: str | None = None,
) -> str | None:
    """
    Queue background work: invoice print cache, Telegram, Redis cache invalidation.
    Returns Celery task id (job_id) or None when running in a background thread.
    """
    from app.services.invoice_print_cache import set_checkout_job_status

    if celery_available_cached():
        try:
            from app.tasks.checkout_tasks import post_checkout_task

            async_result = post_checkout_task.apply_async(
                args=[invoice_id, student_id],
                kwargs={
                    "is_new_student": is_new_student,
                    "registered_by": registered_by,
                    "notify": notify,
                    "enrollment_ids": enrollment_ids or [],
                },
            )
            job_id = async_result.id
            set_checkout_job_status(
                job_id,
                status="pending",
                print_ready=False,
                invoice_no=invoice_no,
            )
            return job_id
        except Exception:
            invalidate_celery_cache()
            logger.exception("Celery checkout post-process dispatch failed; using background fallback")

    threading.Thread(
        target=_run_checkout_post_process_inline,
        args=(invoice_id, student_id),
        kwargs={
            "is_new_student": is_new_student,
            "registered_by": registered_by,
            "notify": notify,
            "enrollment_ids": enrollment_ids,
            "invoice_no": invoice_no,
        },
        daemon=True,
        name="checkout-post-fallback",
    ).start()
    return None


def _run_checkout_post_process_inline(
    invoice_id: int,
    student_id: int,
    *,
    is_new_student: bool,
    registered_by: str | None,
    notify: bool,
    enrollment_ids: list[int] | None,
    invoice_no: str | None = None,
) -> None:
    from app.tasks.checkout_tasks import post_checkout_task

    try:
        post_checkout_task(
            invoice_id,
            student_id,
            is_new_student=is_new_student,
            registered_by=registered_by,
            notify=notify,
            enrollment_ids=enrollment_ids or [],
            job_id="inline",
        )
    except Exception:
        logger.exception("Background checkout post-process failed")
    finally:
        if invoice_no:
            from app.services.invoice_print_cache import set_checkout_job_status

            set_checkout_job_status(
                "inline",
                status="ready",
                print_ready=True,
                invoice_no=invoice_no,
            )


def get_checkout_job_status(job_id: str) -> dict:
    from app.services.invoice_print_cache import get_checkout_job_status as _redis_status

    cached = _redis_status(job_id)
    if cached:
        return {
            "status": cached.get("status", "pending"),
            "print_ready": bool(cached.get("printReady")),
            "invoice_no": cached.get("invoiceNo"),
            "error": cached.get("error"),
        }

    if job_id == "inline":
        return {"status": "ready", "print_ready": True, "invoice_no": None, "error": None}

    if not celery_available_cached():
        return {"status": "ready", "print_ready": True, "invoice_no": None, "error": None}

    try:
        from celery.result import AsyncResult

        from app.core.celery_app import celery_app

        result = AsyncResult(job_id, app=celery_app)
        if result.ready():
            if result.successful():
                payload = result.result or {}
                return {
                    "status": "ready",
                    "print_ready": bool(payload.get("print_ready", True)),
                    "invoice_no": payload.get("invoice_no"),
                    "error": None,
                }
            return {
                "status": "failed",
                "print_ready": False,
                "invoice_no": None,
                "error": str(result.result) if result.result else "Task failed",
            }
        if result.state == "STARTED":
            return {"status": "processing", "print_ready": False, "invoice_no": None, "error": None}
        return {"status": "pending", "print_ready": False, "invoice_no": None, "error": None}
    except Exception:
        logger.exception("Failed to read checkout job status")
        return {"status": "pending", "print_ready": False, "invoice_no": None, "error": None}


def dispatch_google_sheets_backup() -> None:
    if not settings.google_sheets_backup_enabled:
        return
    if celery_available_cached():
        try:
            from app.tasks.google_sheet_tasks import backup_all_to_google_sheets_task

            backup_all_to_google_sheets_task.delay()
            return
        except Exception:
            invalidate_celery_cache()
            logger.exception("Celery backup dispatch failed; running in background thread")

    threading.Thread(
        target=_run_google_sheets_backup_sync,
        daemon=True,
        name="google-sheets-backup-fallback",
    ).start()


def _run_google_sheets_backup_sync() -> None:
    from app.services.google_sheets_backup_service import run_google_sheets_backup
    from app.services.telegram_notify import notify_backup_completed

    try:
        result = run_google_sheets_backup()
        notify_backup_completed(result)
    except Exception:
        logger.exception("Background Google Sheets backup failed")
