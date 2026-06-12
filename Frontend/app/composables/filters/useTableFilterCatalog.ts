import { computed, onMounted, ref } from 'vue'
import type { Course, Product } from '~/types'
import { useCoursesApi, useProductApi, useUserApi } from '~/utils/api'
import { ENROLLMENT_SOURCE_OPTIONS } from '~/utils/constants/enrollmentSources'
import { CAMBODIA_PROVINCE_NAMES } from '~/utils/constants/cambodiaProvinces'
import { type FilterItem, toFilterItems } from '~/utils/filters/tableFilters'

type CatalogOptions = {
  provinces?: boolean
  genders?: boolean
  sources?: boolean
  classes?: boolean
  courses?: boolean
  sellers?: boolean
}

/**
 * Shared filter option lists for server-driven table pages.
 * Loading runs once per composable instance (typically one page).
 */
export function useTableFilterCatalog(options: CatalogOptions = {}) {
  const {
    provinces = false,
    genders = false,
    sources = false,
    classes = false,
    courses = false,
    sellers = false,
  } = options

  const { t, locale } = useI18n()
  const classApi = useProductApi('classes')
  const coursesApi = useCoursesApi()
  const userApi = useUserApi()

  const classItems = ref<FilterItem[]>([])
  const courseItems = ref<FilterItem[]>([])
  const sellerItems = ref<FilterItem[]>([])

  const provinceItems = computed<FilterItem[]>(() => {
    if (!provinces) return []
    const loc = String(locale.value || 'en').toLowerCase().startsWith('km') ? 'km' : 'en'
    return [...CAMBODIA_PROVINCE_NAMES]
      .map((name) => ({ value: name, label: t(`provinces.${name}`) }))
      .sort((a, b) => a.label.localeCompare(b.label, loc))
  })

  const genderItems = computed<FilterItem[]>(() => {
    if (!genders) return []
    return [
      { label: t('pages.allstudent.gender.male'), value: 'male' },
      { label: t('pages.allstudent.gender.female'), value: 'female' },
    ]
  })

  const sourceItems = computed<FilterItem[]>(() => {
    if (!sources) return []
    return toFilterItems(ENROLLMENT_SOURCE_OPTIONS)
  })

  async function loadClassItems() {
    if (!classes) return
    try {
      const res = await classApi.list({
        page: 1,
        limit: 500,
        sortBy: 'name',
        sortOrder: 'asc',
      })
      classItems.value = (res.data || [])
        .map((item: Product) => ({
          label: String(item.name || '').trim(),
          value: String(item.id ?? '').trim(),
        }))
        .filter((item) => Boolean(item.label && item.value))
    } catch {
      classItems.value = []
    }
  }

  async function loadCourseItems() {
    if (!courses) return
    try {
      const res = await coursesApi.list({
        page: 1,
        limit: 500,
        sortBy: 'name',
        sortOrder: 'asc',
      })
      courseItems.value = (res.data || [])
        .map((item: Course) => ({
          label: String(item.courseName || item.courseNameKm || '').trim(),
          value: String(item.id ?? '').trim(),
        }))
        .filter((item) => Boolean(item.label && item.value))
    } catch {
      courseItems.value = []
    }
  }

  async function loadSellerItems() {
    if (!sellers) return
    try {
      const res = await userApi.list({
        page: 1,
        limit: 500,
        sortBy: 'name',
        sortOrder: 'asc',
      })
      const names = new Set<string>()
      for (const user of res.data || []) {
        const name = String((user as { name?: string }).name || '').trim()
        if (name) names.add(name)
      }
      sellerItems.value = [...names]
        .sort((a, b) => a.localeCompare(b))
        .map((name) => ({ label: name, value: name }))
    } catch {
      sellerItems.value = []
    }
  }

  onMounted(() => {
    void Promise.all([loadClassItems(), loadCourseItems(), loadSellerItems()])
  })

  return {
    provinceItems,
    genderItems,
    sourceItems,
    classItems,
    courseItems,
    sellerItems,
  }
}
