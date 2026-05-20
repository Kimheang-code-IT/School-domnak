"""Entity list + keyboard helpers for Telegram report flow."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.services import telegram_report_service as reports
from app.services.telegram_state import UserState

ENTITY_ACTIONS = frozenset({"by_finance", "by_category", "by_course", "by_class", "by_teacher"})

ENTITY_TYPE_LABELS: dict[str, str] = {
    "by_finance": "Classes",
    "by_category": "Categories",
    "by_course": "Courses",
    "by_class": "Classes",
    "by_teacher": "Teachers",
}

BTN_ALL_ENTITIES = "📋 All"
BTN_ENTITY_NEXT = "▶️ Next"
BTN_ENTITY_PREV = "◀️ Prev"
ENTITY_KEYBOARD_PAGE_SIZE = 6


def action_needs_entity(action: str | None) -> bool:
    return action in ENTITY_ACTIONS


def load_entity_catalog(db: Session, action: str) -> list[dict[str, Any]]:
    if action in ("by_finance", "by_class"):
        return reports.list_all_classes(db)
    if action == "by_category":
        return reports.list_all_categories(db)
    if action == "by_course":
        return reports.list_all_courses(db)
    if action == "by_teacher":
        return reports.list_all_teachers(db)
    return []


def format_entity_catalog_text(action: str, entities: list[dict[str, Any]]) -> str:
    import html

    label = ENTITY_TYPE_LABELS.get(action, "Items")
    esc = lambda v: html.escape(str(v), quote=False)
    lines = [
        f"📋 <b>{esc(label)}</b> — {len(entities)} total",
        "",
        "Choose one item below, or tap <b>📋 All</b> for every item.",
        "",
    ]
    if not entities:
        lines.append("No items in the system yet.")
        return "\n".join(lines)

    for index, entity in enumerate(entities, start=1):
        lines.append(f"{index}. {esc(entity['name'])}")
    return "\n".join(lines)


def _truncate_button_label(text: str, *, max_len: int = 64) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) <= max_len:
        return cleaned
    return f"{cleaned[: max_len - 1]}…"


def build_entity_page_keyboard(state: UserState) -> dict[str, Any]:
    catalog = state.get("entity_catalog") or []
    page = max(0, int(state.get("entity_page") or 0))
    start = page * ENTITY_KEYBOARD_PAGE_SIZE
    chunk = catalog[start : start + ENTITY_KEYBOARD_PAGE_SIZE]

    button_map: dict[str, tuple[int | None, str]] = {
        BTN_ALL_ENTITIES.lower(): (None, "All"),
    }
    rows: list[list[dict[str, str]]] = [[{"text": BTN_ALL_ENTITIES}]]

    for offset, entity in enumerate(chunk):
        global_index = start + offset + 1
        label = _truncate_button_label(f"{global_index}. {entity['name']}")
        button_map[label.lower()] = (entity.get("id"), str(entity["name"]))
        rows.append([{"text": label}])

    nav_row: list[dict[str, str]] = []
    if page > 0:
        nav_row.append({"text": BTN_ENTITY_PREV})
        button_map[BTN_ENTITY_PREV.lower()] = (None, "__prev__")
    if start + ENTITY_KEYBOARD_PAGE_SIZE < len(catalog):
        nav_row.append({"text": BTN_ENTITY_NEXT})
        button_map[BTN_ENTITY_NEXT.lower()] = (None, "__next__")
    if nav_row:
        rows.append(nav_row)

    rows.append([{"text": "◀️ Main Menu"}])
    state["entity_button_map"] = button_map

    return {
        "keyboard": rows,
        "resize_keyboard": True,
        "one_time_keyboard": False,
        "is_persistent": True,
    }

