/**
 * Frontend permission tokens (legacy `page:action` shape).
 * Mapped to backend `resource:action` via `utils/auth/policy.ts` (`LEGACY_PERMISSION_MAP`).
 *
 * Settings (`settings:*`) are admin-only: only the Admin role receives
 * `user-management:*` and `role-management:*` from the API.
 */
export const PERMISSIONS = {
  dashboardView: 'dashboard:view',

  categoryView: 'category:view',
  categoryCreate: 'category:create',
  categoryUpdate: 'category:update',
  categoryDelete: 'category:delete',

  coursesView: 'courses:view',
  coursesCreate: 'courses:create',
  coursesUpdate: 'courses:update',
  coursesDelete: 'courses:delete',

  levelsView: 'levels:view',
  levelsCreate: 'levels:create',
  levelsUpdate: 'levels:update',
  levelsDelete: 'levels:delete',

  allClassView: 'allclass:view',
  allClassCreate: 'allclass:create',
  allClassUpdate: 'allclass:update',
  allClassDelete: 'allclass:delete',
  allClassViewRoster: 'allclass:view-roster',
  allClassRemoveStudent: 'allclass:remove-student',
  allClassContinuePayment: 'allclass:continue-payment',

  allStudentView: 'allstudent:view',
  allStudentCreate: 'allstudent:create',
  allStudentUpdate: 'allstudent:update',
  allStudentDelete: 'allstudent:delete',
  allStudentViewEnrollments: 'allstudent:view-enrollments',
  allStudentDeleteEnrollment: 'allstudent:delete-enrollment',
  allStudentPreviewCertificate: 'allstudent:preview-certificate',
  allStudentDownloadCertificate: 'allstudent:download-certificate',

  reportView: 'report:view',
  reportExport: 'report:export',
  reportPreviewInvoice: 'report:preview-invoice',

  comissionView: 'comission:view',
  comissionExport: 'comission:export',

  financeView: 'finance:view',
  financeUpdate: 'finance:update',
  financeExport: 'finance:export',

  historyView: 'history:view',
  historyExport: 'history:export',
  historyDetail: 'history:detail',

  /** User accounts — Admin role only */
  settingsUserView: 'settings:user-management:view',
  settingsUserCreate: 'settings:user-management:create',
  settingsUserUpdate: 'settings:user-management:update',
  settingsUserDelete: 'settings:user-management:delete',

  /** Role policies — Admin role only */
  settingsRoleView: 'settings:role-management:view',
  settingsRoleCreate: 'settings:role-management:create',
  settingsRoleUpdate: 'settings:role-management:update',
  settingsRoleDelete: 'settings:role-management:delete',
} as const

export type Permission = (typeof PERMISSIONS)[keyof typeof PERMISSIONS]

export const ADMIN_WILDCARD = 'admin:*'
export const ALL_PAGES = 'ALL_PAGES'

/** Permissions granted only to the Admin role (settings pages). */
export const ADMIN_ONLY_PERMISSIONS: readonly Permission[] = [
  PERMISSIONS.settingsUserView,
  PERMISSIONS.settingsUserCreate,
  PERMISSIONS.settingsUserUpdate,
  PERMISSIONS.settingsUserDelete,
  PERMISSIONS.settingsRoleView,
  PERMISSIONS.settingsRoleCreate,
  PERMISSIONS.settingsRoleUpdate,
  PERMISSIONS.settingsRoleDelete,
]

export function isAdminOnlyPermission(permission: Permission | string): boolean {
  return (ADMIN_ONLY_PERMISSIONS as readonly string[]).includes(permission)
}

export function isSettingsPath(path: string): boolean {
  return path.startsWith('/settings')
}
