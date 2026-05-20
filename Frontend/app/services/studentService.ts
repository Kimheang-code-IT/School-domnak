import { apiDelete, apiGet, apiPost, apiPut } from './apiClient'
import type { Id, TableQuery, TableResponse } from '~/types/api'
import type { StudentPayload, StudentRow, StudentUpdatePayload } from '~/types/student'

export const studentService = {
  list(query?: TableQuery) {
    return apiGet<TableResponse<StudentRow>>('/students', query)
  },

  create(payload: StudentPayload) {
    return apiPost<StudentRow, StudentPayload>('/students', payload)
  },

  update(id: Id, payload: StudentUpdatePayload) {
    return apiPut<StudentRow, StudentUpdatePayload>(`/students/${id}`, payload)
  },

  remove(id: Id) {
    return apiDelete<{ success: boolean; message: string }>(`/students/${id}`)
  }
}
