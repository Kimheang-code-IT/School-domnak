import type { Pinia } from 'pinia'
import { isLiveBackendApi, isUiOnlyMode } from '~/composables/useBackendMode'
import { useAuthStore } from '~/stores/auth'
import { useAuthSessionManager } from '~/utils/auth/session-manager'
import { normalizeListQuery } from '~/utils/constants/apiPagination'

/**
 * Standard API Fetching Composable
 * ───────────────────────────────────────
 * Use this for all backend requests. It automatically:
 * 1. Attaches the Bearer token (if user is logged in)
 * 2. Handles global error notifications
 * 3. Supports standard REST methods
 */
export function useApi() {
    const toast = useToast()
    const config = useRuntimeConfig()
    // Capture Pinia during setup (safe for debounced/async API calls).
    const pinia = useNuxtApp().$pinia as Pinia
    const authStore = useAuthStore(pinia)
    const session = useAuthSessionManager(pinia)

    // Base URL from nuxt.config (fallback to localhost for dev)
    const baseURL = config.public.apiBase || 'http://localhost:8000/api/v1'

    type ApiErrorPayload = {
        message?: string
        code?: string
        traceId?: string
        errors?: Record<string, string[]>
    }

    const mapApiErrorMessage = (status: number, payload: ApiErrorPayload | null | undefined) => {
        if (payload?.message) return payload.message
        if (status >= 500) return 'Server error. Please try again later.'
        if (status === 401) return 'Unauthorized access.'
        if (status === 403) return 'You do not have permission for this action.'
        if (status === 404) return 'Requested resource was not found.'
        return 'Something went wrong'
    }

    const isAbortError = (err: unknown) => {
        const e = err as { name?: string; message?: string; cause?: { name?: string; message?: string } }
        const message = String(e?.message || e?.cause?.message || '').toLowerCase()
        return (
            e?.name === 'AbortError' ||
            e?.cause?.name === 'AbortError' ||
            message.includes('aborted') ||
            message.includes('abort')
        )
    }

    const inFlight = useState<Map<string, Promise<unknown>>>('api-in-flight', () => new Map())
    const toRequestKey = (method: string, url: string, query?: unknown) => `${method}:${url}:${JSON.stringify(query || {})}`

    const fetch = async <T>(url: string, options: Record<string, unknown> = {}) => {
        if (isUiOnlyMode(config)) {
            throw new Error('UI-only mode is enabled; real API requests are disabled.')
        }

        const bearerToken = session.accessToken.value || authStore.token || null

        const method = String(options.method || 'GET').toUpperCase()
        const key = toRequestKey(method, url, options.query)
        const dedupe = Boolean(options.dedupe)
        const skipAuthRefresh = Boolean(options.skipAuthRefresh)
        const silent = Boolean(options.silent)
        if (dedupe && inFlight.value.has(key)) {
            return (await inFlight.value.get(key)) as T
        }
        const query = options.query != null ? normalizeListQuery(options.query as Record<string, unknown>) : options.query
        const requestOptions = {
          baseURL,
          ...options,
          ...(query !== undefined ? { query } : {}),
          headers: {
            ...(bearerToken ? { Authorization: `Bearer ${bearerToken}` } : {}),
            ...((options.headers as Record<string, string> | undefined) || {})
          }
        }
        delete (requestOptions as Record<string, unknown>).skipAuthRefresh
        delete (requestOptions as Record<string, unknown>).silent
        delete (requestOptions as Record<string, unknown>).dedupe

        const execute = () => $fetch<T>(url, requestOptions)
        const request = execute()
        if (dedupe) inFlight.value.set(key, request as unknown as Promise<unknown>)

        try {
            return await request
        } catch (err: unknown) {
            if (isAbortError(err)) {
                throw err
            }
            const fetchErr = err as { name?: string; response?: { status?: number; _data?: ApiErrorPayload } }
            if (fetchErr?.response?.status === 401 && !skipAuthRefresh) {
              const refreshed = await session.refreshAccessToken()
              if (refreshed) {
                ;(requestOptions.headers as Record<string, string>).Authorization = `Bearer ${session.accessToken.value}`
                return await execute()
              }
              session.clearSession()
              authStore.clearAuth()
              await navigateTo('/login')
              throw err
            }
            if (!silent && fetchErr?.name === 'FetchError') {
              const statusCode = fetchErr.response?.status
              if (statusCode) {
                toast.add({
                  title: `API Error: ${statusCode}`,
                  description: mapApiErrorMessage(statusCode, fetchErr.response?._data),
                  color: 'error'
                })
              } else {
                toast.add({ title: 'Connection Error', description: 'Could not reach the server', color: 'error' })
              }
            }
            throw err
        } finally {
            if (dedupe) inFlight.value.delete(key)
        }
    }

    return {
        get: <T>(url: string, opt?: Record<string, unknown>) => fetch<T>(url, { method: 'GET', ...opt }),
        post: <T>(url: string, body: unknown, opt?: Record<string, unknown>) => fetch<T>(url, { method: 'POST', body, ...opt }),
        put: <T>(url: string, body: unknown, opt?: Record<string, unknown>) => fetch<T>(url, { method: 'PUT', body, ...opt }),
        patch: <T>(url: string, body: unknown, opt?: Record<string, unknown>) => fetch<T>(url, { method: 'PATCH', body, ...opt }),
        delete: <T>(url: string, opt?: Record<string, unknown>) => fetch<T>(url, { method: 'DELETE', ...opt }),
    }
}
