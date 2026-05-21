"""Login rate limiting (Redis-backed with in-process fallback)."""

from __future__ import annotations

import logging
import time
from collections import defaultdict

from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

_memory: dict[str, list[float]] = defaultdict(list)


def _redis_incr(key: str, window_seconds: int) -> int | None:
    try:
        from app.core.redis_cache import get_redis

        client = get_redis()
        pipe = client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds, nx=True)
        results = pipe.execute()
        return int(results[0])
    except Exception:
        logger.debug("Login rate limit Redis unavailable", exc_info=True)
        return None


def enforce_login_rate_limit(identifier: str) -> None:
    """
    Limit failed/successful login attempts per identifier (email + IP).
    Raises HTTP 429 when exceeded.
    """
    if not settings.login_rate_limit_enabled:
        return

    window = settings.login_rate_limit_window_seconds
    max_attempts = settings.login_rate_limit_max_attempts
    key = f"schooldomnak:v1:login:{identifier}"

    count = _redis_incr(key, window)
    if count is not None:
        if count > max_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later.",
            )
        return

    now = time.monotonic()
    bucket = _memory[identifier]
    _memory[identifier] = [t for t in bucket if now - t < window]
    _memory[identifier].append(now)
    if len(_memory[identifier]) > max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
        )
