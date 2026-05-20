import uuid
from typing import Any

_PREVIEW_SESSIONS: dict[str, list[dict[str, Any]]] = {}


def create_preview_session(invoices: list[dict[str, Any]]) -> str:
    key = uuid.uuid4().hex
    _PREVIEW_SESSIONS[key] = invoices
    return key


def get_preview_session(preview_key: str) -> list[dict[str, Any]] | None:
    return _PREVIEW_SESSIONS.get(preview_key)
