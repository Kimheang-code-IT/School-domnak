from datetime import datetime

from app.schemas.common import CamelModel


class CategoryBase(CamelModel):
    name: str
    name_km: str | None = None
    description: str | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(CamelModel):
    name: str | None = None
    name_km: str | None = None
    description: str | None = None


class CategoryRead(CategoryBase):
    id: int
    total: int = 0
    created_at: datetime | None = None
