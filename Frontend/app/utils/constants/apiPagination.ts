/** Must match backend `table_query_params` (`le=500`). */
export const API_MAX_PAGE_LIMIT = 500

export function clampApiPageLimit(limit: number): number {
  if (!Number.isFinite(limit)) return API_MAX_PAGE_LIMIT
  return Math.min(Math.max(1, Math.floor(limit)), API_MAX_PAGE_LIMIT)
}

export function normalizeListQuery<T extends Record<string, unknown>>(query?: T): T | undefined {
  if (!query) return query
  if (query.limit == null) return query
  const limit = Number(query.limit)
  if (!Number.isFinite(limit)) return query
  return { ...query, limit: clampApiPageLimit(limit) } as T
}
