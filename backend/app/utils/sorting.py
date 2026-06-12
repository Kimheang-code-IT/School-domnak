from sqlalchemy import Select
from sqlalchemy.sql.elements import ColumnElement

SortMap = dict[str, ColumnElement]


def apply_sorting(
    statement: Select,
    *,
    sort_by: str | None,
    sort_order: str,
    sort_map: SortMap,
    default_sort: str = "createdAt",
) -> Select:
    sort_key = sort_by if sort_by in sort_map else default_sort
    column = sort_map.get(sort_key)
    if column is None:
        column = next(iter(sort_map.values()))
    direction = sort_order.lower() if sort_order else "desc"
    return statement.order_by(column.asc() if direction == "asc" else column.desc())
