"""Pre-warm invoice print/preview payload in Redis after checkout."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.redis_cache import cache_enabled, get_json, set_json, simple_cache_key
from app.models.invoice import Invoice
from app.services.invoice_preview_service import _build_preview_from_invoice

logger = logging.getLogger(__name__)

_PRINT_TTL_SECONDS = 3600


def print_cache_key(invoice_no: str) -> str:
    return simple_cache_key("invoice_print", invoice_no.strip())


def job_status_key(job_id: str) -> str:
    return simple_cache_key("checkout_job", job_id)


def warm_invoice_print_cache(db: Session, invoice_id: int) -> dict | None:
    invoice = db.scalar(
        select(Invoice)
        .options(
            selectinload(Invoice.lines),
            selectinload(Invoice.student),
        )
        .where(Invoice.id == invoice_id)
    )
    if not invoice:
        logger.warning("Invoice %s not found for print cache", invoice_id)
        return None

    preview = _build_preview_from_invoice(db, invoice)
    if cache_enabled():
        set_json(print_cache_key(invoice.invoice_no), preview, _PRINT_TTL_SECONDS)
    return preview


def get_cached_invoice_print(invoice_no: str) -> dict | None:
    if not cache_enabled():
        return None
    cached = get_json(print_cache_key(invoice_no))
    return cached if isinstance(cached, dict) else None


def set_checkout_job_status(
    job_id: str,
    *,
    status: str,
    print_ready: bool,
    invoice_no: str | None = None,
    error: str | None = None,
) -> None:
    if not cache_enabled() or not job_id:
        return
    payload: dict = {
        "status": status,
        "printReady": print_ready,
        "invoiceNo": invoice_no,
    }
    if error:
        payload["error"] = error
    set_json(job_status_key(job_id), payload, 600)


def get_checkout_job_status(job_id: str) -> dict | None:
    if not cache_enabled() or not job_id:
        return None
    cached = get_json(job_status_key(job_id))
    return cached if isinstance(cached, dict) else None
