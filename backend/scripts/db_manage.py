"""Database helper: seed data, reset tables, run schema migrations.

Run from the `backend` directory:

  python scripts/db_manage.py seed
  python scripts/db_manage.py reset
  python scripts/db_manage.py migrate

Docker (service workdir is /app):

  docker compose exec backend python scripts/db_manage.py seed
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parents[1]
_scripts = Path(__file__).resolve().parent

sys.path.insert(0, str(_backend))
sys.path.insert(0, str(_scripts))


def cmd_seed() -> None:
    """Insert or update admin user + Admin role (no other business rows)."""
    from seed_data import seed

    seed()


def cmd_reset() -> None:
    """Delete all rows in app tables (FK order), then run seed."""
    from reset_database import reset_database

    reset_database()


def cmd_migrate() -> None:
    """Apply Alembic migrations (updates schema only, not row data)."""
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=_backend,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    print("Migrations applied: alembic upgrade head")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage database: seed admin, wipe app data, or run migrations."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("seed", help="Create/update Admin role and admin user (idempotent)")
    sub.add_parser(
        "reset",
        help="TRUNCATE/delete all app tables then seed admin (DESTRUCTIVE)",
    )
    sub.add_parser(
        "migrate",
        help="Run Alembic migrations (schema changes)",
    )

    args = parser.parse_args()
    if args.command == "seed":
        cmd_seed()
    elif args.command == "reset":
        cmd_reset()
    elif args.command == "migrate":
        cmd_migrate()
    else:
        parser.error(f"unknown command: {args.command}")


if __name__ == "__main__":
    main()
