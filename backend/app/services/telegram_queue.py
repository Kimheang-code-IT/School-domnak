"""Redis queue between Telegram getUpdates and bot message handling."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

QUEUE_KEY = "school:telegram:updates"
PROCESSING_KEY = "school:telegram:processing"
STATS_KEY = "school:telegram:stats"


def _client():
    import redis

    return redis.from_url(settings.redis_url, decode_responses=True)


def enqueue_update(update: dict[str, Any]) -> bool:
    """Push an update for the worker (backend telegram_bot container)."""
    try:
        client = _client()
        client.lpush(QUEUE_KEY, json.dumps(update, default=str))
        client.hincrby(STATS_KEY, "enqueued", 1)
        return True
    except Exception:
        logger.exception("Failed to enqueue Telegram update")
        return False


def dequeue_update(timeout_seconds: int = 5) -> dict[str, Any] | None:
    """Block until an update is available (runs in a thread from async code)."""
    try:
        item = _client().brpop(QUEUE_KEY, timeout=timeout_seconds)
        if not item:
            return None
        _payload = item[1]
        return json.loads(_payload)
    except Exception:
        logger.exception("Failed to dequeue Telegram update")
        return None


def queue_length() -> int:
    try:
        return int(_client().llen(QUEUE_KEY))
    except Exception:
        return 0


def set_processing(active: bool) -> None:
    try:
        client = _client()
        if active:
            client.set(PROCESSING_KEY, "1", ex=120)
            client.hincrby(STATS_KEY, "processed", 0)
        else:
            client.delete(PROCESSING_KEY)
    except Exception:
        logger.debug("Could not set Telegram processing flag", exc_info=True)


def is_processing() -> bool:
    try:
        return bool(_client().exists(PROCESSING_KEY))
    except Exception:
        return False


def get_queue_status() -> dict[str, Any]:
    """For API / frontend loading indicator."""
    try:
        client = _client()
        stats = client.hgetall(STATS_KEY) or {}
        return {
            "ok": True,
            "queue_length": int(client.llen(QUEUE_KEY)),
            "processing": bool(client.exists(PROCESSING_KEY)),
            "poller_expected": settings.should_run_telegram_polling(),
            "enqueued_total": int(stats.get("enqueued", 0)),
            "processed_total": int(stats.get("processed", 0)),
        }
    except Exception as exc:
        logger.debug("Telegram queue status unavailable", exc_info=True)
        return {
            "ok": False,
            "queue_length": 0,
            "processing": False,
            "poller_expected": settings.should_run_telegram_polling(),
            "error": str(exc),
        }


def mark_processed() -> None:
    try:
        _client().hincrby(STATS_KEY, "processed", 1)
    except Exception:
        pass
