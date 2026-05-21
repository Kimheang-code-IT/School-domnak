import type { ReportRow, ComissionEntry } from '~/types'
import { englishStudentDisplayName } from '~/utils/format/studentName'

function num(v: unknown, fallback = 0): number {
  if (v == null || v === '') return fallback
  const n = Number(v)
  return Number.isFinite(n) ? n : fallback
}

function str(v: unknown): string {
  return v == null ? '' : String(v).trim()
}

/** Normalizes `/reports-view` rows (camelCase + common snake_case). */
export function mapReportViewRow(raw: Record<string, unknown>): ReportRow {
  const englishName = englishStudentDisplayName(
    str(raw.nameEn),
    str(raw.name_en),
    str(raw.studentName),
    str(raw.student_name),
    str(raw.customer)
  )
  const displayName = englishName || '—'

  const fromStudentPhone =
    str(raw.studentPhone) || str(raw.student_phone)
  const fromPhoneCustomer =
    str(raw.phoneCustomer) || str(raw.phone_customer)
  const phoneCustomer = fromStudentPhone || fromPhoneCustomer || '—'

  const invoiceNo = str(raw.invoiceNo) || str(raw.invoice_no)
  const studentIdRaw = raw.studentId ?? raw.student_id
  let studentId: number | null = null
  if (studentIdRaw != null && studentIdRaw !== '') {
    const n = Number(studentIdRaw)
    if (Number.isFinite(n) && n > 0) studentId = n
  }

  const receipt =
    str(raw.receipt) ||
    str(raw.receipt_number) ||
    str(raw.receipt_no) ||
    str(raw.receiptNumber) ||
    invoiceNo ||
    '—'

  return {
    invoiceNo: invoiceNo || '—',
    date: str(raw.date),
    studentId,
    product:
      str(raw.className) ||
      str(raw.class_name) ||
      str(raw.product) ||
      str(raw.productName),
    className:
      str(raw.className) ||
      str(raw.class_name) ||
      str(raw.product) ||
      str(raw.productName),
    customer: displayName,
    phoneCustomer,
    studentName: displayName,
    studentPhone: phoneCustomer,
    receipt,
    seller: str(raw.seller) || str(raw.sellerName),
    phoneSaler: str(raw.phoneSaler) || str(raw.phone_saler),
    source: str(raw.source),
    address:
      str(raw.address) ||
      str(raw.customerAddress) ||
      str(raw.customer_address) ||
      str(raw.province) ||
      str(raw.studentProvince) ||
      str(raw.student_province) ||
      '—',
    amount: num(raw.amount),
  }
}

function nestedUserName(raw: Record<string, unknown>): string {
  const u = raw.user
  if (!u || typeof u !== 'object') return ''
  return str((u as Record<string, unknown>).name)
}

/** Normalizes `/commission-view` rows (teacher/class/student semantics + legacy seller/product/customer keys). */
export function mapCommissionViewRow(raw: Record<string, unknown>): ComissionEntry {
  const id = str(raw.id) || `row_${str(raw.invoiceNo) || str(raw.date) || Math.random().toString(36).slice(2)}`

  const teacherName =
    str(raw.teacherName) ||
    str(raw.teacher_name) ||
    nestedUserName(raw) ||
    str(raw.userName) ||
    str(raw.user_name) ||
    str(raw.seller) ||
    str(raw.sellerName) ||
    '—'

  const className =
    str(raw.className) ||
    str(raw.class_name) ||
    str(raw.courseName) ||
    str(raw.course_name) ||
    str(raw.product) ||
    '—'

  const studentName = englishStudentDisplayName(
    str(raw.nameEn),
    str(raw.name_en),
    str(raw.studentName),
    str(raw.student_name),
    str(raw.customer)
  ) || '—'

  return {
    id,
    teacherName,
    teacher_key: teacherName,
    className,
    studentName,
    source: str(raw.source),
    date: str(raw.date),
    amount: num(raw.amount),
    commission: num(raw.commission),
    saleCount: raw.saleCount != null ? num(raw.saleCount, 0) : undefined,
  }
}
