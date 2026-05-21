/**
 * Canonical permission pages/actions for Role Management.
 * Keep in sync with backend `app/core/permissions.py` (`ROLE_PERMISSION_CATALOG`).
 */
export const ROLE_PERMISSION_CATALOG: Record<string, readonly string[]> = {
  dashboard: ['view'],
  categories: ['view', 'create', 'update', 'delete'],
  classes: [
    'view',
    'create',
    'update',
    'delete',
    'export',
    'view_roster',
    'remove_student',
    'continue_payment',
  ],
  students: [
    'view',
    'create',
    'update',
    'delete',
    'export',
    'view_enrollments',
    'delete_enrollment',
    'preview_certificate',
    'download_certificate',
  ],
  reports: ['view', 'export', 'preview_invoice'],
  finance: ['view', 'update', 'export'],
  courses: ['view', 'create', 'update', 'delete'],
  levels: ['view', 'create', 'update', 'delete'],
  commissions: ['view', 'export'],
  history: ['view', 'export', 'detail'],
  'user-management': ['view', 'create', 'update', 'delete'],
  'role-management': ['view', 'create', 'update', 'delete'],
}

export function catalogPermissionPages(): string[] {
  return Object.keys(ROLE_PERMISSION_CATALOG).sort((a, b) => a.localeCompare(b))
}

export function catalogPermissionActionsUnion(): string[] {
  const actions = new Set<string>()
  for (const list of Object.values(ROLE_PERMISSION_CATALOG)) {
    for (const action of list) actions.add(action)
  }
  return [...actions].sort((a, b) => a.localeCompare(b))
}

/** Options for the role permission tree (catalog only). */
export function rolePermissionOptions(): {
  pages: string[]
  actions: string[]
  catalog: Record<string, readonly string[]>
} {
  return {
    pages: catalogPermissionPages(),
    actions: catalogPermissionActionsUnion(),
    catalog: ROLE_PERMISSION_CATALOG,
  }
}

/** Drop any page/action not listed in ROLE_PERMISSION_CATALOG. */
export function sanitizeRolePermissions(
  permissions?: Record<string, string[]> | null,
): Record<string, string[]> {
  if (!permissions || typeof permissions !== 'object') return {}
  const sanitized: Record<string, string[]> = {}
  for (const [page, actions] of Object.entries(permissions)) {
    const key = String(page || '').trim()
    const allowed = ROLE_PERMISSION_CATALOG[key]
    if (!allowed) continue
    const allowedSet = new Set(allowed)
    const kept: string[] = []
    for (const action of actions || []) {
      const name = String(action || '').trim()
      if (allowedSet.has(name) && !kept.includes(name)) kept.push(name)
    }
    if (kept.length) sanitized[key] = kept
  }
  return sanitized
}

/** Flatten catalog permissions to `page:action` tokens for the permission tree. */
export function permissionsToPageAccessTokens(
  permissions?: Record<string, string[]> | null,
): string[] {
  const sanitized = sanitizeRolePermissions(permissions)
  return Object.entries(sanitized).flatMap(([page, actions]) =>
    actions.map((action) => `${page}:${action}`),
  )
}

/** @deprecated Use `rolePermissionOptions()` — catalog only, no merge with legacy DB values. */
export function mergeRolePermissionOptions(
  _roles: Array<{ permissions?: Record<string, string[]> }> = [],
): { pages: string[]; actions: string[]; catalog: Record<string, readonly string[]> } {
  return rolePermissionOptions()
}
