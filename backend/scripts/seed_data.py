"""Ensure Admin role exists (no hardcoded user — first account is created via /setup)."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import Base, SessionLocal, engine
from app.core.permissions import ADMIN_PERMISSIONS, sanitize_role_permissions
from sqlalchemy import select
from app.models.role import Role


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin_role = db.query(Role).filter(Role.name == "Admin").one_or_none()
        if admin_role is None:
            admin_role = Role(name="Admin", permissions=ADMIN_PERMISSIONS)
            db.add(admin_role)
            db.flush()
        else:
            admin_role.permissions = ADMIN_PERMISSIONS

        for role in db.scalars(select(Role)).all():
            role.permissions = sanitize_role_permissions(role.permissions)

        db.commit()
        print("Admin role ready (no default user). Use /setup to create the first account.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
