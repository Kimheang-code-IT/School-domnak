"""Celery application for background jobs and Beat schedules."""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "school_domnak",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.telegram_tasks",
        "app.tasks.google_sheet_tasks",
        "app.tasks.report_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.backup_timezone,
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "daily-telegram-summary": {
        "task": "app.tasks.report_tasks.send_daily_summary_report_task",
        "schedule": crontab(hour=20, minute=0),
    },
    "daily-google-sheets-backup": {
        "task": "app.tasks.google_sheet_tasks.backup_all_to_google_sheets_task",
        "schedule": crontab(
            hour=settings.backup_schedule_hour,
            minute=settings.backup_schedule_minute,
        ),
    },
    "weekly-telegram-summary": {
        "task": "app.tasks.report_tasks.send_weekly_summary_report_task",
        "schedule": crontab(hour=20, minute=0, day_of_week=0),
    },
}
