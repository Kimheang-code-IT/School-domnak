from datetime import datetime

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import CamelModel

Permissions = dict[str, list[str]]


def _clean_telegram_key(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


class UserBase(CamelModel):
    name: str
    email: EmailStr
    role_id: int | None = None


class UserCreate(UserBase):
    password: str
    # Frontend sends role name from the select; resolved to role_id in auth_service.
    role: str | None = None
    telegram_key: str | None = None

    @field_validator("telegram_key", mode="before")
    @classmethod
    def validate_telegram_key(cls, value: object) -> str | None:
        return _clean_telegram_key(None if value is None else str(value))


class UserUpdate(CamelModel):
    name: str | None = None
    email: EmailStr | None = None
    role_id: int | None = None
    role: str | None = None
    password: str | None = None
    telegram_key: str | None = None

    @field_validator("telegram_key", mode="before")
    @classmethod
    def validate_telegram_key(cls, value: object) -> str | None:
        return _clean_telegram_key(None if value is None else str(value))


class UserRead(CamelModel):
    id: int
    name: str
    role: str | None = None
    role_id: int | None = None
    email: EmailStr
    password: str = "********"
    telegram_key: str | None = None
    telegram_chat_id: str | None = None
    permissions: Permissions = Field(default_factory=dict)
    last_login: datetime | None = None
    created_at: datetime | None = None
