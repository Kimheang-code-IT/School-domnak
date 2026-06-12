from datetime import date, datetime, time

from sqlalchemy import Select, or_
from sqlalchemy.sql.elements import ColumnElement


def apply_search(statement: Select, search: str | None, columns: list[ColumnElement]) -> Select:
    if not search or not columns:
        return statement
    pattern = f"%{search.strip()}%"
    return statement.where(or_(*(column.ilike(pattern) for column in columns)))


def apply_date_filter(
    statement: Select,
    column: ColumnElement,
    date_from: date | None,
    date_to: date | None,
) -> Select:
    if date_from:
        statement = statement.where(column >= datetime.combine(date_from, time.min))
    if date_to:
        statement = statement.where(column <= datetime.combine(date_to, time.max))
    return statement


def split_filter(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def split_int_filter(value: str | None) -> list[int]:
    ids: list[int] = []
    for part in split_filter(value):
        if part.isdigit():
            parsed = int(part)
            if parsed > 0:
                ids.append(parsed)
    return ids
