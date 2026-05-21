PermissionsMap = dict[str, list[str]]

# Keep in sync with Frontend `app/utils/auth/permissionCatalog.ts` (ROLE_PERMISSION_CATALOG).
ROLE_PERMISSION_CATALOG: PermissionsMap = {
    "dashboard": ["view"],
    "categories": ["view", "create", "update", "delete"],
    "classes": [
        "view",
        "create",
        "update",
        "delete",
        "export",
        "view_roster",
        "remove_student",
        "continue_payment",
    ],
    "students": [
        "view",
        "create",
        "update",
        "delete",
        "export",
        "view_enrollments",
        "delete_enrollment",
        "preview_certificate",
        "download_certificate",
    ],
    "reports": ["view", "export", "preview_invoice"],
    "finance": ["view", "update", "export"],
    "courses": ["view", "create", "update", "delete"],
    "levels": ["view", "create", "update", "delete"],
    "commissions": ["view", "export"],
    "history": ["view", "export", "detail"],
    "user-management": ["view", "create", "update", "delete"],
    "role-management": ["view", "create", "update", "delete"],
}


def catalog_pages() -> list[str]:
    return sorted(ROLE_PERMISSION_CATALOG.keys())


def catalog_actions_union() -> list[str]:
    actions: set[str] = set()
    for page_actions in ROLE_PERMISSION_CATALOG.values():
        actions.update(page_actions)
    return sorted(actions)


def sanitize_role_permissions(permissions: PermissionsMap | None) -> PermissionsMap:
    """Keep only page/action pairs defined in ROLE_PERMISSION_CATALOG."""
    if not permissions:
        return {}
    sanitized: PermissionsMap = {}
    for page, actions in permissions.items():
        key = str(page or "").strip()
        allowed = ROLE_PERMISSION_CATALOG.get(key)
        if not allowed:
            continue
        allowed_set = set(allowed)
        kept = []
        for action in actions or []:
            name = str(action or "").strip()
            if name in allowed_set and name not in kept:
                kept.append(name)
        if kept:
            sanitized[key] = kept
    return sanitized


def full_catalog_permissions() -> PermissionsMap:
    return {page: list(actions) for page, actions in ROLE_PERMISSION_CATALOG.items()}


ADMIN_PERMISSIONS: PermissionsMap = full_catalog_permissions()

STAFF_PERMISSIONS: PermissionsMap = sanitize_role_permissions(
    {
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
)

TEACHER_PERMISSIONS: PermissionsMap = sanitize_role_permissions(
    {
        "dashboard": ["view"],
        "classes": ["view", "view_roster"],
        "students": ["view", "view_enrollments"],
        "commissions": ["view", "export"],
    }
)

DEFAULT_ROLE_PERMISSIONS: dict[str, PermissionsMap] = {
    "Admin": ADMIN_PERMISSIONS,
    "Staff": STAFF_PERMISSIONS,
    "Teacher": TEACHER_PERMISSIONS,
}

# Reserved role: hidden from Role Management; cannot be created, updated, or deleted there.
ROLE_MANAGEMENT_RESERVED_NAMES: frozenset[str] = frozenset({"Admin"})

# User accounts with this role cannot be removed from User Management.
USER_MANAGEMENT_NON_DELETABLE_ROLE_NAMES: frozenset[str] = frozenset({"Admin"})
