from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import (
    ROLE_MANAGEMENT_RESERVED_NAMES,
    ROLE_PERMISSION_CATALOG,
    catalog_actions_union,
    catalog_pages,
    sanitize_role_permissions,
)
from app.core.security import require_permission
from app.models.role import Role
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.common import CommonResponse, TableQueryParams, TableResponse, table_query_params
from app.schemas.role import RoleCreate, RoleRead, RoleUpdate
from app.services.audit_service import write_audit_log
from app.utils.filters import split_filter

router = APIRouter()
repo = BaseRepository(Role)
DbSession = Annotated[Session, Depends(get_db)]
TableParams = Annotated[TableQueryParams, Depends(table_query_params)]
RoleViewUser = Annotated[User, Depends(require_permission("role-management", "view"))]
RoleCreateUser = Annotated[User, Depends(require_permission("role-management", "create"))]
RoleUpdateUser = Annotated[User, Depends(require_permission("role-management", "update"))]
RoleDeleteUser = Annotated[User, Depends(require_permission("role-management", "delete"))]


def _assert_role_manageable(role: Role) -> None:
    if role.name in ROLE_MANAGEMENT_RESERVED_NAMES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This system role cannot be modified from Role Management",
        )


def _assert_role_deletable(role: Role) -> None:
    _assert_role_manageable(role)


def _apply_permissions_payload(data: dict) -> dict:
    if "permissions" not in data:
        return data
    sanitized = sanitize_role_permissions(data.get("permissions"))
    if not sanitized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one permission from the system catalog is required",
        )
    data["permissions"] = sanitized
    return data


@router.get("/permission-catalog")
def permission_catalog(_current_user: RoleViewUser):
    return {
        "catalog": ROLE_PERMISSION_CATALOG,
        "pages": catalog_pages(),
        "actions": catalog_actions_union(),
    }


@router.get("", response_model=TableResponse[RoleRead])
def list_roles(db: DbSession, query: TableParams, current_user: RoleViewUser, role: str | None = Query(None)):
    statement = select(Role).where(Role.name.notin_(ROLE_MANAGEMENT_RESERVED_NAMES))
    roles = split_filter(role)
    if roles:
        statement = statement.where(Role.name.in_(roles))
    rows, total = repo.list_simple(
        db,
        query,
        base_statement=statement,
        sort_map={"id": Role.id, "name": Role.name, "createdAt": Role.created_at},
        search_columns=[Role.name],
        date_column=Role.created_at,
    )
    return {"data": [RoleRead.model_validate(row[0]) for row in rows], "total": total}


@router.post("", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
def create_role(payload: RoleCreate, db: DbSession, current_user: RoleCreateUser):
    if payload.name in ROLE_MANAGEMENT_RESERVED_NAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This role name is reserved for the system",
        )
    data = _apply_permissions_payload(payload.model_dump())
    role = repo.create(db, data)
    write_audit_log(db, action="Create", username=current_user.name, description=f"{current_user.name} created role {role.name}")
    db.commit()
    return RoleRead.model_validate(role)


@router.put("/{role_id}", response_model=RoleRead)
def update_role(role_id: int, payload: RoleUpdate, db: DbSession, current_user: RoleUpdateUser):
    role = repo.get(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    _assert_role_manageable(role)
    data = payload.model_dump(exclude_unset=True)
    if "permissions" in data:
        data = _apply_permissions_payload(data)
    if role.name in ROLE_MANAGEMENT_RESERVED_NAMES and data.get("name") and data["name"] != role.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This system role cannot be renamed",
        )
    role = repo.update(db, role, data)
    write_audit_log(db, action="Update", username=current_user.name, description=f"{current_user.name} updated role {role.name} permissions")
    db.commit()
    return RoleRead.model_validate(role)


@router.delete("/{role_id}", response_model=CommonResponse)
def delete_role(role_id: int, db: DbSession, current_user: RoleDeleteUser):
    role = repo.get(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    _assert_role_deletable(role)
    name = role.name
    repo.delete(db, role)
    write_audit_log(db, action="Delete", username=current_user.name, description=f"{current_user.name} deleted role {name}")
    db.commit()
    return CommonResponse(message="Role deleted")
