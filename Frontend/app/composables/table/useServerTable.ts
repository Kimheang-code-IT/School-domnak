import { computed, onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue'
import { useQueryClient } from '~/composables/data/useQueryClient'
import { isLiveBackendApi, isUiOnlyMode } from '~/composables/useBackendMode'

type ListResult<T> = {
  data?: T[]
  total?: number
  aggregates?: Record<string, number>
}

interface ServerTableResourceOptions<T, Q extends Record<string, unknown>> {
  resourceKey: string
  useBackendApi: Ref<boolean>
  serverQuery: Ref<Q>
  listFn: (query: Q, signal?: AbortSignal) => Promise<ListResult<T>>
  localData: Ref<T[]>
  debounceMs?: number
}

export function useServerTableResource<T, Q extends Record<string, unknown>>(options: ServerTableResourceOptions<T, Q>) {
  const config = useRuntimeConfig()
  const rows = ref<T[]>(options.localData.value)
  const totalRows = ref(rows.value.length)
  const isLoading = ref(false)
  const aggregates = ref<Record<string, number>>({})
  const queryClient = useQueryClient()
  const debounceMs = options.debounceMs ?? 200
  let timer: ReturnType<typeof setTimeout> | null = null
  let controller: AbortController | null = null

  const queryKey = computed(() => `${options.resourceKey}:${JSON.stringify(options.serverQuery.value)}`)

  async function load() {
    const useLiveHttp = isLiveBackendApi(config) && !isUiOnlyMode(config)
    const fetchViaListFn = options.useBackendApi.value || !useLiveHttp
    if (!fetchViaListFn) {
      rows.value = options.localData.value
      totalRows.value = rows.value.length
      return
    }

    controller?.abort()
    controller = new AbortController()
    isLoading.value = true
    try {
      const result = await queryClient.getOrFetch<ListResult<T>>(
        queryKey.value,
        () => options.listFn(options.serverQuery.value, controller?.signal),
        5000
      )
      rows.value = result.data || []
      totalRows.value = result.total ?? rows.value.length
      aggregates.value = result.aggregates || {}
    } catch (err: any) {
      if (err.name === 'AbortError' || err.message?.includes('aborted')) {
        return
      }
      console.error('Failed to load resource:', err)
    } finally {
      isLoading.value = false
    }
  }

  function refresh() {
    queryClient.invalidate(options.resourceKey)
    return load()
  }

  function scheduleLoad() {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      load()
    }, debounceMs)
  }

  onMounted(load)
  watch(options.serverQuery, scheduleLoad, { deep: true })
  watch(options.useBackendApi, scheduleLoad)
  onBeforeUnmount(() => {
    if (timer) clearTimeout(timer)
    controller?.abort()
  })

  return {
    rows,
    totalRows,
    isLoading,
    aggregates,
    load,
    refresh
  }
}
