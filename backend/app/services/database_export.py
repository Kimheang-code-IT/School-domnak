"""Export every table and column from the configured SQL database."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

# Google Sheets limit per cell
MAX_CELL_CHARS = 49_000

# Never export credential hashes to spreadsheets or logs
SENSITIVE_EXPORT_COLUMNS = frozenset({"password_hash", "hashed_password"})


def _serialize_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).hex()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    if isinstance(value, Decimal):
        text = str(value)
    else:
        text = str(value)
    if len(text) > MAX_CELL_CHARS:
        return f"{text[:MAX_CELL_CHARS]}… [truncated, {len(text):,} chars total]"
    return text


def export_all_tables(engine: Engine) -> dict[str, dict[str, list[list[str]]]]:
    """
    Returns {table_name: {"columns": [...], "rows": [[...], ...]}} for every DB table.
    """
    inspector = inspect(engine)
    result: dict[str, dict[str, list[list[str]]]] = {}

    with engine.connect() as connection:
        for table_name in sorted(inspector.get_table_names()):
            columns = [
                column["name"]
                for column in inspector.get_columns(table_name)
                if column["name"] not in SENSITIVE_EXPORT_COLUMNS
            ]
            if not columns:
                continue
            quoted = ", ".join(f'"{column}"' for column in columns)
            query = text(f'SELECT {quoted} FROM "{table_name}"')
            raw_rows = connection.execute(query).fetchall()
            rows = [[_serialize_cell(row[i]) for i in range(len(columns))] for row in raw_rows]
            result[table_name] = {"columns": columns, "rows": rows}

    return result
