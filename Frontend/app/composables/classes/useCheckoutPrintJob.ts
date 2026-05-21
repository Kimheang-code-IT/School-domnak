import { usePosApi } from '~/utils/api'

const POLL_MS = 400
const MAX_WAIT_MS = 30_000

export async function waitForCheckoutPrintReady(jobId: string | null | undefined): Promise<boolean> {
  const id = String(jobId || '').trim()
  if (!id) return true

  const posApi = usePosApi()
  const started = Date.now()

  while (Date.now() - started < MAX_WAIT_MS) {
    try {
      const status = await posApi.getCheckoutJobStatus(id)
      if (status.printReady) return true
      if (status.status === 'failed') return false
    } catch {
      return true
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_MS))
  }

  return true
}
