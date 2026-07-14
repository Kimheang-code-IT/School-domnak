"""Delete all application data (no auto admin). Use /setup to create the first user.

Usage:
  python scripts/reset_database.py
  docker compose exec backend python scripts/db_manage.py reset
"""

from __future__ import annotations

import sys
from pathlib import Path

_backend = Path(__file__).resolve().parents[1]
_scripts = Path(__file__).resolve().parent
sys.path.insert(0, str(_backend))
sys.path.insert(0, str(_scripts))

from sqlalchemy import text

from app.core.database import engine

# FK-safe order (children first). Alembic version table is preserved.
_TRUNCATE_TABLES = (
    "refresh_tokens",
    "invoice_lines",
    "invoices",
    "enrollments",
    "commissions",
    "finance",
    "audit_logs",
    "students",
    "classes",
    "levels",
    "courses",
    "categories",
    "users",
    "roles",
)


def reset_database() -> None:
    dialect = engine.dialect.name
    if dialect != "postgresql":
        raise RuntimeError(
            f"Unsupported database dialect: {dialect}. This project requires PostgreSQL only."
        )
    with engine.begin() as conn:
        tables = ", ".join(_TRUNCATE_TABLES)
        conn.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))
    print("All application data deleted.")
    print("Open http://localhost/setup to create your admin account.")


if __name__ == "__main__":
    reset_database()
