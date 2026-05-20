"""Redis lock so only one process calls Telegram getUpdates (avoids HTTP 409)."""

from __future__ import annotations

import logging
import socket
import uuid

from app.core.config import settings

logger = logging.getLogger(__name__)

LOCK_KEY = "school:telegram:getupdates:lock"
# Long-poll timeout is 30s; TTL must survive a full getUpdates + enqueue.
LOCK_TTL_SECONDS = 90

_INSTANCE_ID = f"{socket.gethostname()}:{uuid.uuid4().hex[:8]}"


def _client():
    import redis

    return redis.from_url(settings.redis_url, decode_responses=True)


def polling_lock_holder() -> str | None:
    try:
        return _client().get(LOCK_KEY)
    except Exception:
        logger.debug("Could not read Telegram polling lock", exc_info=True)
        return None


def instance_id() -> str:
    return _INSTANCE_ID


def holds_polling_lock() -> bool:
    return polling_lock_holder() == _INSTANCE_ID


def acquire_polling_lock() -> bool:
    """Try to become the sole Telegram long-poller."""
    try:
        acquired = _client().set(LOCK_KEY, _INSTANCE_ID, nx=True, ex=LOCK_TTL_SECONDS)
        if acquired:
            logger.info("Telegram polling lock acquired by %s", _INSTANCE_ID)
        return bool(acquired)
    except Exception:
        logger.exception("Redis unavailable for Telegram polling lock")
        return False


def ensure_polling_lock() -> bool:
    """
    Acquire the lock if free, or extend TTL if this process already holds it.
    Without this, each poll iteration fails NX acquire and waits 10s on itself.
    """
    if holds_polling_lock():
        return refresh_polling_lock()
    return acquire_polling_lock()


def refresh_polling_lock() -> bool:
    try:
        return bool(
            _client().set(LOCK_KEY, _INSTANCE_ID, xx=True, ex=LOCK_TTL_SECONDS)
        )
    except Exception:
        logger.debug("Could not refresh Telegram polling lock", exc_info=True)
        return False


def clear_stale_lock_from_same_host() -> None:
    """After container restart, Redis may still hold our hostname with an old instance id."""
    try:
        holder = polling_lock_holder()
        if not holder:
            return
        host = holder.split(":", 1)[0]
        if host == socket.gethostname():
            _client().delete(LOCK_KEY)
            logger.info("Cleared stale Telegram polling lock (%s)", holder)
    except Exception:
        logger.debug("Could not clear stale Telegram polling lock", exc_info=True)


def release_polling_lock() -> None:
    try:
        client = _client()
        holder = client.get(LOCK_KEY)
        if holder == _INSTANCE_ID:
            client.delete(LOCK_KEY)
            logger.info("Telegram polling lock released by %s", _INSTANCE_ID)
    except Exception:
        logger.debug("Could not release Telegram polling lock", exc_info=True)
