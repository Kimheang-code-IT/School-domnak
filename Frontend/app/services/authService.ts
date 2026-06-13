import { apiClient, apiGet, apiPost } from './apiClient'
import type {
  AuthUser,
  LoginPayload,
  LoginResponse,
  RefreshTokenPayload,
  RefreshTokenResponse,
  RegisterAdminPayload,
  SetupStatusResponse
} from '~/types/auth'

export const authService = {
  setupStatus() {
    return apiClient<SetupStatusResponse>('/auth/setup-status', { requireAuth: false })
  },

  registerAdmin(payload: RegisterAdminPayload) {
    return apiPost<{ success: boolean; message: string }, RegisterAdminPayload>(
      '/auth/register-admin',
      payload,
      false
    )
  },

  login(payload: LoginPayload) {
    return apiPost<LoginResponse, LoginPayload>('/auth/login', payload, false)
  },

  refresh(refreshToken: string) {
    const payload: RefreshTokenPayload = { refreshToken }
    return apiPost<RefreshTokenResponse, RefreshTokenPayload>('/auth/refresh', payload, false)
  },

  logout(refreshToken: string) {
    const payload: RefreshTokenPayload = { refreshToken }
    return apiPost<{ success: boolean; message: string }, RefreshTokenPayload>('/auth/logout', payload, false)
  },

  me() {
    return apiGet<AuthUser>('/auth/me')
  }
}
