from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.models.commission import Commission
from app.models.user import User
from app.schemas.commission import CommissionRead
from app.schemas.common import TableQueryParams, TableResponse, table_query_params
from app.services.audit_service import write_audit_log
from app.services.commission_service import sync_commissions_from_invoices
from app.services.export_service import rows_for_export
from app.utils.filters import apply_date_filter, apply_search, split_filter, split_int_filter
from app.utils.pagination import apply_pagination
from app.utils.sorting import apply_sorting

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
TableParams = Annotated[TableQueryParams, Depends(table_query_params)]
CommissionViewUser = Annotated[User, Depends(require_permission("commissions", "view"))]
CommissionExportUser = Annotated[User, Depends(require_permission("commissions", "export"))]

SORT_MAP = {
    "id": Commission.id,
    "teacherName": Commission.teacher_name,
    "className": Commission.class_name,
    "studentName": Commission.student_name,
    "source": Commission.source,
    "amount": Commission.amount,
    "commission": Commission.commission,
    "date": Commission.created_at,
}


def _to_read(row: Commission) -> CommissionRead:
    return CommissionRead(
        id=row.id,
        class_name=row.class_name,
        student_name=row.student_name,
        teacher_name=row.teacher_name,
        source=row.source,
        date=row.created_at,
        amount=row.amount,
        commission=row.commission,
    )


def _commission_filter_kwargs(
    *,
    source: str | None,
    class_id: str | None,
) -> dict:
    return {"source": source, "class_id": class_id}


def _build_commission_query(
    db: Session,
    query: TableParams,
    *,
    source: str | None = None,
    class_id: str | None = None,
):
    statement = select(Commission)

    sources = split_filter(source)
    if sources:
        statement = statement.where(Commission.source.in_(sources))

    class_ids = split_int_filter(class_id)
    if class_ids:
        statement = statement.where(Commission.class_id.in_(class_ids))

    statement = apply_search(
        statement,
        query.search,
        [Commission.teacher_name, Commission.class_name, Commission.student_name, Commission.source],
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
    source: str | None = Query(None),
    class_id: str | None = Query(None, alias="classId"),
):
    _maybe_sync_empty(db)
    statement, total = _build_commission_query(
        db,
        query,
        **_commission_filter_kwargs(source=source, class_id=class_id),
    )
    rows = db.scalars(apply_pagination(statement, query.page, query.limit)).all()
    return {"data": [_to_read(row) for row in rows], "total": total}


@router.get("/export")
def export_commissions(
    db: DbSession,
    query: TableParams,
    current_user: CommissionExportUser,
    source: str | None = Query(None),
    class_id: str | None = Query(None, alias="classId"),
):
    _maybe_sync_empty(db)
    statement, total = _build_commission_query(
        db,
        query,
        **_commission_filter_kwargs(source=source, class_id=class_id),
    )
    rows = db.scalars(statement).all()
    data = [_to_read(row) for row in rows]
    write_audit_log(
        db,
        action="Export",
        username=current_user.name,
        description=f"{current_user.name} exported commission lines",
    )
    db.commit()
    return {"data": rows_for_export(data), "total": total}
