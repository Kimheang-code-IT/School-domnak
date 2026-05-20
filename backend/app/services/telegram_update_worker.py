"""Process Telegram updates from Redis queue (same role as backend worker)."""

from __future__ import annotations

import asyncio
import logging

from app.services.telegram_bot_service import process_telegram_update
from app.services.telegram_queue import (
    dequeue_update,
    mark_processed,
    set_processing,
)

logger = logging.getLogger(__name__)


async def queue_consumer_loop() -> None:
    """Pull updates from Redis and handle them (keeps bot state in one process)."""
    logger.info("Telegram update queue consumer started")
    while True:
        try:
            update = await asyncio.to_thread(dequeue_update, 5)
            if not update:
                continue
            set_processing(True)
            try:
                await process_telegram_update(update)
                mark_processed()
            except Exception:
                logger.exception("Failed to process queued Telegram update")
            finally:
                set_processing(False)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Telegram queue consumer error")
            await asyncio.sleep(2)
