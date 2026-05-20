import { computed, watch, type ComputedRef, type Ref } from 'vue'
import type { PaginationState } from '@tanstack/vue-table'
import type { ApiQueryParams } from '~/utils/api'

export type GlobalDateRange = { start?: string; end?: string }

/** `extraAfter`: same as legacy `useServerListTable` (extra overwrites search/date if keys clash). */
export type TableQueryExtraMerge = 'extraBeforeSearch' | 'extraAfter'

/**
 * Merges TanStack `serverQuery` with trimmed search, global date range, and optional extra params.
 * Resets page index when `searchQuery` changes (same behavior as existing table composables).
 */
export function useTableSearchDateQuery(
  serverQuery: ComputedRef<ApiQueryParams>,
  searchQuery: Ref<string>,
  pagination: Ref<PaginationState>,
  formattedRange: ComputedRef<GlobalDateRange>,
  extraQuery?: ComputedRef<Partial<ApiQueryParams>>,
  extraMerge: TableQueryExtraMerge = 'extraBeforeSearch'
) {
  const mergedServerQuery = computed((): ApiQueryParams => {
    const extra = extraQuery?.value || {}
    const search = searchQuery.value.trim() || undefined
    const dateFrom = formattedRange.value.start || undefined
    const dateTo = formattedRange.value.end || undefined
    if (extraMerge === 'extraAfter') {
      return {
        ...serverQuery.value,
        search,
        dateFrom,
        dateTo,
        ...extra,
      }
    }
    return {
      ...serverQuery.value,
      ...extra,
      search,
      dateFrom,
      dateTo,
    }
  })

  watch(searchQuery, () => {
    pagination.value.pageIndex = 0
  })

  if (extraQuery) {
    watch(extraQuery, () => {
      pagination.value.pageIndex = 0
    }, { deep: true })
  }

  return { mergedServerQuery }
}
