"""Redis cache-aside helpers (lists, dashboard, auth profile)."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_KEY_PREFIX = "schooldomnak:v1:"
_client: Any = None


def get_redis():
    global _client
    if _client is None:
        import redis

        _client = redis.from_url(
            settings.redis_cache_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            health_check_interval=30,
        )
    return _client


def cache_enabled() -> bool:
    return settings.redis_cache_enabled


def ping() -> bool:
    if not cache_enabled():
        return False
    try:
        return bool(get_redis().ping())
    except Exception:
        logger.exception("Redis cache ping failed")
        return False


def _stable_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def list_cache_key(resource: str, params: dict[str, Any]) -> str:
    return f"{_KEY_PREFIX}list:{resource}:{_stable_hash(params)}"


def simple_cache_key(namespace: str, suffix: str) -> str:
    return f"{_KEY_PREFIX}{namespace}:{suffix}"


def get_json(key: str) -> Any | None:
    try:
        raw = get_redis().get(key)
        if not raw:
            return None
        return json.loads(raw)
    except Exception:
        logger.exception("Redis cache get failed for %s", key)
        return None


def set_json(key: str, value: Any, ttl_seconds: int) -> None:
    try:
        get_redis().setex(key, ttl_seconds, json.dumps(value, default=str))
    except Exception:
        logger.exception("Redis cache set failed for %s", key)


def delete_key(key: str) -> None:
    try:
        get_redis().delete(key)
    except Exception:
        logger.exception("Redis cache delete failed for %s", key)


def delete_pattern(pattern: str) -> int:
    """Delete keys matching pattern (e.g. schooldomnak:v1:list:students:*)."""
    try:
        client = get_redis()
        removed = 0
        for key in client.scan_iter(match=pattern, count=200):
            client.delete(key)
            removed += 1
        return removed
    except Exception:
        logger.exception("Redis cache delete_pattern failed for %s", pattern)
        return 0


def invalidate_list_resource(resource: str) -> None:
    removed = delete_pattern(f"{_KEY_PREFIX}list:{resource}:*")
    if removed:
        logger.info("Cache invalidated %s list keys (%d)", resource, removed)


def invalidate_lists(*resources: str) -> None:
    for resource in resources:
        invalidate_list_resource(resource)


def invalidate_dashboard() -> None:
    delete_pattern(f"{_KEY_PREFIX}dashboard:*")


def invalidate_auth_me(user_id: int | None = None) -> None:
    if user_id is not None:
        delete_key(simple_cache_key("auth", f"me:{user_id}"))
        return
    delete_pattern(f"{_KEY_PREFIX}auth:me:*")


def invalidate_all_data_caches() -> None:
    """Clear list + dashboard caches after any data change."""
    delete_pattern(f"{_KEY_PREFIX}list:*")
    invalidate_dashboard()
