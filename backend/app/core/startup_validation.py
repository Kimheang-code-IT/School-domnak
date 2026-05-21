"""Fail fast when production settings are unsafe."""

from __future__ import annotations

import logging
import sys

from app.core.config import Settings

logger = logging.getLogger(__name__)

_WEAK_SECRET_KEYS = frozenset(
    {
        "",
        "change-me-in-production",
        "changeme",
        "secret",
        "dev",
    }
)


def validate_settings(settings: Settings) -> None:
    if not settings.is_production:
        if settings.secret_key.strip().lower() in _WEAK_SECRET_KEYS:
            logger.warning(
                "SECRET_KEY is weak or default — set a long random value before production deploy."
            )
        return

    key = settings.secret_key.strip()
    if len(key) < 32 or key.lower() in _WEAK_SECRET_KEYS:
        logger.critical("Production requires SECRET_KEY with at least 32 characters (not a default).")
        sys.exit(1)

    if settings.database_url.startswith("sqlite"):
        logger.critical("Production must not use SQLite — set DATABASE_URL to PostgreSQL.")
        sys.exit(1)

    if settings.telegram_bot_token.strip() and not settings.telegram_webhook_secret.strip():
        if not settings.telegram_use_polling:
            logger.critical(
                "Production Telegram webhook mode requires TELEGRAM_WEBHOOK_SECRET to be set."
            )
            sys.exit(1)

    logger.info("Production settings validation passed.")
