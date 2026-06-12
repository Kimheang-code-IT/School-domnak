from pydantic import EmailStr, Field

from app.schemas.common import CamelModel

Permissions = dict[str, list[str]]


class LoginRequest(CamelModel):
    email: str
    password: str


class RefreshTokenRequest(CamelModel):
    refresh_token: str


class LogoutRequest(CamelModel):
    refresh_token: str


class AuthUserRead(CamelModel):
    id: int
    name: str
    email: EmailStr
    role: str | None = None
    permissions: Permissions = Field(default_factory=dict)


class TokenResponse(CamelModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: AuthUserRead


class AccessTokenResponse(CamelModel):
    access_token: str
    token_type: str = "bearer"
