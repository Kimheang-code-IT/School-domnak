import { isUiOnlyMode } from '~/composables/useBackendMode'
import { resolveRoutePermission } from '~/utils/auth/routes'

/** UI-only mode: ensure a fixed app session so menus and permissions resolve (admin:*). */
const DEFAULT_SESSION = {
  name: 'App User',
  email: 'app@local',
  avatar: 'https://ui-avatars.com/api/?name=App+User&background=6366f1&color=fff',
  role: 'admin',
  pageAccess: ['admin:*']
}

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

  if (!auth.isLoggedIn && to.path !== '/login') {
    return navigateTo('/login')
  }

  if (auth.isLoggedIn && to.path === '/login') {
    return navigateTo('/')
  }

  if (auth.isLoggedIn && to.path !== '/login') {
    const routeRule = resolveRoutePermission(to.path)
    if (routeRule && !auth.hasPermission(routeRule.permission)) {
      throw createError({
        statusCode: 403,
        statusMessage: 'Forbidden',
        message: 'You do not have permission to access this page.',
        fatal: true,
      })
    }
  }
})
