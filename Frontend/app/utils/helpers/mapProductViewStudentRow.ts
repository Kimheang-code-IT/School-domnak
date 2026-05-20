import type { Product } from '~/types'
import { normalizeCambodiaProvince } from '~/utils/constants/cambodiaProvinces'
import { resolveUploadUrl } from '~/utils/helpers/mediaUrl'

function nonEmptyString(v: unknown): string | undefined {
  if (v == null) return undefined
  const s = String(v).trim()
  return s === '' ? undefined : s
}

function coerceNum(...candidates: unknown[]): number | undefined {
  for (const v of candidates) {
    if (v == null || v === '') continue
    const n = Number(v)
    if (Number.isFinite(n)) return n
  }
  return undefined
}

/** `/products-view` rows for the student registry — snake_case + legacy `name` fallbacks */
export function mapProductViewStudentRow(row: Product): Product {
  const raw = row as unknown as Record<string, unknown>

  const nameKm =
    nonEmptyString(row.nameKm) ??
    nonEmptyString(raw.name_km)
  const nameEn =
    nonEmptyString(row.nameEn) ??
    nonEmptyString(raw.name_en)
  const legacyName = nonEmptyString(row.name)

  const image = nonEmptyString(row.image) ?? nonEmptyString(raw.image)

  return {
    ...row,
    ...(image ? { image: resolveUploadUrl(image) } : {}),
    studentCode:
      nonEmptyString(row.studentCode) ??
      nonEmptyString(raw.student_code) ??
      nonEmptyString(raw.studentId) ??
      nonEmptyString(raw.student_id) ??
      nonEmptyString(raw.displayId) ??
      nonEmptyString(raw.display_id),
    studentId:
      nonEmptyString(row.studentId) ??
      nonEmptyString(raw.student_id) ??
      nonEmptyString(raw.studentCode) ??
      nonEmptyString(raw.student_code),
    displayId:
      nonEmptyString(row.displayId) ??
      nonEmptyString(raw.display_id) ??
      nonEmptyString(raw.studentCode) ??
      nonEmptyString(raw.student_code),
    nameKm: nameKm ?? legacyName,
    nameEn: nameEn ?? legacyName,
    gender: nonEmptyString(row.gender) ?? nonEmptyString(raw.gender),
    birthdate:
      nonEmptyString(row.birthdate) ??
      nonEmptyString(raw.birth_date) ??
      nonEmptyString(raw.dateOfBirth),
    phone:
      nonEmptyString(row.phone) ??
      nonEmptyString(raw.phone_number) ??
      nonEmptyString(raw.mobile),
    province: (() => {
      const rawProvince =
        nonEmptyString(row.province) ?? nonEmptyString(raw.province)
      return rawProvince ? normalizeCambodiaProvince(rawProvince) || rawProvince : undefined
    })(),
    totalCourse:
      coerceNum(
        row.totalCourse,
        raw.total_course,
        raw.totalCourses,
        raw.courseCount
      ) ?? row.totalCourse
  }
}
