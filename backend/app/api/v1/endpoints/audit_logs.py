from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit_log import AuditLogRead
from app.schemas.common import TableQueryParams, TableResponse, table_query_params
from app.services.audit_service import write_audit_log
from app.services.export_service import rows_for_export
from app.utils.filters import apply_date_filter, apply_search, split_filter
from app.utils.pagination import apply_pagination
from app.utils.sorting import apply_sorting

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
TableParams = Annotated[TableQueryParams, Depends(table_query_params)]
HistoryViewUser = Annotated[User, Depends(require_permission("history", "view"))]
HistoryExportUser = Annotated[User, Depends(require_permission("history", "export"))]


def _build_audit_query(db: Session, query: TableQueryParams, action: str | None):
    statement = select(AuditLog)
    actions = split_filter(action)
    if actions:
        statement = statement.where(AuditLog.type_action.in_(actions))
    statement = apply_search(statement, query.search, [AuditLog.type_action, AuditLog.username, AuditLog.description])
    statement = apply_date_filter(statement, AuditLog.created_at, query.date_from, query.date_to)
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    statement = apply_sorting(
        statement,
        sort_by=query.sort_by,
        sort_order=query.sort_order,
        sort_map={
            "id": AuditLog.id,
            "typeAction": AuditLog.type_action,
            "username": AuditLog.username,
            "date": AuditLog.created_at,
            "createdAt": AuditLog.created_at,
        },
        default_sort="date",
    )
    return statement, total


def _to_read(row: AuditLog) -> AuditLogRead:
    return AuditLogRead(
        id=row.id,
        type_action=row.type_action,
        username=row.username,
        date=row.created_at,
        description=row.description,
    )


@router.get("", response_model=TableResponse[AuditLogRead])
def list_audit_logs(db: DbSession, query: TableParams, current_user: HistoryViewUser, action: str | None = Query(None)):
    statement, total = _build_audit_query(db, query, action)
    rows = db.scalars(apply_pagination(statement, query.page, query.limit)).all()
    return {"data": [_to_read(row) for row in rows], "total": total}


@router.get("/export")
def export_audit_logs(db: DbSession, query: TableParams, current_user: HistoryExportUser, action: str | None = Query(None)):
    statement, total = _build_audit_query(db, query, action)
    rows = db.scalars(statement).all()
    data = [_to_read(row) for row in rows]
    write_audit_log(db, action="Export", username=current_user.name, description=f"{current_user.name} exported audit logs")
    db.commit()
    return {"data": rows_for_export(data), "total": total}
