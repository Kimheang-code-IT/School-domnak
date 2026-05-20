import { apiDelete, apiGet, apiPost, apiPut } from './apiClient'
import type { Id, TableQuery, TableResponse } from '~/types/api'
import type { RolePayload, RoleRow, RoleUpdatePayload } from '~/types/role'

export const roleService = {
  list(query?: TableQuery) {
    return apiGet<TableResponse<RoleRow>>('/roles', query)
  },

  create(payload: RolePayload) {
    return apiPost<RoleRow, RolePayload>('/roles', payload)
  },

  update(id: Id, payload: RoleUpdatePayload) {
    return apiPut<RoleRow, RoleUpdatePayload>(`/roles/${id}`, payload)
  },

  remove(id: Id) {
    return apiDelete<{ success: boolean; message: string }>(`/roles/${id}`)
  }
}
