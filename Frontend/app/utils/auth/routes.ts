import { PERMISSIONS, type Permission } from '~/utils/auth/permissions'

export type RoutePermissionEntry = {
  home: string
  match: (path: string) => boolean
  permission: Permission
}

export const routePermissionMap: RoutePermissionEntry[] = [
  { home: '/', match: (path) => path === '/', permission: PERMISSIONS.dashboardView },
  { home: '/category', match: (path) => path.startsWith('/category'), permission: PERMISSIONS.categoryView },
  { home: '/courses', match: (path) => path.startsWith('/courses'), permission: PERMISSIONS.coursesView },
  { home: '/levels', match: (path) => path.startsWith('/levels'), permission: PERMISSIONS.levelsView },
  { home: '/allclass', match: (path) => path.startsWith('/allclass'), permission: PERMISSIONS.allClassView },
  { home: '/allstudent', match: (path) => path.startsWith('/allstudent'), permission: PERMISSIONS.allStudentView },
  { home: '/report', match: (path) => path.startsWith('/report'), permission: PERMISSIONS.reportView },
  { home: '/comission', match: (path) => path.startsWith('/comission'), permission: PERMISSIONS.comissionView },
  { home: '/finance', match: (path) => path.startsWith('/finance'), permission: PERMISSIONS.financeView },
  { home: '/history', match: (path) => path.startsWith('/history'), permission: PERMISSIONS.historyView },
  {
    home: '/settings/user-management',
    match: (path) => path.startsWith('/settings/user-management'),
    permission: PERMISSIONS.settingsUserView,
  },
  {
    home: '/settings/role-management',
    match: (path) => path.startsWith('/settings/role-management'),
    permission: PERMISSIONS.settingsRoleView,
  },
]

export function resolveRoutePermission(path: string): RoutePermissionEntry | undefined {
  return routePermissionMap.find((entry) => entry.match(path))
}

export function useRoutePermissionMap() {
  return routePermissionMap
}
