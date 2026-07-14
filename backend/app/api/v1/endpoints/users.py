from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import (
    ROLE_MANAGEMENT_RESERVED_NAMES,
    USER_MANAGEMENT_NON_DELETABLE_ROLE_NAMES,
)
from app.core.security import require_permission
from app.models.role import Role
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.common import CommonResponse, TableQueryParams, TableResponse, table_query_params
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.audit_service import write_audit_log
from app.services.auth_service import user_create_data, user_update_data
from app.services.cache_invalidation import USERS
from app.services.table_list_cache import cached_table_list

router = APIRouter()
repo = UserRepository()
DbSession = Annotated[Session, Depends(get_db)]
TableParams = Annotated[TableQueryParams, Depends(table_query_params)]
UserViewUser = Annotated[User, Depends(require_permission("user-management", "view"))]
UserCreateUser = Annotated[User, Depends(require_permission("user-management", "create"))]
UserUpdateUser = Annotated[User, Depends(require_permission("user-management", "update"))]
UserDeleteUser = Annotated[User, Depends(require_permission("user-management", "delete"))]


def _assert_user_deletable(user: User) -> None:
    role_name = user.role.name if user.role else None
    if role_name in USER_MANAGEMENT_NON_DELETABLE_ROLE_NAMES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Users with the Admin role cannot be deleted",
        )


def _is_admin_actor(user: User) -> bool:
    role_name = (user.role.name if user.role else "") or ""
    return role_name in ROLE_MANAGEMENT_RESERVED_NAMES


def _assert_can_assign_role(db: Session, *, actor: User, role_id: int | None) -> None:
    """Only Admin actors may assign the reserved Admin role."""
    if role_id is None:
        return
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A valid role is required")
    if role.name in ROLE_MANAGEMENT_RESERVED_NAMES and not _is_admin_actor(actor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin users can assign the Admin role",
        )


def _to_read(user) -> UserRead:
    return UserRead(
        id=user.id,
        name=user.name,
        role=user.role.name if user.role else None,
        role_id=user.role_id,
        email=user.email,
        permissions=user.role.permissions if user.role and user.role.permissions else {},
        last_login=user.last_login,
        created_at=user.created_at,
    )


@router.get("", response_model=TableResponse[UserRead])
def list_users(db: DbSession, query: TableParams, current_user: UserViewUser, role: str | None = Query(None)):
    return cached_table_list(USERS, query, lambda: repo.list_users(db, query, role=role), extra={"role": role})


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: DbSession, current_user: UserCreateUser):
    create_data = user_create_data(db, payload)
    _assert_can_assign_role(db, actor=current_user, role_id=create_data.get("role_id"))
    user = repo.create(db, create_data)
    write_audit_log(db, action="Create", username=current_user.name, description=f"{current_user.name} created user {user.name}")
    db.commit()
    return _to_read(user)


@router.put("/{user_id}", response_model=UserRead)
def update_user(user_id: int, payload: UserUpdate, db: DbSession, current_user: UserUpdateUser):
    user = repo.get(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    update_data = user_update_data(db, payload)
    if "role_id" in update_data:
        _assert_can_assign_role(db, actor=current_user, role_id=update_data.get("role_id"))
    user = repo.update(db, user, update_data)
    write_audit_log(db, action="Update", username=current_user.name, description=f"{current_user.name} updated user {user.name}")
    db.commit()
    return _to_read(user)


@router.delete("/{user_id}", response_model=CommonResponse)
def delete_user(user_id: int, db: DbSession, current_user: UserDeleteUser):
    user = repo.get(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    _assert_user_deletable(user)
    name = user.name
    repo.delete(db, user)
    write_audit_log(db, action="Delete", username=current_user.name, description=f"{current_user.name} deleted user {name}")
    db.commit()
    return CommonResponse(message="User deleted")
