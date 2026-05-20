"""In-memory per-user Telegram bot state (swap with Redis later)."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any, TypedDict


class UserState(TypedDict, total=False):
    selected_action: str | None
    waiting_custom_range: bool
    awaiting_entity: bool
    period: str | None
    custom_start: date | None
    custom_end: date | None
    page: int
    entity_page: int
    entity_catalog: list[dict[str, Any]]
    entity_button_map: dict[str, tuple[int | None, str]]
    filter_entity_id: int | None
    filter_entity_label: str | None
    filter_all_entities: bool


USER_STATE: dict[int, UserState] = {}


def get_user_state(user_id: int) -> UserState:
    if user_id not in USER_STATE:
        USER_STATE[user_id] = UserState(
            selected_action=None,
            waiting_custom_range=False,
            awaiting_entity=False,
            period=None,
            custom_start=None,
            custom_end=None,
            page=1,
            entity_page=0,
            entity_catalog=[],
            entity_button_map={},
            filter_entity_id=None,
            filter_entity_label=None,
            filter_all_entities=False,
        )
    return USER_STATE[user_id]


def clear_user_state(user_id: int) -> None:
    USER_STATE.pop(user_id, None)


def reset_flow(user_id: int) -> None:
    state = get_user_state(user_id)
    state["selected_action"] = None
    state["waiting_custom_range"] = False
    state["awaiting_entity"] = False
    state["period"] = None
    state["custom_start"] = None
    state["custom_end"] = None
    state["page"] = 1
    state["entity_page"] = 0
    state["entity_catalog"] = []
    state["entity_button_map"] = {}
    state["filter_entity_id"] = None
    state["filter_entity_label"] = None
    state["filter_all_entities"] = False


def snapshot_state(user_id: int) -> dict[str, Any]:
    return deepcopy(dict(get_user_state(user_id)))
