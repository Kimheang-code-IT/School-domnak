import type {
  AuditLog,
  Category,
  ComissionEntry,
  Course,
  Level,
  DeliveryEntry,
  FinanceEntry,
  Product,
  ReportRow,
  StudentEnrollmentRow,
  SystemRole,
  SystemUser
} from '~/types'
import { useAuthStore } from '~/stores/auth'
import { useApi } from '~/composables/useApi'

type ApiList<T> = { data: T[]; total?: number }
type AuthUser = { id?: number; name: string; email: string; avatar?: string; role?: string; pageAccess?: string[]; permissions?: Record<string, string[]> }
type LoginResponseFastApi = { accessToken: string; refreshToken?: string; tokenType?: string; user: AuthUser }
type RefreshResponseFastApi = { accessToken: string; tokenType?: string }
type LoginResponseV3 = { success: boolean; message: string; data: { token: string; refreshToken: string; user: AuthUser } }
type LoginResponseV2 = { data: { tokens: { accessToken: string; refreshToken: string }; user: AuthUser } }
type RefreshResponseV2 = { data: { tokens: { accessToken: string; refreshToken: string } } }

export type ApiQueryParams = {
  page?: number
  limit?: number
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
  search?: string
  dateFrom?: string
  dateTo?: string
  [key: string]: string | number | undefined
}

function makeCrudApi<T>(resource: string) {
  const api = useApi()
  return {
    list: (params?: ApiQueryParams, signal?: AbortSignal) =>
      api.get<ApiList<T>>(resource, { query: params, signal, dedupe: true, silent: true }),
    create: (payload: Partial<T>) => api.post<T>(resource, payload),
    update: (id: string | number, payload: Partial<T>) => api.put<T>(`${resource}/${id}`, payload),
    remove: (id: string | number) => api.delete(`${resource}/${id}`)
  }
}

function makeViewListApi<T>(resource: string) {
  const api = useApi()
  return {
    list: (params?: ApiQueryParams, signal?: AbortSignal) =>
      api.get<ApiList<T>>(resource, { query: params, signal, dedupe: true, silent: true })
  }
}

function useSchoolResourcePath(resource?: 'students' | 'classes') {
  const route = useRoute()
  const path = computed(() => route.path)

  const isStudentPage = computed(() => resource === 'students' || (!resource && path.value.startsWith('/allstudent')))
  const baseResource = computed(() => (isStudentPage.value ? '/students' : '/classes'))

  return {
    isStudentPage,
    baseResource
  }
}

function toStudentPayload(payload: Partial<Product>) {
  return {
    image: payload.image,
    nameKm: payload.nameKm || payload.name,
    nameEn: payload.nameEn || payload.name,
    gender: payload.gender,
    birthdate: payload.birthdate,
    phone: payload.phone,
    province: payload.province
  }
}

function toClassPayload(payload: Partial<Product>) {
  return {
    image: payload.image,
    name: payload.name,
    categoryId: payload.categoryId ? Number(payload.categoryId) : undefined,
    courseId: payload.courseId ? Number(payload.courseId) : undefined,
    teacherId: payload.teacherId ? Number(payload.teacherId) : undefined,
    teacherName: payload.teacherName,
    levelId: payload.levelId ? Number(payload.levelId) : undefined,
    level: payload.level,
    levelKm: payload.levelKm,
    classDuration: payload.classDuration,
    daysOfWeek: payload.daysOfWeek,
    timeIn: payload.timeIn,
    timeOut: payload.timeOut,
    timeSlot: payload.timeSlot,
    fullPrice: payload.fullPrice,
    discountAmount: payload.discountAmount,
    outPrice: payload.outPrice,
    teacherCommission: Number(payload.teacherCommission ?? payload.commission ?? 0),
    teacherCommissionMode: payload.teacherCommissionMode ?? 'usd',
    teacherCommissionPercent: Number(payload.teacherCommissionPercent ?? 0),
    status: payload.status
  }
}

export function useAuthApi() {
  const api = useApi()
  const auth = useAuthStore()
  return {
    login: async (payload: { email: string; password: string }) => {
      const response = await api.post<LoginResponseFastApi | LoginResponseV3 | LoginResponseV2 | { token: string; refreshToken?: string; user: AuthUser }>('/auth/login', payload)
      if ('accessToken' in response && response.accessToken) {
        return {
          tokens: {
            accessToken: response.accessToken,
            refreshToken: response.refreshToken || ''
          },
          user: response.user
        }
      }
      if ('success' in response && 'data' in response && response.data && 'token' in response.data) {
        return {
          tokens: {
            accessToken: response.data.token,
            refreshToken: response.data.refreshToken
          },
          user: response.data.user
        }
      }
      if ('data' in response && response.data && 'tokens' in response.data) {
        return {
          tokens: response.data.tokens,
          user: response.data.user
        }
      }
      const legacy = response as { token: string; refreshToken?: string; user: any }
      return {
        tokens: {
          accessToken: legacy.token,
          refreshToken: legacy.refreshToken || ''
        },
        user: legacy.user
      }
    },
    refresh: async () => {
      const response = await api.post<RefreshResponseFastApi | RefreshResponseV2>(
        '/auth/refresh',
        { refreshToken: auth.refreshToken || '' },
        {
          skipAuthRefresh: true,
          headers: auth.refreshToken ? { refreshToken: auth.refreshToken } : {}
        }
      )
      if ('accessToken' in response) {
        return {
          tokens: {
            accessToken: response.accessToken,
            refreshToken: auth.refreshToken || ''
          }
        }
      }
      return response.data
    },
    me: () => api.get<{ user?: any; data?: { user: any } }>('/auth/me'),
    logout: () => api.post('/auth/logout', { refreshToken: auth.refreshToken || '' })
  }
}

export function useCategoryApi() {
  return makeCrudApi<Category>('/categories')
}

export function useCoursesApi() {
  return makeCrudApi<Course>('/courses')
}

export function useLevelsApi() {
  return makeCrudApi<Level>('/levels')
}

export function useProductApi(resource?: 'students' | 'classes') {
  const api = useApi()
  const { isStudentPage, baseResource } = useSchoolResourcePath(resource)

  const payloadForContext = (payload: Partial<Product>) =>
    isStudentPage.value ? toStudentPayload(payload) : toClassPayload(payload)

  return {
    list: (params?: ApiQueryParams, signal?: AbortSignal) =>
      api.get<ApiList<Product>>(baseResource.value, { query: params, signal, dedupe: true, silent: true }),
    create: (payload: Partial<Product>) => api.post<Product>(baseResource.value, payloadForContext(payload)),
    update: (id: string | number, payload: Partial<Product>) =>
      api.put<Product>(`${baseResource.value}/${id}`, payloadForContext(payload)),
    remove: (id: string | number) => api.delete(`${baseResource.value}/${id}`),
    listStockAdditions: (id: number | string, params?: ApiQueryParams) =>
      api.get<ApiList<any>>('/audit-logs', { query: { ...params, search: String(id) } }),
    listDamages: (id: number | string, params?: ApiQueryParams) =>
      api.get<ApiList<any>>('/audit-logs', { query: { ...params, search: String(id) } }),
    /** Class roster rows for a product (class). */
    listEnrollments: (id: number | string, params?: ApiQueryParams) =>
      api.get<ApiList<any>>(`/classes/${id}/enrollments`, { query: params }),
    /**
     * Remove student from the active roster for this class; backend should retain enrollment history / audit trail.
     */
    withdrawStudentFromClassRoster: (productId: number | string, enrollmentId: string) =>
      api.patch<{ success?: boolean }>(
        `/classes/${productId}/enrollments/${encodeURIComponent(String(enrollmentId))}`,
        { rosterActive: false },
      ),
    /** Enrollment lines for a student (courses/classes, pricing). */
    listStudentEnrollments: (studentId: number | string, params?: ApiQueryParams) =>
      api.get<ApiList<StudentEnrollmentRow>>(
        `/students/${studentId}/enrollments`,
        { query: params },
      ),
    deleteStudentEnrollment: (studentId: number | string, enrollmentId: string | number) =>
      api.delete(`/students/${studentId}/enrollments/${encodeURIComponent(String(enrollmentId))}`),
  }
}

export function useRoleApi() {
  return makeCrudApi<SystemRole>('/roles')
}

export function useSystemRoleApi() {
  return useRoleApi()
}

export function useUserApi() {
  return makeCrudApi<SystemUser>('/users')
}

export function useSystemUserApi() {
  return useUserApi()
}

export function useHistoriesApi() {
  const api = useApi()
  return {
    list: (params?: ApiQueryParams, signal?: AbortSignal) =>
      api.get<ApiList<AuditLog>>('/audit-logs', { query: params, signal, dedupe: true, silent: true })
  }
}

export function useHistoryApi() {
  return useHistoriesApi()
}

export function useProductsViewApi(resource?: 'students' | 'classes') {
  const api = useApi()
  const { baseResource } = useSchoolResourcePath(resource)
  return {
    list: (params?: ApiQueryParams, signal?: AbortSignal) =>
      api.get<ApiList<Product>>(baseResource.value, { query: params, signal, dedupe: true, silent: true }),
  }
}

export function useReportsViewApi() {
  const api = useApi()
  return {
    list: (params?: ApiQueryParams, signal?: AbortSignal) =>
      api.get<ApiList<ReportRow>>('/reports/sales-lines', { query: params, signal, dedupe: true, silent: true }),
    exportCsv: (params?: ApiQueryParams) =>
      api.get<{ url?: string; data?: ReportRow[] }>('/reports/sales-lines/export', { query: params }),
  }
}

export function useDeliveriesViewApi() {
  return makeViewListApi<DeliveryEntry>('/deliveries-view')
}

export function useCommissionViewApi() {
  const api = useApi()
  return {
    ...makeViewListApi<ComissionEntry>('/commissions'),
    exportCsv: (params?: ApiQueryParams) =>
      api.get<{ data?: ComissionEntry[]; total?: number }>('/commissions/export', { query: params }),
  }
}

export function useFinanceViewApi() {
  const api = useApi()
  return {
    ...makeViewListApi<FinanceEntry>('/finance'),
    exportCsv: (params?: ApiQueryParams) =>
      api.get<{ data?: FinanceEntry[]; total?: number }>('/finance/export', { query: params }),
    update: (
      id: number,
      payload: {
        electricity?: number
        water?: number
        internet?: number
        totalCommission?: number
        facebook?: number
        other?: number
      },
    ) => api.put<{ data: FinanceEntry }>(`/finance/${id}`, payload)
  }
}

export function useFinanceApi() {
  return useFinanceViewApi()
}

export function useReportApi() {
  return useReportsViewApi()
}

export function useDeliveryApi() {
  return useDeliveriesViewApi()
}

export function useComissionApi() {
  return useCommissionViewApi()
}

export function usePosApi() {
  const api = useApi()
  async function withLegacyFallback<T>(primary: () => Promise<T>, fallback: () => Promise<T>) {
    try {
      return await primary()
    } catch (error: any) {
      if (Number(error?.response?.status || error?.statusCode || 0) === 404) {
        return await fallback()
      }
      throw error
    }
  }
  return {
    createPreviewSession: (invoices: any[]) =>
      api.post<{ previewKey: string }>('/invoices/preview-sessions', { invoices }),
    getPreviewSession: (previewKey: string) =>
      api.get<{ invoices: any[]; invoice?: any }>(`/invoices/preview-sessions/${previewKey}`),
    getInvoicePreviewByNo: (invoiceNo: string) =>
      api.get<{ invoices: any[]; invoice?: any }>(
        `/invoices/by-no/${encodeURIComponent(invoiceNo)}/preview`,
      ),
    getNextInvoiceNo: () =>
      api.get<{ invoiceNo: string }>('/invoices/next-number'),
    calculateTotals: (payload: {
      discountPercent: number
      lines: Array<{ productId: number; qty: number }>
    }) =>
      withLegacyFallback(
        () => api.post<{ subtotal: number; discountAmount: number; total: number }>('/pos/calculate-totals', payload),
        () => api.post<{ subtotal: number; discountAmount: number; total: number }>('/invoices/calculate-totals', payload)
      ),
    checkout: (payload: {
      studentId?: number
      image?: string
      nameKm?: string
      nameEn?: string
      gender?: string
      birthdate?: string
      province?: string
      customerName: string
      customerPhone: string
      customerAddress: string
      source: string
      deliveryType: string
      deliveryPrice: number
      deliveryDate: string
      discountPercent: number
      paymentMethod?: string
      deliveryStatus?: string
      sellerId?: number
      lines: Array<{ productId: number; qty: number }>
    }) =>
      withLegacyFallback(
        () =>
          api.post<{ data: { invoiceNo: string; subtotal: number; discountAmount: number; total: number; invoice: any } }>(
            '/invoices/checkout',
            payload
          ),
        () =>
          api.post<{ data: { invoiceNo: string; subtotal: number; discountAmount: number; total: number; invoice: any } }>(
            '/pos/checkout',
            payload
          )
      )
  }
}
