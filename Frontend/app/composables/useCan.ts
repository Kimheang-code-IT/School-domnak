import { PERMISSIONS, type Permission } from '~/utils/auth/permissions'

/**
 * Page/action permission checks for UI gating.
 * Tokens are normalized to backend `resource:action` via auth policy.
 */
export function useCan() {
  const auth = useAuthStore()

  function can(permission: Permission | string): boolean {
    return auth.hasPermission(permission)
  }

  return {
    can,
    auth,
    PERMISSIONS,
  }
}
