from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.models.user import User
from app.core.config import settings
from app.services.dashboard_service import get_summary
from app.services.table_list_cache import cached_value

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
DashboardViewUser = Annotated[User, Depends(require_permission("dashboard", "view"))]


@router.get("/summary")
def dashboard_summary(db: DbSession, current_user: DashboardViewUser):
    return cached_value(
        "dashboard",
        "summary",
        lambda: get_summary(db),
        ttl_seconds=settings.redis_cache_ttl_dashboard,
    )
