from datetime import datetime, timedelta, timezone
import secrets

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, hash_refresh_token, verify_password
from app.models.refresh_token import RefreshToken
from app.models.role import Role
from app.models.user import User
from app.schemas.auth import AuthUserRead
from app.schemas.user import UserCreate, UserUpdate
from app.services.audit_service import write_audit_log


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def refresh_token_exception() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")


def authenticate_user(db: Session, *, email: str, password: str) -> User | None:
    user = db.scalar(select(User).options(joinedload(User.role)).where(User.email == email))
    if not user or not verify_password(password, user.password_hash):
        return None
    user.last_login = _utcnow()
    write_audit_log(db, action="Login", username=user.name, description=f"{user.name} logged in")
    db.flush()
    return user


def build_login_token(user: User) -> str:
    return create_access_token(user.id)


def create_refresh_token(db: Session, user: User) -> str:
    raw_token = secrets.token_urlsafe(64)
    token = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=_utcnow() + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(token)
    db.flush()
    return raw_token


def get_valid_refresh_token(db: Session, raw_token: str) -> RefreshToken:
    token_hash = hash_refresh_token(raw_token)
    token = db.scalar(
        select(RefreshToken)
        .options(joinedload(RefreshToken.user).joinedload(User.role))
        .where(RefreshToken.token_hash == token_hash)
    )
    if token is None or token.is_revoked or _as_aware(token.expires_at) <= _utcnow():
        raise refresh_token_exception()
    return token


def refresh_access_token(db: Session, raw_token: str) -> str:
    token = get_valid_refresh_token(db, raw_token)
    return create_access_token(token.user_id)


def revoke_refresh_token(db: Session, raw_token: str) -> RefreshToken:
    token = get_valid_refresh_token(db, raw_token)
    token.is_revoked = True
    token.revoked_at = _utcnow()
    db.flush()
    return token


def build_auth_user(user: User) -> AuthUserRead:
    return AuthUserRead(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role.name if user.role else None,
        permissions=user.role.permissions if user.role and user.role.permissions else {},
    )


def user_create_data(payload: UserCreate) -> dict:
    data = payload.model_dump(exclude={"password"})
    data["password_hash"] = get_password_hash(payload.password)
    return data


def user_update_data(payload: UserUpdate) -> dict:
    data = payload.model_dump(exclude_unset=True, exclude={"password"})
    if payload.password:
        data["password_hash"] = get_password_hash(payload.password)
    return data


def ensure_default_admin(db: Session, *, email: str = "admin@example.com", password: str = "password123") -> User:
    admin = db.scalar(select(User).where(User.email == email))
    if admin:
        if not verify_password(password, admin.password_hash):
            admin.password_hash = get_password_hash(password)
            db.flush()
        return admin

    admin_role = db.scalar(select(Role).where(Role.name == "Admin"))
    if not admin_role:
        from app.core.permissions import ADMIN_PERMISSIONS

        admin_role = Role(name="Admin", permissions=ADMIN_PERMISSIONS)
        db.add(admin_role)
        db.flush()

    admin = User(
        name="Admin User",
        email=email,
        password_hash=get_password_hash(password),
        role_id=admin_role.id,
    )
    db.add(admin)
    db.flush()
    return admin
