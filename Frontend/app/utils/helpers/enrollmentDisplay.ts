import {
  computeEnrollmentEndDateIso,
  normalizeIsoDate,
  parseDurationMonthsDecimal,
} from '~/utils/format/duration'

function pickStr(row: Record<string, unknown>, keys: string[]): string {
  for (const k of keys) {
    const v = row[k]
    if (v != null && String(v).trim() !== '') return String(v).trim()
  }
  return ''
}

/** Student enrollment duration in months (not class catalog duration). */
export function pickEnrollmentDurationMonths(row: Record<string, unknown>): string {
  return pickStr(row, ['durationMonths', 'duration_months', 'studentDuration'])
}

/** Study start: explicit start date, else registration date. */
export function resolveEnrollmentStartIso(row: Record<string, unknown>): string {
  const start = pickStr(row, ['startdate', 'startDate', 'start_date'])
  if (start) return normalizeIsoDate(start)
  return normalizeIsoDate(
    pickStr(row, ['registerDate', 'register_date', 'registeredAt']),
  )
}

/** Study end: saved end date, else start + student duration months. */
export function resolveEnrollmentEndIso(row: Record<string, unknown>): string {
  const end = pickStr(row, ['enddate', 'endDate', 'end_date'])
  if (end) return normalizeIsoDate(end)
  const startIso = resolveEnrollmentStartIso(row)
  const months = parseDurationMonthsDecimal(pickEnrollmentDurationMonths(row))
  if (startIso && months) return computeEnrollmentEndDateIso(startIso, months)
  return ''
}
