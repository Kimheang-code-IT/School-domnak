import { computed, ref, type ComputedRef, type Ref } from 'vue'
import type { ApiQueryParams } from '~/utils/api'
import { useTableQuery } from '~/composables/table/useTableQuery'
import { useServerTableResource } from '~/composables/table/useServerTable'
import { useTableSearchDateQuery } from '~/composables/table/useTableSearchDateQuery'

type UseServerListTableOptions<T> = {
  resourceKey: string
  initialSorting?: Array<{ id: string; desc: boolean }>
  extraQuery?: Ref<Record<string, string | number | undefined>>
  localData?: Ref<T[]> | Ref<any[]>
  listFn: (query: ApiQueryParams, signal?: AbortSignal) => Promise<{ data?: T[]; total?: number; aggregates?: Record<string, number> }>
}

export function useServerListTable<T>(options: UseServerListTableOptions<T>) {
  const useBackendApi = useBackendMode()
  const { formattedRange } = useGlobalFilter()
  const fallbackData = (options.localData ?? ref<T[]>([])) as Ref<T[]>
  const { sorting, columnFilters, pagination, serverQuery } = useTableQuery({
    initialSorting: options.initialSorting ?? []
  })
  const searchQuery = ref('')
  const extraQuery = computed(() => options.extraQuery?.value || {}) as ComputedRef<Partial<ApiQueryParams>>
  const { mergedServerQuery } = useTableSearchDateQuery(
    serverQuery,
    searchQuery,
    pagination,
    formattedRange,
    extraQuery,
    'extraAfter'
  )

  const resource = useServerTableResource<T, ApiQueryParams>({
    resourceKey: options.resourceKey,
    useBackendApi,
    serverQuery: mergedServerQuery,
    localData: fallbackData,
    listFn: options.listFn,
    debounceMs: 220
  })

  return {
    sorting,
    columnFilters,
    pagination,
    searchQuery,
    mergedServerQuery,
    resource
  }
}
