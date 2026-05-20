import { ref, computed, onMounted, watch } from 'vue'
import type { Product, Course, FinanceEntry } from '~/types'
import {
  useCategoryApi,
  useCoursesApi,
  useProductsViewApi,
  useReportApi,
  useFinanceViewApi,
  type ApiQueryParams,
} from '~/utils/api'
import { API_MAX_PAGE_LIMIT } from '~/utils/constants/apiPagination'
import {
  classNamesSet,
  filterDashboardClasses,
  filterFinanceRowsByClassNames,
  hasDashboardFilters,
  productQueryParam,
  selectedFilterValues,
  type DashboardSelectOption,
} from '~/utils/analytics/dashboardFilters'

export type { DashboardSelectOption }

async function fetchAllClasses(
  listFn: (query: ApiQueryParams) => Promise<{ data?: Product[]; total?: number }>,
  categoryIdParam?: string,
): Promise<Product[]> {
  const listQuery = {
    limit: API_MAX_PAGE_LIMIT,
    sortBy: 'name',
    sortOrder: 'asc' as const,
    ...(categoryIdParam ? { categoryId: categoryIdParam } : {}),
  }
  const products: Product[] = []
  let page = 1
  let total = 0
  do {
    const res = await listFn({ ...listQuery, page })
    const batch = (res.data || []) as Product[]
    products.push(...batch)
    total = res.total ?? products.length
    if (batch.length < listQuery.limit || products.length >= total) break
    page += 1
  } while (page <= 20)
  return products
}

/** Home dashboard — stats and filters for category / course / class. */
export function useAnalyticsDashboard() {
  const { t } = useI18n()
  const { formattedRange } = useGlobalFilter()
  const categoryApi = useCategoryApi()
  const coursesApi = useCoursesApi()
  const productsViewApi = useProductsViewApi()
  const reportApi = useReportApi()
  const financeViewApi = useFinanceViewApi()

  const pending = ref(false)
  /** After first dashboard refresh completes, chart composable may fetch (avoids duplicate full-unfiltered pulls). */
  const dashboardChartsReady = ref(false)
  const metaLoaded = ref(false)
  const lastClassFetchKey = ref('')
  const apiSummary = ref<{
    stats?: { label: string; value: string; icon: string }[]
    chartData?: { name: string; value: number }[]
  } | null>(null)

  const allClasses = ref<Product[]>([])
  const categoryItems = ref<DashboardSelectOption[]>([])
  const courseItems = ref<DashboardSelectOption[]>([])
  const classItems = ref<DashboardSelectOption[]>([])
  const selectedCategories = ref<DashboardSelectOption[]>([])
  const selectedCourses = ref<DashboardSelectOption[]>([])
  const selectedClasses = ref<DashboardSelectOption[]>([])

  const courseNameById = computed(
    () => new Map(courseItems.value.map((item) => [item.value, item.label])),
  )

  const filterParams = computed(() => ({
    categoryIds: selectedFilterValues(selectedCategories.value),
    courseIds: selectedFilterValues(selectedCourses.value),
    classIds: selectedFilterValues(selectedClasses.value),
  }))

  const dateKey = computed(
    () => `${formattedRange.value.start}|${formattedRange.value.end}`,
  )

  const categoryFilterKey = computed(() => filterParams.value.categoryIds.join(','))

  const filterKey = computed(
    () =>
      `${categoryFilterKey.value}|${filterParams.value.courseIds.join(',')}|${filterParams.value.classIds.join(',')}`,
  )

  const filtersActive = computed(() =>
    hasDashboardFilters(
      filterParams.value.categoryIds,
      filterParams.value.courseIds,
      filterParams.value.classIds,
    ),
  )

  const filteredClasses = computed(() =>
    filterDashboardClasses(allClasses.value, {
      ...filterParams.value,
      courseNameById: courseNameById.value,
    }),
  )

  const stats = computed(() => apiSummary.value?.stats || [])
  const currentAnalytics = computed(() => ({
    chartData: apiSummary.value?.chartData || [],
  }))

  function rebuildClassDropdown() {
    const { categoryIds, courseIds } = filterParams.value
    let list = allClasses.value

    if (categoryIds.length > 0) {
      const allowed = new Set(categoryIds)
      list = list.filter((row) => allowed.has(String(row.categoryId || '')))
    }
    if (courseIds.length > 0) {
      const courseNames = new Set(
        courseIds
          .map((id) => courseNameById.value.get(id))
          .filter((name): name is string => Boolean(name)),
      )
      list = list.filter((row) => row.courseName != null && courseNames.has(row.courseName))
    }

    classItems.value = list
      .map((row) => ({
        label: String(row.name || '').trim(),
        value: String(row.id),
      }))
      .filter((item) => item.label && item.value)
  }

  function pruneInvalidClassSelection() {
    const allowed = new Set(classItems.value.map((item) => item.value))
    const next = selectedClasses.value.filter((item) => allowed.has(item.value))
    const prev = selectedClasses.value
    if (
      next.length === prev.length &&
      next.every((item, index) => item.value === prev[index]?.value)
    ) {
      return
    }
    selectedClasses.value = next
  }

  async function loadMeta() {
    const [catListRes, coursesListRes] = await Promise.all([
      categoryApi.list({ page: 1, limit: 200, sortBy: 'name', sortOrder: 'asc' }),
      coursesApi.list({ page: 1, limit: 200, sortBy: 'courseName', sortOrder: 'asc' }),
    ])

    const cats = catListRes.data || []
    categoryItems.value = cats
      .filter((c: { name?: string }) => String(c?.name || '').toLowerCase() !== 'all')
      .map((c: { id?: string; name?: string }) => ({
        label: String(c.name || ''),
        value: String(c.id || ''),
      }))
      .filter((c: DashboardSelectOption) => c.label && c.value)

    const crs = (coursesListRes.data || []) as Course[]
    courseItems.value = crs.map((c) => ({
      label: c.courseName,
      value: c.id,
    }))

    return { catListRes, cats }
  }

  async function loadClassesIfNeeded() {
    const key = categoryFilterKey.value
    if (key === lastClassFetchKey.value && allClasses.value.length > 0) return

    const catIds = filterParams.value.categoryIds
    const categoryIdParam = catIds.length === 1 ? catIds[0] : undefined
    allClasses.value = await fetchAllClasses(
      (query) => productsViewApi.list(query),
      categoryIdParam,
    )
    lastClassFetchKey.value = key
  }

  async function countFilteredReportLines(
    names: Set<string> | null,
    dateFrom?: string,
    dateTo?: string,
  ): Promise<number> {
    const productParam = productQueryParam(names)
    const res = await reportApi.list({
      page: 1,
      limit: 1,
      dateFrom,
      dateTo,
      ...(productParam ? { product: productParam } : {}),
    })
    return res.total ?? 0
  }

  async function countFilteredFinanceRows(names: Set<string> | null): Promise<number> {
    if (!names || names.size === 0) {
      const res = await financeViewApi.list({ page: 1, limit: 1 })
      return res.total ?? 0
    }

    let count = 0
    let page = 1
    let total = 0
    do {
      const res = await financeViewApi.list({ page, limit: API_MAX_PAGE_LIMIT })
      const batch = filterFinanceRowsByClassNames((res.data || []) as FinanceEntry[], names)
      count += batch.length
      total = res.total ?? count
      const rawLen = (res.data || []).length
      if (rawLen < API_MAX_PAGE_LIMIT || page * API_MAX_PAGE_LIMIT >= total) break
      page += 1
    } while (page <= 20)

    return count
  }

  async function refresh() {
    if (pending.value) return
    pending.value = true
    try {
      const dateFrom = formattedRange.value.start || undefined
      const dateTo = formattedRange.value.end || undefined

      let catListTotal = categoryItems.value.length
      if (!metaLoaded.value) {
        const { catListRes, cats } = await loadMeta()
        catListTotal = catListRes.total ?? cats.length ?? 0
        metaLoaded.value = true
      }

      await loadClassesIfNeeded()
      rebuildClassDropdown()
      pruneInvalidClassSelection()

      const products = filteredClasses.value
      const names = filtersActive.value ? classNamesSet(products) : null
      const catIds = filterParams.value.categoryIds

      const byCategory = new Map<string, number>()
      for (const p of products) {
        const key = p.category || '—'
        byCategory.set(key, (byCategory.get(key) || 0) + Number(p.outPrice || 0))
      }
      const chartData = Array.from(byCategory.entries()).map(([name, value]) => ({
        name,
        value,
      }))

      const [reportLineCount, financeRowCount] = await Promise.all([
        countFilteredReportLines(names, dateFrom, dateTo),
        countFilteredFinanceRows(names),
      ])

      apiSummary.value = {
        stats: [
          {
            label: t('pages.dashboard.summary.totalCategory'),
            value: String(
              filtersActive.value && catIds.length > 0 ? catIds.length : catListTotal,
            ),
            icon: 'i-lucide-folder-tree',
          },
          {
            label: t('pages.dashboard.summary.totalClasses'),
            value: String(products.length),
            icon: 'i-lucide-package',
          },
          {
            label: t('pages.dashboard.summary.totalReportLines'),
            value: String(reportLineCount),
            icon: 'i-lucide-file-text',
          },
          {
            label: t('pages.dashboard.summary.totalFinanceRows'),
            value: String(financeRowCount),
            icon: 'i-lucide-credit-card',
          },
        ],
        chartData,
      }
    } finally {
      pending.value = false
      dashboardChartsReady.value = true
    }
  }

  const chartsRenderKey = computed(() => `${dateKey.value}|${filterKey.value}`)

  onMounted(refresh)
  watch(dateKey, refresh)
  watch(filterKey, refresh)

  return {
    stats,
    currentAnalytics,
    pending,
    dashboardChartsReady,
    chartsRenderKey,
    filteredClasses,
    refresh,
    allClasses,
    categoryItems,
    courseItems,
    classItems,
    selectedCategories,
    selectedCourses,
    selectedClasses,
  }
}
