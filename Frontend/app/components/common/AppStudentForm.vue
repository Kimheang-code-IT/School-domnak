<script setup lang="ts">
import type { Product } from '~/types'
import { parseDate, type DateValue } from '@internationalized/date'
import { onClickOutside } from '@vueuse/core'
import { CAMBODIA_PROVINCE_NAMES, normalizeCambodiaProvince } from '~/utils/constants/cambodiaProvinces'
import { normalizeKhmerText } from '~/utils/format/khmerText'
import { formatStudentCode } from '~/utils/format/studentCode'
import { normalizeCambodiaPhone } from '~/utils/format/phone'
import { formatClassDuration } from '~/utils/format/duration'
import { mapProductViewStudentRow } from '~/utils/helpers/mapProductViewStudentRow'
import { resolveUploadUrl } from '~/utils/helpers/mediaUrl'

const customerType = defineModel<string>('customerType', { required: true })
const customerName = defineModel<string>('customerName', { required: true })
const nameKm = defineModel<string>('nameKm', { default: '' })
const nameEn = defineModel<string>('nameEn', { default: '' })
const gender = defineModel<string>('gender', { default: '' })
const birthdate = defineModel<string>('birthdate', { default: '' })
const province = defineModel<string>('province', { default: '' })
const enrollmentDurationMonths = defineModel<string>('enrollmentDurationMonths', { default: '' })
const enrollmentStartDate = defineModel<string>('enrollmentStartDate', { default: '' })
const studentImage = defineModel<string | undefined>('studentImage')
const customerPhone = defineModel<string>('customerPhone', { required: true })
const customerAddress = defineModel<string>('customerAddress', { required: true })
const deliveryType = defineModel<string>('deliveryType', { required: true })
const deliveryPrice = defineModel<number>('deliveryPrice', { required: true })
const deliveryDate = defineModel<string>('deliveryDate', { required: true })
const deliveryStatus = defineModel<string>('deliveryStatus', { required: true, default: 'pending' })
const sellerId = defineModel<number | undefined>('sellerId')
const selectedStudentId = defineModel<number | undefined>('selectedStudentId')

const props = withDefaults(
  defineProps<{
    /** Full class duration in months (from selected class). */
    classDurationMaxMonths?: number | null
  }>(),
  {
    classDurationMaxMonths: null,
  }
)

const { t, locale, te } = useI18n()
const auth = useAuthStore()
const config = useRuntimeConfig()

type StudentLookupItem = {
  value: string
  studentId: string
  nameKm: string
  nameEn: string
  phone: string
  avatar: { src: string; alt?: string; loading?: 'lazy' } | { icon: string }
  product: Product
}

type StudentsApiList = { data?: Product[] }

function studentDisplayId(p: Product): string {
  return String(
    p.studentCode || p.studentId || p.displayId || formatStudentCode(p.id)
  ).trim()
}

function mapStudentLookupItem(p: Product): StudentLookupItem {
  const studentId = studentDisplayId(p)
  const nameKm = String(p.nameKm ?? '').trim() || '—'
  const nameEn = String(p.nameEn ?? '').trim() || '—'
  const phone = String(p.phone ?? '').trim() || '—'
  return {
    value: String(p.id),
    studentId,
    nameKm,
    nameEn,
    phone,
    avatar: p.image
      ? { src: p.image, alt: nameEn !== '—' ? nameEn : nameKm, loading: 'lazy' as const }
      : { icon: 'i-lucide-user' },
    product: p
  }
}

const {
  data: studentsApiResponse,
  status: studentsFetchStatus,
  execute: loadStudents
} = await useLazyFetch<StudentsApiList>('/students', {
  key: 'app-student-form-lookup',
  baseURL: config.public.apiBase as string,
  query: { page: 1, limit: 500 },
  immediate: false,
  headers: computed((): Record<string, string> => {
    const token = auth.token
    return token ? { Authorization: `Bearer ${token}` } : {}
  })
})

const studentListItems = computed<StudentLookupItem[]>(() =>
  ((studentsApiResponse.value?.data || []) as Product[])
    .map(mapProductViewStudentRow)
    .map(mapStudentLookupItem)
)

const studentSearchQuery = ref('')
const suggestionsOpen = ref(false)
const searchAreaRef = ref<HTMLElement | null>(null)

onClickOutside(searchAreaRef, () => {
  suggestionsOpen.value = false
})

const filteredStudents = computed(() => {
  const q = studentSearchQuery.value.trim().toLowerCase()
  if (!q) return []
  const tokens = q.split(/\s+/).filter(Boolean)
  return studentListItems.value
    .filter((item) => {
      const blob = [item.studentId, item.nameKm, item.nameEn, item.phone, item.value]
        .map((x) => String(x ?? '').toLowerCase())
        .join(' ')
      return tokens.every((token) => blob.includes(token))
    })
    .slice(0, 12)
})

const sellerName = computed(() => String(auth.user?.name || ''))
const sellerRole = computed(() => String(auth.user?.role || '').toLowerCase())

watch(
  () => auth.user,
  (u) => {
    const rawId = Number((u as any)?.id)
    sellerId.value = Number.isFinite(rawId) && rawId > 0 ? rawId : undefined
  },
  { immediate: true, deep: true }
)

const deliveryDatePart = ref('')
const deliveryTimePart = ref('')

const deliveryTypeItems = ['VET', 'Domnaksiiksa', 'Grap', 'J&T']

const genderItems = computed(() => [
  { label: t('product.genderMale'), value: 'male' },
  { label: t('product.genderFemale'), value: 'female' },
  { label: t('product.genderOther'), value: 'other' }
])

const provinceItems = computed(() => {
  const loc = String(locale.value || 'en').toLowerCase().startsWith('km') ? 'km' : 'en'
  return [...CAMBODIA_PROVINCE_NAMES]
    .map((name) => ({ value: name as string, label: t(`provinces.${name}`) }))
    .sort((a, b) => a.label.localeCompare(b.label, loc))
})

watch(province, (v) => {
  const n = normalizeCambodiaProvince(v)
  if (n !== v) province.value = n
  else if (n && !customerAddress.value.trim()) {
    customerAddress.value = n
  }
})

watch(customerPhone, (v) => {
  const n = normalizeCambodiaPhone(v)
  if (n !== v) customerPhone.value = n
})

watch(nameKm, (v) => {
  const n = normalizeKhmerText(v)
  if (n !== v) nameKm.value = n
})

function onNameKmInput(event: Event) {
  const target = event.target as HTMLInputElement | null
  const filtered = normalizeKhmerText(target?.value ?? '')
  nameKm.value = filtered
  if (target && target.value !== filtered) target.value = filtered
}

function onPhoneInput(event: Event) {
  const target = event.target as HTMLInputElement | null
  const digits = normalizeCambodiaPhone(target?.value ?? '')
  customerPhone.value = digits
  if (target && target.value !== digits) target.value = digits
}

function onSelectCustomerType(type: string) {
  customerType.value = type

  if (type === 'walkIn') {
    selectedStudentId.value = undefined
    studentSearchQuery.value = ''
    suggestionsOpen.value = false
    customerName.value = 'Walk-in'
    customerPhone.value = '000000000'
    customerAddress.value = 'Nothing'
    nameKm.value = ''
    nameEn.value = ''
    return
  }

  customerName.value = ''
  customerPhone.value = ''
  customerAddress.value = ''
  selectedStudentId.value = undefined
}

onMounted(() => {
  loadStudents()
})

watch(studentSearchQuery, (q) => {
  if (q.trim()) suggestionsOpen.value = true
})

function onSearchFocus() {
  if (studentSearchQuery.value.trim()) {
    suggestionsOpen.value = true
  }
}

function selectStudentLookupItem(item: StudentLookupItem) {
  applyStudentFromTable(item.product)
  studentSearchQuery.value = ''
  suggestionsOpen.value = false
}

function normalizeGenderInput(raw: string | undefined): string {
  const g = String(raw ?? '').toLowerCase().trim()
  if (g === 'male' || g === 'female' || g === 'other') return g
  return ''
}

function normalizeBirthdateInput(raw: string | undefined): string {
  if (!raw) return ''
  const s = String(raw).trim()
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s
  const d = new Date(s)
  if (!Number.isNaN(d.getTime())) {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}-${m}-${day}`
  }
  return ''
}

const birthdateInputRef = useTemplateRef('birthdateInput')

const enrollmentStartInputRef = useTemplateRef('enrollmentStartInput')

const enrollmentStartCalendar = computed({
  get(): DateValue | undefined {
    const s = normalizeBirthdateInput(enrollmentStartDate.value)
    if (!s) return undefined
    try {
      return parseDate(s)
    } catch {
      return undefined
    }
  },
  set(val: DateValue | undefined) {
    enrollmentStartDate.value = val ? String(val) : ''
  },
})

const durationInputTrailing = computed(() => {
  const unit = t('pages.allclass.fields.durationUnit')
  if (props.classDurationMaxMonths) {
    return formatClassDuration(props.classDurationMaxMonths, t, te)
  }
  return unit
})

const birthdateCalendar = computed({
  get(): DateValue | undefined {
    const s = normalizeBirthdateInput(birthdate.value)
    if (!s) return undefined
    try {
      return parseDate(s)
    } catch {
      return undefined
    }
  },
  set(val: DateValue | undefined) {
    birthdate.value = val ? String(val) : ''
  }
})

function applyStudentFromTable(p: Product) {
  customerType.value = 'Customer'
  selectedStudentId.value = Number.isFinite(Number(p.id)) ? Number(p.id) : undefined
  nameKm.value = normalizeKhmerText(String(p.nameKm ?? '').trim())
  nameEn.value = String(p.nameEn ?? '').trim()
  if (!nameKm.value && !nameEn.value && p.name) {
    nameEn.value = p.name
  }
  customerPhone.value = normalizeCambodiaPhone(String(p.phone ?? '').trim())
  province.value = normalizeCambodiaProvince(String(p.province ?? ''))
  if (!customerAddress.value.trim() && province.value) {
    customerAddress.value = province.value
  }
  gender.value = normalizeGenderInput(p.gender)
  birthdate.value = normalizeBirthdateInput(p.birthdate)
  if (p.image) {
    studentImage.value = p.image
  }
  customerName.value = [nameKm.value, nameEn.value].filter(Boolean).join(' · ')
}

function setWalkInCustomer() {
  onSelectCustomerType('walkIn')
  selectedStudentId.value = undefined
  studentSearchQuery.value = ''
  suggestionsOpen.value = false
}

if (!deliveryType.value) {
  deliveryType.value = deliveryTypeItems[0] as string
}

if (deliveryPrice.value === undefined || deliveryPrice.value === null || Number.isNaN(Number(deliveryPrice.value))) {
  deliveryPrice.value = 2
}

function pad(value: number): string {
  return String(value).padStart(2, '0')
}

function toDisplayDate(value: Date): string {
  const formatter = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Phnom_Penh',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
  const parts = formatter.formatToParts(value)
  const get = (ty: string) => parts.find((p) => p.type === ty)?.value || '00'
  return `${get('day')}/${get('month')}/${get('year')} ${get('hour')}:${get('minute')}:${get('second')}`
}

function parseDisplayDate(value: string): Date | null {
  const normalized = String(value || '').trim()
  const match = normalized.match(/^(\d{2})\/(\d{2})\/(\d{4}) (\d{2}):(\d{2})(?::(\d{2}))?$/)
  if (!match) return null
  const [, dd, mm, yyyy, hh, min, sec] = match

  const isoStr = `${yyyy}-${mm}-${dd}T${hh}:${min}:${sec || '00'}+07:00`
  const date = new Date(isoStr)
  return Number.isNaN(date.getTime()) ? null : date
}

function syncPartsFromModel() {
  const parsed = parseDisplayDate(deliveryDate.value)
  const date = parsed || new Date()

  const formatter = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Phnom_Penh',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  })
  const p = formatter.formatToParts(date)
  const g = (ty: string) => p.find((x) => x.type === ty)?.value || '00'

  deliveryDatePart.value = `${g('year')}-${g('month')}-${g('day')}`
  deliveryTimePart.value = `${g('hour')}:${g('minute')}`
}

function syncModelFromParts() {
  if (!deliveryDatePart.value || !deliveryTimePart.value) return
  const dateParts = deliveryDatePart.value.split('-').map(Number)
  const timeParts = deliveryTimePart.value.split(':').map(Number)

  if (dateParts.length < 3 || timeParts.length < 2) return
  const [yyyy, mm, dd] = dateParts as [number, number, number]
  const [hh, min] = timeParts as [number, number]

  if (Number.isNaN(yyyy) || Number.isNaN(mm) || Number.isNaN(dd) || Number.isNaN(hh) || Number.isNaN(min)) return

  const isoStr = `${pad(yyyy)}-${pad(mm)}-${pad(dd)}T${pad(hh)}:${pad(min)}:00+07:00`
  const date = new Date(isoStr)
  deliveryDate.value = toDisplayDate(date)
}

if (!deliveryDate.value) {
  deliveryDate.value = toDisplayDate(new Date())
}

syncPartsFromModel()

watch(deliveryDate, () => {
  syncPartsFromModel()
})

watch([deliveryDatePart, deliveryTimePart], () => {
  syncModelFromParts()
})

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(file)
  })
}

/** Local file for `UFileUpload`; parent `studentImage` stays a data URL string. */
const imageUploadModel = ref<File | null>(null)
const imageUploadKey = ref(0)

watch(imageUploadModel, async (file) => {
  if (!file) {
    studentImage.value = undefined
    return
  }
  try {
    studentImage.value = await readFileAsDataUrl(file)
  } catch {
    imageUploadModel.value = null
  }
})

watch(
  () => studentImage.value,
  (url) => {
    if (url === undefined || url === '') {
      imageUploadModel.value = null
      imageUploadKey.value++
    }
  }
)

function clearStudentImage() {
  studentImage.value = undefined
}
</script>

<template>
  <div class="w-full flex min-h-0 flex-1 flex-col bg-card overflow-hidden lg:border-r border-default">
    <div class="shrink-0 border-b border-default bg-background px-4 py-2.5 sm:px-6 lg:px-8">
      <div class="flex w-full flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <h2 class="text-base font-semibold tracking-tight text-foreground sm:shrink-0">
          {{ $t('pages.allclass.student.studentInTitle') }}
        </h2>
        <div ref="searchAreaRef" class="relative min-w-0 w-full sm:max-w-xl">
          <CommonAppSearch v-model="studentSearchQuery" :placeholder="$t('pages.allclass.student.searchExisting')"
            class="w-full max-w-none" @focus="onSearchFocus" />
          <div v-if="suggestionsOpen && studentSearchQuery.trim()"
            class="absolute left-0 right-0 top-full z-50 mt-1 overflow-hidden rounded-md border border-default bg-white shadow-lg ring-1 ring-default/40 dark:bg-gray-900">
            <CommonAppLoadingState
              v-if="studentsFetchStatus === 'pending'"
              inline
              small
              compact
              class="w-full text-muted-foreground"
            />
            <div v-else-if="filteredStudents.length" class="max-h-52 overflow-auto">
              <button v-for="item in filteredStudents" :key="item.value" type="button"
                class="flex w-full items-center gap-2 border-b border-default/80 px-3 py-2.5 text-left transition-colors last:border-b-0 hover:bg-muted/60"
                @click="selectStudentLookupItem(item)">
                <UAvatar v-bind="item.avatar" size="sm" class="shrink-0 mr-10" />
                <div
                  class="grid min-w-0 flex-1 grid-cols-[4.5rem_minmax(0,1fr)_minmax(0,1fr)_5.5rem] gap-15 items-center text-sm">
                  <span class="truncate font-medium text-foreground">{{ item.studentId }}</span>
                  <span class="truncate text-foreground">{{ item.nameKm }}</span>
                  <span class="truncate text-foreground">{{ item.nameEn }}</span>
                  <span class="truncate text-muted-foreground tabular-nums">{{ item.phone }}</span>
                </div>
              </button>
            </div>
            <div v-else class="px-3 py-3 text-sm text-muted-foreground">
              {{ $t('pages.allclass.student.noStudentMatches') }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="flex min-h-0 flex-1 flex-col overflow-y-auto p-4 sm:p-6 lg:p-8">
      <div class="mx-auto flex w-full max-w-2xl flex-col gap-6">
        <div class="flex w-full flex-col gap-4">
          <div class="space-y-1.5">
            <label class="text-sm text-muted-foreground">{{ $t('product.image') }}</label>
            <UFileUpload :key="imageUploadKey" v-model="imageUploadModel" icon="i-lucide-image"
              :label="$t('pages.allclass.placeholders.image')" :description="$t('components.fileUploadFormats')"
              accept="image/*" :multiple="false" class="relative w-full">
              <template #default>
                <div v-if="studentImage"
                  class="relative flex h-48 w-full items-center justify-center overflow-hidden rounded-lg border border-default pointer-events-none">
                  <img :src="resolveUploadUrl(studentImage)" alt="" class="max-h-full max-w-full object-contain" />
                  <div class="absolute inset-0 bg-black/25 flex items-end justify-center p-2 pointer-events-none">
                    <span class="text-white text-xs font-medium">
                      {{ $t('components.fileUploadReplaceHint') }}
                    </span>
                  </div>
                </div>
                <UButton v-if="studentImage" icon="i-lucide-x" color="primary" variant="solid" size="xs"
                  class="absolute top-2 right-2 z-10 pointer-events-auto" :aria-label="$t('common.close')"
                  @click.stop.prevent="clearStudentImage" />
              </template>
            </UFileUpload>
          </div>

          <div class="flex flex-col sm:flex-row gap-3 w-full">
            <div class="flex-1 space-y-1.5">
              <label class="text-sm text-muted-foreground">{{ $t('product.nameKm') }} <span
                  class="text-error">*</span></label>
              <UInput v-model="nameKm" size="lg" class="w-full mt-1" autocomplete="off" @input="onNameKmInput" />
            </div>
            <div class="flex-1 space-y-1.5">
              <label class="text-sm text-muted-foreground">{{ $t('product.nameEn') }} <span
                  class="text-error">*</span></label>
              <UInput v-model="nameEn" size="lg" class="w-full mt-1" />
            </div>
          </div>

          <div class="flex flex-col sm:flex-row gap-3 w-full">
            <div class="flex-1 space-y-1.5">
              <label class="text-sm text-muted-foreground">{{ $t('product.gender') }}<span
                  class="text-error">*</span></label>
              <USelectMenu v-model="gender" :items="genderItems" value-key="value" label-key="label" size="lg"
                class="w-full mt-1" />
            </div>
            <div class="flex-1 space-y-1.5">
              <label class="text-sm text-muted-foreground">{{ $t('product.birthdate') }}<span
                  class="text-error">*</span></label>
              <UInputDate ref="birthdateInput" v-model="birthdateCalendar" size="lg" class="w-full mt-1">
                <template #trailing>
                  <UPopover :reference="birthdateInputRef?.inputsRef[3]?.$el">
                    <UButton color="neutral" variant="link" size="sm" icon="i-lucide-calendar"
                      :aria-label="$t('components.selectDate')" class="px-0" />
                    <template #content>
                      <UCalendar v-model="birthdateCalendar" class="p-2" />
                    </template>
                  </UPopover>
                </template>
              </UInputDate>
            </div>
          </div>

          <div class="flex flex-col sm:flex-row gap-3 w-full">
            <div class="flex-1 space-y-1.5">
              <label class="text-sm text-muted-foreground">
                {{ $t('product.phone') }} <span class="text-error">*</span>
              </label>
              <UInput v-model="customerPhone" type="tel" inputmode="numeric" autocomplete="tel" maxlength="11"
                :placeholder="$t('pages.allclass.student.phonePlaceholder')" size="lg" class="w-full mt-1"
                @input="onPhoneInput" />
            </div>
            <div class="flex-1 space-y-1.5">
              <label class="text-sm text-muted-foreground">{{ $t('product.province') }}<span
                  class="text-error">*</span></label>
              <USelectMenu v-model="province" :items="provinceItems" value-key="value" label-key="label" required
                :search-input="{ placeholder: $t('common.search') }"
                :placeholder="$t('pages.allclass.student.provincePlaceholder')" size="lg" class="w-full mt-1" />
            </div>
          </div>

          <div class="flex flex-col sm:flex-row gap-3 w-full">
            <div class="flex-1 space-y-1.5">
              <label class="text-sm text-muted-foreground">
                {{ $t('pages.allclass.student.startDate') }}
                <span class="text-error">*</span>
              </label>
              <UInputDate ref="enrollmentStartInput" v-model="enrollmentStartCalendar" size="lg" class="w-full mt-1">
                <template #trailing>
                  <UPopover :reference="enrollmentStartInputRef?.inputsRef[3]?.$el">
                    <UButton color="neutral" variant="link" size="sm" icon="i-lucide-calendar"
                      :aria-label="$t('components.selectDate')" class="px-0" />
                    <template #content>
                      <UCalendar v-model="enrollmentStartCalendar" class="p-2" />
                    </template>
                  </UPopover>
                </template>
              </UInputDate>
              <p class="text-xs text-muted-foreground">{{ $t('pages.allclass.student.startDateHint') }}</p>
            </div>
            <div class="flex-1 space-y-1.5">
              <label class="text-sm text-muted-foreground">
                {{ $t('pages.allclass.student.durationOnClass') }}
                <span class="text-error">*</span>
              </label>
              <UInput
                v-model="enrollmentDurationMonths"
                type="number"
                min="0.5"
                :max="classDurationMaxMonths ?? undefined"
                step="0.5"
                inputmode="decimal"
                :placeholder="
                  classDurationMaxMonths
                    ? $t('pages.allclass.student.durationPlaceholderMax', { max: classDurationMaxMonths })
                    : $t('pages.allclass.placeholders.duration')
                "
                size="lg"
                class="w-full mt-1"
              >
                <template #trailing>
                  <span class="text-sm text-muted-foreground shrink-0 pe-0.5 tabular-nums">
                    {{ durationInputTrailing }}
                  </span>
                </template>
              </UInput>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
