"""Helpers for Level ↔ SchoolClass denormalized labels."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.level import Level


def apply_level_to_class_data(db: Session, data: dict) -> dict:
    """Copy level_id into denormalized level / level_km strings for legacy readers."""
    level_id = data.get("level_id")
    if level_id is None:
        return data
    level = db.get(Level, int(level_id))
    if not level:
        return data
    data["level"] = level.level_name_en
    data["level_km"] = level.level_name_km
    return data
