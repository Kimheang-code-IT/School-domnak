<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { DropdownMenuItem } from '~/types/nuxt-ui'
import { formatCurrency } from '~/utils/format/currency'
import { formatClassDuration } from '~/utils/format/duration'
import type { StudentEnrollmentRow } from '~/types'
import { totalEnrollmentDiscountAmount } from '~/utils/helpers/mapStudentEnrollmentRow'
import { formatStudentCode } from '~/utils/format/studentCode'
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
const { can, PERMISSIONS } = useCan()

const displayStudentCode = computed(() =>
  formatStudentCode(props.studentId) || props.studentId?.trim() || '',
)

const certificatePreviewRow = ref<StudentEnrollmentRow | null>(null)
const generatedCertificateUrl = ref('')
const isGeneratingCertificate = ref(false)
const isCertificateDataEditorOpen = ref(false)
const certificateCanvas = ref<HTMLCanvasElement | null>(null)
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
}

function filePartSlug(raw: string) {
  return raw.replace(/[^\w.-]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 64) || 'enrollment'
}

async function downloadCertificate() {
  const row = certificatePreviewRow.value
  const sid = filePartSlug(displayStudentCode.value || props.studentId?.trim() || 'student')
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

function toKhmerDigits(raw: string) {
  return raw.replace(/\d/g, (digit) => khmerDigits[digit] || digit)
}

/** Only fields drawn on the Microsoft Office certificate template. */
type CertificateData = {
  nameKm: string
  finishDate: string
}

type CertificateDataKey = keyof CertificateData
type CertificateTextKey = CertificateDataKey

const certificateDataEdits = ref<Partial<Record<CertificateDataKey, string>>>({})

const certificateDataFields: Array<{ key: CertificateDataKey; label: string }> = [
  { key: 'nameKm', label: 'ឈ្មោះខ្មែរ / Khmer Name' },
  { key: 'finishDate', label: 'កាលបរិច្ឆេទបញ្ចប់ / Finish Date' },
]

function baseCertificateDetails(): CertificateData {
  const row = certificatePreviewRow.value
  const fallbackName = props.studentName?.trim() || ''
  const split = splitStudentName(firstText([row?.studentName, fallbackName]))
  const finishRaw = cellDate(firstText([row?.endDate, '']))
  return {
    nameKm: firstText([row?.nameKm, split.km, fallbackName, '—']),
    finishDate: finishRaw === '—' ? '—' : toKhmerDigits(finishRaw),
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
}

function updateCertificateData(key: CertificateDataKey, value: string | number) {
  certificateDataEdits.value = {
    ...certificateDataEdits.value,
    [key]: String(value ?? ''),
  }
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

function drawText(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, options: {
  font?: string
  fillStyle?: string
  align?: CanvasTextAlign
  maxWidth?: number
} = {}) {
  ctx.save()
  ctx.font = options.font || '18px "Noto Sans Khmer", "Khmer OS Siemreap", sans-serif'
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

/** Pixel positions for certificate.png (2000×1414). Drag on canvas to fine-tune. */
const certificateTextPositions = ref<Record<CertificateTextKey, { x: number; y: number }>>({
  nameKm: { x: 1000, y: 680 },
  finishDate: { x: 920, y: 1070 },
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
  const ink = '#143249'
  const nameFont = 'bold 52px "Khmer OS Muol Light", "Khmer OS Muol", "Noto Serif Khmer", "Khmer UI", serif'
  const dateFont = 'bold 36px "Khmer OS Battambang", "Noto Sans Khmer", "Khmer UI", sans-serif'

  return [
    {
      key: 'nameKm' as const,
      text: data.nameKm,
      font: nameFont,
      fillStyle: ink,
      align: 'center' as const,
      maxWidth: 1100,
    },
    {
      key: 'finishDate' as const,
      text: data.finishDate,
      font: dateFont,
      fillStyle: ink,
      align: 'left' as const,
      maxWidth: 420,
    },
  ]
}

async function renderCertificateToCanvas(canvas: HTMLCanvasElement, options: { collectHitBoxes?: boolean } = {}) {
  const img = await loadCertificateTemplate()
  canvas.width = img.naturalWidth || 2000
  canvas.height = img.naturalHeight || 1414
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
  const actions: DropdownMenuItem[] = []
  if (can(PERMISSIONS.allStudentPreviewCertificate) || can(PERMISSIONS.allStudentDownloadCertificate)) {
    actions.push({
      label: t('pages.allstudent.enrollmentModal.actions.certificate'),
      icon: 'i-lucide-award',
      onSelect: () => openCertificatePreview(entry),
    })
  }
  if (can(PERMISSIONS.allStudentDeleteEnrollment)) {
    actions.push({
      label: t('actions.delete'),
      icon: 'i-lucide-trash',
      color: 'error' as const,
      onSelect: () => emit('deleteEnrollment', entry),
    })
  }
  return actions.length ? [actions] : []
}

watch(open, (isOpen) => {
  if (!isOpen) closeCertificatePreview()
})

watch(certificatePreviewRow, () => {
  if (certificatePreviewRow.value) void refreshCertificateImage()
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
              {{ $t('pages.allstudent.enrollmentModal.subtitle', { id: displayStudentCode }) }}
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
              <p class="mt-1 text-xs text-muted-foreground">
                Only Khmer name and finish date are printed on the certificate.
              </p>
            </div>
            <div class="min-h-0 flex-1 space-y-3 overflow-y-auto overflow-x-hidden pr-1">
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
