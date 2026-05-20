<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { DropdownMenuItem } from '~/types/nuxt-ui'
import { formatCurrency } from '~/utils/format/currency'
import { formatClassDuration } from '~/utils/format/duration'
import { resolveUploadUrl } from '~/utils/helpers/mediaUrl'
import type { StudentEnrollmentRow } from '~/types'
import { totalEnrollmentDiscountAmount } from '~/utils/helpers/mapStudentEnrollmentRow'
import certificateImageUrl from '~/assets/images/certificate.png'

const open = defineModel<boolean>('open', { default: false })
const range = defineModel<{ start?: unknown; end?: unknown }>('range', {
  default: () => ({ start: undefined, end: undefined }),
})
const pagination = defineModel<any>('pagination', {
  default: () => ({ pageIndex: 0, pageSize: 50 }),
})

const props = defineProps<{
  studentId: string
  studentName?: string
  studentGender?: string
  studentBirthdate?: string
  studentImage?: string
  data: StudentEnrollmentRow[]
  loading?: boolean
  total: number
}>()

const { t, te } = useI18n()
const toast = useToast()

const certificatePreviewRow = ref<StudentEnrollmentRow | null>(null)
const generatedCertificateUrl = ref('')
const isGeneratingCertificate = ref(false)
const isCertificateDataEditorOpen = ref(false)
const certificateCanvas = ref<HTMLCanvasElement | null>(null)
const certificateImageUploadModel = ref<File | null>(null)
const certificateImageUploadKey = ref(0)
const showCertificatePreview = computed(() => certificatePreviewRow.value != null)

const emit = defineEmits<{
  deleteEnrollment: [row: StudentEnrollmentRow]
}>()

function openCertificatePreview(entry: StudentEnrollmentRow) {
  certificatePreviewRow.value = entry
  resetCertificateDataEditor()
}

function closeCertificatePreview() {
  certificatePreviewRow.value = null
  generatedCertificateUrl.value = ''
  isCertificateDataEditorOpen.value = false
  certificateDataEdits.value = {}
  certificateProfileImage.value = ''
  certificateImageUploadModel.value = null
  certificateImageUploadKey.value++
}

function filePartSlug(raw: string) {
  return raw.replace(/[^\w.-]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 64) || 'enrollment'
}

async function downloadCertificate() {
  const row = certificatePreviewRow.value
  const sid = filePartSlug(props.studentId?.trim() || 'student')
  const eid = row?.id != null ? filePartSlug(String(row.id)) : 'enrollment'
  const filename = `certificate-${sid}-${eid}.png`
  try {
    const url = await generateCertificateImage()
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.rel = 'noopener'
    document.body.appendChild(a)
    a.click()
    a.remove()
  } catch {
    toast.add({
      title: t('pages.allstudent.enrollmentModal.certificatePreview.downloadFailed'),
      color: 'error',
    })
  }
}

function firstText(values: unknown[]) {
  for (const value of values) {
    const text = String(value ?? '').trim()
    if (text) return text
  }
  return ''
}

function splitStudentName(raw: string) {
  const parts = raw.split(/\s*[\/·]\s*/).map((part) => part.trim()).filter(Boolean)
  return {
    km: parts.length > 1 ? parts[0] : raw,
    en: parts.length > 1 ? parts.slice(1).join(' · ') : raw,
  }
}

function genderLabels(raw: string) {
  const value = raw.trim().toLowerCase()
  if (value === 'male' || value === 'm' || value === 'ប្រុស') {
    return { en: 'Male', km: 'ប្រុស' }
  }
  if (value === 'female' || value === 'f' || value === 'ស្រី') {
    return { en: 'Female', km: 'ស្រី' }
  }
  if (value === 'other') return { en: 'Other', km: 'ផ្សេងៗ' }
  return { en: raw || '—', km: raw || '—' }
}

const khmerDigits: Record<string, string> = {
  0: '០',
  1: '១',
  2: '២',
  3: '៣',
  4: '៤',
  5: '៥',
  6: '៦',
  7: '៧',
  8: '៨',
  9: '៩',
}

const certificateKhmerTextMap: Record<string, string> = {
  'general english': 'ភាសាអង់គ្លេសទូទៅ',
  'ielts preparation': 'វគ្គត្រៀមប្រឡង IELTS',
  'conversation lab': 'ថ្នាក់សន្ទនាភាសាអង់គ្លេស',
  'english communication': 'ទំនាក់ទំនងភាសាអង់គ្លេស',
  'mathematics i': 'គណិតវិទ្យា ១',
  'computer basics': 'មូលដ្ឋានគ្រឹះកុំព្យូទ័រ',
  beginner: 'ដំបូង',
  elementary: 'បឋម',
  'pre-intermediate': 'មុនមធ្យម',
  intermediate: 'មធ្យម',
  advanced: 'កម្រិតខ្ពស់',
  month: 'ខែ',
  months: 'ខែ',
  year: 'ឆ្នាំ',
  years: 'ឆ្នាំ',
}

function toKhmerDigits(raw: string) {
  return raw.replace(/\d/g, (digit) => khmerDigits[digit] || digit)
}

function toKhmerCertificateText(raw: string) {
  const text = raw.trim()
  const mapped = certificateKhmerTextMap[text.toLowerCase()]
  if (mapped) return mapped

  return toKhmerDigits(text)
    .replace(/\bmonths?\b/gi, 'ខែ')
    .replace(/\byears?\b/gi, 'ឆ្នាំ')
}

type CertificateData = {
  nameKm: string
  nameEn: string
  genderEn: string
  genderKm: string
  birthdateEn: string
  birthdateKm: string
  courseEn: string
  courseKm: string
  levelEn: string
  levelKm: string
  durationEn: string
  durationKm: string
  issuedDate: string
}

type CertificateDataKey = keyof CertificateData

const certificateDataEdits = ref<Partial<Record<CertificateDataKey, string>>>({})
const certificateProfileImage = ref('')

const certificateDataFields: Array<{ key: CertificateDataKey; label: string }> = [
  { key: 'nameKm', label: 'Name Khmer' },
  { key: 'nameEn', label: 'Name English' },
  { key: 'genderKm', label: 'Gender Khmer' },
  { key: 'genderEn', label: 'Gender English' },
  { key: 'birthdateKm', label: 'DOB Khmer' },
  { key: 'birthdateEn', label: 'DOB English' },
  { key: 'courseKm', label: 'Course Khmer' },
  { key: 'courseEn', label: 'Course English' },
  { key: 'levelKm', label: 'Level Khmer' },
  { key: 'levelEn', label: 'Level English' },
  { key: 'durationKm', label: 'Duration Khmer' },
  { key: 'durationEn', label: 'Duration English' },
  { key: 'issuedDate', label: 'Issued Date' },
]

function baseCertificateDetails(): CertificateData {
  const row = certificatePreviewRow.value
  const fallbackName = props.studentName?.trim() || ''
  const split = splitStudentName(firstText([row?.studentName, fallbackName]))
  const gender = genderLabels(firstText([row?.gender, props.studentGender]))
  const birthdate = cellDate(firstText([row?.birthdate, props.studentBirthdate]))
  const course = firstText([row?.courseName, '—'])
  const level = firstText([row?.level, row?.classLevel, row?.courseLevel, '—'])
  const duration = firstText([
    row?.classDuration,
    row?.duration,
    row?.durationClass,
    row?.courseDuration,
    [cellDate(row?.startDate), cellDate(row?.endDate)].filter((v) => v && v !== '—').join(' - '),
    '—',
  ])
  return {
    nameKm: firstText([row?.nameKm, split.km, fallbackName, '—']),
    nameEn: firstText([row?.nameEn, split.en, fallbackName, '—']),
    genderEn: gender.en,
    genderKm: gender.km,
    birthdateEn: birthdate,
    birthdateKm: toKhmerDigits(birthdate),
    courseEn: course,
    courseKm: toKhmerCertificateText(course),
    levelEn: level,
    levelKm: toKhmerCertificateText(level),
    durationEn: duration,
    durationKm: toKhmerCertificateText(duration),
    issuedDate: cellDate(new Date().toISOString()),
  }
}

function certificateDetails(): CertificateData {
  return {
    ...baseCertificateDetails(),
    ...certificateDataEdits.value,
  }
}

function resetCertificateDataEditor() {
  certificateDataEdits.value = { ...baseCertificateDetails() }
  certificateProfileImage.value = props.studentImage?.trim() || ''
  certificateImageUploadModel.value = null
  certificateImageUploadKey.value++
}

function updateCertificateData(key: CertificateDataKey, value: string | number) {
  const text = String(value ?? '')
  const next = {
    ...certificateDataEdits.value,
    [key]: text,
  }

  if (key === 'birthdateEn') next.birthdateKm = toKhmerDigits(text)
  if (key === 'courseEn') next.courseKm = toKhmerCertificateText(text)
  if (key === 'levelEn') next.levelKm = toKhmerCertificateText(text)
  if (key === 'durationEn') next.durationKm = toKhmerCertificateText(text)
  if (key === 'genderEn') next.genderKm = genderLabels(text).km

  certificateDataEdits.value = next
  void renderCertificatePreview()
}

function clearCertificateProfileImage() {
  certificateProfileImage.value = ''
  certificateImageUploadModel.value = null
  certificateImageUploadKey.value++
  void renderCertificatePreview()
}

let certificateTemplatePromise: Promise<HTMLImageElement> | null = null

function loadCertificateTemplate() {
  if (certificateTemplatePromise) return certificateTemplatePromise
  certificateTemplatePromise = new Promise<HTMLImageElement>((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = certificateImageUrl
  })
  return certificateTemplatePromise
}

function loadCertificateImage(src: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const img = new Image()
    if (/^https?:\/\//i.test(src)) img.crossOrigin = 'anonymous'
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = src
  })
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(file)
  })
}

function drawText(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, options: {
  font?: string
  fillStyle?: string
  align?: CanvasTextAlign
  maxWidth?: number
} = {}) {
  ctx.save()
  ctx.font = options.font || '18px "Times New Roman", "Khmer OS Siemreap", serif'
  ctx.fillStyle = options.fillStyle || '#132f43'
  ctx.textAlign = options.align || 'left'
  ctx.textBaseline = 'middle'
  const width = Math.min(ctx.measureText(text).width, options.maxWidth ?? Number.POSITIVE_INFINITY)
  ctx.fillText(text, x, y, options.maxWidth)
  ctx.restore()
  const fontSize = Number((options.font || '').match(/(\d+)px/)?.[1] ?? 18)
  return {
    x: options.align === 'center' ? x - width / 2 : x,
    y: y - fontSize / 2,
    width,
    height: fontSize,
  }
}

function drawCoverImage(
  ctx: CanvasRenderingContext2D,
  img: HTMLImageElement,
  x: number,
  y: number,
  width: number,
  height: number,
) {
  const sourceRatio = img.naturalWidth / img.naturalHeight
  const targetWidth = Math.min(width, height * sourceRatio)
  const targetHeight = Math.min(height, width / sourceRatio)
  const targetX = x + (width - targetWidth) / 2
  const targetY = y + (height - targetHeight) / 2

  ctx.save()
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(x, y, width, height)
  ctx.drawImage(img, targetX, targetY, targetWidth, targetHeight)
  ctx.restore()
}

type CertificateTextKey =
  | 'nameKm'
  | 'genderKm'
  | 'birthdateKm'
  | 'courseKm'
  | 'levelKm'
  | 'durationKm'
  | 'nameEn'
  | 'genderEn'
  | 'birthdateEn'
  | 'courseEn'
  | 'levelEn'
  | 'durationEn'
  | 'issuedDate'

const certificateTextPositions = ref<Record<CertificateTextKey, { x: number; y: number }>>({
  nameKm: { x: 440, y: 617 },
  genderKm: { x: 231, y: 710 },
  birthdateKm: { x: 601, y: 710 },
  courseKm: { x: 574, y: 772 },
  levelKm: { x: 277, y: 842 },
  durationKm: { x: 385, y: 912 },
  nameEn: { x: 1419, y: 617 },
  genderEn: { x: 1120, y: 710 },
  birthdateEn: { x: 1500, y: 710 },
  courseEn: { x: 1267, y: 778 },
  levelEn: { x: 1126, y: 847 },
  durationEn: { x: 1278, y: 914 },
  issuedDate: { x: 1577, y: 1058 },
})

const draggingCertificateText = ref<{
  key: CertificateTextKey
  offsetX: number
  offsetY: number
} | null>(null)

let certificateHitBoxes: Array<{
  key: CertificateTextKey
  x: number
  y: number
  width: number
  height: number
}> = []

function certificateTextFields(data: ReturnType<typeof certificateDetails>) {
  const blue = '#143249'
  const black = '#111827'
  const kmFont = 'bold 42px "Khmer OS Muol Light", "Khmer OS Muol", "Khmer UI", "Khmer OS Siemreap", serif'
  const kmTextFont = 'bold 36px "Khmer OS Battambang", "Khmer OS Siemreap", "Khmer UI", "Noto Serif Khmer", serif'
  const enFont = 'bold 36px "Times New Roman", serif'
  const enBoldFont = 'bold 36px "Times New Roman", serif'

  return [
    { key: 'nameKm' as const, text: data.nameKm, font: kmFont, fillStyle: black, maxWidth: 520 },
    { key: 'genderKm' as const, text: data.genderKm, font: kmTextFont, fillStyle: black, maxWidth: 320 },
    { key: 'birthdateKm' as const, text: data.birthdateKm, font: kmTextFont, fillStyle: black, maxWidth: 300 },
    { key: 'courseKm' as const, text: data.courseKm, font: kmTextFont, fillStyle: black, maxWidth: 560 },
    { key: 'levelKm' as const, text: data.levelKm, font: kmTextFont, fillStyle: black, maxWidth: 420 },
    { key: 'durationKm' as const, text: data.durationKm, font: kmTextFont, fillStyle: black, maxWidth: 500 },
    { key: 'nameEn' as const, text: data.nameEn, font: 'bold 48px "Times New Roman", serif', fillStyle: blue, align: 'center' as const, maxWidth: 700 },
    { key: 'genderEn' as const, text: data.genderEn, font: enFont, fillStyle: black, maxWidth: 220 },
    { key: 'birthdateEn' as const, text: data.birthdateEn, font: enFont, fillStyle: black, maxWidth: 300 },
    { key: 'courseEn' as const, text: data.courseEn, font: enFont, fillStyle: black, maxWidth: 560 },
    { key: 'levelEn' as const, text: data.levelEn, font: enFont, fillStyle: black, maxWidth: 420 },
    { key: 'durationEn' as const, text: data.durationEn, font: enFont, fillStyle: black, maxWidth: 500 },
    { key: 'issuedDate' as const, text: data.issuedDate, font: enBoldFont, fillStyle: blue, maxWidth: 280 },
  ]
}

async function drawCertificateProfile(ctx: CanvasRenderingContext2D, data: ReturnType<typeof certificateDetails>) {
  const src = resolveUploadUrl(certificateProfileImage.value || props.studentImage?.trim())
  if (!src) return

  try {
    const img = await loadCertificateImage(src)
    const x = 875
    const y = 1050
    const width = 200
    const height = 240
    const centerX = x + width / 2
    drawCoverImage(ctx, img, x, y, width, height)
    
  } catch {
    // Keep certificate generation working even if a profile image URL cannot be loaded.
  }
}

async function renderCertificateToCanvas(canvas: HTMLCanvasElement, options: { collectHitBoxes?: boolean } = {}) {
  const img = await loadCertificateTemplate()
  canvas.width = img.naturalWidth || 1024
  canvas.height = img.naturalHeight || 724
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('Canvas is not available')
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height)

  const data = certificateDetails()
  const nextHitBoxes: typeof certificateHitBoxes = []
  for (const field of certificateTextFields(data)) {
    const position = certificateTextPositions.value[field.key]
    const box = drawText(ctx, field.text, position.x, position.y, field)
    nextHitBoxes.push({
      key: field.key,
      ...box,
    })
  }
  await drawCertificateProfile(ctx, data)
  if (options.collectHitBoxes) certificateHitBoxes = nextHitBoxes
}

async function renderCertificatePreview() {
  const canvas = certificateCanvas.value
  if (!canvas) return
  await renderCertificateToCanvas(canvas, { collectHitBoxes: true })
}

async function generateCertificateImage() {
  const canvas = document.createElement('canvas')
  await renderCertificateToCanvas(canvas)

  return canvas.toDataURL('image/png')
}

async function refreshCertificateImage() {
  if (!certificatePreviewRow.value) return
  isGeneratingCertificate.value = true
  try {
    await nextTick()
    await renderCertificatePreview()
    generatedCertificateUrl.value = ''
  } catch {
    generatedCertificateUrl.value = certificateImageUrl
    toast.add({
      title: t('pages.allstudent.enrollmentModal.certificatePreview.generateFailed'),
      color: 'error',
    })
  } finally {
    isGeneratingCertificate.value = false
  }
}

function certificateCanvasPoint(event: PointerEvent) {
  const canvas = certificateCanvas.value
  if (!canvas) return null
  const rect = canvas.getBoundingClientRect()
  return {
    x: ((event.clientX - rect.left) / rect.width) * canvas.width,
    y: ((event.clientY - rect.top) / rect.height) * canvas.height,
  }
}

function hitCertificateText(point: { x: number; y: number }) {
  const padding = 10
  for (const box of [...certificateHitBoxes].reverse()) {
    if (
      point.x >= box.x - padding &&
      point.x <= box.x + box.width + padding &&
      point.y >= box.y - padding &&
      point.y <= box.y + box.height + padding
    ) {
      return box.key
    }
  }
  return null
}

function onCertificatePointerDown(event: PointerEvent) {
  const point = certificateCanvasPoint(event)
  if (!point) return
  const key = hitCertificateText(point)
  if (!key) return
  const position = certificateTextPositions.value[key]
  draggingCertificateText.value = {
    key,
    offsetX: point.x - position.x,
    offsetY: point.y - position.y,
  }
  ;(event.currentTarget as HTMLCanvasElement | null)?.setPointerCapture?.(event.pointerId)
}

function onCertificatePointerMove(event: PointerEvent) {
  const drag = draggingCertificateText.value
  if (!drag) return
  const point = certificateCanvasPoint(event)
  if (!point) return
  certificateTextPositions.value[drag.key] = {
    x: Math.round(point.x - drag.offsetX),
    y: Math.round(point.y - drag.offsetY),
  }
  void renderCertificatePreview()
}

function onCertificatePointerUp(event: PointerEvent) {
  draggingCertificateText.value = null
  ;(event.currentTarget as HTMLCanvasElement | null)?.releasePointerCapture?.(event.pointerId)
}

function getDropdownActions(entry: StudentEnrollmentRow): DropdownMenuItem[][] {
  return [
    [
      {
        label: t('pages.allstudent.enrollmentModal.actions.certificate'),
        icon: 'i-lucide-award',
        onSelect: () => openCertificatePreview(entry),
      },
      {
        label: t('actions.delete'),
        icon: 'i-lucide-trash',
        color: 'error' as const,
        onSelect: () => emit('deleteEnrollment', entry),
      },
    ],
  ]
}

watch(open, (isOpen) => {
  if (!isOpen) closeCertificatePreview()
})

watch(certificatePreviewRow, () => {
  if (certificatePreviewRow.value) void refreshCertificateImage()
})

watch(certificateImageUploadModel, async (file) => {
  if (!file) return
  try {
    certificateProfileImage.value = await readFileAsDataUrl(file)
    void renderCertificatePreview()
  } catch {
    certificateImageUploadModel.value = null
  }
})

/** Calendar date only: `dd/mm/yyyy` (no time). */
function cellDate(val: string | undefined) {
  const raw = val != null ? String(val).trim() : ''
  if (raw === '') return '—'
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return raw
  const dd = String(d.getDate()).padStart(2, '0')
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const yyyy = String(d.getFullYear())
  return `${dd}/${mm}/${yyyy}`
}

const footerSums = computed(() => {
  const rows = props.data ?? []
  const sumNum = (get: (r: StudentEnrollmentRow) => number) =>
    rows.reduce((acc, r) => acc + get(r), 0)
  return {
    totalPrice: sumNum((r) => Number(r.totalPrice || 0)),
    discountPrice: sumNum((r) => totalEnrollmentDiscountAmount(r)),
    priceAfterDiscount: sumNum((r) =>
      Number(r.invoiceGrandTotal ?? r.priceAfterDiscount ?? 0),
    ),
  }
})

const columns = computed(() => [
  { accessorKey: 'no', header: t('pages.allstudent.enrollmentModal.columns.no'), enableSorting: false },
  {
    accessorKey: 'courseName',
    header: t('pages.allstudent.enrollmentModal.columns.courseName'),
    footer: t('pages.allstudent.enrollmentModal.footer.courseCount', { count: props.total }),
  },
  { accessorKey: 'className', header: t('pages.allstudent.enrollmentModal.columns.className') },
  { accessorKey: 'durationMonths', header: t('pages.allstudent.enrollmentModal.columns.duration') },
  { accessorKey: 'startDate', header: t('pages.allstudent.enrollmentModal.columns.startDate') },
  { accessorKey: 'endDate', header: t('pages.allstudent.enrollmentModal.columns.endDate') },
  {
    accessorKey: 'totalPrice',
    header: t('pages.allstudent.enrollmentModal.columns.totalPrice'),
    footer: formatCurrency(footerSums.value.totalPrice, 'USD'),
  },
  {
    accessorKey: 'discountPrice',
    header: t('pages.allstudent.enrollmentModal.columns.discountPrice'),
    footer: formatCurrency(footerSums.value.discountPrice, 'USD'),
  },
  {
    accessorKey: 'priceAfterDiscount',
    header: t('pages.allstudent.enrollmentModal.columns.priceAfterDiscount'),
    footer: formatCurrency(footerSums.value.priceAfterDiscount, 'USD'),
  },
  { accessorKey: 'registerDate', header: t('pages.allstudent.enrollmentModal.columns.registerDate') },
  { id: 'action', header: t('common.actions') },
])
</script>

<template>
  <UModal
    v-model:open="open"
    :dismissible="false"
    :ui="{ content: 'sm:max-w-7xl h-[98vh] flex flex-col' }"
  >
    <template #header>
      <div class="flex items-center justify-between w-full gap-3 flex-wrap">
        <div class="flex min-w-0 flex-1 flex-col gap-0.5">
          <template v-if="showCertificatePreview">
            <div class="flex items-center gap-2 min-w-0">
              <UButton
                icon="i-lucide-arrow-left"
                color="neutral"
                variant="ghost"
                size="sm"
                class="shrink-0"
                :aria-label="$t('pages.allstudent.enrollmentModal.certificatePreview.back')"
                @click="closeCertificatePreview"
              />
              <div class="min-w-0 flex-1 flex flex-col gap-0.5">
                <h3 class="truncate font-semibold text-foreground">
                  {{ $t('pages.allstudent.enrollmentModal.certificatePreview.title') }}
                </h3>
              </div>
            </div>
          </template>
          <template v-else>
            <h3 class="truncate font-semibold text-foreground">
              {{ studentName?.trim() || $t('pages.allstudent.enrollmentModal.titleFallback') }}
            </h3>
            <p class="text-xs text-muted-foreground truncate">
              {{ $t('pages.allstudent.enrollmentModal.subtitle', { id: studentId }) }}
            </p>
          </template>
        </div>
        <div class="flex items-center gap-8 shrink-0">
          <CommonAppDatepicker v-if="!showCertificatePreview" v-model:range="range" />
          <UButton
            v-if="showCertificatePreview"
            icon="i-lucide-pencil"
            color="neutral"
            variant="outline"
            size="sm"
            class="shrink-0"
            @click="isCertificateDataEditorOpen = !isCertificateDataEditorOpen"
          >
            Edit Data
          </UButton>
          <UButton
            v-if="showCertificatePreview"
            icon="i-lucide-download"
            color="neutral"
            variant="outline"
            size="sm"
            class="shrink-0"
            :aria-label="$t('pages.allstudent.enrollmentModal.certificatePreview.download')"
            @click="downloadCertificate"
          >
            {{ $t('pages.allstudent.enrollmentModal.certificatePreview.download') }}
          </UButton>
          <UButton
            icon="i-lucide-x"
            color="neutral"
            variant="ghost"
            size="sm"
            square
            class="shrink-0"
            :aria-label="$t('common.close')"
            @click="open = false"
          />
        </div>
      </div>
    </template>

    <template #body>
      <div class="flex min-h-0 flex-1 flex-col gap-3">
        <div
          v-if="showCertificatePreview"
          class="grid min-h-0 flex-1 gap-3 overflow-auto -my-3"
          :class="isCertificateDataEditorOpen ? 'grid-cols-1 lg:grid-cols-[minmax(0,1fr)_24rem]' : 'grid-cols-1'"
        >
          <div class="flex min-h-0 flex-col items-center justify-center">
            <CommonAppLoadingState
              v-if="isGeneratingCertificate"
              compact
              class="py-8"
            />
            <canvas
              v-show="!isGeneratingCertificate"
              ref="certificateCanvas"
              class="mx-auto block h-auto max-h-[calc(98vh-9rem)] w-auto max-w-full touch-none cursor-grab border border-gray-500 bg-gray-200 object-contain active:cursor-grabbing"
              @pointerdown="onCertificatePointerDown"
              @pointermove="onCertificatePointerMove"
              @pointerup="onCertificatePointerUp"
              @pointercancel="onCertificatePointerUp"
              @pointerleave="onCertificatePointerUp"
            />
          </div>
          <div
            v-if="isCertificateDataEditorOpen"
            class="flex max-h-[calc(98vh-9rem)] min-h-0 flex-col overflow-hidden rounded-lg border border-default bg-muted/30 p-3"
          >
            <div class="mb-3">
              <h4 class="text-sm font-semibold text-foreground">
                Edit Certificate Data
              </h4>
            </div>
            <div class="shrink-0">
              <UFormField label="Profile Image" size="xs" class="w-full">
                <UFileUpload
                  :key="certificateImageUploadKey"
                  v-model="certificateImageUploadModel"
                  icon="i-lucide-image"
                  label="Upload profile image"
                  description="PNG, JPG or GIF"
                  accept="image/*"
                  :multiple="false"
                  class="relative w-full"
                >
                  <template #default>
                    <div
                      v-if="certificateProfileImage"
                      class="relative flex h-40 w-full items-center justify-center overflow-hidden border border-default pointer-events-none"
                    >
                      <img
                        :src="certificateProfileImage"
                        alt=""
                        class="max-h-full max-w-full object-contain"
                      />
                      <div class="absolute inset-0 flex items-end justify-center bg-black/25 p-2">
                        <span class="text-xs font-medium text-white">
                          Click or drop to replace image
                        </span>
                      </div>
                    </div>
                    <UButton
                      v-if="certificateProfileImage"
                      icon="i-lucide-x"
                      color="primary"
                      variant="solid"
                      size="xs"
                      class="absolute top-2 right-2 z-10 pointer-events-auto"
                      :aria-label="$t('common.close')"
                      @click.stop.prevent="clearCertificateProfileImage"
                    />
                  </template>
                </UFileUpload>
              </UFormField>
            </div>
            <div class="mt-3 min-h-0 flex-1 space-y-3 overflow-y-auto overflow-x-hidden pr-1">
              <UFormField
                v-for="field in certificateDataFields"
                :key="field.key"
                :label="field.label"
                size="md"
                class="w-full"
              >
                <UInput
                  :model-value="certificateDataEdits[field.key] ?? ''"
                  size="md"
                  class="w-full"
                  @update:model-value="updateCertificateData(field.key, $event)"
                />
              </UFormField>
            </div>
          </div>
        </div>
        <TableApptable
          v-else
          :columns="columns"
          :data="data"
          :loading="loading"
          :total-rows="total"
          server-pagination
          v-model:pagination="pagination"
          :selectable="false"
          :virtualize="false"
          :get-row-actions="getDropdownActions"
          class="min-h-0 flex-1"
          :ui="{ root: 'min-w-full', td: 'empty:p-2' }"
        >
          <template #no-cell="{ row }">
            <span class="text-xs text-muted-foreground tabular-nums">{{
              pagination.pageIndex * pagination.pageSize + row.index + 1
            }}</span>
          </template>
          <template #durationMonths-cell="{ row }">
            <span class="text-sm text-muted-foreground">
              {{
                formatClassDuration(
                  row.original.durationMonths || row.original.classDuration || '',
                  t,
                  te,
                ) || '—'
              }}
            </span>
          </template>
          <template #startDate-cell="{ row }">
            <span class="text-sm text-muted-foreground">{{ cellDate(String(row.original.startDate || '')) }}</span>
          </template>
          <template #endDate-cell="{ row }">
            <span class="text-sm text-muted-foreground">{{ cellDate(String(row.original.endDate || '')) }}</span>
          </template>
          <template #registerDate-cell="{ row }">
            <span class="text-sm text-muted-foreground">{{ cellDate(String(row.original.registerDate || '')) }}</span>
          </template>
          <template #totalPrice-cell="{ row }">
            <span class="tabular-nums font-medium">{{ formatCurrency(Number(row.original.totalPrice || 0), 'USD') }}</span>
          </template>
          <template #discountPrice-cell="{ row }">
            <span class="tabular-nums">{{
              formatCurrency(totalEnrollmentDiscountAmount(row.original), 'USD')
            }}</span>
          </template>
          <template #priceAfterDiscount-cell="{ row }">
            <span class="tabular-nums font-semibold text-foreground">
              {{
                formatCurrency(
                  Number(row.original.invoiceGrandTotal ?? row.original.priceAfterDiscount ?? 0),
                  'USD',
                )
              }}
            </span>
          </template>
        </TableApptable>
      </div>
    </template>
  </UModal>
</template>
