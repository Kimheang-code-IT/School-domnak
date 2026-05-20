"""Send Telegram alerts (e.g. after scheduled backup)."""

from __future__ import annotations

import asyncio
import logging

from app.services.google_sheets_backup_service import BackupResult

logger = logging.getLogger(__name__)


def notify_backup_completed(result: BackupResult) -> None:
    """Fire-and-forget Telegram alert after backup (success or failure)."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_send_backup_alert(result))
    except RuntimeError:
        asyncio.run(_send_backup_alert(result))
    except Exception:
        logger.exception("Could not schedule Telegram backup alert")


async def _send_backup_alert(result: BackupResult) -> None:
    from app.services.telegram_bot_service import (
        send_backup_failure_alert,
        send_backup_success_alert,
    )

    try:
        if result.ok:
            await send_backup_success_alert(result)
        else:
            await send_backup_failure_alert(result)
    except Exception:
        logger.exception("Telegram backup alert failed")
