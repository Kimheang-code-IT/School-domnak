from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.class_model import SchoolClass
from app.repositories.base import BaseRepository
from app.schemas.category import CategoryRead
from app.schemas.common import TableQueryParams


class CategoryRepository(BaseRepository[Category]):
    def __init__(self) -> None:
        super().__init__(Category)

    def list_categories(self, db: Session, query: TableQueryParams) -> tuple[list[CategoryRead], int]:
        total_classes = func.count(SchoolClass.id).label("total")
        statement = (
            select(Category, total_classes)
            .outerjoin(SchoolClass, SchoolClass.category_id == Category.id)
            .group_by(Category.id)
        )
        rows, total = self.list_simple(
            db,
            query,
            base_statement=statement,
            sort_map={
                "id": Category.id,
                "name": Category.name,
                "description": Category.description,
                "total": total_classes,
                "createdAt": Category.created_at,
            },
            search_columns=[Category.name, Category.description],
            date_column=Category.created_at,
        )
        data = [
            CategoryRead(
                id=category.id,
                name=category.name,
                description=category.description,
                total=total_count,
                created_at=category.created_at,
            )
            for category, total_count in rows
        ]
        return data, total
