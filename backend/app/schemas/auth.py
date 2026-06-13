from pydantic import EmailStr, Field, model_validator

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


class SetupStatusResponse(CamelModel):
    needs_setup: bool


class RegisterAdminRequest(CamelModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    confirm_password: str = Field(min_length=6, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterAdminRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self
