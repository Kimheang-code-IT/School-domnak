from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    AuthUserRead,
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    SetupRequest,
    SetupStatusRead,
    TokenResponse,
)
from app.schemas.common import CommonResponse
from app.services.audit_service import write_audit_log
from app.core.config import settings
from app.services.auth_service import (
    authenticate_user,
    build_auth_user,
    build_login_token,
    change_user_password,
    create_initial_admin,
    create_refresh_token,
    needs_initial_setup,
    refresh_access_token,
    revoke_refresh_token,
)
from app.middleware.rate_limit import enforce_login_rate_limit
from app.services.table_list_cache import cached_value
from app.core.redis_cache import invalidate_auth_me

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]


@router.get("/setup-status", response_model=SetupStatusRead)
def setup_status(db: DbSession):
    return SetupStatusRead(needs_setup=needs_initial_setup(db))


@router.post("/setup", response_model=TokenResponse)
def setup(payload: SetupRequest, request: Request, db: DbSession):
    client_ip = request.client.host if request.client else "unknown"
    enforce_login_rate_limit(f"setup:{client_ip}")
    user = create_initial_admin(
        db,
        name=payload.name,
        email=str(payload.email),
        password=payload.password,
    )
    refresh_token = create_refresh_token(db, user)
    access_token = build_login_token(user)
    db.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=build_auth_user(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: DbSession):
    client_ip = request.client.host if request.client else "unknown"
    enforce_login_rate_limit(f"{client_ip}:{payload.email.strip().lower()}")
    user = authenticate_user(db, email=payload.email, password=payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.role_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has no role assigned. Ask an administrator to set a role in User Management.",
        )
    refresh_token = create_refresh_token(db, user)
    access_token = build_login_token(user)
    db.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=build_auth_user(user),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(payload: RefreshTokenRequest, db: DbSession):
    return AccessTokenResponse(access_token=refresh_access_token(db, payload.refresh_token))


@router.get("/me", response_model=AuthUserRead)
def me(current_user: CurrentUser):
    user_id = current_user.id

    def _load() -> dict:
        return build_auth_user(current_user).model_dump(mode="json")

    payload = cached_value(
        "auth",
        f"me:{user_id}",
        _load,
        ttl_seconds=settings.redis_cache_ttl_auth_me,
    )
    return AuthUserRead.model_validate(payload)


@router.post("/change-password", response_model=CommonResponse)
def change_password(payload: ChangePasswordRequest, db: DbSession, current_user: CurrentUser):
    change_user_password(
        db,
        current_user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    invalidate_auth_me(current_user.id)
    db.commit()
    return CommonResponse(message="Password updated")


@router.post("/logout", response_model=CommonResponse)
def logout(payload: LogoutRequest, db: DbSession):
    token = revoke_refresh_token(db, payload.refresh_token)
    write_audit_log(
        db,
        action="Logout",
        username=token.user.name,
        description=f"{token.user.name} logged out",
    )
    db.commit()
    return CommonResponse(message="Logged out")
