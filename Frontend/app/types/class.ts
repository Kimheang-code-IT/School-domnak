export type ClassRow = {
  id: number
  image?: string | null
  name: string
  category?: string | null
  categoryId?: number | null
  courseId?: number | null
  courseName?: string | null
  teacherId?: number | null
  teacherName?: string | null
  level?: string | null
  levelKm?: string | null
  classDuration?: string | null
  daysOfWeek: string[]
  timeIn?: string | null
  timeOut?: string | null
  timeSlot?: string | null
  fullPrice: number | string
  discountAmount: number | string
  outPrice: number | string
  teacherCommission?: number | string
  teacherCommissionMode?: string
  teacherCommissionPercent?: number | string
  status: string
  studentCount?: number
  createdAt?: string | null
}

export type ClassPayload = {
  image?: string | null
  name: string
  categoryId?: number | null
  courseId?: number | null
  teacherId?: number | null
  teacherName?: string | null
  level?: string | null
  levelKm?: string | null
  classDuration?: string | null
  daysOfWeek?: string[]
  timeIn?: string | null
  timeOut?: string | null
  timeSlot?: string | null
  fullPrice?: number | string
  discountAmount?: number | string
  outPrice?: number | string
  teacherCommission?: number | string
  status?: string
}

export type ClassUpdatePayload = Partial<ClassPayload>
