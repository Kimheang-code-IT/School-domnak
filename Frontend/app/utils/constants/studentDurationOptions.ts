/**
 * Student study-duration presets stored as `enrollments.duration_months`.
 * Weeks use fractional months (≈ days/30) so end-date math stays accurate.
 */
export type StudentDurationOption = {
  /** Value persisted to DB / sent as durationMonths */
  months: number
  /** Present when this option is week-based */
  weeks?: number
}

export const STUDENT_DURATION_OPTIONS: readonly StudentDurationOption[] = [
  { months: 0.23, weeks: 1 },
  { months: 0.47, weeks: 2 },
  { months: 0.7, weeks: 3 },
  { months: 1 },
  { months: 1.5 },
  { months: 2 },
  { months: 2.5 },
  { months: 3 },
  { months: 3.5 },
  { months: 4 },
  { months: 4.5 },
  { months: 5 },
] as const

/** Exact day counts for week presets (matches backend enrollment_dates). */
export const WEEK_DURATION_DAYS: Readonly<Record<number, number>> = {
  0.23: 7,
  0.47: 14,
  0.7: 21,
}

export function findStudentDurationOption(months: number | null | undefined): StudentDurationOption | null {
  if (months == null || !Number.isFinite(months) || months <= 0) return null
  const rounded = Math.round(months * 100) / 100
  return (
    STUDENT_DURATION_OPTIONS.find((opt) => Math.abs(opt.months - rounded) < 0.011) ?? null
  )
}

/** Normalize a stored/raw value to a preset `months` string for selects. */
export function normalizeStudentDurationValue(raw: unknown): string {
  const n = Number.parseFloat(String(raw ?? '').trim().replace(',', '.'))
  if (!Number.isFinite(n) || n <= 0) return ''
  const match = findStudentDurationOption(n)
  if (match) return String(match.months)
  // Keep legacy custom values selectable by showing as-is
  return String(n)
}

export function filterStudentDurationOptions(maxMonths: number | null | undefined): StudentDurationOption[] {
  if (maxMonths == null || !Number.isFinite(maxMonths) || maxMonths <= 0) {
    return [...STUDENT_DURATION_OPTIONS]
  }
  return STUDENT_DURATION_OPTIONS.filter((opt) => opt.months <= maxMonths + 0.001)
}
