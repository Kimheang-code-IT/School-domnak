export type PermissionsMap = Record<string, string[]>

export type AuthUser = {
  id: number
  name: string
  email: string
  role?: string | null
  permissions: PermissionsMap
}

export type LoginPayload = {
  email: string
  password: string
}

export type LoginResponse = {
  accessToken: string
  refreshToken: string
  tokenType: 'bearer' | string
  user: AuthUser
}

export type RefreshTokenPayload = {
  refreshToken: string
}

export type RefreshTokenResponse = {
  accessToken: string
  tokenType: 'bearer' | string
}
