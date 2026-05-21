"""Targeted Redis invalidation from ORM changes (avoids flushing entire cache)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.redis_cache import invalidate_auth_me, invalidate_dashboard, invalidate_lists
from app.services.cache_invalidation import (
    AUDIT_LOGS,
    CATEGORIES,
    CLASSES,
    COMMISSIONS,
    COURSES,
    FINANCE,
    LEVELS,
    REPORTS,
    ROLES,
    STUDENTS,
    USERS,
)

_MODEL_RESOURCES: dict[str, tuple[str, ...]] = {
    "Student": (STUDENTS, REPORTS, COMMISSIONS, FINANCE),
    "Enrollment": (STUDENTS, CLASSES, REPORTS, COMMISSIONS, FINANCE),
    "SchoolClass": (CLASSES, COURSES, CATEGORIES, LEVELS, REPORTS, COMMISSIONS, FINANCE),
    "Course": (COURSES, CLASSES, REPORTS),
    "Category": (CATEGORIES, CLASSES),
    "Level": (LEVELS, CLASSES),
    "Invoice": (REPORTS, COMMISSIONS, FINANCE, STUDENTS, CLASSES),
    "InvoiceLine": (REPORTS, COMMISSIONS, FINANCE, STUDENTS, CLASSES),
    "Commission": (COMMISSIONS, REPORTS, FINANCE),
    "Finance": (FINANCE, REPORTS, COMMISSIONS),
    "User": (USERS,),
    "Role": (ROLES, USERS),
    "AuditLog": (AUDIT_LOGS,),
}

_AUTH_MODELS = frozenset({"User", "Role"})
_DASHBOARD_MODELS = frozenset(
    {
        "Student",
        "Enrollment",
        "SchoolClass",
        "Course",
        "Category",
        "Level",
        "Invoice",
        "InvoiceLine",
        "Commission",
        "Finance",
    }
)


def invalidate_caches_for_session(session: Session) -> None:
    """Invalidate only list resources affected by committed ORM changes."""
    from app.services.cache_invalidation import after_any_write

    changed = set(session.new) | set(session.dirty) | set(session.deleted)
    if not changed:
        return

    resources: set[str] = set()
    auth_stale = False
    dashboard_stale = False
    unknown = False

    for obj in changed:
        name = type(obj).__name__
        mapped = _MODEL_RESOURCES.get(name)
        if mapped is None:
            unknown = True
            continue
        resources.update(mapped)
        if name in _AUTH_MODELS:
            auth_stale = True
        if name in _DASHBOARD_MODELS:
            dashboard_stale = True

    if unknown:
        after_any_write()
        invalidate_auth_me()
        return

    if resources:
        invalidate_lists(*sorted(resources))
    if dashboard_stale:
        invalidate_dashboard()
    if auth_stale:
        invalidate_auth_me()
