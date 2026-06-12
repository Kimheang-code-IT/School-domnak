import type { TableQuery } from '~/types/api'

export const ACCESS_TOKEN_STORAGE_KEY = 'school_access_token'
export const REFRESH_TOKEN_STORAGE_KEY = 'school_refresh_token'
export const AUTH_USER_STORAGE_KEY = 'school_auth_user'

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

type ApiClientOptions<TBody = unknown> = {
  method?: HttpMethod
  query?: TableQuery
  body?: TBody
  headers?: HeadersInit
  requireAuth?: boolean
}

type FetchBody = Record<string, unknown> | BodyInit | null | undefined

function getBaseURL() {
  const config = useRuntimeConfig()
  return config.public.apiBase || 'http://localhost:8000/api/v1'
}

export function getStoredAccessToken() {
  if (!import.meta.client) return null
  return localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY)
}

export function setStoredAccessToken(token: string | null) {
  if (!import.meta.client) return
  if (token) localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token)
  else localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY)
}

export function getStoredRefreshToken() {
  if (!import.meta.client) return null
  return localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)
}

export function setStoredRefreshToken(token: string | null) {
  if (!import.meta.client) return
  if (token) localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token)
  else localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY)
}

export async function apiClient<TResponse, TBody = unknown>(
  path: string,
  options: ApiClientOptions<TBody> = {}
) {
  const token = getStoredAccessToken()
  const headers = new Headers(options.headers)

  if (options.requireAuth !== false && token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  return await $fetch<TResponse>(path, {
    baseURL: getBaseURL(),
    method: options.method || 'GET',
    query: options.query,
    body: options.body as FetchBody,
    headers
  })
}

export const apiGet = <TResponse>(path: string, query?: TableQuery) =>
  apiClient<TResponse>(path, { method: 'GET', query })

export const apiPost = <TResponse, TBody>(path: string, body: TBody, requireAuth = true) =>
  apiClient<TResponse, TBody>(path, { method: 'POST', body, requireAuth })

export const apiPut = <TResponse, TBody>(path: string, body: TBody) =>
  apiClient<TResponse, TBody>(path, { method: 'PUT', body })

export const apiDelete = <TResponse>(path: string) =>
  apiClient<TResponse>(path, { method: 'DELETE' })
