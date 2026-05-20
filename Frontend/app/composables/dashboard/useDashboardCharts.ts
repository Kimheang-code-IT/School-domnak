import { ref, computed, type Ref } from 'vue'
import { watchDebounced } from '@vueuse/core'
import type { ComissionEntry, Product, ReportRow } from '~/types'
import {
  useCommissionViewApi,
  useProductsViewApi,
  useReportApi,
  type ApiQueryParams,
} from '~/utils/api'
import { mapReportViewRow } from '~/utils/helpers/mapReportCommissionRows'
import { mapCommissionViewRow } from '~/utils/helpers/mapReportCommissionRows'
import {
  buildClassEnrollmentBar,
  buildCommissionByTeacher,
  buildProvinceStudentCounts,
  type BarChartData,
  type ChartPoint,
} from '~/utils/analytics/buildDashboardCharts'
import {
  classNamesSet,
  filterCommissionRowsByClassNames,
  filterDashboardClasses,
  filterReportRowsByClassNames,
  dashboardScopedQueryParams,
  hasDashboardFilters,
  selectedFilterValues,
  type DashboardSelectOption,
} from '~/utils/analytics/dashboardFilters'
import { API_MAX_PAGE_LIMIT } from '~/utils/constants/apiPagination'

const PAGE_SIZE = API_MAX_PAGE_LIMIT
const MAX_PAGES = 30

export type DashboardChartFilters = {
  /** True after dashboard has loaded category/course/class context (avoids duplicate full scans on mount). */
  chartsReady: Ref<boolean>
  selectedCategories: Ref<DashboardSelectOption[]>
  selectedCourses: Ref<DashboardSelectOption[]>
  selectedClasses: Ref<DashboardSelectOption[]>
  courseItems: Ref<DashboardSelectOption[]>
  /** Classes already filtered by dashboard (category / course / class). */
  filteredClasses: Ref<Product[]>
  /** Tracks catalogue load when filter key is unchanged (e.g. after first fetch). */
  allClasses?: Ref<Product[]>
}

async function fetchAllPages<T>(
  listFn: (query: ApiQueryParams, signal?: AbortSignal) => Promise<{ data?: T[]; total?: number }>,
  baseQuery: ApiQueryParams,
  signal?: AbortSignal,
): Promise<T[]> {
  const rows: T[] = []
  let page = 1

  while (page <= MAX_PAGES) {
    const res = await listFn({ ...baseQuery, page, limit: PAGE_SIZE }, signal)
    const batch = Array.isArray(res.data) ? res.data : []
    rows.push(...batch)
    const total = res.total ?? rows.length
    if (rows.length >= total || batch.length < PAGE_SIZE) break
    page += 1
  }

  return rows
}

/** Single debounced reload for all dashboard charts; respects category/course/class + date range. */
export function useDashboardCharts(filters: DashboardChartFilters) {
  const { formattedRange } = useGlobalFilter()
  const reportApi = useReportApi()
  const commissionApi = useCommissionViewApi()
  const classesApi = useProductsViewApi('classes')

  const chartsLoading = ref(false)
  const provinceStudentData = ref<ChartPoint[]>([])
  const commissionPieData = ref<ChartPoint[]>([])
  const classEnrollmentBar = ref<BarChartData>({ labels: [], values: [] })

  let abortController: AbortController | null = null

  const dateKey = computed(
    () => `${formattedRange.value.start}|${formattedRange.value.end}`,
  )

  const courseNameById = computed(
    () => new Map(filters.courseItems.value.map((item) => [item.value, item.label])),
  )

  const filterParams = computed(() => ({
    categoryIds: selectedFilterValues(filters.selectedCategories.value),
    courseIds: selectedFilterValues(filters.selectedCourses.value),
    classIds: selectedFilterValues(filters.selectedClasses.value),
  }))

  const filterKey = computed(
    () =>
      `${filterParams.value.categoryIds.join(',')}|${filterParams.value.courseIds.join(',')}|${filterParams.value.classIds.join(',')}`,
  )

  const filtersActive = computed(() =>
    hasDashboardFilters(
      filterParams.value.categoryIds,
      filterParams.value.courseIds,
      filterParams.value.classIds,
    ),
  )

  /** null until dashboard ready; includes class counts so charts refetch once classes have loaded. */
  const chartsFetchKey = computed<string | null>(() => {
    if (!filters.chartsReady.value) return null
    const allLen = filters.allClasses?.value?.length ?? 0
    const filteredLen = filters.filteredClasses.value.length
    return `${dateKey.value}::${filterKey.value}::${allLen}::${filteredLen}`
  })

  async function refresh() {
    abortController?.abort()
    abortController = new AbortController()
    const signal = abortController.signal

    chartsLoading.value = true
    try {
      const dateFrom = formattedRange.value.start || undefined
      const dateTo = formattedRange.value.end || undefined
      const query = { dateFrom, dateTo }
      const { courseIds, classIds } = filterParams.value
      const classesForCharts = filters.filteredClasses.value
      const names = filtersActive.value ? classNamesSet(classesForCharts) : null
      const scopedParams = dashboardScopedQueryParams({
        courseIds,
        classIds,
        names,
      })

      const listQuery = {
        ...query,
        sortBy: 'date',
        sortOrder: 'desc' as const,
        ...scopedParams,
      }

      const [commissionRowsAll, reportRowsAll] = await Promise.all([
        fetchAllPages<ComissionEntry>(
          async (q, sig) => {
            const res = await commissionApi.list(q, sig)
            return {
              ...res,
              data: (res.data || []).map((row) =>
                mapCommissionViewRow(row as unknown as Record<string, unknown>),
              ),
            }
          },
          listQuery,
          signal,
        ),
        fetchAllPages<ReportRow>(
          async (q, sig) => {
            const res = await reportApi.list(q, sig)
            return {
              ...res,
              data: (res.data || []).map((row) =>
                mapReportViewRow(row as unknown as Record<string, unknown>),
              ),
            }
          },
          listQuery,
          signal,
        ),
      ])

      let classesForBar = classesForCharts
      if (!classesForBar.length && filters.allClasses?.value?.length) {
        classesForBar = filterDashboardClasses(filters.allClasses.value, {
          ...filterParams.value,
          categoryIds: filterParams.value.categoryIds,
          courseNameById: courseNameById.value,
        })
      }
      if (!classesForBar.length) {
        const classListQuery: ApiQueryParams = {
          sortBy: 'name',
          sortOrder: 'desc',
          ...(filterParams.value.categoryIds.length === 1
            ? { categoryId: filterParams.value.categoryIds[0] }
            : {}),
        }
        classesForBar = await fetchAllPages<Product>(
          (q, sig) => classesApi.list(q, sig),
          classListQuery,
          signal,
        )
        classesForBar = filterDashboardClasses(classesForBar, {
          ...filterParams.value,
          categoryIds: filterParams.value.categoryIds,
          courseNameById: courseNameById.value,
        })
      }

      const reportRows = scopedParams.product
        ? reportRowsAll
        : filterReportRowsByClassNames(reportRowsAll, names)
      const commissionRows = filterCommissionRowsByClassNames(commissionRowsAll, names)

      provinceStudentData.value = buildProvinceStudentCounts(reportRows)
      commissionPieData.value = buildCommissionByTeacher(commissionRows)
      classEnrollmentBar.value = buildClassEnrollmentBar(classesForBar)
    } catch (err) {
      const name = (err as { name?: string })?.name
      const message = String((err as { message?: string })?.message || '').toLowerCase()
      const aborted = name === 'AbortError' || message.includes('abort')
      if (!aborted) {
        console.error('Dashboard charts failed to load:', err)
      }
    } finally {
      chartsLoading.value = false
    }
  }

  watchDebounced(
    chartsFetchKey,
    (key) => {
      if (key == null) return
      void refresh()
    },
    { debounce: 250, maxWait: 720, flush: 'post' },
  )

  return {
    chartsLoading,
    provinceStudentData,
    commissionPieData,
    classEnrollmentBar,
    refresh,
  }
}
