import { apiDelete, apiGet, apiPost, apiPut } from './apiClient'
import type { CoursePayload, CourseRow, Id, TableQuery, TableResponse } from '~/types/api'

export const courseService = {
  list(query?: TableQuery) {
    return apiGet<TableResponse<CourseRow>>('/courses', query)
  },

  create(payload: CoursePayload) {
    return apiPost<CourseRow, CoursePayload>('/courses', payload)
  },

  update(id: Id, payload: Partial<CoursePayload>) {
    return apiPut<CourseRow, Partial<CoursePayload>>(`/courses/${id}`, payload)
  },

  remove(id: Id) {
    return apiDelete<{ success: boolean; message: string }>(`/courses/${id}`)
  }
}
