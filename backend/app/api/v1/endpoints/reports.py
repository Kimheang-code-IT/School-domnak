from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.models.user import User
from app.repositories.report_repository import ReportRepository
from app.schemas.common import TableQueryParams, TableResponse, table_query_params
from app.schemas.report import ReportSalesLineRead
from app.services.audit_service import write_audit_log
from app.services.cache_invalidation import REPORTS
from app.services.export_service import rows_for_export
from app.services.table_list_cache import cached_table_list

router = APIRouter()
repo = ReportRepository()
DbSession = Annotated[Session, Depends(get_db)]
TableParams = Annotated[TableQueryParams, Depends(table_query_params)]
ReportViewUser = Annotated[User, Depends(require_permission("reports", "view"))]
ReportExportUser = Annotated[User, Depends(require_permission("reports", "export"))]


def _report_list_kwargs(
    *,
    product: str | None,
    address: str | None,
    seller: str | None,
    source: str | None,
    class_id: str | None,
    course_id: str | None,
) -> dict:
    return {
        "product": product,
        "address": address,
        "seller": seller,
        "source": source,
        "class_id": class_id,
        "course_id": course_id,
    }


@router.get("/sales-lines", response_model=TableResponse[ReportSalesLineRead])
def sales_lines(
    db: DbSession,
    query: TableParams,
    current_user: ReportViewUser,
    product: str | None = Query(None),
    address: str | None = Query(None),
    seller: str | None = Query(None),
    source: str | None = Query(None),
    class_id: str | None = Query(None, alias="classId"),
    course_id: str | None = Query(None, alias="courseId"),
):
    return cached_table_list(
        REPORTS,
        query,
        lambda: repo.list_sales_lines(
            db,
            query,
            **_report_list_kwargs(
                product=product,
                address=address,
                seller=seller,
                source=source,
                class_id=class_id,
                course_id=course_id,
            ),
        ),
        extra=_report_list_kwargs(
            product=product,
            address=address,
            seller=seller,
            source=source,
            class_id=class_id,
            course_id=course_id,
        ),
    )


@router.get("/sales-lines/export")
def export_sales_lines(
    db: DbSession,
    query: TableParams,
    current_user: ReportExportUser,
    product: str | None = Query(None),
    address: str | None = Query(None),
    seller: str | None = Query(None),
    source: str | None = Query(None),
    class_id: str | None = Query(None, alias="classId"),
    course_id: str | None = Query(None, alias="courseId"),
):
    data, total = repo.list_sales_lines(
        db,
        query,
        export=True,
        **_report_list_kwargs(
            product=product,
            address=address,
            seller=seller,
            source=source,
            class_id=class_id,
            course_id=course_id,
        ),
    )
    write_audit_log(db, action="Export", username=current_user.name, description=f"{current_user.name} exported sales lines")
    db.commit()
    return {"data": rows_for_export(data), "total": total}
