from datetime import datetime

from pydantic import Field

from app.schemas.common import CamelModel

Permissions = dict[str, list[str]]


class RoleBase(CamelModel):
    name: str
    permissions: Permissions = Field(default_factory=dict)


class RoleCreate(RoleBase):
    pass


class RoleUpdate(CamelModel):
    name: str | None = None
    permissions: Permissions | None = None


class RoleRead(RoleBase):
    id: int
    created_at: datetime | None = None
