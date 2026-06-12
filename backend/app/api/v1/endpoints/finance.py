from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.models.class_model import SchoolClass
from app.models.finance import Finance
from app.models.user import User
from app.schemas.common import TableQueryParams, TableResponse, table_query_params
from app.schemas.finance import FinanceRead, FinanceUpdate
from app.services.audit_service import write_audit_log
from app.services.export_service import rows_for_export
from app.services.finance_service import recalculate_finance, sync_finance_for_all_classes
from app.utils.filters import apply_date_filter, apply_search
from app.utils.pagination import apply_pagination
from app.utils.sorting import apply_sorting

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
TableParams = Annotated[TableQueryParams, Depends(table_query_params)]
FinanceViewUser = Annotated[User, Depends(require_permission("finance", "view"))]
FinanceUpdateUser = Annotated[User, Depends(require_permission("finance", "update"))]
FinanceExportUser = Annotated[User, Depends(require_permission("finance", "export"))]

SORT_MAP = {
    "id": Finance.id,
    "className": SchoolClass.name,
    "productName": SchoolClass.name,
    "electricity": Finance.electricity,
    "water": Finance.water,
    "internet": Finance.internet,
    "totalCommission": Finance.total_commission,
    "facebook": Finance.facebook,
    "other": Finance.other,
    "amount": Finance.amount,
    "finalPrice": Finance.final_price,
    "createdAt": Finance.created_at,
}


def _to_read(row: Finance, class_name: str | None) -> FinanceRead:
    return FinanceRead(
        id=row.id,
        class_name=class_name,
        product_name=class_name,
        electricity=row.electricity,
        water=row.water,
        internet=row.internet,
        total_commission=row.total_commission,
        facebook=row.facebook,
        other=row.other,
        amount=row.amount,
        print_price=row.amount,
        final_price=row.final_price,
        in_price_for_pos=row.in_price_for_pos,
    )


def _build_finance_query(db: Session, query: TableParams):
    statement = (
        select(Finance, SchoolClass.name.label("class_name"))
        .outerjoin(SchoolClass, SchoolClass.id == Finance.class_id)
    )
    statement = apply_search(statement, query.search, [SchoolClass.name])
    statement = apply_date_filter(statement, Finance.created_at, query.date_from, query.date_to)
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    statement = apply_sorting(
        statement,
        sort_by=query.sort_by,
        sort_order=query.sort_order,
        sort_map=SORT_MAP,
    )
    return statement, total


def _maybe_sync_empty(db: Session) -> None:
    if (db.scalar(select(func.count()).select_from(Finance)) or 0) == 0:
        sync_finance_for_all_classes(db)
        db.commit()


@router.get("", response_model=TableResponse[FinanceRead])
def list_finance(db: DbSession, query: TableParams, current_user: FinanceViewUser):
    _maybe_sync_empty(db)
    statement, total = _build_finance_query(db, query)
    rows = db.execute(apply_pagination(statement, query.page, query.limit)).all()
    return {"data": [_to_read(row, class_name) for row, class_name in rows], "total": total}


@router.get("/export")
def export_finance(db: DbSession, query: TableParams, current_user: FinanceExportUser):
    _maybe_sync_empty(db)
    statement, total = _build_finance_query(db, query)
    rows = db.execute(statement).all()
    data = [_to_read(row, class_name) for row, class_name in rows]
    write_audit_log(
        db,
        action="Export",
        username=current_user.name,
        description=f"{current_user.name} exported finance rows",
    )
    db.commit()
    return {"data": rows_for_export(data), "total": total}


@router.put("/{finance_id}", response_model=FinanceRead)
def update_finance(finance_id: int, payload: FinanceUpdate, db: DbSession, current_user: FinanceUpdateUser):
    row = db.get(Finance, finance_id)
    if not row:
        raise HTTPException(status_code=404, detail="Finance row not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    recalculate_finance(row)
    write_audit_log(db, action="Update", username=current_user.name, description=f"{current_user.name} updated finance row {finance_id}")
    db.commit()
    db.refresh(row)
    return _to_read(row, row.school_class.name if row.school_class else None)
