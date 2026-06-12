import type { StudentEnrollmentRow } from '~/types'

function num(v: unknown, fallback = 0): number {
  if (v == null || v === '') return fallback
  const n = Number(v)
  return Number.isFinite(n) ? n : fallback
}

function firstAmount(...vals: unknown[]): number {
  for (const v of vals) {
    if (v == null || v === '') continue
    const n = Number(v)
    if (Number.isFinite(n)) return n
  }
  return 0
}

function str(v: unknown): string {
  return v == null ? '' : String(v).trim()
}

export function mapStudentEnrollmentRow(raw: Record<string, unknown>): StudentEnrollmentRow {
  const id = str(raw.id) || `e_${Math.random().toString(36).slice(2, 9)}`
  const totalPrice = firstAmount(raw.totalPrice, raw.total_price, raw.listPrice)
  const discountPrice = firstAmount(
    raw.discountPrice,
    raw.discount_price,
    raw.discountAmount,
    raw.discount_amount,
  )
  const explicitAfter = firstAmount(raw.priceAfterDiscount, raw.price_after_discount, raw.finalPrice)
  const priceAfterDiscount =
    explicitAfter > 0 ? explicitAfter : Math.max(0, totalPrice - discountPrice)

  return {
    id,
    studentName:
      str(raw.studentName) || str(raw.student_name) || str(raw.name) || '',
    nameKm: str(raw.nameKm) || str(raw.name_km) || '',
    nameEn: str(raw.nameEn) || str(raw.name_en) || '',
    gender: str(raw.gender) || str(raw.studentGender) || str(raw.sex) || '',
    birthdate:
      str(raw.birthdate) || str(raw.birthDate) || str(raw.dateOfBirth) || '',
    courseName:
      str(raw.courseName) || str(raw.course_name) || str(raw.course) || '—',
    className:
      str(raw.className) ||
      str(raw.class_name) ||
      str(raw.classTitle) ||
      str(raw.productName) ||
      '—',
    level:
      str(raw.level) || str(raw.classLevel) || str(raw.courseLevel) || '',
    classDuration:
      str(raw.classDuration) ||
      str(raw.duration) ||
      str(raw.durationClass) ||
      str(raw.courseDuration) ||
      '',
    startDate:
      str(raw.startDate) || str(raw.start_date) || str(raw.startdate) || '',
    endDate: str(raw.endDate) || str(raw.end_date) || str(raw.enddate) || '',
    totalPrice,
    discountPrice,
    priceAfterDiscount,
    registerDate:
      str(raw.registerDate) ||
      str(raw.register_date) ||
      str(raw.registeredAt) ||
      '',
  }
}
