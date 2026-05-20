"""Long-polling loop for Telegram (development / no public webhook)."""

from __future__ import annotations

import asyncio
import logging

import httpx

from app.core.config import settings
from app.services.telegram_bot_service import (
    TELEGRAM_API,
    _token,
    delete_webhook,
    process_telegram_update,
    setup_telegram_bot,
)
from app.services.telegram_polling_lock import (
    clear_stale_lock_from_same_host,
    ensure_polling_lock,
    holds_polling_lock,
    polling_lock_holder,
    refresh_polling_lock,
    release_polling_lock,
)
from app.services.telegram_queue import enqueue_update

logger = logging.getLogger(__name__)

_polling_task: asyncio.Task | None = None


class TelegramPollingConflictError(Exception):
    """Telegram returned 409 — another process is already calling getUpdates."""


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
    if response.status_code == 409:
        raise TelegramPollingConflictError(response.text)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(payload.get("description", "getUpdates failed"))
    return payload.get("result", [])


async def polling_loop() -> None:
    if not settings.should_run_telegram_polling():
        logger.error(
            "Telegram polling not allowed in this process "
            "(set TELEGRAM_POLLING_ROLE=dedicated on school-telegram-bot only)."
        )
        return

    await setup_telegram_bot()
    try:
        await delete_webhook(drop_pending_updates=True)
    except Exception:
        logger.debug("deleteWebhook on polling start failed", exc_info=True)

    clear_stale_lock_from_same_host()

    offset = 0
    conflict_backoff = 30
    lock_wait_logged = False
    logger.info("Telegram polling started (role=%s)", settings.telegram_polling_role or "api")
    async with httpx.AsyncClient() as client:
        while True:
            try:
                if not ensure_polling_lock():
                    holder = polling_lock_holder()
                    if not lock_wait_logged:
                        logger.info(
                            "Another process holds Telegram polling lock (%s); "
                            "this worker will retry (frontend/API stay available).",
                            holder or "unknown",
                        )
                        lock_wait_logged = True
                    await asyncio.sleep(5)
                    continue
                lock_wait_logged = False

                updates = await _get_updates(client, offset)
                if holds_polling_lock():
                    refresh_polling_lock()
                conflict_backoff = 30
                for update in updates:
                    if not enqueue_update(update):
                        try:
                            await process_telegram_update(update)
                        except Exception:
                            logger.exception("Failed to process Telegram update inline")
                    offset = max(offset, update.get("update_id", 0) + 1)
            except asyncio.CancelledError:
                release_polling_lock()
                raise
            except TelegramPollingConflictError:
                release_polling_lock()
                holder = polling_lock_holder()
                logger.warning(
                    "Telegram 409 Conflict: another process is polling this bot token "
                    "(lock holder: %s). Retrying in %ss… "
                    "Stop local uvicorn/run_telegram_polling.py; keep only school-telegram-bot.",
                    holder or "unknown",
                    conflict_backoff,
                )
                try:
                    await delete_webhook(drop_pending_updates=True)
                except Exception:
                    logger.debug("deleteWebhook after 409 failed", exc_info=True)
                await asyncio.sleep(conflict_backoff)
                conflict_backoff = min(conflict_backoff * 2, 300)
            except Exception:
                logger.exception("Telegram polling error")
                await asyncio.sleep(3)


def start_telegram_polling() -> asyncio.Task | None:
    global _polling_task
    if _polling_task is not None:
        return _polling_task
    if not settings.should_run_telegram_polling():
        logger.info(
            "Telegram polling not started (token empty, TELEGRAM_USE_POLLING=false, "
            "TELEGRAM_POLLING_ROLE=disabled, or not the dedicated bot container)"
        )
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
