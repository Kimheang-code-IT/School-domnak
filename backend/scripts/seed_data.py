"""Seed Admin role + single admin user (no sample business data)."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import Base, SessionLocal, engine
from app.core.permissions import ADMIN_PERMISSIONS
from app.core.security import get_password_hash
from app.models.role import Role
from app.models.user import User

ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "admin12!@$"
ADMIN_NAME = "admin"


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

        admin = db.query(User).filter(User.email == ADMIN_EMAIL).one_or_none()
        if admin is None:
            admin = User(
                name=ADMIN_NAME,
                email=ADMIN_EMAIL,
                password_hash=get_password_hash(ADMIN_PASSWORD),
                role_id=admin_role.id,
            )
            db.add(admin)
        else:
            admin.name = ADMIN_NAME
            admin.role_id = admin_role.id
            admin.password_hash = get_password_hash(ADMIN_PASSWORD)

        db.commit()
        print(f"Admin ready: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
