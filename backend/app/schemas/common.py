from datetime import date
from typing import Generic, Literal, TypeVar

from fastapi import Query
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")
SortOrder = Literal["asc", "desc"]


def to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,
    )


class TableResponse(BaseModel, Generic[T]):
    data: list[T]
    total: int


class CommonResponse(CamelModel):
    success: bool = True
    message: str = "OK"


class TableQueryParams(CamelModel):
    page: int = 1
    limit: int = 10
    sort_by: str | None = None
    sort_order: SortOrder = "desc"
    search: str | None = None
    date_from: date | None = None
    date_to: date | None = None


def table_query_params(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=500),
    sort_by: str | None = Query(None, alias="sortBy"),
    sort_order: SortOrder = Query("desc", alias="sortOrder"),
    search: str | None = Query(None),
    date_from: date | None = Query(None, alias="dateFrom"),
    date_to: date | None = Query(None, alias="dateTo"),
) -> TableQueryParams:
    return TableQueryParams(
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
