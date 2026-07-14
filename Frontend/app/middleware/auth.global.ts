import { isUiOnlyMode } from '~/composables/useBackendMode'
import { authService } from '~/services/authService'
import { resolveRoutePermission, routePermissionMap } from '~/utils/auth/routes'

/** UI-only mode: ensure a fixed app session so menus and permissions resolve (admin:*). */
const DEFAULT_SESSION = {
  name: 'App User',
  email: 'app@local',
  avatar: 'https://ui-avatars.com/api/?name=App+User&background=6366f1&color=fff',
  role: 'admin',
  pageAccess: ['admin:*']
}

const PUBLIC_AUTH_PATHS = new Set(['/login', '/setup'])

export default defineNuxtRouteMiddleware(async (to) => {
  const config = useRuntimeConfig()
  const auth = useAuthStore()

  if (isUiOnlyMode(config)) {
    if (!auth.isLoggedIn) {
      auth.setAuth('app-session', { ...DEFAULT_SESSION }, '')
    }
    return
  }

  if (import.meta.server) return

  auth.hydrateFromStorage()

  const needsSetup = useState<boolean | null>('auth-needs-setup', () => null)
  if (needsSetup.value === null) {
    try {
      const status = await authService.setupStatus()
      needsSetup.value = Boolean(status.needsSetup)
    } catch {
      needsSetup.value = false
    }
  }

  if (needsSetup.value) {
    if (to.path !== '/setup') {
      return navigateTo('/setup')
    }
    return
  }

  if (to.path === '/setup') {
    return navigateTo('/login')
  }

  const permissionsSynced = useState('auth-permissions-synced', () => false)
  if (auth.isLoggedIn && !permissionsSynced.value) {
    permissionsSynced.value = true
    try {
      await auth.fetchMe()
    } catch {
      permissionsSynced.value = false
    }
  }

  if (['app-session', 'mock-access-token', 'verifiable-pdme-session-token'].includes(String(auth.token || ''))) {
    auth.clearAuth()
  }

  if (!auth.isLoggedIn && !PUBLIC_AUTH_PATHS.has(to.path)) {
    return navigateTo('/login')
  }

  if (auth.isLoggedIn && !auth.pageAccess.length && to.path !== '/login') {
    auth.clearAuth()
    return navigateTo('/login?error=no_role')
  }

  if (auth.isLoggedIn && to.path === '/login') {
    const homeRule = resolveRoutePermission('/')
    if (homeRule && auth.hasPermission(homeRule.permission)) {
      return navigateTo('/')
    }
    const firstAllowed = routePermissionMap.find((entry) => auth.hasPermission(entry.permission))
    return navigateTo(firstAllowed?.home || '/login?error=no_permissions')
  }

  if (auth.isLoggedIn && to.path !== '/login') {
    const routeRule = resolveRoutePermission(to.path)
    if (routeRule && !auth.hasPermission(routeRule.permission)) {
      const firstAllowed = routePermissionMap.find((entry) => auth.hasPermission(entry.permission))
      if (firstAllowed) {
        return navigateTo(firstAllowed.home)
      }
      auth.clearAuth()
      return navigateTo('/login?error=no_permissions')
    }
  }
})
