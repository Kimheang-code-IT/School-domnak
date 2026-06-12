"""Sync full database snapshots to a Google Spreadsheet (one tab per table)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.engine import Engine

from app.core.config import settings
from app.services.database_export import export_all_tables

logger = logging.getLogger(__name__)

SCOPES = ("https://www.googleapis.com/auth/spreadsheets",)
META_SHEET_TITLE = "_backup_meta"
SHEET_TITLE_MAX_LEN = 100
WRITE_CHUNK_ROWS = 4000
INVALID_SHEET_CHARS = set(r"[]:*?/\\")


@dataclass
class BackupResult:
    ok: bool
    message: str
    tables_synced: int = 0
    total_rows: int = 0
    spreadsheet_url: str | None = None
    finished_at: str | None = None


def _sheet_title_safe(table_name: str) -> str:
    safe = "".join("_" if char in INVALID_SHEET_CHARS else char for char in table_name.strip())
    safe = safe[:SHEET_TITLE_MAX_LEN] or "table"
    return safe


def _credentials_path() -> Path:
    path = settings.google_sheets_credentials_file
    if path.is_absolute():
        return path
    backend_root = Path(__file__).resolve().parents[2]
    return backend_root / path


def _build_sheets_service():
    credentials_file = _credentials_path()
    if not credentials_file.is_file():
        raise FileNotFoundError(
            f"Google service account JSON not found at {credentials_file}. "
            "See backend/README.md — Google Sheets backup setup."
        )
    credentials = Credentials.from_service_account_file(str(credentials_file), scopes=SCOPES)
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def _normalize_spreadsheet_id(raw: str) -> str:
    """Accept bare ID or full Google Sheets URL."""
    value = raw.strip()
    if "/spreadsheets/d/" in value:
        return value.split("/spreadsheets/d/", 1)[1].split("/", 1)[0].split("?", 1)[0]
    return value.split("/", 1)[0].split("?", 1)[0]


def _spreadsheet_url(spreadsheet_id: str) -> str:
    return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"


def _get_sheet_map(service, spreadsheet_id: str) -> dict[str, int]:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    return {
        sheet["properties"]["title"]: sheet["properties"]["sheetId"]
        for sheet in meta.get("sheets", [])
    }


def _ensure_sheet(service, spreadsheet_id: str, title: str, sheet_map: dict[str, int]) -> int:
    if title in sheet_map:
        return sheet_map[title]

    response = (
        service.spreadsheets()
        .batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
        )
        .execute()
    )
    sheet_id = response["replies"][0]["addSheet"]["properties"]["sheetId"]
    sheet_map[title] = sheet_id
    return sheet_id


def _clear_sheet(service, spreadsheet_id: str, sheet_title: str) -> None:
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_title}'",
        body={},
    ).execute()


def _write_sheet_values(service, spreadsheet_id: str, sheet_title: str, values: list[list[str]]) -> None:
    if not values:
        _clear_sheet(service, spreadsheet_id, sheet_title)
        return

    for start in range(0, len(values), WRITE_CHUNK_ROWS):
        chunk = values[start : start + WRITE_CHUNK_ROWS]
        row_number = start + 1
        range_name = f"'{sheet_title}'!A{row_number}"
        (
            service.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body={"values": chunk},
            )
            .execute()
        )


def _write_meta_sheet(
    service,
    spreadsheet_id: str,
    sheet_map: dict[str, int],
    *,
    status: str,
    message: str,
    tables_synced: int,
    total_rows: int,
) -> None:
    tz = ZoneInfo(settings.backup_timezone)
    finished_at = datetime.now(tz).isoformat()
    _ensure_sheet(service, spreadsheet_id, META_SHEET_TITLE, sheet_map)
    meta_values = [
        ["key", "value"],
        ["status", status],
        ["message", message],
        ["finished_at", finished_at],
        ["timezone", settings.backup_timezone],
        ["tables_synced", str(tables_synced)],
        ["total_rows", str(total_rows)],
        ["spreadsheet_id", spreadsheet_id],
    ]
    _write_sheet_values(service, spreadsheet_id, META_SHEET_TITLE, meta_values)


def run_google_sheets_backup(engine: Engine | None = None) -> BackupResult:
    if not settings.google_sheets_backup_enabled:
        return BackupResult(ok=False, message="Google Sheets backup is disabled (GOOGLE_SHEETS_BACKUP_ENABLED=false).")

    spreadsheet_id = _normalize_spreadsheet_id(settings.google_sheets_spreadsheet_id)
    if not spreadsheet_id:
        return BackupResult(
            ok=False,
            message="GOOGLE_SHEETS_SPREADSHEET_ID is not set.",
        )

    from app.core.database import engine as default_engine

    db_engine = engine or default_engine
    tz = ZoneInfo(settings.backup_timezone)
    finished_at = datetime.now(tz).isoformat()

    try:
        service = _build_sheets_service()
        tables = export_all_tables(db_engine)
        sheet_map = _get_sheet_map(service, spreadsheet_id)

        tables_synced = 0
        total_rows = 0

        for table_name, payload in tables.items():
            sheet_title = _sheet_title_safe(table_name)
            _ensure_sheet(service, spreadsheet_id, sheet_title, sheet_map)
            columns = payload["columns"]
            rows = payload["rows"]
            values = [columns, *rows]
            _write_sheet_values(service, spreadsheet_id, sheet_title, values)
            tables_synced += 1
            total_rows += len(rows)
            logger.info("Backed up table %s (%s rows) to sheet %s", table_name, len(rows), sheet_title)

        message = f"Synced {tables_synced} tables ({total_rows} data rows)."
        _write_meta_sheet(
            service,
            spreadsheet_id,
            sheet_map,
            status="ok",
            message=message,
            tables_synced=tables_synced,
            total_rows=total_rows,
        )
        url = _spreadsheet_url(spreadsheet_id)
        logger.info("Google Sheets backup completed: %s", message)
        return BackupResult(
            ok=True,
            message=message,
            tables_synced=tables_synced,
            total_rows=total_rows,
            spreadsheet_url=url,
            finished_at=finished_at,
        )
    except FileNotFoundError as exc:
        logger.exception("Google Sheets backup credentials missing")
        return BackupResult(ok=False, message=str(exc), finished_at=finished_at)
    except HttpError as exc:
        logger.exception("Google Sheets API error")
        detail = exc.reason or str(exc)
        try:
            service = _build_sheets_service()
            sheet_map = _get_sheet_map(service, settings.google_sheets_spreadsheet_id)
            _write_meta_sheet(
                service,
                settings.google_sheets_spreadsheet_id,
                sheet_map,
                status="error",
                message=detail,
                tables_synced=0,
                total_rows=0,
            )
        except Exception:
            logger.exception("Could not write backup error to meta sheet")
        return BackupResult(ok=False, message=f"Google Sheets API error: {detail}", finished_at=finished_at)
    except Exception as exc:
        logger.exception("Google Sheets backup failed")
        return BackupResult(ok=False, message=str(exc), finished_at=finished_at)
