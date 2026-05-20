import { ref, computed, onMounted, onUnmounted } from 'vue'

export type TelegramQueueStatus = {
  ok: boolean
  busy: boolean
  queue_length: number
  processing: boolean
  poller_expected?: boolean
  enqueued_total?: number
  processed_total?: number
  error?: string
}

/**
 * Polls backend while Telegram bot is processing queued getUpdates.
 * Drives full-screen AppMatrixLoader overlay in default layout when busy.
 */
export function useTelegramBotStatus(pollMs = 2000) {
  const api = useApi()
  const status = ref<TelegramQueueStatus | null>(null)
  const pollError = ref(false)
  let timer: ReturnType<typeof setInterval> | null = null

  const busy = computed(() => Boolean(status.value?.busy))
  const queueLength = computed(() => status.value?.queue_length ?? 0)
  const processing = computed(() => Boolean(status.value?.processing))

  async function refresh() {
    if (!import.meta.client) return
    try {
      const data = await api.get<TelegramQueueStatus>('/telegram/status')
      status.value = data
      pollError.value = false
    } catch {
      pollError.value = true
      status.value = null
    }
  }

  function startPolling() {
    if (!import.meta.client || timer) return
    void refresh()
    timer = setInterval(() => void refresh(), pollMs)
  }

  function stopPolling() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  onMounted(startPolling)
  onUnmounted(stopPolling)

  return {
    status,
    busy,
    queueLength,
    processing,
    pollError,
    refresh,
    startPolling,
    stopPolling,
  }
}
