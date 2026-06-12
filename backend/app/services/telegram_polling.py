"""Long-polling loop for Telegram (development / no public webhook)."""

from __future__ import annotations

import asyncio
import logging

import httpx

from app.core.config import settings
from app.services.telegram_bot_service import (
    TELEGRAM_API,
    _token,
    process_telegram_update,
    setup_telegram_bot,
)

logger = logging.getLogger(__name__)

_polling_task: asyncio.Task | None = None


async def _get_updates(client: httpx.AsyncClient, offset: int) -> list[dict]:
    token = _token()
    if not token:
        return []
    url = TELEGRAM_API.format(token=token, method="getUpdates")
    response = await client.get(
        url,
        params={"offset": offset, "timeout": 30, "allowed_updates": ["message", "edited_message", "callback_query"]},
        timeout=35.0,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(payload.get("description", "getUpdates failed"))
    return payload.get("result", [])


async def polling_loop() -> None:
    await setup_telegram_bot()
    offset = 0
    logger.info("Telegram polling started")
    async with httpx.AsyncClient() as client:
        while True:
            try:
                updates = await _get_updates(client, offset)
                for update in updates:
                    try:
                        await process_telegram_update(update)
                    except Exception:
                        logger.exception("Failed to process Telegram update")
                    offset = max(offset, update.get("update_id", 0) + 1)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Telegram polling error")
                await asyncio.sleep(3)


def start_telegram_polling() -> asyncio.Task | None:
    global _polling_task
    if _polling_task is not None:
        return _polling_task
    if not settings.telegram_bot_token.strip():
        logger.info("Telegram polling not started (TELEGRAM_BOT_TOKEN empty)")
        return None
    if not settings.telegram_use_polling:
        logger.info("Telegram polling disabled (TELEGRAM_USE_POLLING=false)")
        return None
    async def _run() -> None:
        try:
            await polling_loop()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Telegram polling crashed")

    _polling_task = asyncio.create_task(_run(), name="telegram_polling")
    return _polling_task


async def stop_telegram_polling() -> None:
    global _polling_task
    if _polling_task is None:
        return
    _polling_task.cancel()
    try:
        await _polling_task
    except asyncio.CancelledError:
        pass
    _polling_task = None
    logger.info("Telegram polling stopped")
