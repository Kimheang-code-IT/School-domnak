import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  ACCESS_TOKEN_STORAGE_KEY,
  AUTH_USER_STORAGE_KEY,
  REFRESH_TOKEN_STORAGE_KEY,
  setStoredAccessToken,
  setStoredRefreshToken
} from '~/services/apiClient'
import { authService } from '~/services/authService'
import type { AuthUser, LoginPayload, PermissionsMap } from '~/types/auth'
import { hasPermission as hasPermissionByPolicy } from '~/utils/auth/policy'

type StoreAuthUser = Partial<AuthUser> & {
  name: string
  email: string
  avatar?: string
  pageAccess?: string[]
}

function readStorage(key: string) {
  if (!import.meta.client) return null
  return localStorage.getItem(key)
}

function writeStorage(key: string, value: string | null) {
  if (!import.meta.client) return
  if (value) localStorage.setItem(key, value)
  else localStorage.removeItem(key)
}

function readStoredUser() {
  const raw = readStorage(AUTH_USER_STORAGE_KEY)
  if (!raw) return null

  try {
    return JSON.parse(raw) as StoreAuthUser
  } catch {
    writeStorage(AUTH_USER_STORAGE_KEY, null)
    return null
  }
}

export const useBackendAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(readStorage(ACCESS_TOKEN_STORAGE_KEY))
  const refreshToken = ref<string | null>(readStorage(REFRESH_TOKEN_STORAGE_KEY))
  const user = ref<StoreAuthUser | null>(readStoredUser())
  const loading = ref(false)

  const permissions = computed<PermissionsMap>(() => user.value?.permissions || {})
  const pageAccess = computed(() =>
    [
      ...(user.value?.pageAccess || []),
      ...Object.entries(permissions.value).flatMap(([page, actions]) =>
      actions.map(action => `${page}:${action}`)
    )
    ]
  )
  const isLoggedIn = computed(() => Boolean(accessToken.value && user.value))

  function hydrateFromStorage() {
    if (!import.meta.client) return

    accessToken.value = readStorage(ACCESS_TOKEN_STORAGE_KEY)
    refreshToken.value = readStorage(REFRESH_TOKEN_STORAGE_KEY)
    user.value = readStoredUser()
  }

  function setSession(nextAccessToken: string, nextRefreshToken: string, nextUser: StoreAuthUser) {
    accessToken.value = nextAccessToken
    refreshToken.value = nextRefreshToken
    user.value = nextUser
    setStoredAccessToken(nextAccessToken)
    setStoredRefreshToken(nextRefreshToken)
    writeStorage(AUTH_USER_STORAGE_KEY, JSON.stringify(nextUser))
  }

  function clearAuth() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    setStoredAccessToken(null)
    setStoredRefreshToken(null)
    writeStorage(AUTH_USER_STORAGE_KEY, null)
  }

  function setAccessToken(token: string | null) {
    accessToken.value = token
    setStoredAccessToken(token)
  }

  function setRefreshToken(token: string | null) {
    refreshToken.value = token
    setStoredRefreshToken(token)
  }

  function setAuth(nextAccessToken: string, nextUser: StoreAuthUser, nextRefreshToken?: string | null) {
    setSession(nextAccessToken, nextRefreshToken || refreshToken.value || '', nextUser)
  }

  function hasPermission(page: string, action?: string) {
    if (action) {
      return hasPermissionByPolicy(pageAccess.value, `${page}:${action}`)
    }
    return hasPermissionByPolicy(pageAccess.value, page)
  }

  async function login(payload: LoginPayload) {
    loading.value = true
    try {
      const response = await authService.login(payload)
      setSession(response.accessToken, response.refreshToken, response.user)
      return response.user
    } finally {
      loading.value = false
    }
  }

  async function refreshAccessToken() {
    if (!refreshToken.value) return null
    const response = await authService.refresh(refreshToken.value)
    accessToken.value = response.accessToken
    setStoredAccessToken(response.accessToken)
    return response.accessToken
  }

  async function fetchMe() {
    const currentUser = await authService.me()
    user.value = currentUser
    writeStorage(AUTH_USER_STORAGE_KEY, JSON.stringify(currentUser))
    return currentUser
  }

  async function logout() {
    const token = refreshToken.value
    if (token) {
      await authService.logout(token).catch(() => undefined)
    }
    clearAuth()
  }

  return {
    accessToken,
    refreshToken,
    token: accessToken,
    user,
    permissions,
    pageAccess,
    loading,
    isLoggedIn,
    hydrateFromStorage,
    hasPermission,
    login,
    logout,
    clearAuth,
    setAccessToken,
    setRefreshToken,
    setAuth,
    setSession,
    refreshAccessToken,
    fetchMe
  }
})
