import { apiDelete, apiGet, apiPost, apiPut } from './apiClient'
import type { Id, TableQuery, TableResponse } from '~/types/api'
import type { ClassPayload, ClassRow, ClassUpdatePayload } from '~/types/class'

export const classService = {
  list(query?: TableQuery) {
    return apiGet<TableResponse<ClassRow>>('/classes', query)
  },

  create(payload: ClassPayload) {
    return apiPost<ClassRow, ClassPayload>('/classes', payload)
  },

  update(id: Id, payload: ClassUpdatePayload) {
    return apiPut<ClassRow, ClassUpdatePayload>(`/classes/${id}`, payload)
  },

  remove(id: Id) {
    return apiDelete<{ success: boolean; message: string }>(`/classes/${id}`)
  }
}
