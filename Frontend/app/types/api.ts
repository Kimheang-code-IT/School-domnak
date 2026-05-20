export type SortOrder = 'asc' | 'desc'

export type QueryValue = string | number | boolean | null | undefined

export type TableQuery = {
  page?: number
  limit?: number
  sortBy?: string
  sortOrder?: SortOrder
  search?: string
  dateFrom?: string
  dateTo?: string
  categoryId?: string | number
  product?: string
  action?: string
  role?: string
  [key: string]: QueryValue
}

export type TableResponse<T> = {
  data: T[]
  total: number
}

export type Id = string | number

export type CrudService<TRow, TCreate, TUpdate = Partial<TCreate>> = {
  list: (query?: TableQuery) => Promise<TableResponse<TRow>>
  create: (payload: TCreate) => Promise<TRow>
  update: (id: Id, payload: TUpdate) => Promise<TRow>
  remove: (id: Id) => Promise<unknown>
}

export type CategoryRow = {
  id: number
  name: string
  description?: string | null
  total: number
  createdAt?: string | null
}

export type CategoryPayload = {
  name: string
  description?: string | null
}

export type CourseRow = {
  id: number
  courseName: string
  courseNameKm?: string | null
  description?: string | null
  totalClass: number
  createdAt?: string | null
}

export type CoursePayload = {
  courseName: string
  courseNameKm?: string | null
  description?: string | null
}

export type UserRow = {
  id: number
  name: string
  role?: string | null
  roleId?: number | null
  email: string
  password: '********' | string
  permissions?: Record<string, string[]>
  lastLogin?: string | null
  createdAt?: string | null
}

export type UserCreatePayload = {
  name: string
  email: string
  password: string
  roleId?: number | null
}

export type UserUpdatePayload = Partial<UserCreatePayload>
