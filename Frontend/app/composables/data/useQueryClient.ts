type CacheEntry<T = unknown> = {
  data: T
  expiresAt: number
}

const queryCache = new Map<string, CacheEntry>()
const inFlight = new Map<string, Promise<unknown>>()

export function useQueryClient() {
  function get<T>(key: string): T | null {
    const hit = queryCache.get(key)
    if (!hit) return null
    if (Date.now() > hit.expiresAt) {
      queryCache.delete(key)
      return null
    }
    return hit.data as T
  }

  function set<T>(key: string, value: T, staleMs = 8000) {
    queryCache.set(key, {
      data: value,
      expiresAt: Date.now() + staleMs
    })
  }

  async function getOrFetch<T>(key: string, fetcher: () => Promise<T>, staleMs = 8000): Promise<T> {
    const cached = get<T>(key)
    if (cached !== null) return cached

    const existing = inFlight.get(key)
    if (existing) return existing as Promise<T>

    const promise = fetcher()
      .then((result) => {
        set(key, result, staleMs)
        return result
      })
      .finally(() => {
        inFlight.delete(key)
      })

    inFlight.set(key, promise)
    return promise
  }

  function invalidate(prefix?: string) {
    if (!prefix) {
      queryCache.clear()
      return
    }
    for (const key of queryCache.keys()) {
      if (key.startsWith(prefix)) queryCache.delete(key)
    }
  }

  return {
    get,
    set,
    getOrFetch,
    invalidate
  }
}
