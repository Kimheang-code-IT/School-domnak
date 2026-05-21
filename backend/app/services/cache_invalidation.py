"""Invalidate Redis caches when data changes."""

from __future__ import annotations

from app.core.redis_cache import (
    invalidate_all_data_caches,
    invalidate_auth_me,
    invalidate_dashboard,
    invalidate_list_resource,
    invalidate_lists,
)

# Resource keys used in table_list_cache.cached_table_list()
STUDENTS = "students"
CLASSES = "classes"
COURSES = "courses"
CATEGORIES = "categories"
LEVELS = "levels"
REPORTS = "reports"
COMMISSIONS = "commissions"
FINANCE = "finance"
ROLES = "roles"
USERS = "users"
AUDIT_LOGS = "audit_logs"


def after_student_change() -> None:
    invalidate_lists(STUDENTS, REPORTS, COMMISSIONS, FINANCE)
    invalidate_dashboard()


def after_class_change() -> None:
    invalidate_lists(CLASSES, COURSES, CATEGORIES, LEVELS, REPORTS, COMMISSIONS, FINANCE)
    invalidate_dashboard()


def after_course_change() -> None:
    invalidate_lists(COURSES, CLASSES, REPORTS)
    invalidate_dashboard()


def after_category_change() -> None:
    invalidate_lists(CATEGORIES, CLASSES)
    invalidate_dashboard()


def after_level_change() -> None:
    invalidate_lists(LEVELS, CLASSES)
    invalidate_dashboard()


def after_invoice_or_enrollment_change() -> None:
    invalidate_lists(REPORTS, COMMISSIONS, FINANCE, STUDENTS, CLASSES)
    invalidate_dashboard()


def after_user_or_role_change(user_id: int | None = None) -> None:
    invalidate_lists(USERS, ROLES)
    invalidate_auth_me(user_id)


def after_any_write() -> None:
    """Broad invalidation when many tables may have changed."""
    invalidate_all_data_caches()


def student_enrollments_resource(student_id: int) -> str:
    return f"student_enrollments:{student_id}"


def class_enrollments_resource(class_id: int) -> str:
    return f"class_enrollments:{class_id}"


def invalidate_student_enrollments(student_id: int) -> None:
    invalidate_list_resource(student_enrollments_resource(student_id))


def invalidate_class_enrollments(class_id: int) -> None:
    invalidate_list_resource(class_enrollments_resource(class_id))
