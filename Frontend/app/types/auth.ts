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

export type SetupPayload = {
  name: string
  email: string
  password: string
}

export type SetupStatus = {
  needsSetup: boolean
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
