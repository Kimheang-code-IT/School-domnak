/** Extract month count from stored duration (e.g. `3`, `"23"`, `"3 months"`). */
export function parseDurationMonths(value: unknown): number | null {
  const raw = String(value ?? '').trim()
  if (!raw) return null

  const leading = raw.match(/^(\d+)/)
  if (leading) {
    const n = Number.parseInt(leading[1]!, 10)
    return Number.isFinite(n) && n > 0 ? n : null
  }

  return null
}

type DurationTranslate = (key: string, params?: Record<string, unknown>) => string

/** Display label such as `2 months` / `២ ខែ` from a numeric or legacy string value. */
export function formatClassDuration(
  value: unknown,
  t: DurationTranslate,
  te?: (key: string) => boolean
): string {
  const raw = String(value ?? '').trim()
  if (!raw) return ''

  const months = parseDurationMonths(raw)
  if (months != null) {
    const key =
      months === 1 ? 'pages.allclass.durationMonth' : 'pages.allclass.durationMonths'
    if (!te || te(key)) return t(key, { count: months })
    return months === 1 ? `${months} month` : `${months} months`
  }

  return raw
}
