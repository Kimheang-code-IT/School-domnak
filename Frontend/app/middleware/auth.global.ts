import { isUiOnlyMode } from '~/composables/useBackendMode'
import { authService } from '~/services/authService'
import { resolveRoutePermission } from '~/utils/auth/routes'

const AUTH_PUBLIC_PATHS = ['/login', '/register-admin']

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

  if (['app-session', 'mock-access-token', 'verifiable-pdme-session-token'].includes(String(auth.token || ''))) {
    auth.clearAuth()
  }

  if (!auth.isLoggedIn) {
    if (to.path === '/register-admin') {
      try {
        const status = await authService.setupStatus()
        if (!status.needsSetup) {
          return navigateTo('/login')
        }
      } catch {
        return navigateTo('/login')
      }
      return
    }

    if (to.path === '/login') {
      try {
        const status = await authService.setupStatus()
        if (status.needsSetup) {
          return navigateTo('/register-admin')
        }
      } catch {
        // Allow login if setup status cannot be checked
      }
      return
    }

    if (!AUTH_PUBLIC_PATHS.includes(to.path)) {
      try {
        const status = await authService.setupStatus()
        if (status.needsSetup) {
          return navigateTo('/register-admin')
        }
      } catch {
        // Fall through to login
      }
      return navigateTo('/login')
    }
    return
  }

  if (auth.isLoggedIn && AUTH_PUBLIC_PATHS.includes(to.path)) {
    return navigateTo('/')
  }

  if (auth.isLoggedIn && !AUTH_PUBLIC_PATHS.includes(to.path)) {
    const routeRule = resolveRoutePermission(to.path)
    if (routeRule && !auth.hasPermission(routeRule.permission)) {
      return navigateTo('/')
    }
  }
})
