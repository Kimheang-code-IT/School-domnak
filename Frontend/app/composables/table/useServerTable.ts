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

type LoadOptions = {
  /** Bypass client cache and hit the API. */
  force?: boolean
  /** Do not flip `isLoading` (keeps the table visible during post-mutation refresh). */
  silent?: boolean
}

export function useServerTableResource<T, Q extends Record<string, unknown>>(options: ServerTableResourceOptions<T, Q>) {
  const config = useRuntimeConfig()
  const rows = ref<T[]>(options.localData.value) as Ref<T[]>
  const totalRows = ref(rows.value.length)
  const isLoading = ref(false)
  const aggregates = ref<Record<string, number>>({})
  const queryClient = useQueryClient()
  const debounceMs = options.debounceMs ?? 150
  let timer: ReturnType<typeof setTimeout> | null = null
  let controller: AbortController | null = null

  const queryKey = computed(() => `${options.resourceKey}:${JSON.stringify(options.serverQuery.value)}`)

  function clearScheduledLoad() {
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  async function load(loadOpts?: LoadOptions) {
    const useLiveHttp = isLiveBackendApi(config) && !isUiOnlyMode(config)
    const fetchViaListFn = options.useBackendApi.value || !useLiveHttp
    if (!fetchViaListFn) {
      rows.value = options.localData.value
      totalRows.value = rows.value.length
      return
    }

    controller?.abort()
    controller = new AbortController()
    const signal = controller.signal
    const key = queryKey.value
    const silent = Boolean(loadOpts?.silent)
    if (!silent) isLoading.value = true
    try {
      let result: ListResult<T>
      if (loadOpts?.force) {
        queryClient.invalidate(options.resourceKey)
        result = await options.listFn(options.serverQuery.value, signal)
        if (!signal.aborted) {
          queryClient.set(key, result, 5000)
        }
      } else {
        result = await queryClient.getOrFetch<ListResult<T>>(
          key,
          () => options.listFn(options.serverQuery.value, signal),
          5000
        )
      }
      if (signal.aborted) return
      rows.value = result.data || []
      totalRows.value = result.total ?? rows.value.length
      aggregates.value = result.aggregates || {}
    } catch (err: any) {
      if (err.name === 'AbortError' || err.message?.includes('aborted')) {
        return
      }
      console.error('Failed to load resource:', err)
    } finally {
      if (!signal.aborted && !silent) isLoading.value = false
    }
  }

  /** Re-fetch list after create/update/delete. Silent by default so the UI does not flash a loader. */
  function refresh(loadOpts?: { silent?: boolean }) {
    clearScheduledLoad()
    return load({ force: true, silent: loadOpts?.silent ?? true })
  }

  function scheduleLoad() {
    clearScheduledLoad()
    timer = setTimeout(() => {
      timer = null
      void load()
    }, debounceMs)
  }

  onMounted(() => {
    void load()
  })
  watch(options.serverQuery, scheduleLoad, { deep: true })
  watch(options.useBackendApi, scheduleLoad)
  onBeforeUnmount(() => {
    clearScheduledLoad()
    controller?.abort()
  })

  return {
    rows,
    totalRows,
    isLoading,
    aggregates,
    load,
    refresh,
  }
}
