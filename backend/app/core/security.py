from datetime import datetime, timedelta, timezone
from typing import Any, Callable
import hashlib
import hmac

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.services.audit_service import write_audit_log

pwd_context = CryptContext(schemes=["bcrypt", "pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")

PERMISSION_DENIED_MESSAGE = "You do not have permission to perform this action"
PermissionsMap = dict[str, list[str]]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def hash_refresh_token(refresh_token: str) -> str:
    return hmac.new(
        settings.secret_key.encode("utf-8"),
        refresh_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_access_token(user_id: int | str, expires_delta: timedelta | None = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        subject = payload.get("sub")
        if subject is None:
            raise _credentials_exception()
        user_id = int(subject)
    except (JWTError, ValueError) as exc:
        raise _credentials_exception() from exc

    user = db.scalar(
        select(User)
        .options(joinedload(User.role))
        .where(User.id == user_id)
    )
    if user is None:
        raise _credentials_exception()
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


def has_permission(user: User, page: str, action: str) -> bool:
    permissions = user.role.permissions if user.role and user.role.permissions else {}
    actions = permissions.get(page, [])
    return "*" in actions or action in actions


def _log_permission_denied(db: Session, user: User, page: str, action: str) -> None:
    write_audit_log(
        db,
        action="Denied",
        username=user.name,
        description=f"{user.name} tried to {action} on {page} but permission denied",
    )
    db.commit()


def require_permission(page: str, action: str) -> Callable[..., User]:
    def dependency(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        if not has_permission(current_user, page, action):
            _log_permission_denied(db, current_user, page, action)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=PERMISSION_DENIED_MESSAGE)
        return current_user

    return dependency


def enforce_permission(db: Session, user: User, page: str, action: str) -> None:
    if not has_permission(user, page, action):
        _log_permission_denied(db, user, page, action)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=PERMISSION_DENIED_MESSAGE)
