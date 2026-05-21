from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import enforce_permission, get_current_active_user, require_permission
from app.models.class_model import SchoolClass
from app.models.commission import Commission
from app.models.enrollment import Enrollment
from app.models.finance import Finance
from app.models.invoice import InvoiceLine
from app.models.student import Student
from app.models.user import User
from app.repositories.class_repository import ClassRepository
from app.schemas.class_schema import ClassCreate, ClassRead, ClassUpdate
from app.schemas.common import CommonResponse, TableQueryParams, TableResponse, table_query_params
from app.schemas.enrollment import ClassEnrollmentRead, EnrollmentPatch
from app.services.audit_service import write_audit_log
from app.services.enrollment_service import sync_class_roster_enrollments, to_class_enrollment_read
from app.services.finance_service import ensure_finance_for_class
from app.services.cache_invalidation import CLASSES, class_enrollments_resource
from app.services.level_service import apply_level_to_class_data
from app.services.table_list_cache import cached_table_list
from app.utils.image_storage import persist_image

router = APIRouter()
repo = ClassRepository()
DbSession = Annotated[Session, Depends(get_db)]
TableParams = Annotated[TableQueryParams, Depends(table_query_params)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]
ClassViewUser = Annotated[User, Depends(require_permission("classes", "view"))]
ClassCreateUser = Annotated[User, Depends(require_permission("classes", "create"))]
ClassUpdateUser = Annotated[User, Depends(require_permission("classes", "update"))]
ClassDeleteUser = Annotated[User, Depends(require_permission("classes", "delete"))]
ClassRosterViewUser = Annotated[User, Depends(require_permission("classes", "view_roster"))]


def _to_read(item, student_count: int = 0) -> ClassRead:
    return ClassRead(
        id=item.id,
        name=item.name,
        image=item.image,
        category_id=item.category_id,
        category=item.category.name if item.category else None,
        course_id=item.course_id,
        course_name=item.course.course_name if item.course else None,
        teacher_id=item.teacher_id,
        teacher_name=item.teacher_name,
        level_id=item.level_id,
        level=item.level,
        level_km=item.level_km,
        level_name_en=item.level,
        level_name_km=item.level_km,
        class_duration=item.class_duration,
        days_of_week=item.days_of_week or [],
        time_in=item.time_in,
        time_out=item.time_out,
        time_slot=item.time_slot,
        full_price=item.full_price,
        discount_amount=item.discount_amount,
        out_price=item.out_price,
        teacher_commission=item.teacher_commission,
        teacher_commission_mode=item.teacher_commission_mode,
        teacher_commission_percent=item.teacher_commission_percent,
        status=item.status,
        student_count=student_count,
        created_at=item.created_at,
    )


@router.get("", response_model=TableResponse[ClassRead])
def list_classes(
    db: DbSession,
    query: TableParams,
    current_user: ClassViewUser,
    category_id: int | None = Query(None, alias="categoryId"),
):
    return cached_table_list(
        CLASSES,
        query,
        lambda: repo.list_classes(db, query, category_id=category_id),
        extra={"categoryId": category_id},
    )


@router.post("", response_model=ClassRead, status_code=status.HTTP_201_CREATED)
def create_class(payload: ClassCreate, db: DbSession, current_user: ClassCreateUser):
    data = apply_level_to_class_data(db, payload.model_dump())
    if "image" in data:
        data["image"] = persist_image(data.get("image"), "classes")
    item = repo.create(db, data)
    ensure_finance_for_class(db, item)
    write_audit_log(db, action="Create", username=current_user.name, description=f"{current_user.name} created class {item.name}")
    db.commit()
    return _to_read(item)


@router.put("/{class_id}", response_model=ClassRead)
def update_class(class_id: int, payload: ClassUpdate, db: DbSession, current_user: ClassUpdateUser):
    item = repo.get(db, class_id)
    if not item:
        raise HTTPException(status_code=404, detail="Class not found")
    data = apply_level_to_class_data(db, payload.model_dump(exclude_unset=True))
    if "image" in data:
        data["image"] = persist_image(data.get("image"), "classes")
    item = repo.update(db, item, data)
    ensure_finance_for_class(db, item)
    write_audit_log(db, action="Update", username=current_user.name, description=f"{current_user.name} updated class {item.name}")
    db.commit()
    count = db.scalar(select(func.count(Enrollment.id)).where(Enrollment.class_id == item.id)) or 0
    return _to_read(item, count)


@router.delete("/{class_id}", response_model=CommonResponse)
def delete_class(class_id: int, db: DbSession, current_user: ClassDeleteUser):
    item = repo.get(db, class_id)
    if not item:
        raise HTTPException(status_code=404, detail="Class not found")
    name = item.name
    # Remove dependents first: enrollments.class_id is NOT NULL, so ORM would try to NULL it on class delete.
    db.execute(delete(Enrollment).where(Enrollment.class_id == class_id))
    db.execute(delete(Finance).where(Finance.class_id == class_id))
    db.execute(delete(Commission).where(Commission.class_id == class_id))
    db.execute(update(InvoiceLine).where(InvoiceLine.class_id == class_id).values(class_id=None))
    repo.delete(db, item)
    write_audit_log(db, action="Delete", username=current_user.name, description=f"{current_user.name} deleted class {name}")
    db.commit()
    return CommonResponse(message="Class deleted")


@router.get("/{class_id}/enrollments", response_model=TableResponse[ClassEnrollmentRead])
def list_class_enrollments(class_id: int, db: DbSession, query: TableParams, current_user: ClassRosterViewUser):
    school_class = db.get(SchoolClass, class_id)
    if not school_class:
        raise HTTPException(status_code=404, detail="Class not found")

    def _load() -> tuple[list[ClassEnrollmentRead], int]:
        sync_class_roster_enrollments(db, class_id, school_class)
        db.commit()

        statement = (
            select(Enrollment, Student)
            .join(Student, Student.id == Enrollment.student_id)
            .where(Enrollment.class_id == class_id, Enrollment.roster_active.is_(True))
        )
        if query.search:
            pattern = f"%{query.search}%"
            statement = statement.where(
                (Student.name_en.ilike(pattern))
                | (Student.name_km.ilike(pattern))
                | (Student.phone.ilike(pattern))
            )
        total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
        rows = db.execute(statement.offset((query.page - 1) * query.limit).limit(query.limit)).all()
        return [to_class_enrollment_read(enrollment, student) for enrollment, student in rows], total

    return cached_table_list(class_enrollments_resource(class_id), query, _load)


@router.patch("/{class_id}/enrollments/{enrollment_id}", response_model=ClassEnrollmentRead)
def patch_class_enrollment(class_id: int, enrollment_id: int, payload: EnrollmentPatch, db: DbSession, current_user: CurrentUser):
    action = "remove_student" if payload.roster_active is False else "continue_payment"
    enforce_permission(db, current_user, "classes", action)
    enrollment = db.scalar(select(Enrollment).where(Enrollment.id == enrollment_id, Enrollment.class_id == class_id))
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(enrollment, key, value)
    if payload.roster_active is False and payload.status is None:
        enrollment.status = "Inactive"
    elif payload.roster_active is True and payload.status is None:
        enrollment.status = "Active"
    write_audit_log(db, action="Update", username=current_user.name, description=f"{current_user.name} updated enrollment {enrollment.id}")
    db.commit()
    db.refresh(enrollment)
    return to_class_enrollment_read(enrollment, enrollment.student)
