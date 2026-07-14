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
        telegram_key=user.telegram_key,
        last_login=user.last_login,
        permissions=user.role.permissions if user.role and user.role.permissions else {},
    )


def change_user_password(db: Session, user: User, *, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    cleaned = (new_password or "").strip()
    if len(cleaned) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters",
        )
    if verify_password(cleaned, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password",
        )
    user.password_hash = get_password_hash(cleaned)
    write_audit_log(
        db,
        action="Update",
        username=user.name,
        description=f"{user.name} changed their password",
    )
    db.flush()


def resolve_role_id(db: Session, *, role_id: int | None = None, role_name: str | None = None) -> int | None:
    if role_id is not None:
        return role_id
    name = (role_name or "").strip()
    if not name:
        return None
    role = db.scalar(select(Role).where(Role.name == name))
    return role.id if role else None


def user_create_data(db: Session, payload: UserCreate) -> dict:
    from app.services.telegram_auth_service import generate_telegram_key, normalize_telegram_key

    data = payload.model_dump(exclude={"password", "role"})
    data["password_hash"] = get_password_hash(payload.password)
    resolved_role_id = resolve_role_id(db, role_id=payload.role_id, role_name=payload.role)
    if resolved_role_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid role is required",
        )
    data["role_id"] = resolved_role_id
    key = normalize_telegram_key(payload.telegram_key) or generate_telegram_key()
    existing = db.scalar(select(User).where(User.telegram_key == key))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram key is already used by another user",
        )
    data["telegram_key"] = key
    return data


def user_update_data(db: Session, payload: UserUpdate, *, user_id: int | None = None) -> dict:
    from app.services.telegram_auth_service import normalize_telegram_key

    data = payload.model_dump(exclude_unset=True, exclude={"password", "role"})
    if payload.password:
        data["password_hash"] = get_password_hash(payload.password)
    if payload.role_id is not None or payload.role is not None:
        resolved_role_id = resolve_role_id(db, role_id=payload.role_id, role_name=payload.role)
        if resolved_role_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A valid role is required",
            )
        data["role_id"] = resolved_role_id
    if "telegram_key" in data:
        key = normalize_telegram_key(data.get("telegram_key"))
        if not key:
            data.pop("telegram_key", None)
        else:
            existing = db.scalar(select(User).where(User.telegram_key == key))
            if existing is not None and (user_id is None or existing.id != user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Telegram key is already used by another user",
                )
            data["telegram_key"] = key
            # Changing the key requires re-registration in Telegram.
            data["telegram_chat_id"] = None
    return data


def needs_initial_setup(db: Session) -> bool:
    return db.scalar(select(User.id).limit(1)) is None


def create_initial_admin(db: Session, *, name: str, email: str, password: str) -> User:
    """Create the first Admin user. Raises 409 if any user already exists."""
    if not needs_initial_setup(db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Setup already completed. Sign in instead.",
        )

    from app.core.permissions import ADMIN_PERMISSIONS, sanitize_role_permissions
    from app.services.telegram_auth_service import generate_telegram_key

    clean_name = (name or "").strip()
    clean_email = (email or "").strip().lower()
    if not clean_name or not clean_email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name, email, and password are required.",
        )

    admin_role = db.scalar(select(Role).where(Role.name == "Admin"))
    if admin_role is None:
        admin_role = Role(name="Admin", permissions=ADMIN_PERMISSIONS)
        db.add(admin_role)
        db.flush()
    else:
        admin_role.permissions = sanitize_role_permissions(admin_role.permissions or ADMIN_PERMISSIONS)

    user = User(
        name=clean_name,
        email=clean_email,
        password_hash=get_password_hash(password),
        role_id=admin_role.id,
        telegram_key=generate_telegram_key(),
        last_login=_utcnow(),
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    # Ensure role relationship is loaded for token response
    user = db.scalar(select(User).options(joinedload(User.role)).where(User.id == user.id))
    assert user is not None
    write_audit_log(
        db,
        action="Create",
        username=user.name,
        description=f"Initial admin setup for {user.email}",
    )
    return user


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
