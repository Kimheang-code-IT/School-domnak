from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.class_model import SchoolClass
from app.models.level import Level
from app.repositories.base import BaseRepository
from app.schemas.common import TableQueryParams
from app.schemas.level import LevelRead


class LevelRepository(BaseRepository[Level]):
    def __init__(self) -> None:
        super().__init__(Level)

    def list_levels(self, db: Session, query: TableQueryParams) -> tuple[list[LevelRead], int]:
        total_class = func.count(SchoolClass.id).label("total_class")
        statement = (
            select(Level, total_class)
            .outerjoin(SchoolClass, SchoolClass.level_id == Level.id)
            .group_by(Level.id)
        )
        rows, total = self.list_simple(
            db,
            query,
            base_statement=statement,
            sort_map={
                "id": Level.id,
                "levelNameKm": Level.level_name_km,
                "levelNameEn": Level.level_name_en,
                "totalClass": total_class,
                "createdAt": Level.created_at,
            },
            search_columns=[Level.level_name_km, Level.level_name_en, Level.description],
            date_column=Level.created_at,
        )
        data = [
            LevelRead(
                id=level.id,
                level_name_km=level.level_name_km,
                level_name_en=level.level_name_en,
                description=level.description,
                total_class=class_count,
                created_at=level.created_at,
            )
            for level, class_count in rows
        ]
        return data, total
