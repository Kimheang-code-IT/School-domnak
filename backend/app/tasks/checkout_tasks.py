"""Checkout post-processing: Telegram, print cache, Redis invalidation."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.enrollment import Enrollment
from app.models.invoice import Invoice
from app.models.student import Student
from app.services.cache_invalidation import after_invoice_or_enrollment_change
from app.services.invoice_print_cache import set_checkout_job_status, warm_invoice_print_cache
from app.services.telegram_activity_service import _send_registration_with_enrollments

logger = logging.getLogger(__name__)


@celery_app.task(name="checkout.post_process", bind=True, max_retries=3)
def post_checkout_task(
    self,
    invoice_id: int,
    student_id: int,
    *,
    is_new_student: bool = False,
    registered_by: str | None = None,
    notify: bool = True,
    enrollment_ids: list[int] | None = None,
    job_id: str | None = None,
) -> dict:
    effective_job_id = job_id or self.request.id
    if effective_job_id:
        set_checkout_job_status(
            effective_job_id,
            status="processing",
            print_ready=False,
        )

    db = SessionLocal()
    try:
        invoice = db.scalar(
            select(Invoice)
            .options(selectinload(Invoice.lines), selectinload(Invoice.student))
            .where(Invoice.id == invoice_id)
        )
        if not invoice:
            logger.error("Invoice %s not found for checkout post-process", invoice_id)
            if effective_job_id:
                set_checkout_job_status(
                    effective_job_id,
                    status="failed",
                    print_ready=False,
                    error="Invoice not found",
                )
            return {"status": "failed", "invoice_id": invoice_id, "print_ready": False}

        student = db.scalar(
            select(Student)
            .options(selectinload(Student.enrollments).selectinload(Enrollment.school_class))
            .where(Student.id == student_id)
        )

        enrollments: list[tuple[Enrollment, object]] = []
        if enrollment_ids and student:
            id_set = set(enrollment_ids)
            for enrollment in student.enrollments:
                if enrollment.id in id_set and enrollment.school_class:
                    enrollments.append((enrollment, enrollment.school_class))

        warm_invoice_print_cache(db, invoice_id)

        if notify and student and (is_new_student or enrollments):
            if not enrollments and is_new_student:
                from app.services.telegram_activity_service import _send_new_student

                asyncio.run(_send_new_student(student, registered_by))
            elif enrollments:
                asyncio.run(
                    _send_registration_with_enrollments(
                        student,
                        enrollments,
                        is_new_student=is_new_student,
                        registered_by=registered_by,
                        invoice=invoice,
                    )
                )

        after_invoice_or_enrollment_change()

        if effective_job_id:
            set_checkout_job_status(
                effective_job_id,
                status="ready",
                print_ready=True,
                invoice_no=invoice.invoice_no,
            )

        return {
            "status": "ready",
            "invoice_id": invoice_id,
            "invoice_no": invoice.invoice_no,
            "print_ready": True,
        }
    except Exception as exc:
        logger.exception("Checkout post-process failed")
        if effective_job_id:
            set_checkout_job_status(
                effective_job_id,
                status="failed",
                print_ready=False,
                error=str(exc),
            )
        if self.request.retries >= self.max_retries:
            raise
        raise self.retry(exc=exc, countdown=15) from exc
    finally:
        db.close()
