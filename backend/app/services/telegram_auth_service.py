"""Telegram bot access via per-user telegram_key registration."""

from __future__ import annotations

import re
import secrets

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.user import User

_KEY_COMMAND_RE = re.compile(
    r"^(?:/register(?:@\w+)?|/login(?:@\w+)?)\s+(.+)$",
    re.IGNORECASE,
)


def generate_telegram_key() -> str:
    """Human-readable key shown in User Management (e.g. LC-A1B2C3D4)."""
    return f"LC-{secrets.token_hex(4).upper()}"


def normalize_telegram_key(raw: str | None) -> str:
    return (raw or "").strip()


def extract_telegram_key_from_text(text: str) -> str | None:
    """Accept `/register KEY`, `/login KEY`, or a bare KEY."""
    raw = (text or "").strip()
    if not raw:
        return None
    match = _KEY_COMMAND_RE.match(raw)
    if match:
        return normalize_telegram_key(match.group(1))
    # Bare key: avoid treating menu buttons / dates as keys
    if raw.startswith("/"):
        return None
    if "\n" in raw:
        return None
    if len(raw) > 64 or len(raw) < 4:
        return None
    # Likely a period/menu button label
    lowered = raw.lower()
    if lowered in {
        "today",
        "yesterday",
        "this month",
        "this year",
        "all time",
        "custom range",
        "cancel",
        "back",
        "main menu",
    }:
        return None
    if raw.startswith(("📊", "💰", "🏫", "☁️", "◀️", "▶️", "📋")):
        return None
    return normalize_telegram_key(raw)


def find_user_by_telegram_chat(db: Session, chat_id: int | str) -> User | None:
    return db.scalar(select(User).where(User.telegram_chat_id == str(chat_id)))


def find_user_by_telegram_key(db: Session, key: str) -> User | None:
    cleaned = normalize_telegram_key(key)
    if not cleaned:
        return None
    return db.scalar(select(User).where(User.telegram_key == cleaned))


def is_telegram_chat_registered(db: Session, chat_id: int | str) -> bool:
    return find_user_by_telegram_chat(db, chat_id) is not None


def register_telegram_chat(db: Session, *, chat_id: int | str, key: str) -> User | None:
    """
    Bind this Telegram chat to the user owning `key`.
    Moves the chat off any previous user; keeps one chat per key.
    """
    user = find_user_by_telegram_key(db, key)
    if user is None:
        return None
    chat = str(chat_id)
    # Free this chat from any other account first.
    db.execute(
        update(User)
        .where(User.telegram_chat_id == chat, User.id != user.id)
        .values(telegram_chat_id=None)
    )
    user.telegram_chat_id = chat
    db.commit()
    db.refresh(user)
    return user


def unlink_telegram_chat(db: Session, chat_id: int | str) -> bool:
    user = find_user_by_telegram_chat(db, chat_id)
    if user is None:
        return False
    user.telegram_chat_id = None
    db.commit()
    return True
