import { apiDelete, apiGet, apiPost, apiPut } from './apiClient'
import type {
  Id,
  TableQuery,
  TableResponse,
  UserCreatePayload,
  UserRow,
  UserUpdatePayload
} from '~/types/api'

export const userService = {
  list(query?: TableQuery) {
    return apiGet<TableResponse<UserRow>>('/users', query)
  },

  create(payload: UserCreatePayload) {
    return apiPost<UserRow, UserCreatePayload>('/users', payload)
  },

  update(id: Id, payload: UserUpdatePayload) {
    return apiPut<UserRow, UserUpdatePayload>(`/users/${id}`, payload)
  },

  remove(id: Id) {
    return apiDelete<{ success: boolean; message: string }>(`/users/${id}`)
  }
}
