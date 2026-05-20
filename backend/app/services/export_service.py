from collections.abc import Iterable


def rows_for_export(rows: Iterable) -> list[dict]:
    return [row.model_dump(by_alias=True) if hasattr(row, "model_dump") else dict(row) for row in rows]
