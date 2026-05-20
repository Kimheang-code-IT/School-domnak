"""Google Sheets backup tasks (Celery)."""

from __future__ import annotations

import logging

from app.core.celery_app import celery_app
from app.core.config import settings
from app.services.google_sheets_backup_service import run_google_sheets_backup
from app.services.telegram_notify import notify_backup_completed

logger = logging.getLogger(__name__)


@celery_app.task(name="google_sheets.backup_all", bind=True, max_retries=2)
def backup_all_to_google_sheets_task(self) -> dict[str, object]:
    if not settings.google_sheets_backup_enabled:
        logger.info("Google Sheets backup skipped (disabled).")
        return {"ok": False, "message": "backup disabled"}

    try:
        result = run_google_sheets_backup()
        notify_backup_completed(result)
        return {
            "ok": result.ok,
            "message": result.message,
            "tables_synced": result.tables_synced,
            "total_rows": result.total_rows,
        }
    except Exception as exc:
        logger.exception("Google Sheets backup task failed")
        raise self.retry(exc=exc, countdown=120) from exc
