import { apiDelete, apiGet, apiPost, apiPut } from './apiClient'
import type { CategoryPayload, CategoryRow, Id, TableQuery, TableResponse } from '~/types/api'

export const categoryService = {
  list(query?: TableQuery) {
    return apiGet<TableResponse<CategoryRow>>('/categories', query)
  },

  create(payload: CategoryPayload) {
    return apiPost<CategoryRow, CategoryPayload>('/categories', payload)
  },

  update(id: Id, payload: Partial<CategoryPayload>) {
    return apiPut<CategoryRow, Partial<CategoryPayload>>(`/categories/${id}`, payload)
  },

  remove(id: Id) {
    return apiDelete<{ success: boolean; message: string }>(`/categories/${id}`)
  }
}
