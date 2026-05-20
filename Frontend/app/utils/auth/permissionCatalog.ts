/**
 * Canonical permission pages/actions (aligned with backend `ADMIN_PERMISSIONS`).
 * Role form uses this plus permissions found on loaded roles.
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

/** Pages + actions for permission-tree: catalog merged with permissions on existing roles. */
export function mergeRolePermissionOptions(
  roles: Array<{ permissions?: Record<string, string[]> }>,
): { pages: string[]; actions: string[] } {
  const pages = new Set(catalogPermissionPages())
  const actions = new Set(catalogPermissionActionsUnion())

  for (const role of roles) {
    const perms = role.permissions
    if (!perms || typeof perms !== 'object') continue
    for (const [page, list] of Object.entries(perms)) {
      const key = String(page || '').trim()
      if (key) pages.add(key)
      if (Array.isArray(list)) {
        for (const action of list) {
          const a = String(action || '').trim()
          if (a) actions.add(a)
        }
      }
    }
  }

  return {
    pages: [...pages].sort((a, b) => a.localeCompare(b)),
    actions: [...actions].sort((a, b) => a.localeCompare(b)),
  }
}
