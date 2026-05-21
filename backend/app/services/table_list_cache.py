"""Cache-aside for paginated table API responses: Redis → else DB → store in Redis."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from app.core.config import settings
from app.core.redis_cache import cache_enabled, get_json, list_cache_key, set_json
from app.schemas.common import TableQueryParams

logger = logging.getLogger(__name__)

SerializeFn = Callable[[list[Any], int], dict[str, Any]]
LoadFn = Callable[[], tuple[list[Any], int]]


def build_list_params(query: TableQueryParams, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    params: dict[str, Any] = query.model_dump(mode="json")
    if extra:
        for key, value in extra.items():
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            params[key] = value
    return params


def default_serialize(data: list[Any], total: int) -> dict[str, Any]:
    rows: list[Any] = []
    for item in data:
        if hasattr(item, "model_dump"):
            rows.append(item.model_dump(mode="json"))
        elif isinstance(item, dict):
            rows.append(item)
        else:
            rows.append(item)
    return {"data": rows, "total": total}


def cached_table_list(
    resource: str,
    query: TableQueryParams,
    loader: LoadFn,
    *,
    extra: dict[str, Any] | None = None,
    ttl_seconds: int | None = None,
    serialize: SerializeFn | None = None,
) -> dict[str, Any]:
    """
    1. Check Redis for this resource + query + filters
    2. On hit → return cached JSON
    3. On miss → run loader(), serialize, save to Redis, return
    """
    if not cache_enabled():
        data, total = loader()
        return (serialize or default_serialize)(data, total)

    params = build_list_params(query, extra)
    key = list_cache_key(resource, params)
    cached = get_json(key)
    if cached is not None:
        logger.debug("Redis cache HIT %s", resource)
        return cached

    data, total = loader()
    payload = (serialize or default_serialize)(data, total)
    ttl = ttl_seconds if ttl_seconds is not None else settings.redis_cache_ttl_list
    set_json(key, payload, ttl)
    logger.debug("Redis cache MISS %s (stored %ss)", resource, ttl)
    return payload


def cached_value(
    namespace: str,
    suffix: str,
    loader: Callable[[], dict[str, Any]],
    *,
    ttl_seconds: int,
) -> dict[str, Any]:
    from app.core.redis_cache import get_json, set_json, simple_cache_key

    if not cache_enabled():
        return loader()

    key = simple_cache_key(namespace, suffix)
    cached = get_json(key)
    if cached is not None:
        return cached

    payload = loader()
    set_json(key, payload, ttl_seconds)
    return payload
