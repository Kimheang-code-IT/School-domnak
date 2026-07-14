from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import require_permission
from app.models.class_model import SchoolClass
from app.models.commission import Commission
from app.models.student import Student
from app.models.user import User
from app.schemas.commission import CommissionRead
from app.schemas.common import TableQueryParams, TableResponse, table_query_params
from app.services.audit_service import write_audit_log
from app.services.commission_service import sync_commissions_from_invoices
from app.services.export_service import rows_for_export
from app.utils.filters import apply_date_filter, apply_search, split_int_filter
from app.utils.pagination import apply_pagination
from app.services.cache_invalidation import COMMISSIONS
from app.services.table_list_cache import cached_table_list
from app.utils.sorting import apply_sorting

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
TableParams = Annotated[TableQueryParams, Depends(table_query_params)]
CommissionViewUser = Annotated[User, Depends(require_permission("commissions", "view"))]
CommissionExportUser = Annotated[User, Depends(require_permission("commissions", "export"))]

SORT_MAP = {
    "id": Commission.id,
    "teacherName": User.name,
    "className": SchoolClass.name,
    "studentName": Student.name_en,
    "amount": Commission.amount,
    "commission": Commission.commission,
    "date": Commission.created_at,
}


def _teacher_label(row: Commission) -> str:
    if row.teacher is not None and (row.teacher.name or "").strip():
        return row.teacher.name.strip()
    if row.school_class is not None and row.school_class.teacher is not None:
        name = (row.school_class.teacher.name or "").strip()
        if name:
            return name
    return "Unknown"


def _student_label(row: Commission) -> str | None:
    if row.student is None:
        return None
    en = (row.student.name_en or "").strip()
    if en:
        return en
    return (row.student.name_km or "").strip() or None


def _class_label(row: Commission) -> str | None:
    if row.school_class is not None:
        return row.school_class.name
    return None


def _to_read(row: Commission) -> CommissionRead:
    return CommissionRead(
        id=row.id,
        class_id=row.class_id,
        student_id=row.student_id,
        invoice_id=row.invoice_id,
        teacher_id=row.teacher_id,
        class_name=_class_label(row),
        student_name=_student_label(row),
        teacher_name=_teacher_label(row),
        date=row.created_at,
        amount=row.amount,
        commission=row.commission,
    )


def _commission_filter_kwargs(*, class_id: str | None) -> dict:
    return {"class_id": class_id}


def _build_commission_query(
    db: Session,
    query: TableParams,
    *,
    class_id: str | None = None,
):
    statement = (
        select(Commission)
        .outerjoin(SchoolClass, SchoolClass.id == Commission.class_id)
        .outerjoin(Student, Student.id == Commission.student_id)
        .outerjoin(User, User.id == Commission.teacher_id)
        .options(
            selectinload(Commission.school_class).selectinload(SchoolClass.teacher),
            selectinload(Commission.student),
            selectinload(Commission.teacher),
        )
    )

    class_ids = split_int_filter(class_id)
    if class_ids:
        statement = statement.where(Commission.class_id.in_(class_ids))

    statement = apply_search(
        statement,
        query.search,
        [User.name, SchoolClass.name, Student.name_en, Student.name_km],
    )
    statement = apply_date_filter(statement, Commission.created_at, query.date_from, query.date_to)
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    statement = apply_sorting(
        statement,
        sort_by=query.sort_by,
        sort_order=query.sort_order,
        sort_map=SORT_MAP,
        default_sort="date",
    )
    return statement, total


def _maybe_sync_empty(db: Session) -> None:
    if (db.scalar(select(func.count()).select_from(Commission)) or 0) == 0:
        sync_commissions_from_invoices(db)
        db.commit()


@router.get("", response_model=TableResponse[CommissionRead])
def list_commissions(
    db: DbSession,
    query: TableParams,
    current_user: CommissionViewUser,
    class_id: str | None = Query(None, alias="classId"),
):
    def _load() -> tuple[list[CommissionRead], int]:
        _maybe_sync_empty(db)
        statement, total = _build_commission_query(
            db,
            query,
            **_commission_filter_kwargs(class_id=class_id),
        )
        rows = db.scalars(apply_pagination(statement, query.page, query.limit)).unique().all()
        return [_to_read(row) for row in rows], total

    return cached_table_list(
        COMMISSIONS,
        query,
        _load,
        extra=_commission_filter_kwargs(class_id=class_id),
    )


@router.get("/export")
def export_commissions(
    db: DbSession,
    query: TableParams,
    current_user: CommissionExportUser,
    class_id: str | None = Query(None, alias="classId"),
):
    _maybe_sync_empty(db)
    statement, total = _build_commission_query(
        db,
        query,
        **_commission_filter_kwargs(class_id=class_id),
    )
    rows = db.scalars(statement).unique().all()
    data = [_to_read(row) for row in rows]
    write_audit_log(
        db,
        action="Export",
        username=current_user.name,
        description=f"{current_user.name} exported commission lines",
    )
    db.commit()
    return {"data": rows_for_export(data), "total": total}
