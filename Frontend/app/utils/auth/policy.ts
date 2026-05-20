import {
  ADMIN_WILDCARD,
  ALL_PAGES,
  type Permission,
} from '~/utils/auth/permissions'

/** Maps frontend permission tokens to backend `pageAccess` entries (`resource:action`). */
const LEGACY_PERMISSION_MAP: Record<string, string> = {
  'dashboard:view': 'dashboard:view',

  'category:view': 'categories:view',
  'category:create': 'categories:create',
  'category:update': 'categories:update',
  'category:delete': 'categories:delete',

  'courses:view': 'courses:view',
  'courses:create': 'courses:create',
  'courses:update': 'courses:update',
  'courses:delete': 'courses:delete',

  'levels:view': 'levels:view',
  'levels:create': 'levels:create',
  'levels:update': 'levels:update',
  'levels:delete': 'levels:delete',

  'allclass:view': 'classes:view',
  'allclass:create': 'classes:create',
  'allclass:update': 'classes:update',
  'allclass:delete': 'classes:delete',
  'allclass:view-roster': 'classes:view_roster',
  'allclass:remove-student': 'classes:remove_student',
  'allclass:continue-payment': 'classes:continue_payment',

  'allstudent:view': 'students:view',
  'allstudent:create': 'students:create',
  'allstudent:update': 'students:update',
  'allstudent:delete': 'students:delete',
  'allstudent:view-enrollments': 'students:view_enrollments',
  'allstudent:delete-enrollment': 'students:delete_enrollment',
  'allstudent:preview-certificate': 'students:preview_certificate',
  'allstudent:download-certificate': 'students:download_certificate',

  'report:view': 'reports:view',
  'report:export': 'reports:export',
  'report:preview-invoice': 'reports:preview_invoice',

  'comission:view': 'commissions:view',
  'comission:export': 'commissions:export',

  'finance:view': 'finance:view',
  'finance:update': 'finance:update',
  'finance:export': 'finance:export',

  'history:view': 'history:view',
  'history:export': 'history:export',
  'history:detail': 'history:detail',

  'settings:user-management:view': 'user-management:view',
  'settings:user-management:create': 'user-management:create',
  'settings:user-management:update': 'user-management:update',
  'settings:user-management:delete': 'user-management:delete',
  'settings:user-management:edit': 'user-management:update',

  'settings:role-management:view': 'role-management:view',
  'settings:role-management:create': 'role-management:create',
  'settings:role-management:update': 'role-management:update',
  'settings:role-management:delete': 'role-management:delete',
  'settings:role-management:edit': 'role-management:update',
}

export function normalizePermissionToken(permission: Permission | string): string {
  return LEGACY_PERMISSION_MAP[permission] || permission
}

export function hasPermission(
  permissions: string[] | undefined,
  permission: Permission | string,
): boolean {
  const tokens = Array.isArray(permissions) ? permissions : []
  if (tokens.includes(ADMIN_WILDCARD) || tokens.includes(ALL_PAGES)) return true
  const normalized = normalizePermissionToken(permission)
  return tokens.includes(normalized)
}
