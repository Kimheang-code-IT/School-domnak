from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.models.enrollment import Enrollment
from app.models.invoice import Invoice, InvoiceLine
from app.models.user import User
from app.repositories.student_repository import StudentRepository
from app.schemas.common import CommonResponse, TableQueryParams, TableResponse, table_query_params
from app.schemas.enrollment import StudentEnrollmentRead
from app.schemas.student import StudentCreate, StudentRead, StudentUpdate, format_student_code
from app.services.audit_service import write_audit_log
from app.utils.image_storage import persist_image
from app.utils.task_dispatch import dispatch_new_student_alerts
from app.utils.filters import split_filter, split_int_filter

router = APIRouter()
repo = StudentRepository()
DbSession = Annotated[Session, Depends(get_db)]
TableParams = Annotated[TableQueryParams, Depends(table_query_params)]
StudentViewUser = Annotated[User, Depends(require_permission("students", "view"))]
StudentCreateUser = Annotated[User, Depends(require_permission("students", "create"))]
StudentUpdateUser = Annotated[User, Depends(require_permission("students", "update"))]
StudentDeleteUser = Annotated[User, Depends(require_permission("students", "delete"))]
StudentEnrollmentViewUser = Annotated[User, Depends(require_permission("students", "view_enrollments"))]
StudentEnrollmentDeleteUser = Annotated[User, Depends(require_permission("students", "delete_enrollment"))]


def _student_read_data(student, total_course: int = 0) -> dict:
    code = format_student_code(student.id)
    return {
        **student.__dict__,
        "student_code": code,
        "student_id": code,
        "display_id": code,
        "total_course": total_course,
    }


@router.get("", response_model=TableResponse[StudentRead])
def list_students(
    db: DbSession,
    query: TableParams,
    current_user: StudentViewUser,
    province: str | None = Query(None),
    gender: str | None = Query(None),
    class_id: str | None = Query(None, alias="classId"),
    course_id: str | None = Query(None, alias="courseId"),
):
    data, total = repo.list_students(
        db,
        query,
        provinces=split_filter(province),
        genders=split_filter(gender),
        class_ids=split_int_filter(class_id),
        course_ids=split_int_filter(course_id),
    )
    return {"data": data, "total": total}


@router.post("", response_model=StudentRead, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentCreate, db: DbSession, current_user: StudentCreateUser):
    data = payload.model_dump()
    if "image" in data:
        data["image"] = persist_image(data.get("image"), "students")
    student = repo.create(db, data)
    write_audit_log(db, action="Create", username=current_user.name, description=f"{current_user.name} created student {student.name_en}")
    db.commit()
    db.refresh(student)
    dispatch_new_student_alerts(student.id, registered_by=current_user.name)
    return StudentRead.model_validate(_student_read_data(student, 0))


@router.put("/{student_id}", response_model=StudentRead)
def update_student(student_id: int, payload: StudentUpdate, db: DbSession, current_user: StudentUpdateUser):
    student = repo.get(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    data = payload.model_dump(exclude_unset=True)
    if "image" in data:
        data["image"] = persist_image(data.get("image"), "students")
    student = repo.update(db, student, data)
    write_audit_log(db, action="Update", username=current_user.name, description=f"{current_user.name} updated student {student.name_en}")
    db.commit()
    total_course = db.scalar(select(func.count(Enrollment.id)).where(Enrollment.student_id == student.id)) or 0
    return StudentRead.model_validate(_student_read_data(student, total_course))


@router.delete("/{student_id}", response_model=CommonResponse)
def delete_student(student_id: int, db: DbSession, current_user: StudentDeleteUser):
    student = repo.get(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    name = student.name_en
    repo.delete(db, student)
    write_audit_log(db, action="Delete", username=current_user.name, description=f"{current_user.name} deleted student {name}")
    db.commit()
    return CommonResponse(message="Student deleted")


def _latest_invoice_for_enrollment(db: Session, *, student_id: int, class_id: int) -> Invoice | None:
    return db.scalar(
        select(Invoice)
        .join(InvoiceLine, InvoiceLine.invoice_id == Invoice.id)
        .where(Invoice.student_id == student_id, InvoiceLine.class_id == class_id)
        .order_by(Invoice.created_at.desc())
        .limit(1)
    )


@router.get("/{student_id}/enrollments", response_model=TableResponse[StudentEnrollmentRead])
def list_student_enrollments(student_id: int, db: DbSession, query: TableParams, current_user: StudentEnrollmentViewUser):
    statement = (
        select(Enrollment)
        .where(Enrollment.student_id == student_id)
        .order_by(Enrollment.register_date.desc(), Enrollment.id.desc())
    )
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(statement.offset((query.page - 1) * query.limit).limit(query.limit)).all()
    data = []
    for enrollment in rows:
        student = enrollment.student
        school_class = enrollment.school_class
        invoice = (
            _latest_invoice_for_enrollment(db, student_id=student_id, class_id=enrollment.class_id)
            if enrollment.class_id
            else None
        )
        data.append(
            StudentEnrollmentRead(
                id=enrollment.id,
                status=enrollment.status,
                roster_active=enrollment.roster_active,
                course_name=school_class.course.course_name if school_class and school_class.course else None,
                class_name=school_class.name if school_class else None,
                level=school_class.level if school_class else None,
                class_duration=school_class.class_duration if school_class else None,
                duration_months=enrollment.duration_months,
                start_date=enrollment.start_date,
                end_date=enrollment.end_date,
                total_price=enrollment.total_price,
                discount_price=enrollment.discount_price,
                price_after_discount=enrollment.price_after_discount,
                invoice_discount_amount=invoice.discount_amount if invoice else None,
                invoice_grand_total=invoice.total if invoice else None,
                register_date=enrollment.register_date,
                name_km=student.name_km,
                name_en=student.name_en,
                birthdate=student.birthdate,
                gender=student.gender,
            )
        )
    return {"data": data, "total": total}


@router.delete("/{student_id}/enrollments/{enrollment_id}", response_model=CommonResponse)
def delete_student_enrollment(student_id: int, enrollment_id: int, db: DbSession, current_user: StudentEnrollmentDeleteUser):
    enrollment = db.scalar(select(Enrollment).where(Enrollment.id == enrollment_id, Enrollment.student_id == student_id))
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    db.delete(enrollment)
    write_audit_log(db, action="Delete", username=current_user.name, description=f"{current_user.name} deleted enrollment {enrollment_id}")
    db.commit()
    return CommonResponse(message="Enrollment deleted")
