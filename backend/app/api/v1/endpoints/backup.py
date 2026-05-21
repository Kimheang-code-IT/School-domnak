from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import require_permission
from app.models.user import User
from app.schemas.common import CommonResponse
from app.utils.task_dispatch import dispatch_google_sheets_backup

router = APIRouter()

BackupAdminUser = Annotated[User, Depends(require_permission("role-management", "view"))]


@router.post("/google-sheets", response_model=CommonResponse)
def trigger_google_sheets_backup(current_user: BackupAdminUser) -> CommonResponse:
    """Queue full database backup to Google Sheets (Celery) or run in a background thread."""
    dispatch_google_sheets_backup()
    return CommonResponse(message="Google Sheets backup started in the background.")
