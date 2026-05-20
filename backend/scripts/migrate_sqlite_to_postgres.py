#!/usr/bin/env python3
"""
Copy data from SQLite to PostgreSQL table-by-table (preserves FK order).

Usage (from backend/ with venv active):
  export SQLITE_URL=sqlite:///./school.db
  export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:15432/school_db
  python scripts/migrate_sqlite_to_postgres.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import MetaData, create_engine, inspect, text
from sqlalchemy.engine import Engine

# Tables in dependency order (parents before children)
TABLE_ORDER = [
    "roles",
    "users",
    "categories",
    "courses",
    "classes",
    "students",
    "enrollments",
    "invoices",
    "invoice_lines",
    "commissions",
    "finance",
    "audit_logs",
    "refresh_tokens",
]


def ordered_tables(engine: Engine) -> list[str]:
    existing = set(inspect(engine).get_table_names())
    ordered = [name for name in TABLE_ORDER if name in existing]
    for name in sorted(existing):
        if name not in ordered and name != "alembic_version":
            ordered.append(name)
    return ordered


def reset_destination(dst: Engine, tables: list[str]) -> None:
    with dst.begin() as conn:
        for table in reversed(tables):
            conn.execute(text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE'))


def copy_table(src: Engine, dst: Engine, table: str) -> int:
    metadata = MetaData()
    metadata.reflect(bind=src, only=[table])
    if table not in metadata.tables:
        return 0
    tbl = metadata.tables[table]
    columns = [col.name for col in tbl.columns]
    if not columns:
        return 0

    with src.connect() as sconn, dst.begin() as dconn:
        rows = sconn.execute(text(f'SELECT * FROM "{table}"')).mappings().all()
        if not rows:
            return 0
        placeholders = ", ".join(f":{col}" for col in columns)
        col_list = ", ".join(f'"{col}"' for col in columns)
        insert_sql = text(f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders})')
        dconn.execute(insert_sql, [{col: row[col] for col in columns} for row in rows])
        return len(rows)


def main() -> int:
    sqlite_url = os.getenv("SQLITE_URL", "sqlite:///./school.db")
    postgres_url = os.getenv("DATABASE_URL")
    if not postgres_url:
        print("Set DATABASE_URL to your PostgreSQL connection string.", file=sys.stderr)
        return 1

    src = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    dst = create_engine(postgres_url, future=True)

    tables = ordered_tables(src)
    print(f"Tables to migrate: {', '.join(tables)}")

    reset_destination(dst, tables)

    total = 0
    for table in tables:
        count = copy_table(src, dst, table)
        print(f"  {table}: {count} rows")
        total += count

    print(f"Done. {total} rows copied.")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    raise SystemExit(main())
