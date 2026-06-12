import { useCrudTable } from './useCrudTable'
import { userService } from '~/services/userService'
import type { TableQuery, UserCreatePayload, UserRow, UserUpdatePayload } from '~/types/api'

export function useUsers(initialQuery: TableQuery = {}) {
  return useCrudTable<UserRow, UserCreatePayload, UserUpdatePayload>(userService, initialQuery)
}
