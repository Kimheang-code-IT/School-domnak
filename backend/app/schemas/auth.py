from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas.common import CamelModel

Permissions = dict[str, list[str]]


class LoginRequest(CamelModel):
    email: str
    password: str


class SetupRequest(CamelModel):
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class SetupStatusRead(CamelModel):
    needs_setup: bool


class RefreshTokenRequest(CamelModel):
    refresh_token: str


class LogoutRequest(CamelModel):
    refresh_token: str


class ChangePasswordRequest(CamelModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class AuthUserRead(CamelModel):
    id: int
    name: str
    email: EmailStr
    role: str | None = None
    telegram_key: str | None = None
    last_login: datetime | None = None
    permissions: Permissions = Field(default_factory=dict)


class TokenResponse(CamelModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: AuthUserRead


class AccessTokenResponse(CamelModel):
    access_token: str
    token_type: str = "bearer"
