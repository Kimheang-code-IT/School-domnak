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
from app.services.telegram_state import clear_user_state, get_user_state, reset_flow
from app.utils.date_period import parse_custom_date_range

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
PAGE_SIZE = 20

ACTION_LABELS: dict[str, str] = {
    "students_summary": "Students Summary",
    "income_summary": "Income Summary",
    "by_category": "By Category",
    "by_course": "By Course",
    "by_class": "By Class",
    "by_teacher": "By Teacher",
    "registration_summary": "Registration Summary",
}

ACTION_CALLBACKS = {
    "students_summary",
    "income_summary",
    "by_category",
    "by_course",
    "by_class",
    "by_teacher",
    "registration_summary",
}

# Report reply keyboard (bottom of chat — step 1)
BTN_STUDENTS = "📊 Students"
BTN_INCOME = "💰 Income"
BTN_CATEGORY = "📂 Category"
BTN_COURSE = "📚 Course"
BTN_CLASS = "🏫 Class"
BTN_TEACHER = "👨‍🏫 Teacher"

# Period reply keyboard (bottom of chat — step 2)
BTN_PERIOD_TODAY = "Today"
BTN_PERIOD_YESTERDAY = "Yesterday"
BTN_PERIOD_WEEK = "This Week"
BTN_PERIOD_MONTH = "This Month"
BTN_PERIOD_LAST_MONTH = "Last Month"
BTN_PERIOD_YEAR = "This Year"
BTN_PERIOD_ALL = "All Time"
BTN_PERIOD_CUSTOM = "Custom Range"
BTN_CANCEL_KB = "Cancel"

COMMAND_TO_ACTION: dict[str, str] = {
    "/students": "students_summary",
    "/income": "income_summary",
    "/category": "by_category",
    "/course": "by_course",
    "/class": "by_class",
    "/teacher": "by_teacher",
    "/registration": "registration_summary",
}

REPLY_TEXT_TO_ACTION: dict[str, str] = {
    BTN_STUDENTS.lower(): "students_summary",
    BTN_INCOME.lower(): "income_summary",
    BTN_CATEGORY.lower(): "by_category",
    BTN_COURSE.lower(): "by_course",
    BTN_CLASS.lower(): "by_class",
    BTN_TEACHER.lower(): "by_teacher",
    "students": "students_summary",
    "income": "income_summary",
    "category": "by_category",
    "course": "by_course",
    "class": "by_class",
    "teacher": "by_teacher",
}

REPLY_TEXT_TO_PERIOD: dict[str, str] = {
    BTN_PERIOD_TODAY.lower(): "today",
    BTN_PERIOD_YESTERDAY.lower(): "yesterday",
    BTN_PERIOD_WEEK.lower(): "this_week",
    BTN_PERIOD_MONTH.lower(): "this_month",
    BTN_PERIOD_LAST_MONTH.lower(): "last_month",
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
    """Step 1 — pick which report."""
    return {
        "keyboard": [
            [{"text": BTN_STUDENTS}, {"text": BTN_INCOME}],
            [{"text": BTN_CATEGORY}, {"text": BTN_COURSE}],
            [{"text": BTN_CLASS}, {"text": BTN_TEACHER}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
    }


def build_period_reply_keyboard() -> dict[str, Any]:
    """Step 2 — pick date period (bottom keyboard)."""
    return {
        "keyboard": [
            [{"text": BTN_PERIOD_TODAY}, {"text": BTN_PERIOD_YESTERDAY}],
            [{"text": BTN_PERIOD_WEEK}, {"text": BTN_PERIOD_MONTH}],
            [{"text": BTN_PERIOD_LAST_MONTH}, {"text": BTN_PERIOD_YEAR}],
            [{"text": BTN_PERIOD_ALL}, {"text": BTN_PERIOD_CUSTOM}],
            [{"text": BTN_CANCEL_KB}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
        "is_persistent": True,
    }


def build_report_inline_keyboard() -> dict[str, Any]:
    """Report buttons on the message (always visible in chat)."""
    return {
        "inline_keyboard": [
            [
                {"text": BTN_STUDENTS, "callback_data": "action:students_summary"},
                {"text": BTN_INCOME, "callback_data": "action:income_summary"},
            ],
            [
                {"text": BTN_CATEGORY, "callback_data": "action:by_category"},
                {"text": BTN_COURSE, "callback_data": "action:by_course"},
            ],
            [
                {"text": BTN_CLASS, "callback_data": "action:by_class"},
                {"text": BTN_TEACHER, "callback_data": "action:by_teacher"},
            ],
        ]
    }


def build_period_inline_keyboard() -> dict[str, Any]:
    """Period buttons on the message (always visible in chat)."""
    return {
        "inline_keyboard": [
            [
                {"text": BTN_PERIOD_TODAY, "callback_data": "period:today"},
                {"text": BTN_PERIOD_YESTERDAY, "callback_data": "period:yesterday"},
            ],
            [
                {"text": BTN_PERIOD_WEEK, "callback_data": "period:this_week"},
                {"text": BTN_PERIOD_MONTH, "callback_data": "period:this_month"},
            ],
            [
                {"text": BTN_PERIOD_LAST_MONTH, "callback_data": "period:last_month"},
                {"text": BTN_PERIOD_YEAR, "callback_data": "period:this_year"},
            ],
            [
                {"text": BTN_PERIOD_ALL, "callback_data": "period:all_time"},
                {"text": BTN_PERIOD_CUSTOM, "callback_data": "period:custom_range"},
            ],
            [{"text": BTN_CANCEL_KB, "callback_data": "nav:cancel"}],
        ]
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
    inline_keyboard: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text[:4096],
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if inline_keyboard is not None:
        payload["reply_markup"] = inline_keyboard
    elif reply_keyboard is not None:
        payload["reply_markup"] = reply_keyboard
    await _api("sendMessage", payload)


async def refresh_bottom_keyboard(chat_id: int | str, keyboard: dict[str, Any], hint: str) -> None:
    """Force-update bottom reply keyboard (Telegram Desktop often keeps the previous one)."""
    await send_message(chat_id, hint, reply_keyboard=keyboard)


async def send_backup_success_alert(result: reports.BackupResult) -> None:
    """Notify allowed chats when scheduled backup succeeds (no buttons)."""
    if not result.ok:
        return
    chats = _allowed_chat_ids()
    if not chats:
        return
    text = (
        "✅ <b>Backup completed</b>\n\n"
        f"{_esc(result.message)}"
    )
    if result.spreadsheet_url:
        text += f"\n\n{_esc(result.spreadsheet_url)}"
    if result.finished_at:
        text += f"\n\nTime: {_esc(result.finished_at)}"
    for chat_id in chats:
        try:
            await send_message(chat_id, text)
        except Exception:
            logger.exception("Failed to send backup alert to chat_id=%s", chat_id)


async def answer_callback(callback_query_id: str, text: str | None = None) -> None:
    payload: dict[str, Any] = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text[:200]
    await _api("answerCallbackQuery", payload)


async def send_report_message(chat_id: int | str, text: str) -> None:
    """Report text + period keyboard (tap another period to refresh)."""
    await send_message(chat_id, text, reply_keyboard=build_period_reply_keyboard())


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
    return (
        f"📊 <b>Students Summary</b>\n"
        f"Period: {_esc(period_label)}\n\n"
        f"Total Students: {data.total_students}\n"
        f"Total Enrollments: {data.total_enrollments}\n"
        f"Active Students: {data.total_active_students}\n"
        f"Inactive Students: {data.total_inactive_students}\n"
        f"New Students In Period: {data.students_registered_in_period}"
    )


def _format_income_summary(period_label: str, data: reports.IncomeSummary) -> str:
    return (
        f"💰 <b>Income Summary</b>\n"
        f"Period: {_esc(period_label)}\n\n"
        f"Total Invoices: {data.total_invoice}\n"
        f"Subtotal: ${data.subtotal:,.2f}\n"
        f"Discount: ${data.discount:,.2f}\n"
        f"Total Income: ${data.total_income:,.2f}"
    )


def _format_registration_summary(period_label: str, data: reports.RegistrationSummary) -> str:
    return (
        f"📝 <b>Registration Summary</b>\n"
        f"Period: {_esc(period_label)}\n\n"
        f"Total Registrations: {data.total_registrations}\n"
        f"Active: {data.active_registrations}\n"
        f"Inactive: {data.inactive_registrations}\n"
        f"Registration Amount: ${data.total_registration_amount:,.2f}"
    )


def _format_list_report(
    title: str,
    period_label: str,
    items: list[dict[str, Any]],
    *,
    page: int,
    formatter,
) -> tuple[str, bool]:
    start = (page - 1) * PAGE_SIZE
    chunk = items[start : start + PAGE_SIZE]
    has_next = len(items) > start + PAGE_SIZE
    lines = [f"{title}", f"Period: {_esc(period_label)}", ""]
    if not chunk:
        lines.append("No data for this period.")
    else:
        for index, item in enumerate(chunk, start=start + 1):
            lines.append(formatter(index, item))
            lines.append("")
    return "\n".join(lines).strip(), has_next


def run_report_for_action(
    db: Session,
    user_id: int,
    action: str,
    *,
    page: int = 1,
) -> str:
    start, end, period_label = _resolve_dates_from_state(user_id)

    if action == "students_summary":
        data = reports.get_students_summary(db, start, end)
        return _format_students_summary(period_label, data)

    if action == "income_summary":
        data = reports.get_income_summary(db, start, end)
        return _format_income_summary(period_label, data)

    if action == "registration_summary":
        data = reports.get_registration_summary(db, start, end)
        return _format_registration_summary(period_label, data)

    if action == "by_category":
        items = reports.get_students_by_category(db, start, end)

        def fmt(i: int, row: dict[str, Any]) -> str:
            return (
                f"{i}. {_esc(row['category_name'])}\n"
                f"Students: {row['total_students']}\n"
                f"Income: ${row['total_income']:,.2f}"
            )

        text, _has_next = _format_list_report(
            "📂 <b>Students By Category</b>", period_label, items, page=page, formatter=fmt
        )
        return text

    if action == "by_course":
        items = reports.get_students_by_course(db, start, end)

        def fmt(i: int, row: dict[str, Any]) -> str:
            name = row["course_name"]
            if row.get("course_name_km"):
                name = f"{row['course_name_km']} / {name}"
            return (
                f"{i}. {_esc(name)}\n"
                f"Students: {row['total_students']}\n"
                f"Income: ${row['total_income']:,.2f}"
            )

        text, _has_next = _format_list_report(
            "📚 <b>Students By Course</b>", period_label, items, page=page, formatter=fmt
        )
        return text

    if action == "by_class":
        items = reports.get_students_by_class(db, start, end)

        def fmt(i: int, row: dict[str, Any]) -> str:
            return (
                f"{i}. {_esc(row['class_name'])}\n"
                f"Teacher: {_esc(row['teacher_name'])}\n"
                f"Students: {row['total_students']}\n"
                f"Income: ${row['total_income']:,.2f}"
            )

        text, _has_next = _format_list_report(
            "🏫 <b>Students By Class</b>", period_label, items, page=page, formatter=fmt
        )
        return text

    if action == "by_teacher":
        items = reports.get_students_by_teacher(db, start, end)

        def fmt(i: int, row: dict[str, Any]) -> str:
            return (
                f"{i}. {_esc(row['teacher_name'])}\n"
                f"Students: {row['total_students']}\n"
                f"Income: ${row['total_income']:,.2f}\n"
                f"Commission: ${row['total_commission']:,.2f}"
            )

        text, _has_next = _format_list_report(
            "👨‍🏫 <b>Students By Teacher</b>", period_label, items, page=page, formatter=fmt
        )
        return text

    return "Unknown report action."


def report_menu_text() -> str:
    return (
        "📋 <b>School Domnak Reports</b>\n\n"
        "<b>Step 1:</b> Tap a report button on this message\n"
        "<b>Step 2:</b> Tap a period (Today, This Month, …)\n\n"
        "Or use commands: /students /income /category /course /class /teacher"
    )


def help_text() -> str:
    return (
        "🤖 <b>School Domnak Bot</b>\n\n"
        f"{report_menu_text()}\n\n"
        "Backup runs automatically daily. You will get a message when it succeeds."
    )


def summary_text(db: Session) -> str:
    students = reports.get_students_summary(db, None, None)
    income = reports.get_income_summary(db, None, None)
    registration = reports.get_registration_summary(db, None, None)
    return (
        "📋 <b>System Summary</b> (All Time)\n\n"
        f"Students: {students.total_students}\n"
        f"Enrollments: {students.total_enrollments}\n"
        f"Income: ${income.total_income:,.2f}\n"
        f"Registrations: {registration.total_registrations}"
    )


def _normalize_reply_key(text: str) -> str:
    return (text or "").strip().lower()


def _action_from_reply_text(text: str) -> str | None:
    return REPLY_TEXT_TO_ACTION.get(_normalize_reply_key(text))


def _period_from_reply_text(text: str) -> str | None:
    return REPLY_TEXT_TO_PERIOD.get(_normalize_reply_key(text))


async def show_report_menu(chat_id: int | str) -> None:
    await send_message(
        chat_id,
        report_menu_text(),
        inline_keyboard=build_report_inline_keyboard(),
    )
    await refresh_bottom_keyboard(
        chat_id,
        build_report_reply_keyboard(),
        "Or use the report keys below:",
    )


async def show_period_menu(chat_id: int | str, action: str) -> None:
    label = ACTION_LABELS.get(action, action)
    text = f"📅 <b>{_esc(label)}</b>\n\nTap a period below:"
    await send_message(chat_id, text, inline_keyboard=build_period_inline_keyboard())
    await refresh_bottom_keyboard(
        chat_id,
        build_period_reply_keyboard(),
        "Or use the period keys below:",
    )


async def apply_period_selection(chat_id: int, user_id: int, period: str) -> None:
    state = get_user_state(user_id)
    action = state.get("selected_action")
    if not action:
        await show_report_menu(chat_id)
        return
    if period == "custom_range":
        state["waiting_custom_range"] = True
        state["period"] = period
        await send_message(
            chat_id,
            "📆 Please enter date range like:\n<code>2026-05-01 to 2026-05-18</code>",
            inline_keyboard=build_period_inline_keyboard(),
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
    await show_period_menu(chat_id, action)


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
            await show_report_menu(chat_id)
            return
        await execute_report(chat_id, user_id, action)
        return

    key = _normalize_reply_key(normalized)

    if key in (BTN_CANCEL_KB.lower(), "cancel", "/cancel"):
        clear_user_state(user_id)
        await show_report_menu(chat_id)
        return

    period_key = _period_from_reply_text(normalized)
    if period_key and state.get("selected_action"):
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

    if command in ("/cancel",):
        clear_user_state(user_id)
        await show_report_menu(chat_id)
        return

    if command in ("/start", "/help", "/report"):
        if command == "/help":
            await send_message(chat_id, help_text(), reply_keyboard=build_report_reply_keyboard())
            return
        reset_flow(user_id)
        await show_report_menu(chat_id)
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
        clear_user_state(user_id)
        await send_message(chat_id, "Cancelled.")
        await show_report_menu(chat_id)
        return

    if data.startswith("action:"):
        action = data.split(":", 1)[1]
        if action not in ACTION_CALLBACKS:
            return
        state["selected_action"] = action
        state["page"] = 1
        state["waiting_custom_range"] = False
        await show_period_menu(chat_id, action)
        return

    if data.startswith("period:"):
        period = data.split(":", 1)[1]
        if not state.get("selected_action"):
            await show_report_menu(chat_id)
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


async def delete_webhook() -> None:
    await _api("deleteWebhook", {"drop_pending_updates": False})


BOT_COMMANDS = [
    {"command": "start", "description": "Report commands list"},
    {"command": "students", "description": "Students summary"},
    {"command": "income", "description": "Income summary"},
    {"command": "category", "description": "By category"},
    {"command": "course", "description": "By course"},
    {"command": "class", "description": "By class"},
    {"command": "teacher", "description": "By teacher"},
    {"command": "summary", "description": "All-time overview"},
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
            await delete_webhook()
        except Exception:
            logger.debug("deleteWebhook on setup failed", exc_info=True)
