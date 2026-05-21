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

/** Class discount (enrollment) + checkout invoice discount, for display in enrollment tables. */
export function totalEnrollmentDiscountAmount(
  row: Pick<
    StudentEnrollmentRow,
    | 'totalPrice'
    | 'discountPrice'
    | 'priceAfterDiscount'
    | 'invoiceDiscountAmount'
    | 'invoiceGrandTotal'
  >,
): number {
  const classDiscount = Number(row.discountPrice || 0)
  const invoiceDiscount = Number(row.invoiceDiscountAmount || 0)
  if (classDiscount > 0 || invoiceDiscount > 0) {
    return classDiscount + invoiceDiscount
  }
  const total = Number(row.totalPrice || 0)
  const final = Number(row.invoiceGrandTotal ?? row.priceAfterDiscount ?? 0)
  return Math.max(0, total - final)
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
  const hasExplicitAfter =
    (raw.priceAfterDiscount != null && raw.priceAfterDiscount !== '') ||
    (raw.price_after_discount != null && raw.price_after_discount !== '')
  const priceAfterDiscount = hasExplicitAfter
    ? firstAmount(raw.priceAfterDiscount, raw.price_after_discount, raw.finalPrice)
    : Math.max(0, totalPrice - discountPrice)

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
    courseNameKm:
      str(raw.courseNameKm) || str(raw.course_name_km) || '',
    className:
      str(raw.className) ||
      str(raw.class_name) ||
      str(raw.classTitle) ||
      str(raw.productName) ||
      '—',
    level:
      str(raw.level) || str(raw.classLevel) || str(raw.courseLevel) || '',
    levelKm:
      str(raw.levelKm) || str(raw.level_km) || str(raw.levelNameKm) || str(raw.level_name_km) || '',
    levelNameKm:
      str(raw.levelNameKm) || str(raw.level_name_km) || str(raw.levelKm) || str(raw.level_km) || '',
    classDuration:
      str(raw.classDuration) ||
      str(raw.duration) ||
      str(raw.durationClass) ||
      str(raw.courseDuration) ||
      '',
    durationMonths:
      str(raw.durationMonths) ||
      str(raw.duration_months) ||
      '',
    startDate:
      str(raw.startDate) || str(raw.start_date) || str(raw.startdate) || '',
    endDate: str(raw.endDate) || str(raw.end_date) || str(raw.enddate) || '',
    status: str(raw.status) || str(raw.enrollmentStatus) || '',
    rosterActive:
      raw.rosterActive === true || raw.roster_active === true
        ? true
        : raw.rosterActive === false || raw.roster_active === false
          ? false
          : undefined,
    totalPrice,
    discountPrice,
    priceAfterDiscount,
    invoiceDiscountAmount: firstAmount(
      raw.invoiceDiscountAmount,
      raw.invoice_discount_amount,
    ),
    invoiceGrandTotal: firstAmount(raw.invoiceGrandTotal, raw.invoice_grand_total),
    registerDate:
      str(raw.registerDate) ||
      str(raw.register_date) ||
      str(raw.registeredAt) ||
      '',
  }
}
