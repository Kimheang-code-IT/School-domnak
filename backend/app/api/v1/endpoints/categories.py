from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.models.user import User
from app.repositories.category_repository import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.common import CommonResponse, TableQueryParams, TableResponse, table_query_params
from app.services.audit_service import write_audit_log
from app.services.cache_invalidation import CATEGORIES
from app.services.table_list_cache import cached_table_list

router = APIRouter()
repo = CategoryRepository()
DbSession = Annotated[Session, Depends(get_db)]
TableParams = Annotated[TableQueryParams, Depends(table_query_params)]
CategoryViewUser = Annotated[User, Depends(require_permission("categories", "view"))]
CategoryCreateUser = Annotated[User, Depends(require_permission("categories", "create"))]
CategoryUpdateUser = Annotated[User, Depends(require_permission("categories", "update"))]
CategoryDeleteUser = Annotated[User, Depends(require_permission("categories", "delete"))]


@router.get("", response_model=TableResponse[CategoryRead])
def list_categories(db: DbSession, query: TableParams, current_user: CategoryViewUser):
    return cached_table_list(CATEGORIES, query, lambda: repo.list_categories(db, query))


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: DbSession, current_user: CategoryCreateUser):
    category = repo.create(db, payload.model_dump())
    write_audit_log(db, action="Create", username=current_user.name, description=f"{current_user.name} created category {category.name}")
    db.commit()
    return CategoryRead.model_validate({**category.__dict__, "total": 0})


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(category_id: int, db: DbSession, current_user: CategoryViewUser):
    category = repo.get(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return CategoryRead.model_validate({**category.__dict__, "total": len(category.classes)})


@router.put("/{category_id}", response_model=CategoryRead)
def update_category(category_id: int, payload: CategoryUpdate, db: DbSession, current_user: CategoryUpdateUser):
    category = repo.get(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    category = repo.update(db, category, payload.model_dump(exclude_unset=True))
    write_audit_log(db, action="Update", username=current_user.name, description=f"{current_user.name} updated category {category.name}")
    db.commit()
    return CategoryRead.model_validate({**category.__dict__, "total": len(category.classes)})


@router.delete("/{category_id}", response_model=CommonResponse)
def delete_category(category_id: int, db: DbSession, current_user: CategoryDeleteUser):
    category = repo.get(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    name = category.name
    repo.delete(db, category)
    write_audit_log(db, action="Delete", username=current_user.name, description=f"{current_user.name} deleted category {name}")
    db.commit()
    return CommonResponse(message="Category deleted")
