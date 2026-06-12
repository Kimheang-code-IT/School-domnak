export type StudentRow = {
  id: number
  studentCode: string
  studentId: string
  displayId: string
  image?: string | null
  nameKm: string
  nameEn: string
  gender?: string | null
  birthdate?: string | null
  phone?: string | null
  province?: string | null
  totalCourse: number
  createdAt?: string | null
}

export type StudentPayload = {
  image?: string | null
  nameKm: string
  nameEn: string
  gender?: string | null
  birthdate?: string | null
  phone?: string | null
  province?: string | null
}

export type StudentUpdatePayload = Partial<StudentPayload>
