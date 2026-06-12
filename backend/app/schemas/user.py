from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas.common import CamelModel

Permissions = dict[str, list[str]]


class UserBase(CamelModel):
    name: str
    email: EmailStr
    role_id: int | None = None


class UserCreate(UserBase):
    password: str


class UserUpdate(CamelModel):
    name: str | None = None
    email: EmailStr | None = None
    role_id: int | None = None
    password: str | None = None


class UserRead(CamelModel):
    id: int
    name: str
    role: str | None = None
    role_id: int | None = None
    email: EmailStr
    password: str = "********"
    permissions: Permissions = Field(default_factory=dict)
    last_login: datetime | None = None
    created_at: datetime | None = None
