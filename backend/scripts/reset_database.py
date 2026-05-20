"""Delete all application data, then seed roles + admin only.

Usage:
  python scripts/reset_database.py
  docker compose exec backend python scripts/reset_database.py
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
from seed_data import seed

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
    with engine.begin() as conn:
        if dialect == "postgresql":
            tables = ", ".join(_TRUNCATE_TABLES)
            conn.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))
        elif dialect == "sqlite":
            conn.execute(text("PRAGMA foreign_keys = OFF"))
            for table in _TRUNCATE_TABLES:
                conn.execute(text(f"DELETE FROM {table}"))
            conn.execute(text("DELETE FROM sqlite_sequence"))
            conn.execute(text("PRAGMA foreign_keys = ON"))
        else:
            raise RuntimeError(f"Unsupported database dialect: {dialect}")
    print("All application data deleted.")
    seed()


if __name__ == "__main__":
    reset_database()
