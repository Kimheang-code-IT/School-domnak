import { computed, ref, type ComputedRef } from 'vue'
import type { ApiQueryParams } from '~/utils/api'
import {
  buildCommaSeparatedFilterQuery,
  type FilterSelection,
} from '~/utils/filters/tableFilters'

/** Multi-select filters mapped to comma-separated API query params (server-side only). */
export function useServerTableFilters(paramKeys: string[]): {
  selections: Record<string, Ref<FilterSelection[]>>
  queryParams: ComputedRef<Partial<ApiQueryParams>>
} {
  const selections = Object.fromEntries(
    paramKeys.map((key) => [key, ref<FilterSelection[]>([])]),
  ) as Record<string, Ref<FilterSelection[]>>

  const queryParams = computed(() => {
    const mapping: Record<string, FilterSelection[] | Ref<FilterSelection[]>> = {}
    for (const key of paramKeys) {
      mapping[key] = selections[key] as FilterSelection[] | Ref<FilterSelection[]>
    }
    return buildCommaSeparatedFilterQuery(mapping)
  })

  return { selections, queryParams }
}
