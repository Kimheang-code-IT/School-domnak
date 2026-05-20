PermissionsMap = dict[str, list[str]]

ADMIN_PERMISSIONS: PermissionsMap = {
    "dashboard": ["view"],
    "classes": ["view", "create", "update", "delete", "export", "view_roster", "remove_student", "continue_payment"],
    "students": ["view", "create", "update", "delete", "export", "view_enrollments", "delete_enrollment", "preview_certificate", "download_certificate"],
    "reports": ["view", "export", "preview_invoice"],
    "finance": ["view", "update", "export"],
    "categories": ["view", "create", "update", "delete"],
    "levels": ["view", "create", "update", "delete"],
    "courses": ["view", "create", "update", "delete"],
    "commissions": ["view", "export"],
    "history": ["view", "export", "detail"],
    "user-management": ["view", "create", "update", "delete"],
    "role-management": ["view", "create", "update", "delete"],
}

STAFF_PERMISSIONS: PermissionsMap = {
    "dashboard": ["view"],
    "classes": ["view", "create", "update", "view_roster", "continue_payment"],
    "students": ["view", "create", "update", "view_enrollments", "preview_certificate"],
    "reports": ["view", "preview_invoice"],
    "finance": ["view", "export"],
    "categories": ["view"],
    "levels": ["view"],
    "courses": ["view"],
    "commissions": ["view", "export"],
    "history": ["view"],
}

TEACHER_PERMISSIONS: PermissionsMap = {
    "dashboard": ["view"],
    "classes": ["view", "view_roster"],
    "students": ["view", "view_enrollments"],
    "commissions": ["view", "export"],
}

DEFAULT_ROLE_PERMISSIONS: dict[str, PermissionsMap] = {
    "Admin": ADMIN_PERMISSIONS,
    "Staff": STAFF_PERMISSIONS,
    "Teacher": TEACHER_PERMISSIONS,
}

# Reserved role: hidden from Role Management; cannot be created, updated, or deleted there.
ROLE_MANAGEMENT_RESERVED_NAMES: frozenset[str] = frozenset({"Admin"})

# User accounts with this role cannot be removed from User Management.
USER_MANAGEMENT_NON_DELETABLE_ROLE_NAMES: frozenset[str] = frozenset({"Admin"})
