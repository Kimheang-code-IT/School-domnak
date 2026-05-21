from datetime import datetime

from pydantic import Field, model_validator

from app.core.permissions import sanitize_role_permissions
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

    @model_validator(mode="after")
    def _sanitize_permissions(self) -> "RoleRead":
        self.permissions = sanitize_role_permissions(self.permissions)
        return self
