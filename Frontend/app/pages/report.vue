<script setup lang="ts">
import { useReport } from '~/composables/table/useReport'
import { useTableToolbarFilters } from '~/composables/filters/useTableToolbarFilters'
import { formatCurrency } from '~/utils/format/currency'
import { formatDate } from '~/utils/format/date'
import {
  clampExchangeRate,
  displayToUsd,
  formatKhr,
  usdToDisplay,
} from '~/utils/format/paymentCurrency'
import { usePosApi } from '~/utils/api'

const { t } = useI18n()
const { can, PERMISSIONS } = useCan()
const router = useRouter()
const toast = useToast()
const posApi = usePosApi()
const { exchangeRate: sharedExchangeRate } = useExchangeRate()
const isExportOpen = ref(false)

const isPayOwnOpen = ref(false)
const payOwnSubmitting = ref(false)
const payOwnInvoiceId = ref<number | null>(null)
const payOwnInvoiceNo = ref('')
const payOwnRemaining = ref(0)
const payOwnRate = ref(4100)
const payOwnCurrency = ref<'USD' | 'KHR'>('USD')
const payOwnInput = ref(0)

const {
  rowSelection,
  sorting,
  searchQuery,
  columnVisibility,
  columnFilters,
  pagination,
  totalRows,
  isLoading,
  filteredReportRows,
  catalog,
  selections,
  selectedReportRows,
  allFilteredSelected,
  someFilteredSelected,
  toggleSelectAllFiltered,
  columns,
  fetchExportData,
  refresh: refreshReport,
} = useReport()

const toolbarFilters = useTableToolbarFilters(
  computed(() => [
    {
      key: 'address',
      model: selections.address,
      items: catalog.provinceItems,
      placeholder: t('pages.report.columns.address'),
      class: 'w-24 sm:w-36',
    },
    {
      key: 'seller',
      model: selections.seller,
      items: catalog.sellerItems,
      placeholder: t('pages.report.columns.seller'),
      class: 'w-24 sm:w-36',
    },
    {
      key: 'classId',
      model: selections.classId,
      items: catalog.classItems,
      placeholder: t('pages.dashboard.filterClass'),
      class: 'w-24 sm:w-36',
    },
    {
      key: 'courseId',
      model: selections.courseId,
      items: catalog.courseItems,
      placeholder: t('pages.dashboard.filterCourse'),
      class: 'w-24 sm:w-36',
    },
  ]),
)

interface PosInvoicePayload {
  invoiceNo: string
  date: string
  product: string
  customer: string
  phoneCustomer: string
  seller: string
  phoneSaler?: string
  address: string
  amount: number
}

function mapRowToInvoicePayload(row: Record<string, unknown>): PosInvoicePayload {
  return {
    invoiceNo: String(row?.invoiceNo || ''),
    date: String(row?.date || ''),
    product: String(row?.className || row?.product || ''),
    customer: String(row?.customer || ''),
    phoneCustomer: String(row?.phoneCustomer || ''),
    seller: String(row?.seller || ''),
    phoneSaler: String(row?.phoneSaler || ''),
    address: String(row?.address || ''),
    amount: Number(row?.amount || 0),
  }
}

async function createPreviewAndGo(invoices: PosInvoicePayload[], autoPrint?: boolean) {
  const invoiceList = dedupeInvoicePayloads(invoices)
    .map((row) => String(row.invoiceNo || '').trim())
    .filter(Boolean)

  if (!invoiceList.length) {
    toast.add({
      title: 'Preview failed',
      description: 'Missing invoice number for this row.',
      color: 'error',
    })
    return
  }

  await router.push({
    path: '/allclass',
    query: {
      invoice: invoiceList.join(','),
      ...(autoPrint ? { autoPrint: '1' } : {}),
    },
  })
}

async function goToInvoice(row: Record<string, unknown>) {
  await createPreviewAndGo([mapRowToInvoicePayload(row)])
}

async function openEditInvoice(row: Record<string, unknown>) {
  const invoiceNo = String(row?.invoiceNo || '').trim()
  const invoiceId = Number(row?.invoiceId)
  if (!invoiceNo && !(Number.isFinite(invoiceId) && invoiceId > 0)) {
    toast.add({
      title: t('pages.report.editInvoice'),
      description: 'Missing invoice number for this row.',
      color: 'error',
    })
    return
  }
  await router.push({
    path: '/allclass',
    query: {
      ...(invoiceNo ? { editInvoice: invoiceNo } : {}),
      ...(Number.isFinite(invoiceId) && invoiceId > 0 ? { editInvoiceId: String(invoiceId) } : {}),
    },
  })
}

function openPayOwn(row: Record<string, unknown>) {
  const id = Number(row?.invoiceId)
  if (!Number.isFinite(id) || id <= 0) {
    toast.add({
      title: t('pages.report.payOwnTitle'),
      description: 'Missing invoice id.',
      color: 'error',
    })
    return
  }
  payOwnInvoiceId.value = id
  payOwnInvoiceNo.value = String(row?.invoiceNo || '').trim()
  payOwnRemaining.value = Math.max(0, Number(row?.amountOwn || 0))
  payOwnRate.value = clampExchangeRate(row?.exchangeRate ?? sharedExchangeRate.value)
  payOwnCurrency.value = 'USD'
  payOwnInput.value = usdToDisplay(payOwnRemaining.value, 'USD', payOwnRate.value)
  isPayOwnOpen.value = true
}

const payOwnDisplayRemaining = computed(() =>
  usdToDisplay(payOwnRemaining.value, payOwnCurrency.value, payOwnRate.value),
)

function setPayOwnCurrency(next: 'USD' | 'KHR') {
  if (payOwnCurrency.value === next) return
  const asUsd = displayToUsd(Number(payOwnInput.value || 0), payOwnCurrency.value, payOwnRate.value)
  payOwnCurrency.value = next
  payOwnInput.value = usdToDisplay(asUsd, next, payOwnRate.value)
}

function onPayOwnRateInput(event: Event) {
  const target = event.target as HTMLInputElement | null
  const asUsd = displayToUsd(Number(payOwnInput.value || 0), payOwnCurrency.value, payOwnRate.value)
  payOwnRate.value = clampExchangeRate(target?.value)
  sharedExchangeRate.value = payOwnRate.value
  payOwnInput.value = usdToDisplay(asUsd, payOwnCurrency.value, payOwnRate.value)
}

async function submitPayOwn() {
  if (!payOwnInvoiceId.value) return
  const amountUsd = displayToUsd(Number(payOwnInput.value || 0), payOwnCurrency.value, payOwnRate.value)
  if (!(amountUsd > 0)) {
    toast.add({
      title: t('pages.report.payOwnTitle'),
      description: t('pages.report.payOwnInvalid'),
      color: 'warning',
    })
    return
  }
  if (amountUsd > payOwnRemaining.value + 0.001) {
    toast.add({
      title: t('pages.report.payOwnTitle'),
      description: t('pages.report.payOwnExceeds'),
      color: 'warning',
    })
    return
  }
  payOwnSubmitting.value = true
  try {
    await posApi.payInvoiceOwn(payOwnInvoiceId.value, { amount: amountUsd })
    toast.add({
      title: t('pages.report.payOwnTitle'),
      description: t('pages.report.payOwnSuccess'),
      color: 'success',
    })
    isPayOwnOpen.value = false
    await refreshReport()
  } catch (error: any) {
    toast.add({
      title: t('pages.report.payOwnTitle'),
      description: String(error?.data?.detail || error?.message || t('common.error')),
      color: 'error',
    })
  } finally {
    payOwnSubmitting.value = false
  }
}

function dedupeInvoicePayloads(invoices: PosInvoicePayload[]): PosInvoicePayload[] {
  const seen = new Set<string>()
  const unique: PosInvoicePayload[] = []
  for (const invoice of invoices) {
    const key = String(invoice.invoiceNo || '').trim()
    if (!key || seen.has(key)) continue
    seen.add(key)
    unique.push(invoice)
  }
  return unique
}

function goToSelectedInvoices() {
  if (!selectedReportRows.value.length) return
  const payloads = dedupeInvoicePayloads(
    selectedReportRows.value.map((row) =>
      mapRowToInvoicePayload(row as unknown as Record<string, unknown>),
    ),
  )
  if (!payloads.length) return
  return createPreviewAndGo(payloads)
}
</script>

<template>
  <div class="flex flex-col h-full bg-background overflow-hidden text-foreground tracking-tight">
    <LayoutAppHeader :title="t('pages.report.title')" show-datepicker>
      <template #right>
        <UButton
          v-if="can(PERMISSIONS.reportPreviewInvoice)"
          icon="i-lucide-receipt-text"
          color="primary"
          variant="solid"
          class="font-normal shadow-sm shrink-0"
          :disabled="selectedReportRows.length === 0"
          @click="goToSelectedInvoices"
        >
          <span class="hidden sm:inline">{{ $t('common.preview') }}</span>
        </UButton>
        <UButton
          v-if="can(PERMISSIONS.reportExport)"
          icon="i-lucide-download"
          color="neutral"
          variant="subtle"
          class="font-normal shadow-sm shrink-0"
          @click="isExportOpen = true"
        >
          <span class="hidden sm:inline">{{ $t('common.export') }}</span>
        </UButton>
      </template>
    </LayoutAppHeader>

    <div class="flex-1 p-2 overflow-hidden">
      <TableApptable
        :title="t('pages.report.tableTitle')"
        v-model:row-selection="rowSelection"
        v-model:sorting="sorting"
        v-model:column-visibility="columnVisibility"
        v-model:pagination="pagination"
        v-model:column-filters="columnFilters"
        :data="filteredReportRows"
        :total-rows="totalRows"
        :loading="isLoading"
        :columns="columns"
        :selectable="true"
        server-pagination
      >
        <template #filters>
          <TableToolbarFilters :filters="toolbarFilters" />
        </template>
        <template #header>
          <div class="w-full max-w-md">
            <CommonAppSearch
              v-model="searchQuery"
              :placeholder="t('pages.report.searchPlaceholder')"
            />
          </div>
        </template>
        <template #no-header>
          <div class="flex items-center">
            <UCheckbox
              :model-value="allFilteredSelected"
              :indeterminate="someFilteredSelected"
              @update:model-value="toggleSelectAllFiltered(!!$event)"
            />
          </div>
        </template>
        <template #no-cell="{ row }">
          <div class="flex items-center gap-2">
            <UCheckbox
              :model-value="row.getIsSelected()"
              @update:model-value="row.toggleSelected(!!$event)"
            />
            <span class="text-sm text-muted-foreground">{{ row.index + 1 }}</span>
          </div>
        </template>

        <template #date-cell="{ row }">
          <span class="text-sm text-muted-foreground">{{ formatDate(row.original.date) }}</span>
        </template>
        <template #amount-cell="{ row }">
          <div class="text-sm font-medium tabular-nums">
            <div>{{ formatCurrency(row.original.amount, 'USD') }}</div>
            <div class="text-[11px] text-muted-foreground">
              {{ formatKhr(Number(row.original.amount || 0), Number(row.original.exchangeRate || 4100)) }}
            </div>
          </div>
        </template>
        <template #amountPaid-cell="{ row }">
          <div class="text-sm tabular-nums">
            <div>{{ formatCurrency(Number(row.original.amountPaid || 0), 'USD') }}</div>
            <div class="text-[11px] text-muted-foreground">
              {{ formatKhr(Number(row.original.amountPaid || 0), Number(row.original.exchangeRate || 4100)) }}
            </div>
          </div>
        </template>
        <template #amountOwn-cell="{ row }">
          <div class="text-sm tabular-nums" :class="Number(row.original.amountOwn || 0) > 0 ? 'text-amber-600 font-medium' : ''">
            <div>{{ formatCurrency(Number(row.original.amountOwn || 0), 'USD') }}</div>
            <div class="text-[11px] text-muted-foreground">
              {{ formatKhr(Number(row.original.amountOwn || 0), Number(row.original.exchangeRate || 4100)) }}
            </div>
          </div>
        </template>
        <template #seller-cell="{ row }">
          <UBadge color="primary" variant="soft" class="font-normal">
            {{ row.original.seller }}
          </UBadge>
        </template>
        <template #className-cell="{ row }">
          <UBadge color="neutral" variant="soft" class="font-normal">
            {{ row.original.className || row.original.product || '—' }}
          </UBadge>
        </template>
        <template #address-cell="{ row }">
          <span class="text-sm text-foreground line-clamp-2" :title="row.original.address">
            {{ row.original.address || '—' }}
          </span>
        </template>
        <template #paymentStatus-cell="{ row }">
          <UBadge
            v-if="String(row.original.paymentStatus || '').toLowerCase() !== 'own'"
            color="success"
            variant="soft"
            class="font-normal"
          >
            {{ $t('pages.report.statusPaid') }}
          </UBadge>
          <UButton
            v-else-if="can(PERMISSIONS.reportEditInvoice)"
            color="warning"
            variant="soft"
            size="xs"
            class="font-normal"
            @click="openPayOwn(row.original as unknown as Record<string, unknown>)"
          >
            {{ $t('pages.report.statusOwn') }}
            <span v-if="Number(row.original.amountOwn || 0) > 0" class="ml-1 tabular-nums">
              ({{ formatCurrency(Number(row.original.amountOwn || 0), 'USD') }})
            </span>
          </UButton>
          <UBadge v-else color="warning" variant="soft" class="font-normal">
            {{ $t('pages.report.statusOwn') }}
          </UBadge>
        </template>
        <template #invoiceNo-cell="{ row }">
          <div class="flex items-center gap-2">
            <span class="text-sm font-medium">{{ row.original.invoiceNo }}</span>
            <UButton
              v-if="can(PERMISSIONS.reportPreviewInvoice)"
              icon="i-lucide-receipt-text"
              color="primary"
              variant="ghost"
              size="xs"
              @click="goToInvoice(row.original as unknown as Record<string, unknown>)"
            />
            <UButton
              v-if="can(PERMISSIONS.reportEditInvoice)"
              icon="i-lucide-pencil"
              color="neutral"
              variant="ghost"
              size="xs"
              :title="$t('pages.report.editInvoice')"
              @click="openEditInvoice(row.original as unknown as Record<string, unknown>)"
            />
          </div>
        </template>
      </TableApptable>

      <UModal v-model:open="isPayOwnOpen" :ui="{ content: 'w-[min(96vw,420px)]' }">
        <template #header>
          <div class="flex items-center justify-between gap-3 p-4 w-full">
            <div class="min-w-0">
              <h3 class="text-lg font-semibold truncate">{{ $t('pages.report.payOwnTitle') }}</h3>
              <p class="text-sm text-muted truncate">{{ payOwnInvoiceNo }}</p>
            </div>
            <UButton
              icon="i-lucide-x"
              color="neutral"
              variant="ghost"
              size="sm"
              :disabled="payOwnSubmitting"
              @click="isPayOwnOpen = false"
            />
          </div>
        </template>
        <template #body>
          <div class="flex flex-col gap-3 p-4">
            <div class="flex items-center justify-between text-sm">
              <span class="text-muted-foreground">{{ $t('pages.report.payOwnRemaining') }}</span>
              <span class="font-semibold tabular-nums">
                {{
                  payOwnCurrency === 'KHR'
                    ? `${payOwnDisplayRemaining.toLocaleString()} ៛`
                    : formatCurrency(payOwnRemaining, 'USD')
                }}
              </span>
            </div>
            <div class="flex items-center justify-between gap-2">
              <span class="text-sm text-muted-foreground">{{ $t('pages.report.payOwnAmount') }}</span>
              <div class="inline-flex rounded-md border border-default overflow-hidden shrink-0">
                <UButton
                  type="button"
                  size="xs"
                  :variant="payOwnCurrency === 'USD' ? 'solid' : 'ghost'"
                  :color="payOwnCurrency === 'USD' ? 'primary' : 'neutral'"
                  class="rounded-none"
                  @click="setPayOwnCurrency('USD')"
                >
                  USD
                </UButton>
                <UButton
                  type="button"
                  size="xs"
                  :variant="payOwnCurrency === 'KHR' ? 'solid' : 'ghost'"
                  :color="payOwnCurrency === 'KHR' ? 'primary' : 'neutral'"
                  class="rounded-none"
                  @click="setPayOwnCurrency('KHR')"
                >
                  KHR
                </UButton>
              </div>
            </div>
            <div class="flex items-center justify-between gap-2">
              <span class="text-sm text-muted-foreground">{{ $t('pages.allclass.payment.exchangeRate') }}</span>
              <UInput
                :model-value="payOwnRate"
                type="number"
                size="xs"
                min="1"
                step="1"
                class="w-24 text-right"
                @input="onPayOwnRateInput"
              />
            </div>
            <p class="text-xs text-muted-foreground">{{ $t('pages.allclass.payment.fxHint', { rate: payOwnRate }) }}</p>
            <UInput v-model.number="payOwnInput" type="number" min="0" step="any" size="lg" />
          </div>
        </template>
        <template #footer>
          <div class="flex justify-end gap-2 p-4">
            <UButton color="neutral" variant="ghost" :disabled="payOwnSubmitting" @click="isPayOwnOpen = false">
              {{ $t('components.cancel') }}
            </UButton>
            <UButton color="primary" :loading="payOwnSubmitting" @click="submitPayOwn">
              {{ $t('common.confirm') }}
            </UButton>
          </div>
        </template>
      </UModal>

      <CommonAppExport
        v-model:open="isExportOpen"
        :data="filteredReportRows"
        :fetch-export-data="fetchExportData"
        filename="report"
        date-field="date"
      />
    </div>
  </div>
</template>
