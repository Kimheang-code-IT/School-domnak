from fastapi import APIRouter

from app.api.v1.endpoints import (
    audit_logs,
    auth,
    backup,
    categories,
    classes,
    commissions,
    courses,
    dashboard,
    enrollments,
    finance,
    levels,
    invoices,
    reports,
    roles,
    students,
    telegram,
    users,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(courses.router, prefix="/courses", tags=["courses"])
api_router.include_router(levels.router, prefix="/levels", tags=["levels"])
api_router.include_router(classes.router, prefix="/classes", tags=["classes"])
api_router.include_router(students.router, prefix="/students", tags=["students"])
api_router.include_router(enrollments.router, prefix="/enrollments", tags=["enrollments"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(finance.router, prefix="/finance", tags=["finance"])
api_router.include_router(commissions.router, prefix="/commissions", tags=["commissions"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit logs"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(backup.router, prefix="/backup", tags=["backup"])
api_router.include_router(telegram.router, prefix="/telegram", tags=["telegram"])
