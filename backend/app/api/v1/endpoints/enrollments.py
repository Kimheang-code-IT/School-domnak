from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import require_permission
from app.models.class_model import SchoolClass
from app.models.enrollment import Enrollment
from app.models.student import Student
from app.models.user import User
from app.schemas.common import CommonResponse
from app.schemas.enrollment import EnrollmentCreate
from app.services.audit_service import write_audit_log
from app.services.telegram_activity_service import notify_class_enrollment

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
EnrollmentCreateUser = Annotated[User, Depends(require_permission("classes", "continue_payment"))]


@router.post("", response_model=CommonResponse, status_code=status.HTTP_201_CREATED)
def create_enrollment(payload: EnrollmentCreate, db: DbSession, current_user: EnrollmentCreateUser):
    student = db.get(Student, payload.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    school_class = db.scalar(
        select(SchoolClass)
        .options(selectinload(SchoolClass.course), selectinload(SchoolClass.teacher))
        .where(SchoolClass.id == payload.class_id)
    )
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")

    enrollment = Enrollment(**payload.model_dump())
    db.add(enrollment)
    write_audit_log(db, action="Create", username=current_user.name, description=f"{current_user.name} created enrollment")
    db.commit()
    db.refresh(enrollment)
    notify_class_enrollment(student, school_class, enrollment, enrolled_by=current_user.name)
    return CommonResponse(message="Enrollment created")
