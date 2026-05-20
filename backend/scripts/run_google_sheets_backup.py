"""Run a one-off full database backup to Google Sheets (for testing or Windows Task Scheduler)."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import app.models  # noqa: F401
from app.services.google_sheets_backup_service import run_google_sheets_backup


def main() -> int:
    result = run_google_sheets_backup()
    print(result.message)
    if result.spreadsheet_url:
        print(result.spreadsheet_url)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
