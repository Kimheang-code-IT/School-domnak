import type { PermissionsMap } from './auth'

export type RoleRow = {
  id: number
  name: string
  permissions: PermissionsMap
  createdAt?: string | null
}

export type RolePayload = {
  name: string
  permissions: PermissionsMap
}

export type RoleUpdatePayload = Partial<RolePayload>
