export interface AuditLog {
  id: number
  typeAction: 'Login' | 'Logout' | 'Create' | 'Update' | 'Delete' | 'Export'
  username: string
  date: string
  description: string
  metadata?: any
}

export interface Category {
  id: string
  name: string
  description: string
  total: number
  createdAt: string
}

export interface Statistic {
  label: string
  value: string
  icon: string
}

export interface ChartDataPoint {
  name: string
  value: number
}

export interface FormField {
  key: string
  label: string
  type?: 'input' | 'number' | 'integer' | 'tel' | 'select' | 'permission-tree' | 'textarea' | 'password' | 'date' | 'file' | 'time' | 'discount' | string
  icon?: string
  placeholder?: string
  /** Shown after integer/number inputs (e.g. unit label). */
  trailing?: string
  inputmode?: string
  autocomplete?: string
  maxlength?: number
  pattern?: string
  /** Show USD trailing on number inputs (also auto for common price keys). */
  currency?: boolean
  /** Discount field with % / USD toggle; value saved as USD in `key`. */
  discount?: boolean
  /** Base price field for percent discount math (default `fullPrice`). */
  discountBaseKey?: string
  /** Teacher commission field with % / USD toggle (class form). */
  commission?: boolean
  items?: any[]
  childItems?: any[]
  multiple?: boolean
  readonly?: boolean
  required?: boolean
  class?: string
}

/** Derived on the server from `inStock`; same keys as `product.stockStatus.*` i18n. */
export type ProductStockStatusTier = 'aLot' | 'lower' | 'out'

export interface Product {
  id: number
  studentCode?: string
  studentId?: string
  displayId?: string
  image: string
  name: string
  /** Display name of the category (from joined category row). */
  category: string
  /** Public category id from the API (`Cat_00001`). */
  categoryId: string
  inPrice: number
  outPrice: number
  commission: number
  teacherCommissionMode?: string
  teacherCommissionPercent?: number
  totalStock: number
  inStock: number
  sold: number
  added: number
  damaged: number
  status: 'active' | 'inactive' | 'out_of_stock'
  /** Stock level band from backend (`GET /products` and `/products/stock-status`). */
  stockStatus?: ProductStockStatusTier
  stockNote?: string
  createdAt: string
  /** Optional — class / course POS (e.g. all-class grid) */
  courseId?: string
  courseName?: string
  teacherId?: string
  teacherName?: string
  levelId?: string
  level?: string
  levelKm?: string
  levelNameEn?: string
  levelNameKm?: string
  classLevel?: string
  courseLevel?: string
  classDuration?: string
  duration?: string
  durationClass?: string
  courseDuration?: string
  daysOfWeek?: string[]
  timeIn?: string
  timeOut?: string
  /** e.g. `08:00 - 10:00` */
  timeSlot?: string
  /** List price before discount */
  fullPrice?: number
  discountPercent?: number
  discountAmount?: number
  /** Student registry (`allstudent` table) — optional when row is a student record */
  nameKm?: string
  nameEn?: string
  gender?: string
  birthdate?: string
  phone?: string
  province?: string
  totalCourse?: number
}

export interface FinanceEntry {
  id: string
  /** Legacy API field — prefer `className` for display */
  productName?: string
  className?: string
  printPrice?: number
  electricity?: number
  water?: number
  internet?: number
  totalCommission: number
  facebook: number
  other: number
  inPriceForPos?: number
  amount?: number
  finalPrice?: number
}

export interface ReportRow {
  invoiceNo: string
  date: string
  /** Numeric student PK when linked */
  studentId?: number | null
  product: string
  customer: string
  phoneCustomer: string
  seller: string
  phoneSaler: string
  source: string
  address: string
  amount: number
  /** Table column `studentName` — same person as `customer` when API uses either key */
  studentName: string
  /** Table column `studentPhone` — same as `phoneCustomer` when API uses either key */
  studentPhone: string
  /** Table column `receipt` — receipt / ref no.; falls back to `invoiceNo` if unset */
  receipt: string
}

export interface DeliveryEntry {
  invoiceId: string
  address: string
  deliveryType: 'VET' | 'Domnaksiiksa' | 'Grap' | 'J&T'
  deliveryPrice: number
  date: string
}

export interface Level {
  id: string
  levelNameKm: string
  levelNameEn: string
  description?: string
  totalClass: number
  createdAt: string
}

export interface Course {
  id: string
  courseName: string
  courseNameKm?: string
  /** Shown in the course list table (like category description). */
  description?: string
  totalClass: number
  createdAt: string
}

/** One enrollment line for “student → classes/courses” drill-down (student profile modal). */
export interface StudentEnrollmentRow {
  id: string | number
  courseName: string
  className: string
  studentName?: string
  nameKm?: string
  nameEn?: string
  gender?: string
  birthdate?: string
  level?: string
  classLevel?: string
  courseLevel?: string
  duration?: string
  classDuration?: string
  durationMonths?: string
  durationClass?: string
  courseDuration?: string
  startDate: string
  endDate: string
  status?: string
  rosterActive?: boolean
  totalPrice: number
  discountPrice: number
  priceAfterDiscount: number
  invoiceDiscountAmount?: number
  invoiceGrandTotal?: number
  registerDate: string
}

export interface ComissionEntry {
  id: string
  /** Teacher display name (from Users with teacher role / API teacher fields). */
  teacherName: string
  /** Grouping key for commission table (same as teacherName). */
  teacher_key?: string
  /** Class / section title (was product/course row label). */
  className: string
  studentName: string
  source: string
  date: string
  amount: number
  commission: number
  saleCount?: number
}

export interface SystemRole {
  id: number
  name: string
  permissions?: Record<string, string[]>
  pageAccess?: string[]
}

export interface SystemUser {
  id: number
  name: string
  role: string
  email: string
  password?: string
  lastLogin: string
  commission?: number
  permissions?: Record<string, string[]>
}

export interface User {
  id: number
  name: string
  position: string
  email: string
  role: string
  pageAccess?: string[]
  permissions?: Record<string, string[]>
  joinDate?: string
}

export interface AuthUser {
  id?: number
  name: string
  email: string
  avatar?: string
  role?: string
  pageAccess?: string[]
  permissions?: Record<string, string[]>
}

export interface AuthTokenPair {
  accessToken: string
  refreshToken: string
}
