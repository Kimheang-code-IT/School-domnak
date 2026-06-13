"""Remove legacy seed/demo user accounts from the database.

These accounts were created by older seed scripts and block first-time /register-admin.

Usage:
  cd backend
  python scripts/remove_static_seed_users.py
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.models.refresh_token import RefreshToken
from app.models.user import User

LEGACY_SEED_EMAILS = (
    "admin@example.com",
    "staff@example.com",
    "teacher@example.com",
    "admin@gmail.com",
)


def remove_static_seed_users() -> None:
    db = SessionLocal()
    try:
        users = db.scalars(select(User).where(User.email.in_(LEGACY_SEED_EMAILS))).all()
        if not users:
            print("No legacy seed users found.")
            return

        user_ids = [user.id for user in users]
        for user in users:
            print(f"Removing user: {user.email} ({user.name})")

        db.execute(delete(RefreshToken).where(RefreshToken.user_id.in_(user_ids)))
        db.execute(delete(User).where(User.id.in_(user_ids)))
        db.commit()
        print(f"Removed {len(users)} legacy user(s). Use /register-admin to create the first admin.")
    finally:
        db.close()


if __name__ == "__main__":
    remove_static_seed_users()
