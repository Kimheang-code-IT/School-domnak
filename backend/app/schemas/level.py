from datetime import datetime

from app.schemas.common import CamelModel


class LevelBase(CamelModel):
    level_name_km: str
    level_name_en: str
    description: str | None = None


class LevelCreate(LevelBase):
    pass


class LevelUpdate(CamelModel):
    level_name_km: str | None = None
    level_name_en: str | None = None
    description: str | None = None


class LevelRead(LevelBase):
    id: int
    total_class: int = 0
    created_at: datetime | None = None
