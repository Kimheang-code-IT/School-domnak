import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from '#imports'
import { usePosApi } from '~/utils/api'
import {
  cartLinesFromBundle,
  linesForPreviewBundle,
  normalizePreviewBundles,
  previewHeaderFromBundle,
  type InvoicePreviewRow,
} from '~/utils/helpers/invoicePreview'

function parseInvoiceQuery(raw: string): string[] {
  return raw
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean)
}

export function usePosInvoicePreview() {
  const route = useRoute()
  const router = useRouter()
  const posApi = usePosApi()

  const previewBundles = ref<InvoicePreviewRow[]>([])
  const currentPreviewIndex = ref(0)
  const isLoadingPreview = ref(false)
  const previewError = ref<string | null>(null)

  const shouldAutoOpenPrintDialog = computed(() => String(route.query.autoPrint || '') === '1')

  const previewInvoiceCount = computed(() => previewBundles.value.length)

  const hasMultiplePreviewInvoices = computed(() => previewInvoiceCount.value > 1)

  const currentPreviewBundle = computed(
    () => previewBundles.value[currentPreviewIndex.value] ?? null,
  )

  const currentPreviewLines = computed(() => cartLinesFromBundle(currentPreviewBundle.value))

  const currentPreviewHeader = computed(() =>
    previewHeaderFromBundle(currentPreviewBundle.value),
  )

  const selectedReportInvoices = computed(() =>
    linesForPreviewBundle(currentPreviewBundle.value),
  )

  const selectedReportInvoice = computed(() => currentPreviewHeader.value)

  const hasReportPreviewInvoices = computed(
    () => previewBundles.value.length > 0 && Boolean(currentPreviewBundle.value),
  )

  const canGoPrevPreview = computed(() => currentPreviewIndex.value > 0)

  const canGoNextPreview = computed(
    () => currentPreviewIndex.value < previewBundles.value.length - 1,
  )

  function applyPreviewBundles(bundles: InvoicePreviewRow[]) {
    previewBundles.value = normalizePreviewBundles(bundles)
    const routeIndex = Number(route.query.previewIndex)
    const startIndex =
      Number.isInteger(routeIndex) &&
      routeIndex >= 0 &&
      routeIndex < previewBundles.value.length
        ? routeIndex
        : 0
    currentPreviewIndex.value = startIndex
  }

  function applyPreviewBundle(bundle: { invoices?: InvoicePreviewRow[]; invoice?: InvoicePreviewRow | null }) {
    const source = bundle.invoice
      ? [bundle.invoice]
      : Array.isArray(bundle.invoices)
        ? bundle.invoices
        : []
    applyPreviewBundles(source)
  }

  function goToPreviewIndex(index: number) {
    if (previewBundles.value.length === 0) return
    const next = Math.min(Math.max(0, index), previewBundles.value.length - 1)
    currentPreviewIndex.value = next
  }

  function goToPrevPreview() {
    goToPreviewIndex(currentPreviewIndex.value - 1)
  }

  function goToNextPreview() {
    goToPreviewIndex(currentPreviewIndex.value + 1)
  }

  function exitPreviewMode() {
    previewBundles.value = []
    currentPreviewIndex.value = 0
    previewError.value = null
    router.push({ path: '/allclass', query: {} })
  }

  async function loadPreviewFromRoute() {
    const previewKey = String(route.query.previewKey || '')
    const invoiceParam = String(route.query.invoice || '')
    const invoiceNoLegacy = String(route.query.invoiceNo || '')

    const invoiceNos = invoiceParam
      ? parseInvoiceQuery(invoiceParam)
      : invoiceNoLegacy
        ? [invoiceNoLegacy.trim()]
        : []

    if (!previewKey && invoiceNos.length === 0) {
      previewBundles.value = []
      currentPreviewIndex.value = 0
      previewError.value = null
      return
    }

    isLoadingPreview.value = true
    previewError.value = null
    try {
      if (previewKey) {
        const preview = await posApi.getPreviewSession(previewKey)
        applyPreviewBundle(preview || {})
        return
      }

      if (invoiceNos.length === 1) {
        const preview = await posApi.getInvoicePreviewByNo(invoiceNos[0]!)
        applyPreviewBundle(preview || {})
        return
      }

      const preview = await posApi.getInvoicesPreview(invoiceNos)
      applyPreviewBundle(preview || {})
    } catch (err) {
      previewBundles.value = []
      currentPreviewIndex.value = 0
      previewError.value = (err as Error)?.message || 'Failed to load invoice preview'
      console.error('Invoice preview failed:', err)
    } finally {
      isLoadingPreview.value = false
    }
  }

  onMounted(loadPreviewFromRoute)
  watch(
    () => [
      String(route.query.previewKey || ''),
      String(route.query.invoice || ''),
      String(route.query.invoiceNo || ''),
    ],
    loadPreviewFromRoute,
  )

  return {
    previewBundles,
    currentPreviewIndex,
    previewInvoiceCount,
    hasMultiplePreviewInvoices,
    currentPreviewBundle,
    currentPreviewLines,
    currentPreviewHeader,
    selectedReportInvoices,
    selectedReportInvoice,
    hasReportPreviewInvoices,
    isLoadingPreview,
    previewError,
    shouldAutoOpenPrintDialog,
    canGoPrevPreview,
    canGoNextPreview,
    goToPrevPreview,
    goToNextPreview,
    goToPreviewIndex,
    exitPreviewMode,
    loadPreviewFromRoute,
  }
}
