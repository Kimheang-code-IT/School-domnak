"""Telegram bot: command-based reports, period reply keyboard, backup alerts."""

from __future__ import annotations

import html
import logging
from datetime import date
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.services import telegram_report_service as reports
from app.services.telegram_bot_entities import (
    BTN_ALL_ENTITIES,
    BTN_ENTITY_NEXT,
    BTN_ENTITY_PREV,
    action_needs_entity,
    build_entity_page_keyboard,
    load_entity_catalog,
)
from app.services.telegram_auth_service import (
    extract_telegram_key_from_text,
    is_telegram_chat_registered,
    register_telegram_chat,
    unlink_telegram_chat,
)
from app.services.telegram_state import clear_user_state, get_user_state, reset_flow
from app.utils.date_period import parse_custom_date_range

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
PAGE_SIZE = 20

ACTION_LABELS: dict[str, str] = {
    "students_summary": "Students",
    "by_finance": "Finance",
    "by_class": "Classes",
}

ACTION_CALLBACKS = {
    "students_summary",
    "by_finance",
    "by_class",
}

# Report reply keyboard (bottom of chat — step 1)
BTN_STUDENTS = "🧑‍💻 Students"
BTN_FINANCE = "💰 Finance"
BTN_CLASS = "🏫 Classes"
BTN_BACKUP = "☁️ Backup"

# Period reply keyboard (bottom of chat — step 2)
BTN_PERIOD_TODAY = "Today"
BTN_PERIOD_YESTERDAY = "Yesterday"
BTN_PERIOD_MONTH = "This Month"
BTN_PERIOD_YEAR = "This Year"
BTN_PERIOD_ALL = "All Time"
BTN_PERIOD_CUSTOM = "Custom Range"
BTN_MAIN_MENU = "◀️ Main Menu"

# Text the user may send to leave period selection / return to report buttons
MAIN_MENU_REPLY_KEYS = frozenset(
    {
        BTN_MAIN_MENU.lower(),
        "cancel",
        "/cancel",
        "back",
        "/back",
        "main menu",
        "/menu",
    }
)

COMMAND_TO_ACTION: dict[str, str] = {
    "/students": "students_summary",
    "/finance": "by_finance",
    "/class": "by_class",
    "/classes": "by_class",
}

REPLY_TEXT_TO_ACTION: dict[str, str] = {
    BTN_STUDENTS.lower(): "students_summary",
    BTN_FINANCE.lower(): "by_finance",
    BTN_CLASS.lower(): "by_class",
    "students": "students_summary",
    "finance": "by_finance",
    "class": "by_class",
    "classes": "by_class",
}

REPLY_TEXT_TO_PERIOD: dict[str, str] = {
    BTN_PERIOD_TODAY.lower(): "today",
    BTN_PERIOD_YESTERDAY.lower(): "yesterday",
    BTN_PERIOD_MONTH.lower(): "this_month",
    BTN_PERIOD_YEAR.lower(): "this_year",
    BTN_PERIOD_ALL.lower(): "all_time",
    BTN_PERIOD_CUSTOM.lower(): "custom_range",
}


def _token() -> str:
    return settings.telegram_bot_token.strip()


def _allowed_chat_ids() -> set[str]:
    raw = settings.telegram_chat_id.strip()
    if not raw:
        return set()
    return {part.strip() for part in raw.split(",") if part.strip()}


def is_chat_allowed(chat_id: int | str) -> bool:
    """Legacy env allowlist (used for outbound system alerts)."""
    allowed = _allowed_chat_ids()
    if not allowed:
        return True
    return str(chat_id) in allowed


def register_prompt_text() -> str:
    return (
        f"{welcome_text()}\n\n"
        "🔐 Please enter your <b>Telegram Key</b> to use this bot.\n\n"
        "Example: <code>LC-A1B2C3D4</code>"
    )


async def ensure_telegram_registered(chat_id: int | str, text: str) -> bool:
    """
    Return True if this chat may use tools.
    Unregistered chats may only submit a telegram_key to register.
    """
    db = SessionLocal()
    try:
        if is_telegram_chat_registered(db, chat_id):
            return True

        key = extract_telegram_key_from_text(text)
        if key:
            user = register_telegram_chat(db, chat_id=chat_id, key=key)
            if user:
                await send_message(
                    chat_id,
                    (
                        f"✅ Registered as <b>{_esc(user.name)}</b>.\n\n"
                        f"{report_menu_text()}"
                    ),
                    reply_keyboard=build_report_reply_keyboard(),
                )
                return False  # already replied; caller should stop
            await send_message(chat_id, register_prompt_text())
            return False

        await send_message(chat_id, register_prompt_text())
        return False
    finally:
        db.close()


def build_report_reply_keyboard() -> dict[str, Any]:
    """Students, Finance, Classes, Backup only."""
    return {
        "keyboard": [
            [{"text": BTN_STUDENTS}, {"text": BTN_FINANCE}],
            [{"text": BTN_CLASS}, {"text": BTN_BACKUP}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def build_period_reply_keyboard() -> dict[str, Any]:
    """Step 3 — pick date period (bottom keyboard)."""
    return {
        "keyboard": [
            [{"text": BTN_PERIOD_TODAY}, {"text": BTN_PERIOD_YESTERDAY}],
            [{"text": BTN_PERIOD_MONTH}, {"text": BTN_PERIOD_YEAR}],
            [{"text": BTN_PERIOD_ALL}, {"text": BTN_PERIOD_CUSTOM}],
            [{"text": BTN_MAIN_MENU}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
        "is_persistent": True,
    }


def _esc(text: Any) -> str:
    return html.escape(str(text), quote=False)


async def _api(method: str, payload: dict[str, Any]) -> dict[str, Any]:
    token = _token()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
    url = TELEGRAM_API.format(token=token, method=method)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", "Telegram API error"))
    return data


async def send_message(
    chat_id: int | str,
    text: str,
    *,
    reply_keyboard: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text[:4096],
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_keyboard is not None:
        payload["reply_markup"] = reply_keyboard
    await _api("sendMessage", payload)


def format_backup_success_message(result: reports.BackupResult) -> str:
    lines = [
        "✅ <b>Backup completed successfully</b>",
        "",
        "☁️ <b>Google Sheets Backup</b>",
        f"Tables synced: {result.tables_synced}",
        f"Total rows: {result.total_rows}",
        "",
        _esc(result.message),
    ]
    if result.spreadsheet_url:
        lines.extend(["", f"Spreadsheet:\n{_esc(result.spreadsheet_url)}"])
    if result.finished_at:
        lines.extend(["", f"Time: {_esc(result.finished_at)}"])
    return "\n".join(lines)


async def send_backup_failure_alert(
    result: reports.BackupResult,
    *,
    primary_chat_id: int | str | None = None,
) -> None:
    """Notify chats when backup fails."""
    if result.ok:
        return
    text = (
        "❌ <b>Backup failed</b>\n\n"
        f"{_esc(result.message)}"
    )
    if result.finished_at:
        text += f"\n\nTime: {_esc(result.finished_at)}"
    await _broadcast_backup_message(text, primary_chat_id=primary_chat_id)


async def _broadcast_backup_message(
    text: str,
    *,
    primary_chat_id: int | str | None = None,
) -> None:
    if not _token():
        logger.warning("Telegram backup alert skipped: TELEGRAM_BOT_TOKEN not set")
        return
    keyboard = build_report_reply_keyboard()
    targets: list[str] = []
    if primary_chat_id is not None:
        targets.append(str(primary_chat_id))
    for chat_id in sorted(_allowed_chat_ids()):
        if chat_id not in targets:
            targets.append(chat_id)
    if not targets:
        logger.warning("Telegram backup alert skipped: TELEGRAM_CHAT_ID not set")
        return
    for chat_id in targets:
        try:
            await send_message(chat_id, text, reply_keyboard=keyboard)
        except Exception:
            logger.exception("Failed to send backup alert to chat_id=%s", chat_id)


async def send_backup_success_alert(
    result: reports.BackupResult,
    *,
    primary_chat_id: int | str | None = None,
) -> None:
    """Notify allowed chats (and optional trigger chat) when backup succeeds."""
    if not result.ok:
        return
    await _broadcast_backup_message(
        format_backup_success_message(result),
        primary_chat_id=primary_chat_id,
    )


async def answer_callback(callback_query_id: str, text: str | None = None) -> None:
    payload: dict[str, Any] = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text[:200]
    await _api("answerCallbackQuery", payload)


async def send_report_message(chat_id: int | str, text: str) -> None:
    """Report result; restore main report keyboard so user can pick another report."""
    await send_message(chat_id, text, reply_keyboard=build_report_reply_keyboard())


def _resolve_dates_from_state(user_id: int) -> tuple[Any, Any, str]:
    state = get_user_state(user_id)
    period = state.get("period") or "all_time"
    if period == "custom_range":
        start, end, label = reports.resolve_period_range(
            period,
            custom_start=state.get("custom_start"),
            custom_end=state.get("custom_end"),
        )
    else:
        start, end, label = reports.resolve_period_range(period)
    return start, end, label


def _format_students_summary(period_label: str, data: reports.StudentsSummary) -> str:
    """Compact totals (scheduled / celery tasks)."""
    return (
        f"📊 <b>Students Summary</b>\n"
        f"Period: {_esc(period_label)}\n\n"
        f"Total Students: {data.total_students}\n"
        f"Total Enrollments: {data.total_enrollments}\n"
        f"Active Students: {data.total_active_students}\n"
        f"Inactive Students: {data.total_inactive_students}\n"
        f"New Students In Period: {data.students_registered_in_period}"
    )


def _roster_totals(items: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "active": sum(int(row.get("active") or 0) for row in items),
        "inactive": sum(int(row.get("inactive") or 0) for row in items),
        "graduate": sum(int(row.get("graduate") or 0) for row in items),
    }


def _format_students_roster_report(
    period_label: str,
    items: list[dict[str, Any]],
    *,
    page: int = 1,
) -> str:
    start = (page - 1) * PAGE_SIZE
    chunk = items[start : start + PAGE_SIZE]
    lines = [f"📊 <b>Students Summary</b> ( {_esc(period_label)} )", ""]
    if not chunk:
        lines.append("No student data for this period.")
        return "\n".join(lines).strip()

    for index, row in enumerate(chunk):
        lines.append(f"<b>Class Name: {_esc(row['class_name'])}</b>")
        lines.append("")
        students = row.get("students") or []
        if students:
            for student in students:
                lines.append(f"- {_esc(student['name'])} : {_esc(student['duration'])}")
        else:
            lines.append("- No students")
        lines.append("")
        lines.append(f"Total Active : {row.get('active', 0)}")
        lines.append(f"Total Inactive : {row.get('inactive', 0)}")
        lines.append(f"Total Graduate : {row.get('graduate', 0)}")
        if index < len(chunk) - 1 or start + PAGE_SIZE < len(items):
            lines.append("")
            lines.append("---------------------------")
            lines.append("")

    totals = _roster_totals(items)
    lines.append("========================")
    lines.append("")
    lines.append(f"Total All Active : {totals['active']}")
    lines.append(f"Total All Inactive : {totals['inactive']}")
    lines.append(f"Total All Graduate : {totals['graduate']}")
    return "\n".join(lines).strip()


def _format_classes_summary_report(
    period_label: str,
    items: list[dict[str, Any]],
    *,
    page: int = 1,
) -> str:
    start = (page - 1) * PAGE_SIZE
    chunk = items[start : start + PAGE_SIZE]
    lines = [f"📊 <b>Class Summary</b> ( {_esc(period_label)} )", ""]
    if not chunk:
        lines.append("No class data for this period.")
        return "\n".join(lines).strip()

    for index, row in enumerate(chunk):
        lines.append(f"<b>Class Name: {_esc(row['class_name'])}</b>")
        lines.append("")
        lines.append(f"Total Active : {row.get('active', 0)}")
        lines.append(f"Total Inactive : {row.get('inactive', 0)}")
        lines.append(f"Total Graduate : {row.get('graduate', 0)}")
        if index < len(chunk) - 1 or start + PAGE_SIZE < len(items):
            lines.append("")
            lines.append("---------------------------")
            lines.append("")

    totals = _roster_totals(items)
    lines.append("========================")
    lines.append("")
    lines.append(f"Total All Active : {totals['active']}")
    lines.append(f"Total All Inactive : {totals['inactive']}")
    lines.append(f"Total All Graduate : {totals['graduate']}")
    return "\n".join(lines).strip()


def _format_finance_row_block(row: dict[str, Any]) -> list[str]:
    return [
        f"<b>Class Name: {_esc(row['class_name'])}</b>",
        "",
        f"- Electricity : ${row['electricity']:,.2f}",
        f"- Water : ${row['water']:,.2f}",
        f"- Internet : ${row['internet']:,.2f}",
        f"- Tik Tok : ${row['total_commission']:,.2f}",
        f"- Facebook : ${row['facebook']:,.2f}",
        f"- Other : ${row['other']:,.2f}",
        "",
        f"Grand Total (after discount) : ${row['amount']:,.2f}",
        f"Final Price : ${row['final_price']:,.2f}",
    ]


def _finance_totals(items: list[dict[str, Any]]) -> dict[str, float]:
    keys = (
        "electricity",
        "water",
        "internet",
        "total_commission",
        "facebook",
        "other",
        "amount",
        "final_price",
    )
    totals = {key: 0.0 for key in keys}
    for row in items:
        for key in keys:
            totals[key] += float(row.get(key) or 0)
    return totals


def _format_finance_report(
    period_label: str,
    items: list[dict[str, Any]],
    *,
    page: int,
) -> str:
    start = (page - 1) * PAGE_SIZE
    chunk = items[start : start + PAGE_SIZE]
    lines = [f"📊 <b>Finance Summary</b> ( {_esc(period_label)} )", ""]
    if not chunk:
        lines.append("No finance data for this period.")
        return "\n".join(lines).strip()

    for index, row in enumerate(chunk):
        lines.extend(_format_finance_row_block(row))
        if index < len(chunk) - 1 or start + PAGE_SIZE < len(items):
            lines.append("")
            lines.append("---------------------")
            lines.append("")

    totals = _finance_totals(items)
    lines.append("==================")
    lines.append("")
    lines.append(f"Grand Total (after discount) : ${totals['amount']:,.2f}")
    lines.append(f"Final Price : ${totals['final_price']:,.2f}")
    return "\n".join(lines).strip()


def _scope_header(scope_label: str | None) -> list[str]:
    if not scope_label:
        return []
    return [f"Item: <b>{_esc(scope_label)}</b>", ""]


def _scope_label_from_state(user_id: int) -> str | None:
    state = get_user_state(user_id)
    if state.get("filter_all_entities"):
        return "All"
    return state.get("filter_entity_label")


def _entity_filter_kwargs(user_id: int, action: str) -> dict[str, Any]:
    state = get_user_state(user_id)
    if state.get("filter_all_entities"):
        return {}
    entity_id = state.get("filter_entity_id")
    if action in ("students_summary", "by_class", "by_finance") and entity_id is not None:
        return {"class_id": entity_id}
    return {}


def run_report_for_action(
    db: Session,
    user_id: int,
    action: str,
    *,
    page: int = 1,
) -> str:
    start, end, period_label = _resolve_dates_from_state(user_id)
    filters = _entity_filter_kwargs(user_id, action)

    if action == "students_summary":
        items = reports.get_class_roster_report(db, start, end, include_students=True, **filters)
        return _format_students_roster_report(period_label, items, page=page)

    if action == "by_finance":
        items = reports.get_finance_report(db, start, end, **filters)
        return _format_finance_report(period_label, items, page=page)

    if action == "by_class":
        items = reports.get_classes_summary_report(db, start, end, **filters)
        return _format_classes_summary_report(period_label, items, page=page)

    return "Unknown report action."


def welcome_text() -> str:
    return "📋 <b>Welcome To Telegram ChatBot , Learn computer</b>"


def step1_text() -> str:
    return "<b>Step 1 — Please, Select tool do you want o know ?</b>"


def step2_text() -> str:
    return "<b>Step 2 — Please, Filter class do you want o know ?</b>"


def step3_text() -> str:
    return "<b>Step 3 — Please, Select Preiod do you want o know ?</b>"


def report_menu_text() -> str:
    """Main menu: welcome + Step 1 only (tools on the keyboard)."""
    return f"{welcome_text()}\n\n{step1_text()}"


def help_text() -> str:
    tz = settings.backup_timezone
    hour = settings.backup_schedule_hour
    minute = settings.backup_schedule_minute
    return (
        f"{report_menu_text()}\n\n"
        f"Tap <b>{_esc(BTN_BACKUP)}</b> to back up the database to Google Sheets now.\n"
        f"Automatic backup runs daily at {hour:02d}:{minute:02d} ({_esc(tz)})."
    )


def summary_text(db: Session) -> str:
    students = reports.get_students_summary(db, None, None)
    finance_rows = reports.get_finance_report(db, None, None)
    finance_total = sum(row["final_price"] for row in finance_rows)
    return (
        "📋 <b>System Summary</b> (All Time)\n\n"
        f"Students: {students.total_students}\n"
        f"Enrollments: {students.total_enrollments}\n"
        f"Finance classes: {len(finance_rows)}\n"
        f"Finance final total: ${finance_total:,.2f}"
    )


def _normalize_reply_key(text: str) -> str:
    return (text or "").strip().lower()


def _is_main_menu_request(text: str) -> bool:
    key = _normalize_reply_key(text)
    if key in MAIN_MENU_REPLY_KEYS:
        return True
    command = key.split()[0] if key else ""
    return command in ("/cancel", "/back", "/menu")


def _action_from_reply_text(text: str) -> str | None:
    return REPLY_TEXT_TO_ACTION.get(_normalize_reply_key(text))


def _period_from_reply_text(text: str) -> str | None:
    return REPLY_TEXT_TO_PERIOD.get(_normalize_reply_key(text))


def _is_backup_request(text: str) -> bool:
    key = _normalize_reply_key(text)
    if key in (BTN_BACKUP.lower(), "backup", "/backup", "backup to google sheets"):
        return True
    return BTN_BACKUP.lower() in key or "backup to google" in key


async def handle_manual_backup(chat_id: int | str) -> None:
    """Queue or run Google Sheets backup; success/failure alerts via Telegram."""
    keyboard = build_report_reply_keyboard()
    if not settings.google_sheets_backup_enabled:
        await send_message(
            chat_id,
            "⚠️ Google Sheets backup is disabled. Set GOOGLE_SHEETS_BACKUP_ENABLED=true in server config.",
            reply_keyboard=keyboard,
        )
        return

    from app.utils.task_dispatch import celery_available_cached, dispatch_google_sheets_backup

    if celery_available_cached():
        await send_message(
            chat_id,
            "⏳ <b>Backup queued</b>\nCelery worker is exporting to Google Sheets…",
            reply_keyboard=keyboard,
        )
        try:
            dispatch_google_sheets_backup()
        except Exception as exc:
            logger.exception("Failed to queue backup task")
            await send_message(
                chat_id,
                f"❌ <b>Could not queue backup</b>\n\n{_esc(exc)}",
                reply_keyboard=keyboard,
            )
        return

    await send_message(
        chat_id,
        "⏳ <b>Backup started</b>\nExporting database to Google Sheets…",
        reply_keyboard=keyboard,
    )

    import asyncio

    from app.services.google_sheets_backup_service import run_google_sheets_backup
    from app.services.telegram_notify import notify_backup_completed

    try:
        result = await asyncio.to_thread(run_google_sheets_backup)
        notify_backup_completed(result)
    except Exception as exc:
        logger.exception("Manual Telegram backup failed")
        await send_message(
            chat_id,
            f"❌ <b>Backup failed</b>\n\n{_esc(exc)}",
            reply_keyboard=keyboard,
        )


async def return_to_main_menu(chat_id: int | str, user_id: int) -> None:
    """Clear flow state and show report-type keyboard (Students, Income, …)."""
    clear_user_state(user_id)
    await send_message(
        chat_id,
        report_menu_text(),
        reply_keyboard=build_report_reply_keyboard(),
    )


async def show_report_menu(chat_id: int | str) -> None:
    await send_message(
        chat_id,
        report_menu_text(),
        reply_keyboard=build_report_reply_keyboard(),
    )


async def show_entity_menu(chat_id: int | str, user_id: int, action: str) -> None:
    """Step 2 — only the step sentence; class choices are on the keyboard."""
    _ = action
    state = get_user_state(user_id)
    await send_message(
        chat_id,
        step2_text(),
        reply_keyboard=build_entity_page_keyboard(state),
    )


async def show_period_menu(chat_id: int | str, action: str, user_id: int) -> None:
    """Step 3 — only the step sentence; period choices are on the keyboard."""
    _ = (action, user_id)
    await send_message(chat_id, step3_text(), reply_keyboard=build_period_reply_keyboard())


async def apply_period_selection(chat_id: int, user_id: int, period: str) -> None:
    state = get_user_state(user_id)
    action = state.get("selected_action")
    if not action:
        await return_to_main_menu(chat_id, user_id)
        return
    if period == "custom_range":
        state["waiting_custom_range"] = True
        state["period"] = period
        await send_message(
            chat_id,
            "📆 Please enter date range like:\n<code>2026-05-01 to 2026-05-18</code>",
            reply_keyboard=build_period_reply_keyboard(),
        )
        return
    state["waiting_custom_range"] = False
    state["period"] = period
    state["custom_start"] = None
    state["custom_end"] = None
    await execute_report(chat_id, user_id, action)


async def start_report_command(chat_id: int, user_id: int, action: str) -> None:
    state = get_user_state(user_id)
    state["selected_action"] = action
    state["page"] = 1
    state["waiting_custom_range"] = False
    state["awaiting_entity"] = False
    state["filter_entity_id"] = None
    state["filter_entity_label"] = None
    state["filter_all_entities"] = False
    state["entity_page"] = 0
    state["entity_catalog"] = []
    state["entity_button_map"] = {}

    if action_needs_entity(action):
        db = SessionLocal()
        try:
            state["entity_catalog"] = load_entity_catalog(db, action)
            state["awaiting_entity"] = True
            await show_entity_menu(chat_id, user_id, action)
        finally:
            db.close()
        return

    await show_period_menu(chat_id, action, user_id)


async def execute_report(
    chat_id: int | str,
    user_id: int,
    action: str,
    *,
    page: int = 1,
) -> None:
    db = SessionLocal()
    try:
        get_user_state(user_id)["page"] = page
        text = run_report_for_action(db, user_id, action, page=page)
        await send_report_message(chat_id, text)
    except Exception as exc:
        logger.exception("Report failed for action=%s", action)
        await send_message(
            chat_id,
            f"❌ Report failed.\n\n{_esc(exc)}",
            reply_keyboard=build_period_reply_keyboard(),
        )
    finally:
        db.close()


async def handle_text_message(chat_id: int, user_id: int, text: str) -> None:
    state = get_user_state(user_id)
    normalized = (text or "").strip()
    command = normalized.split()[0].lower() if normalized else ""

    if _is_main_menu_request(normalized):
        await return_to_main_menu(chat_id, user_id)
        return

    if state.get("waiting_custom_range"):
        try:
            start, end = parse_custom_date_range(normalized)
        except ValueError as exc:
            await send_message(
                chat_id,
                f"❌ {_esc(exc)}\n\nExample:\n<code>2026-05-01 to 2026-05-18</code>",
                reply_keyboard=build_period_reply_keyboard(),
            )
            return
        state["waiting_custom_range"] = False
        state["custom_start"] = start
        state["custom_end"] = end
        state["period"] = "custom_range"
        action = state.get("selected_action")
        if not action:
            await return_to_main_menu(chat_id, user_id)
            return
        await execute_report(chat_id, user_id, action)
        return

    key = _normalize_reply_key(normalized)

    if _is_backup_request(normalized) or command == "/backup":
        await handle_manual_backup(chat_id)
        return

    if command in ("/logout", "/unlink"):
        db = SessionLocal()
        try:
            unlinked = unlink_telegram_chat(db, chat_id)
        finally:
            db.close()
        clear_user_state(user_id)
        if unlinked:
            await send_message(chat_id, "🔓 Unlinked. Send your telegram_key to register again.")
        else:
            await send_message(chat_id, register_prompt_text())
        return

    if state.get("awaiting_entity"):
        action = state.get("selected_action")
        if not action:
            await return_to_main_menu(chat_id, user_id)
            return
        button_map = state.get("entity_button_map") or {}
        entry = button_map.get(key)
        if entry is not None:
            entity_id, label = entry
            if label == "__prev__":
                state["entity_page"] = max(0, int(state.get("entity_page") or 0) - 1)
                await show_entity_menu(chat_id, user_id, action)
                return
            if label == "__next__":
                state["entity_page"] = int(state.get("entity_page") or 0) + 1
                await show_entity_menu(chat_id, user_id, action)
                return
            state["filter_entity_id"] = entity_id
            state["filter_entity_label"] = label
            state["filter_all_entities"] = label == "All"
            state["awaiting_entity"] = False
            await show_period_menu(chat_id, action, user_id)
            return
        await send_message(
            chat_id,
            f"Tap an item, <b>{_esc(BTN_ALL_ENTITIES)}</b>, or <b>{_esc(BTN_MAIN_MENU)}</b>.",
            reply_keyboard=build_entity_page_keyboard(state),
        )
        return

    period_key = _period_from_reply_text(normalized)
    if period_key and state.get("selected_action") and not state.get("awaiting_entity"):
        await apply_period_selection(chat_id, user_id, period_key)
        return

    action_key = _action_from_reply_text(normalized)
    if action_key:
        await start_report_command(chat_id, user_id, action_key)
        return

    if command in COMMAND_TO_ACTION:
        reset_flow(user_id)
        await start_report_command(chat_id, user_id, COMMAND_TO_ACTION[command])
        return

    if command in ("/start", "/help", "/report"):
        if command == "/help":
            await send_message(chat_id, help_text(), reply_keyboard=build_report_reply_keyboard())
            return
        await return_to_main_menu(chat_id, user_id)
        return

    if command == "/summary":
        db = SessionLocal()
        try:
            await send_message(
                chat_id,
                summary_text(db),
                reply_keyboard=build_report_reply_keyboard(),
            )
        finally:
            db.close()
        return

    await send_message(
        chat_id,
        "Tap a report on the keyboard below, or send /start",
        reply_keyboard=build_report_reply_keyboard(),
    )


async def handle_callback_query(update: dict[str, Any]) -> None:
    callback = update.get("callback_query") or {}
    callback_id = callback.get("id")
    data = (callback.get("data") or "").strip()
    message = callback.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    message_id = message.get("message_id")
    from_user = callback.get("from") or {}
    user_id = from_user.get("id")

    if chat_id is None or user_id is None:
        return
    db = SessionLocal()
    try:
        registered = is_telegram_chat_registered(db, chat_id)
    finally:
        db.close()
    if not registered:
        if callback_id:
            await answer_callback(callback_id, "Enter telegram_key first")
        await send_message(chat_id, register_prompt_text())
        return
    if callback_id:
        await answer_callback(callback_id)

    state = get_user_state(user_id)

    if data == "nav:cancel":
        await return_to_main_menu(chat_id, user_id)
        return

    if data.startswith("action:"):
        action = data.split(":", 1)[1]
        if action not in ACTION_CALLBACKS:
            return
        await start_report_command(chat_id, user_id, action)
        return

    if data.startswith("period:"):
        period = data.split(":", 1)[1]
        if not state.get("selected_action"):
            await return_to_main_menu(chat_id, user_id)
            return
        await apply_period_selection(chat_id, user_id, period)
        return


async def process_telegram_update(update: dict[str, Any]) -> None:
    if not _token():
        logger.warning("Telegram update ignored: TELEGRAM_BOT_TOKEN not set")
        return

    if "callback_query" in update:
        await handle_callback_query(update)
        return

    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    from_user = message.get("from") or {}
    user_id = from_user.get("id")
    text = message.get("text") or ""

    if chat_id is None or user_id is None:
        return

    if not await ensure_telegram_registered(chat_id, text):
        return

    await handle_text_message(chat_id, user_id, text)


async def set_webhook(webhook_url: str) -> None:
    secret = settings.telegram_webhook_secret.strip() or None
    payload: dict[str, Any] = {
        "url": webhook_url,
        "allowed_updates": ["message", "edited_message", "callback_query"],
    }
    if secret:
        payload["secret_token"] = secret
    await _api("setWebhook", payload)


async def delete_webhook(*, drop_pending_updates: bool = False) -> None:
    await _api("deleteWebhook", {"drop_pending_updates": drop_pending_updates})


BOT_COMMANDS = [
    {"command": "start", "description": "Show tools menu"},
    {"command": "students", "description": "Students by class"},
    {"command": "finance", "description": "Finance by class"},
    {"command": "classes", "description": "Class summary"},
    {"command": "backup", "description": "Backup to Google Sheets now"},
    {"command": "register", "description": "Register with telegram_key"},
    {"command": "logout", "description": "Unlink this Telegram chat"},
    {"command": "help", "description": "Help"},
    {"command": "cancel", "description": "Cancel"},
]


async def set_bot_commands() -> None:
    """Register command list shown in Telegram menu (☰ / list)."""
    if not _token():
        return
    await _api("setMyCommands", {"commands": BOT_COMMANDS})
    logger.info("Telegram bot command menu registered (%s commands)", len(BOT_COMMANDS))


async def setup_telegram_bot() -> None:
    """Call once on startup: command menu + delete webhook when polling."""
    if not _token():
        return
    await set_bot_commands()
    if settings.telegram_use_polling:
        try:
            await delete_webhook(drop_pending_updates=True)
        except Exception:
            logger.debug("deleteWebhook on setup failed", exc_info=True)
