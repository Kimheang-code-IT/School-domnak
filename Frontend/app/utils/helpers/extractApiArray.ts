/** Normalizes `{ data: T[] }`, `{ data: { data: T[] } }`, or top-level array API responses. */
export function extractApiArray<T>(res: unknown): T[] {
  if (res == null || typeof res !== 'object') return []
  const r = res as Record<string, unknown>
  const top = r.data
  if (Array.isArray(top)) return top as T[]
  if (top && typeof top === 'object' && Array.isArray((top as { data?: unknown }).data)) {
    return (top as { data: T[] }).data
  }
  return []
}
