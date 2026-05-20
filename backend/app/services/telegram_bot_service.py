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
    ENTITY_TYPE_LABELS,
    action_needs_entity,
    build_entity_page_keyboard,
    format_entity_catalog_text,
    load_entity_catalog,
)
from app.services.telegram_state import clear_user_state, get_user_state, reset_flow
from app.utils.date_period import parse_custom_date_range

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
PAGE_SIZE = 20

ACTION_LABELS: dict[str, str] = {
    "students_summary": "Students Summary",
    "by_finance": "Finance",
    "by_category": "By Category",
    "by_course": "By Course",
    "by_class": "By Class",
    "by_teacher": "By Teacher",
    "registration_summary": "Registration Summary",
}

ACTION_CALLBACKS = {
    "students_summary",
    "by_finance",
    "by_category",
    "by_course",
    "by_class",
    "by_teacher",
    "registration_summary",
}

# Report reply keyboard (bottom of chat — step 1)
BTN_STUDENTS = "📊 Students"
BTN_FINANCE = "💰 Finance"
BTN_CATEGORY = "📂 Category"
BTN_COURSE = "📚 Course"
BTN_CLASS = "🏫 Class"
BTN_TEACHER = "👨‍🏫 Teacher"

# Period reply keyboard (bottom of chat — step 2)
BTN_PERIOD_TODAY = "Today"
BTN_PERIOD_YESTERDAY = "Yesterday"
BTN_PERIOD_MONTH = "This Month"
BTN_PERIOD_YEAR = "This Year"
BTN_PERIOD_ALL = "All Time"
BTN_PERIOD_CUSTOM = "Custom Range"
BTN_MAIN_MENU = "◀️ Main Menu"
BTN_BACKUP = "☁️ Backup to Google Sheets"

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
    "/income": "by_finance",
    "/category": "by_category",
    "/course": "by_course",
    "/class": "by_class",
    "/teacher": "by_teacher",
    "/registration": "registration_summary",
}

REPLY_TEXT_TO_ACTION: dict[str, str] = {
    BTN_STUDENTS.lower(): "students_summary",
    BTN_FINANCE.lower(): "by_finance",
    "income": "by_finance",
    "💰 income": "by_finance",
    BTN_CATEGORY.lower(): "by_category",
    BTN_COURSE.lower(): "by_course",
    BTN_CLASS.lower(): "by_class",
    BTN_TEACHER.lower(): "by_teacher",
    "students": "students_summary",
    "finance": "by_finance",
    "category": "by_category",
    "course": "by_course",
    "class": "by_class",
    "teacher": "by_teacher",
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
    allowed = _allowed_chat_ids()
    if not allowed:
        return True
    return str(chat_id) in allowed


def build_report_reply_keyboard() -> dict[str, Any]:
    """Reports + manual Google Sheets backup."""
    return {
        "keyboard": [
            [{"text": BTN_STUDENTS}, {"text": BTN_FINANCE}],
            [{"text": BTN_CATEGORY}, {"text": BTN_COURSE}],
            [{"text": BTN_CLASS}, {"text": BTN_TEACHER}],
            [{"text": BTN_BACKUP}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def build_period_reply_keyboard() -> dict[str, Any]:
    """Step 2 — pick date period (bottom keyboard)."""
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


def _format_students_summary_by_class(
    period_label: str,
    items: list[dict[str, Any]],
    *,
    page: int = 1,
) -> str:
    start = (page - 1) * PAGE_SIZE
    chunk = items[start : start + PAGE_SIZE]
    lines = ["📊 <b>Students Summary</b>", f"Period: {_esc(period_label)}", ""]
    if not chunk:
        lines.append("No student data for this period.")
    else:
        for row in chunk:
            lines.append(f"- Class Name: {_esc(row['class_name'])}")
            lines.append(f"Total Students: {row['active_students']} ( Active )")
            lines.append(f"Total Students: {row['inactive_students']} ( Inactive )")
            lines.append(f"Total Enrollments: {row['total_enrollments']}")
            lines.append(f"New Students In Period: {row['new_students_in_period']}")
            lines.append("")
    return "\n".join(lines).strip()


def _format_finance_row_block(index: int, row: dict[str, Any]) -> list[str]:
    return [
        f"{index}. {_esc(row['class_name'])}",
        f"Electricity: ${row['electricity']:,.2f}",
        f"Water: ${row['water']:,.2f}",
        f"Internet: ${row['internet']:,.2f}",
        f"Total Commission: ${row['total_commission']:,.2f}",
        f"Facebook: ${row['facebook']:,.2f}",
        f"Other: ${row['other']:,.2f}",
        f"Amount: ${row['amount']:,.2f}",
        f"Final Price: ${row['final_price']:,.2f}",
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
    scope_label: str | None = None,
) -> str:
    start = (page - 1) * PAGE_SIZE
    chunk = items[start : start + PAGE_SIZE]
    lines = ["💰 <b>Finance</b>", f"Period: {_esc(period_label)}", ""]
    lines.extend(_scope_header(scope_label))
    if not chunk:
        lines.append("No finance data for this period.")
    else:
        for index, row in enumerate(chunk, start=start + 1):
            lines.extend(_format_finance_row_block(index, row))
            lines.append("")
        if len(items) > 1:
            totals = _finance_totals(items)
            lines.append(f"<b>Total (Count: {len(items)})</b>")
            lines.append(f"Electricity: ${totals['electricity']:,.2f}")
            lines.append(f"Water: ${totals['water']:,.2f}")
            lines.append(f"Internet: ${totals['internet']:,.2f}")
            lines.append(f"Total Commission: ${totals['total_commission']:,.2f}")
            lines.append(f"Facebook: ${totals['facebook']:,.2f}")
            lines.append(f"Other: ${totals['other']:,.2f}")
            lines.append(f"Amount: ${totals['amount']:,.2f}")
            lines.append(f"Final Price: ${totals['final_price']:,.2f}")
    return "\n".join(lines).strip()


def _format_registration_summary(period_label: str, data: reports.RegistrationSummary) -> str:
    return (
        f"📝 <b>Registration Summary</b>\n"
        f"Period: {_esc(period_label)}\n\n"
        f"Total Registrations: {data.total_registrations}\n"
        f"Active: {data.active_registrations}\n"
        f"Inactive: {data.inactive_registrations}\n"
        f"Registration Amount: ${data.total_registration_amount:,.2f}"
    )


def _scope_header(scope_label: str | None) -> list[str]:
    if not scope_label:
        return []
    return [f"Item: <b>{_esc(scope_label)}</b>", ""]


def _format_enrollment_detail_report(
    title: str,
    period_label: str,
    items: list[dict[str, Any]],
    *,
    page: int,
    scope_label: str | None = None,
    show_teacher_line: bool = False,
    show_commission: bool = False,
) -> str:
    start = (page - 1) * PAGE_SIZE
    chunk = items[start : start + PAGE_SIZE]
    lines = [title, f"Period: {_esc(period_label)}", ""]
    lines.extend(_scope_header(scope_label))
    if not chunk:
        lines.append("No data for this period.")
    else:
        for index, row in enumerate(chunk, start=start + 1):
            lines.append(f"{index}. {_esc(row['item_name'])}")
            if show_teacher_line:
                lines.append(f"- Teacher: {_esc(row.get('teacher_name') or '—')}")
            else:
                class_names = row.get("class_names") or []
                if class_names:
                    for class_name in class_names:
                        lines.append(f"- Class Name: {_esc(class_name)}")
                else:
                    lines.append("- Class Name: —")
            lines.append(f"Students: {row['active_students']} ( Active )")
            lines.append(f"Students: {row['inactive_students']} ( Inactive )")
            lines.append(f"Subtotal: ${row['subtotal']:,.2f}")
            lines.append(f"Discount: ${row['discount']:,.2f}")
            lines.append(f"Grand Total: ${row['grand_total']:,.2f}")
            if show_commission:
                lines.append(f"Commission: ${row.get('commission', 0):,.2f}")
            lines.append("")
    return "\n".join(lines).strip()


def _format_list_report(
    title: str,
    period_label: str,
    items: list[dict[str, Any]],
    *,
    page: int,
    formatter,
    scope_label: str | None = None,
) -> tuple[str, bool]:
    start = (page - 1) * PAGE_SIZE
    chunk = items[start : start + PAGE_SIZE]
    has_next = len(items) > start + PAGE_SIZE
    lines = [f"{title}", f"Period: {_esc(period_label)}", ""]
    lines.extend(_scope_header(scope_label))
    if not chunk:
        lines.append("No data for this period.")
    else:
        for index, item in enumerate(chunk, start=start + 1):
            lines.append(formatter(index, item))
            lines.append("")
    return "\n".join(lines).strip(), has_next


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
    if action == "by_category" and entity_id is not None:
        return {"category_id": entity_id}
    if action == "by_course" and entity_id is not None:
        return {"course_id": entity_id}
    if action in ("by_class", "by_finance") and entity_id is not None:
        return {"class_id": entity_id}
    if action == "by_teacher":
        label = state.get("filter_entity_label")
        if label and label != "All":
            return {"teacher_name": label}
    return {}


def run_report_for_action(
    db: Session,
    user_id: int,
    action: str,
    *,
    page: int = 1,
) -> str:
    start, end, period_label = _resolve_dates_from_state(user_id)
    scope_label = _scope_label_from_state(user_id) if action_needs_entity(action) else None
    filters = _entity_filter_kwargs(user_id, action)

    if action == "students_summary":
        items = reports.get_students_summary_by_class(db, start, end)
        return _format_students_summary_by_class(period_label, items, page=page)

    if action == "by_finance":
        items = reports.get_finance_report(db, start, end, **filters)
        return _format_finance_report(period_label, items, page=page, scope_label=scope_label)

    if action == "registration_summary":
        data = reports.get_registration_summary(db, start, end)
        return _format_registration_summary(period_label, data)

    if action == "by_category":
        items = reports.get_students_by_category_detail(db, start, end, **filters)
        return _format_enrollment_detail_report(
            "📂 <b>Students By Category</b>",
            period_label,
            items,
            page=page,
            scope_label=scope_label,
        )

    if action == "by_course":
        items = reports.get_students_by_course_detail(db, start, end, **filters)
        return _format_enrollment_detail_report(
            "📚 <b>Students By Course</b>",
            period_label,
            items,
            page=page,
            scope_label=scope_label,
        )

    if action == "by_class":
        items = reports.get_students_by_class_detail(db, start, end, **filters)
        return _format_enrollment_detail_report(
            "🏫 <b>Students By Class</b>",
            period_label,
            items,
            page=page,
            scope_label=scope_label,
            show_teacher_line=True,
        )

    if action == "by_teacher":
        items = reports.get_students_by_teacher_detail(db, start, end, **filters)
        return _format_enrollment_detail_report(
            "👨‍🏫 <b>Students By Teacher</b>",
            period_label,
            items,
            page=page,
            scope_label=scope_label,
            show_commission=True,
        )

    return "Unknown report action."


def report_menu_text() -> str:
    return (
        "📋 <b>School Domnak Reports</b>\n\n"
        "<b>Step 1:</b> Choose report type\n"
        "<b>Step 2:</b> Finance / Category / Course / Class / Teacher — pick item or <b>📋 All</b>\n"
        "<b>Step 3:</b> Choose period (<b>All Time</b> = no date filter)\n\n"
        "Students goes straight to period.\n"
        "Commands: /students /finance /category /course /class /teacher"
    )


def help_text() -> str:
    tz = settings.backup_timezone
    hour = settings.backup_schedule_hour
    minute = settings.backup_schedule_minute
    return (
        "🤖 <b>School Domnak Bot</b>\n\n"
        f"{report_menu_text()}\n\n"
        f"Tap <b>{_esc(BTN_BACKUP)}</b> to back up the database to Google Sheets now.\n"
        f"Automatic backup runs daily at {hour:02d}:{minute:02d} ({_esc(tz)})."
    )


def summary_text(db: Session) -> str:
    students = reports.get_students_summary(db, None, None)
    finance_rows = reports.get_finance_report(db, None, None)
    finance_total = sum(row["final_price"] for row in finance_rows)
    registration = reports.get_registration_summary(db, None, None)
    return (
        "📋 <b>System Summary</b> (All Time)\n\n"
        f"Students: {students.total_students}\n"
        f"Enrollments: {students.total_enrollments}\n"
        f"Finance classes: {len(finance_rows)}\n"
        f"Finance final total: ${finance_total:,.2f}\n"
        f"Registrations: {registration.total_registrations}"
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

    from app.utils.task_dispatch import _celery_available, dispatch_google_sheets_backup

    if _celery_available():
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
    state = get_user_state(user_id)
    catalog = state.get("entity_catalog") or []
    entity_label = ENTITY_TYPE_LABELS.get(action, "Items")
    text = (
        f"<b>Step 2 — {_esc(entity_label)}</b>\n\n"
        f"{format_entity_catalog_text(action, catalog)}"
    )
    await send_message(
        chat_id,
        text,
        reply_keyboard=build_entity_page_keyboard(state),
    )


async def show_period_menu(chat_id: int | str, action: str, user_id: int) -> None:
    state = get_user_state(user_id)
    label = ACTION_LABELS.get(action, action)
    item_line = ""
    if action_needs_entity(action):
        picked = "All" if state.get("filter_all_entities") else state.get("filter_entity_label")
        if picked:
            item_line = f"Item: <b>{_esc(picked)}</b>\n\n"
    text = (
        f"📅 <b>{_esc(label)}</b>\n\n"
        f"{item_line}"
        f"<b>Step 3:</b> Choose a period (<b>{_esc(BTN_PERIOD_ALL)}</b> = show all dates).\n"
        f"Tap <b>{_esc(BTN_MAIN_MENU)}</b> to go back."
    )
    await send_message(chat_id, text, reply_keyboard=build_period_reply_keyboard())


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
    if not is_chat_allowed(chat_id):
        if callback_id:
            await answer_callback(callback_id, "Unauthorized")
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

    if not is_chat_allowed(chat_id):
        logger.warning("Rejected Telegram message from unauthorized chat_id=%s", chat_id)
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
    {"command": "start", "description": "Report commands list"},
    {"command": "students", "description": "Students summary"},
    {"command": "finance", "description": "Finance by class"},
    {"command": "category", "description": "By category"},
    {"command": "course", "description": "By course"},
    {"command": "class", "description": "By class"},
    {"command": "teacher", "description": "By teacher"},
    {"command": "summary", "description": "All-time overview"},
    {"command": "backup", "description": "Backup to Google Sheets now"},
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
