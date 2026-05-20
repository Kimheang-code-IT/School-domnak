"""Daily scheduled Google Sheets database backup."""

from __future__ import annotations

import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.services.google_sheets_backup_service import run_google_sheets_backup
from app.services.telegram_notify import notify_backup_completed

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _scheduled_backup_job() -> None:
    logger.info("Starting scheduled Google Sheets backup")
    result = run_google_sheets_backup()
    if result.ok:
        logger.info("Scheduled backup finished: %s", result.message)
    else:
        logger.error("Scheduled backup failed: %s", result.message)
    notify_backup_completed(result)


def start_backup_scheduler() -> BackgroundScheduler | None:
    global _scheduler

    if _scheduler is not None:
        return _scheduler

    if not settings.google_sheets_backup_enabled:
        logger.info("Google Sheets backup scheduler not started (disabled in settings).")
        return None

    tz = ZoneInfo(settings.backup_timezone)
    _scheduler = BackgroundScheduler(timezone=tz)
    _scheduler.add_job(
        _scheduled_backup_job,
        CronTrigger(
            hour=settings.backup_schedule_hour,
            minute=settings.backup_schedule_minute,
            timezone=tz,
        ),
        id="google_sheets_database_backup",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    _scheduler.start()
    logger.info(
        "Google Sheets backup scheduled daily at %02d:%02d (%s)",
        settings.backup_schedule_hour,
        settings.backup_schedule_minute,
        settings.backup_timezone,
    )
    return _scheduler


def stop_backup_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Google Sheets backup scheduler stopped.")
