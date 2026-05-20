import { useCrudTable } from './useCrudTable'
import { categoryService } from '~/services/categoryService'
import type { CategoryPayload, CategoryRow, TableQuery } from '~/types/api'

export function useCategories(initialQuery: TableQuery = {}) {
  return useCrudTable<CategoryRow, CategoryPayload>(categoryService, initialQuery)
}
