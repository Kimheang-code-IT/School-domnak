import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { Product } from '~/types'
import { useCategoryApi, useProductsViewApi } from '~/utils/api'
import { extractApiArray } from '~/utils/helpers/extractApiArray'
import { API_MAX_PAGE_LIMIT, clampApiPageLimit } from '~/utils/constants/apiPagination'
import { resolveUploadUrl } from '~/utils/helpers/mediaUrl'

function toNumber(value: unknown, fallback = 0) {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : fallback
}

function text(value: unknown, fallback = '') {
  const stringValue = String(value ?? '').trim()
  return stringValue || fallback
}

function mapClassApiRow(row: Record<string, unknown>): Product {
  const fullPrice = toNumber(row.fullPrice)
  const outPrice = toNumber(row.outPrice)
  const discountAmount = toNumber(row.discountAmount)

  return {
    id: toNumber(row.id),
    image: resolveUploadUrl(text(row.image)),
    name: text(row.name, 'Class'),
    category: text(row.category),
    categoryId: text(row.categoryId),
    inPrice: outPrice,
    outPrice,
    commission: toNumber(row.teacherCommission ?? row.teacher_commission),
    teacherCommissionMode: text(row.teacherCommissionMode ?? row.teacher_commission_mode) || 'usd',
    teacherCommissionPercent: toNumber(row.teacherCommissionPercent ?? row.teacher_commission_percent),
    totalStock: toNumber(row.studentCount),
    inStock: 0,
    sold: toNumber(row.studentCount),
    added: 0,
    damaged: 0,
    status: 'active',
    createdAt: text(row.createdAt),
    courseId: text(row.courseId),
    courseName: text(row.courseName),
    teacherId: text(row.teacherId),
    teacherName: text(row.teacherName),
    levelId: text(row.levelId),
    level: text(row.levelNameEn || row.level),
    levelKm: text(row.levelNameKm || row.levelKm),
    levelNameEn: text(row.levelNameEn),
    levelNameKm: text(row.levelNameKm),
    classDuration: text(row.classDuration),
    daysOfWeek: Array.isArray(row.daysOfWeek) ? row.daysOfWeek.map((day) => text(day)).filter(Boolean) : [],
    timeIn: text(row.timeIn),
    timeOut: text(row.timeOut),
    timeSlot: text(row.timeSlot),
    fullPrice,
    discountAmount,
    discountPercent: fullPrice > 0 && discountAmount > 0 ? Math.round((discountAmount / fullPrice) * 100) : undefined
  }
}

export function usePosProducts() {
  const productsViewApi = useProductsViewApi('classes')
  const categoryApi = useCategoryApi()
  const isLoadingProducts = ref(false)
  const products = ref<Product[]>([])
  const categories = ref<{ label: string; value: string }[]>([{ label: 'All', value: 'All' }])
  /** Must match `UTabs` item `value` (e.g. `'All'` or category id) — not a numeric index. */
  const selectedCategoryId = ref('All')
  const searchQuery = ref('')
  const debouncedSearchQuery = ref('')
  const visibleCount = ref(60)
  const categoryTabs = computed(() => categories.value)
  let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null

  async function loadCategories() {
    const res = await categoryApi.list({ limit: 100 })
    const raw = extractApiArray<Record<string, unknown>>(res)
    const cats = raw
      .filter((item: any) => String(item.name || '').toLowerCase() !== 'all')
      .map((item: any) => ({
        label: String(item.name || ''),
        value: String(item.id || '')
      }))
    categories.value = [{ label: 'All', value: 'All' }, ...cats]
  }

  async function loadProducts() {
    isLoadingProducts.value = true
    try {
      const query: any = {
        page: 1,
        limit: clampApiPageLimit(visibleCount.value),
        search: debouncedSearchQuery.value || undefined,
        categoryId:
          selectedCategoryId.value === 'All' ? undefined : selectedCategoryId.value
      }
      const res = await productsViewApi.list(query)
      products.value = extractApiArray<Record<string, unknown>>(res).map(mapClassApiRow)
    } catch (error) {
      console.error('Failed to load classes:', error)
      products.value = []
    } finally {
      isLoadingProducts.value = false
    }
  }

  function loadMoreProducts() {
    if (visibleCount.value >= API_MAX_PAGE_LIMIT) return
    visibleCount.value = Math.min(visibleCount.value + 60, API_MAX_PAGE_LIMIT)
  }

  function selectCategoryById(categoryId: string) {
    const id = String(categoryId ?? '').trim()
    if (!id) return
    if (categories.value.some((entry) => entry.value === id)) {
      selectedCategoryId.value = id
    }
  }

  const filteredProducts = computed(() => products.value.filter((item) => item.status !== 'out_of_stock'))

  watch(searchQuery, (value) => {
    if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
    searchDebounceTimer = setTimeout(() => {
      debouncedSearchQuery.value = value.trim().toLowerCase()
    }, 300)
  }, { immediate: true })

  watch([debouncedSearchQuery, selectedCategoryId], async () => {
    visibleCount.value = 60
    await loadProducts()
  })

  watch(visibleCount, loadProducts)

  onMounted(async () => {
    try {
      await loadCategories()
    } catch {
      categories.value = [{ label: 'All', value: 'All' }]
    }
    await loadProducts()
  })

  onBeforeUnmount(() => {
    if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  })

  async function refreshProducts() {
    await loadProducts()
  }

  return {
    isLoadingProducts,
    filteredProducts,
    categoryTabs,
    selectedCategoryId,
    searchQuery,
    loadMoreProducts,
    selectCategoryById,
    refreshProducts
  }
}
