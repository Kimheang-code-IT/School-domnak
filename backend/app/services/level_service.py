"""Helpers for Level ↔ SchoolClass relationships."""

from __future__ import annotations

from sqlalchemy.orm import Session


def apply_level_to_class_data(db: Session, data: dict) -> dict:
    """Kept for compatibility; classes store level_id only (no denormalized labels)."""
    data.pop("level", None)
    data.pop("level_km", None)
    data.pop("teacher_name", None)
    return data
