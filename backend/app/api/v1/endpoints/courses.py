from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.models.user import User
from app.repositories.course_repository import CourseRepository
from app.schemas.common import CommonResponse, TableQueryParams, TableResponse, table_query_params
from app.schemas.course import CourseCreate, CourseRead, CourseUpdate
from app.services.audit_service import write_audit_log

router = APIRouter()
repo = CourseRepository()
DbSession = Annotated[Session, Depends(get_db)]
TableParams = Annotated[TableQueryParams, Depends(table_query_params)]
CourseViewUser = Annotated[User, Depends(require_permission("courses", "view"))]
CourseCreateUser = Annotated[User, Depends(require_permission("courses", "create"))]
CourseUpdateUser = Annotated[User, Depends(require_permission("courses", "update"))]
CourseDeleteUser = Annotated[User, Depends(require_permission("courses", "delete"))]


@router.get("", response_model=TableResponse[CourseRead])
def list_courses(db: DbSession, query: TableParams, current_user: CourseViewUser):
    data, total = repo.list_courses(db, query)
    return {"data": data, "total": total}


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
def create_course(payload: CourseCreate, db: DbSession, current_user: CourseCreateUser):
    course = repo.create(db, payload.model_dump())
    write_audit_log(db, action="Create", username=current_user.name, description=f"{current_user.name} created course {course.course_name}")
    db.commit()
    return CourseRead.model_validate({**course.__dict__, "total_class": 0})


@router.put("/{course_id}", response_model=CourseRead)
def update_course(course_id: int, payload: CourseUpdate, db: DbSession, current_user: CourseUpdateUser):
    course = repo.get(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    course = repo.update(db, course, payload.model_dump(exclude_unset=True))
    write_audit_log(db, action="Update", username=current_user.name, description=f"{current_user.name} updated course {course.course_name}")
    db.commit()
    return CourseRead.model_validate({**course.__dict__, "total_class": len(course.classes)})


@router.delete("/{course_id}", response_model=CommonResponse)
def delete_course(course_id: int, db: DbSession, current_user: CourseDeleteUser):
    course = repo.get(db, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    name = course.course_name
    repo.delete(db, course)
    write_audit_log(db, action="Delete", username=current_user.name, description=f"{current_user.name} deleted course {name}")
    db.commit()
    return CommonResponse(message="Course deleted")
