import { useCrudTable } from './useCrudTable'
import { roleService } from '~/services/roleService'
import type { TableQuery } from '~/types/api'
import type { RolePayload, RoleRow, RoleUpdatePayload } from '~/types/role'

export function useRoles(initialQuery: TableQuery = {}) {
  return useCrudTable<RoleRow, RolePayload, RoleUpdatePayload>(roleService, initialQuery)
}
