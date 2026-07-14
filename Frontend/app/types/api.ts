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
