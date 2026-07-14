import {
  WEEK_DURATION_DAYS,
  findStudentDurationOption,
} from '~/utils/constants/studentDurationOptions'

/** Extract month count from stored duration (e.g. `3`, `1.5`, `"3 months"`). */
export function parseDurationMonthsDecimal(value: unknown): number | null {
  const raw = String(value ?? '').trim().replace(',', '.')
  if (!raw) return null
  const match = raw.match(/^(\d+(?:\.\d+)?)/)
  if (!match) return null
  const n = Number.parseFloat(match[1]!)
  return Number.isFinite(n) && n > 0 ? n : null
}

/** Normalize to `YYYY-MM-DD` or return empty string. */
export function normalizeIsoDate(value: unknown): string {
  if (!value) return ''
  const s = String(value).trim()
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return ''
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/** Calendar day after an ISO date (`YYYY-MM-DD`), or empty if invalid. */
export function dayAfterIsoDate(iso: string): string {
  const normalized = normalizeIsoDate(iso)
  if (!normalized) return ''
  const [y, m, d] = normalized.split('-').map(Number)
  const next = new Date(y!, m! - 1, d!)
  next.setDate(next.getDate() + 1)
  return normalizeIsoDate(next)
}

/** End study date from start ISO date and duration in months (matches backend). */
export function computeEnrollmentEndDateIso(startIso: string, months: number): string {
  const normalized = normalizeIsoDate(startIso)
  if (!normalized || !months || months <= 0) return ''
  const [y, m, d] = normalized.split('-').map(Number)
  const start = new Date(y!, m! - 1, d!)

  const weekKey = Math.round(months * 100) / 100
  const weekDays = WEEK_DURATION_DAYS[weekKey]
  if (weekDays) {
    start.setDate(start.getDate() + weekDays)
    return normalizeIsoDate(start)
  }

  const whole = Math.floor(months)
  const fraction = months - whole
  start.setMonth(start.getMonth() + whole)
  if (fraction > 0) {
    start.setDate(start.getDate() + Math.round(fraction * 30))
  }
  return normalizeIsoDate(start)
}

export function prorateByDuration(
  fullPrice: number,
  studentMonths: number,
  classMonths: number
): number {
  if (!Number.isFinite(fullPrice) || fullPrice <= 0) return 0
  if (!classMonths || classMonths <= 0) return fullPrice
  const ratio = studentMonths / classMonths
  if (ratio >= 1) return fullPrice
  if (ratio <= 0) return 0
  return Math.round(fullPrice * ratio * 100) / 100
}

type DurationTranslate = (key: string, params?: Record<string, unknown>) => string

/** Display label such as `2 months` / `1 week` from a numeric or legacy string value. */
export function formatClassDuration(
  value: unknown,
  t: DurationTranslate,
  te?: (key: string) => boolean
): string {
  const raw = String(value ?? '').trim()
  if (!raw) return ''

  const months = parseDurationMonthsDecimal(raw)
  if (months != null) {
    const preset = findStudentDurationOption(months)
    if (preset?.weeks) {
      const key =
        preset.weeks === 1 ? 'pages.allclass.durationWeek' : 'pages.allclass.durationWeeks'
      if (!te || te(key)) return t(key, { count: preset.weeks })
      return preset.weeks === 1 ? '1 week' : `${preset.weeks} weeks`
    }
    if (Number.isInteger(months)) {
      const key =
        months === 1 ? 'pages.allclass.durationMonth' : 'pages.allclass.durationMonths'
      if (!te || te(key)) return t(key, { count: months })
    }
    const halfKey = 'pages.allclass.durationMonths'
    if (!te || te(halfKey)) return t(halfKey, { count: months })
    return months === 1 ? `${months} month` : `${months} months`
  }

  return raw
}
