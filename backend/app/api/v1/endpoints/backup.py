from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import require_permission
from app.models.user import User
from app.schemas.common import CommonResponse
from app.services.google_sheets_backup_service import BackupResult, run_google_sheets_backup
from app.services.telegram_notify import notify_backup_completed

router = APIRouter()

BackupAdminUser = Annotated[User, Depends(require_permission("role-management", "view"))]


@router.post("/google-sheets", response_model=CommonResponse)
def trigger_google_sheets_backup(current_user: BackupAdminUser) -> CommonResponse:
    """Manually run a full database backup to Google Sheets (same job as the 19:00 schedule)."""
    result: BackupResult = run_google_sheets_backup()
    notify_backup_completed(result)
    if not result.ok:
        return CommonResponse(message=result.message)
    extra = f" Spreadsheet: {result.spreadsheet_url}" if result.spreadsheet_url else ""
    return CommonResponse(message=f"{result.message}{extra}")
