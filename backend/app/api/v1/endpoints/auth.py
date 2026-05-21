from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    AuthUserRead,
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from app.schemas.common import CommonResponse
from app.services.audit_service import write_audit_log
from app.services.auth_service import (
    authenticate_user,
    build_auth_user,
    build_login_token,
    create_refresh_token,
    refresh_access_token,
    revoke_refresh_token,
)

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession):
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
    return build_auth_user(current_user)


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
