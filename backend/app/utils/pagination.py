from sqlalchemy import Select


def get_offset(page: int, limit: int) -> int:
    return max(page - 1, 0) * limit


def apply_pagination(statement: Select, page: int, limit: int) -> Select:
    return statement.offset(get_offset(page, limit)).limit(limit)
