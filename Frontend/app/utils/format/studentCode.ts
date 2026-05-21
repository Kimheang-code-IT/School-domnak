/** Matches backend `format_student_code` (7-digit zero-padded id). */
export function formatStudentCode(studentId: number | string | null | undefined): string {
  const n = Number(studentId)
  if (!Number.isFinite(n) || n <= 0) return ''
  return String(Math.trunc(n)).padStart(7, '0')
}
