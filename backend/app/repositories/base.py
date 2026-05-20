from typing import Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.schemas.common import TableQueryParams
from app.utils.filters import apply_date_filter, apply_search
from app.utils.pagination import apply_pagination
from app.utils.sorting import SortMap, apply_sorting

ModelT = TypeVar("ModelT")


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, model: type[ModelT]) -> None:
        self.model = model

    def get(self, db: Session, item_id: int) -> ModelT | None:
        return db.get(self.model, item_id)

    def create(self, db: Session, data: dict) -> ModelT:
        item = self.model(**data)
        db.add(item)
        db.flush()
        db.refresh(item)
        return item

    def update(self, db: Session, item: ModelT, data: dict) -> ModelT:
        for key, value in data.items():
            setattr(item, key, value)
        db.flush()
        db.refresh(item)
        return item

    def delete(self, db: Session, item: ModelT) -> None:
        db.delete(item)
        db.flush()

    def list_simple(
        self,
        db: Session,
        query: TableQueryParams,
        *,
        base_statement: Select,
        sort_map: SortMap,
        search_columns: list,
        date_column,
        default_sort: str = "createdAt",
    ):
        statement = apply_search(base_statement, query.search, search_columns)
        statement = apply_date_filter(statement, date_column, query.date_from, query.date_to)
        total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
        statement = apply_sorting(
            statement,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
            sort_map=sort_map,
            default_sort=default_sort,
        )
        rows = db.execute(apply_pagination(statement, query.page, query.limit)).all()
        return rows, total
