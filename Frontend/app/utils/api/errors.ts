/** True when an API call was rejected with HTTP 403 (forbidden). */
export function isForbiddenError(err: unknown): boolean {
  const e = err as { response?: { status?: number }; status?: number; statusCode?: number }
  const status = e?.response?.status ?? e?.status ?? e?.statusCode
  return status === 403
}
