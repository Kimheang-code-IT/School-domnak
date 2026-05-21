"""Verify Google Sheets backup covers every DB table and column (except password hashes)."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import app.models  # noqa: F401
from sqlalchemy import inspect

from app.core.database import engine
from app.services.database_export import SENSITIVE_EXPORT_COLUMNS, export_all_tables

# Application tables (SQLAlchemy models). DB may also include alembic_version.
EXPECTED_APP_TABLES = frozenset(
    {
        "audit_logs",
        "categories",
        "classes",
        "commissions",
        "courses",
        "enrollments",
        "finance",
        "invoice_lines",
        "invoices",
        "levels",
        "refresh_tokens",
        "roles",
        "students",
        "users",
    }
)


def main() -> int:
    inspector = inspect(engine)
    db_tables = sorted(inspector.get_table_names())
    exported = export_all_tables(engine)

    errors: list[str] = []
    lines: list[str] = []

    for table_name in db_tables:
        db_cols = [c["name"] for c in inspector.get_columns(table_name)]
        expected_cols = [c for c in db_cols if c not in SENSITIVE_EXPORT_COLUMNS]
        skipped = [c for c in db_cols if c in SENSITIVE_EXPORT_COLUMNS]

        if table_name not in exported:
            errors.append(f"Table {table_name!r} missing from export")
            continue

        if exported[table_name]["columns"] != expected_cols:
            errors.append(
                f"Table {table_name!r} column mismatch: "
                f"export={exported[table_name]['columns']!r} expected={expected_cols!r}"
            )

        row_count = len(exported[table_name]["rows"])
        skip_note = f" (skipped: {', '.join(skipped)})" if skipped else ""
        lines.append(f"  {table_name}: {len(expected_cols)} columns, {row_count} rows{skip_note}")

    missing_app = EXPECTED_APP_TABLES - set(db_tables)
    if missing_app:
        errors.append(f"Expected app tables not in database: {sorted(missing_app)}")

    extra = set(exported) - set(db_tables)
    if extra:
        errors.append(f"Export contains unknown tables: {sorted(extra)}")

    print("Google Sheets backup export verification")
    print(f"Database tables: {len(db_tables)}")
    print("Tables:")
    print("\n".join(lines))
    print(f"Total data rows: {sum(len(v['rows']) for v in exported.values())}")
    print(f"Sensitive columns never exported: {sorted(SENSITIVE_EXPORT_COLUMNS)}")

    if errors:
        print("\nFAILED:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("\nOK: every table and every exportable column is included.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
