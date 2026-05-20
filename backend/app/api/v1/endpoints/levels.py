from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.models.user import User
from app.repositories.level_repository import LevelRepository
from app.schemas.common import CommonResponse, TableQueryParams, TableResponse, table_query_params
from app.schemas.level import LevelCreate, LevelRead, LevelUpdate
from app.services.audit_service import write_audit_log

router = APIRouter()
repo = LevelRepository()
DbSession = Annotated[Session, Depends(get_db)]
TableParams = Annotated[TableQueryParams, Depends(table_query_params)]
LevelViewUser = Annotated[User, Depends(require_permission("levels", "view"))]
LevelCreateUser = Annotated[User, Depends(require_permission("levels", "create"))]
LevelUpdateUser = Annotated[User, Depends(require_permission("levels", "update"))]
LevelDeleteUser = Annotated[User, Depends(require_permission("levels", "delete"))]


@router.get("", response_model=TableResponse[LevelRead])
def list_levels(db: DbSession, query: TableParams, current_user: LevelViewUser):
    data, total = repo.list_levels(db, query)
    return {"data": data, "total": total}


@router.post("", response_model=LevelRead, status_code=status.HTTP_201_CREATED)
def create_level(payload: LevelCreate, db: DbSession, current_user: LevelCreateUser):
    level = repo.create(db, payload.model_dump())
    write_audit_log(
        db,
        action="Create",
        username=current_user.name,
        description=f"{current_user.name} created level {level.level_name_en}",
    )
    db.commit()
    return LevelRead.model_validate({**level.__dict__, "total_class": 0})


@router.get("/{level_id}", response_model=LevelRead)
def get_level(level_id: int, db: DbSession, current_user: LevelViewUser):
    level = repo.get(db, level_id)
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    return LevelRead.model_validate({**level.__dict__, "total_class": len(level.classes)})


@router.put("/{level_id}", response_model=LevelRead)
def update_level(level_id: int, payload: LevelUpdate, db: DbSession, current_user: LevelUpdateUser):
    level = repo.get(db, level_id)
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    level = repo.update(db, level, payload.model_dump(exclude_unset=True))
    write_audit_log(
        db,
        action="Update",
        username=current_user.name,
        description=f"{current_user.name} updated level {level.level_name_en}",
    )
    db.commit()
    return LevelRead.model_validate({**level.__dict__, "total_class": len(level.classes)})


@router.delete("/{level_id}", response_model=CommonResponse)
def delete_level(level_id: int, db: DbSession, current_user: LevelDeleteUser):
    level = repo.get(db, level_id)
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    name = level.level_name_en
    repo.delete(db, level)
    write_audit_log(
        db,
        action="Delete",
        username=current_user.name,
        description=f"{current_user.name} deleted level {name}",
    )
    db.commit()
    return CommonResponse(message="Level deleted")
