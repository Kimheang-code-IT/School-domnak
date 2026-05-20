<script setup lang="ts">
import { useReport } from '~/composables/table/useReport'
import { useTableToolbarFilters } from '~/composables/filters/useTableToolbarFilters'
import { formatCurrency } from '~/utils/format/currency'
import { formatDate } from '~/utils/format/date'
import { usePosApi } from '~/utils/api'

const { t } = useI18n()
const router = useRouter()
const toast = useToast()
const posApi = usePosApi()
const isExportOpen = ref(false)

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
      key: 'source',
      model: selections.source,
      items: catalog.sourceItems,
      placeholder: t('pages.report.columns.source'),
      class: 'w-24 sm:w-32',
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
  source?: string
  address: string
  amount: number
}

function mapRowToInvoicePayload(row: Record<string, unknown>): PosInvoicePayload {
  return {
    invoiceNo: String(row?.invoiceNo || ''),
    date: String(row?.date || ''),
    product: String(row?.product || ''),
    customer: String(row?.customer || ''),
    phoneCustomer: String(row?.phoneCustomer || ''),
    seller: String(row?.seller || ''),
    phoneSaler: String(row?.phoneSaler || ''),
    source: String(row?.source || ''),
    address: String(row?.address || ''),
    amount: Number(row?.amount || 0),
  }
}

async function createPreviewAndGo(invoices: PosInvoicePayload[], autoPrint?: boolean) {
  const invoiceNo = String(invoices[0]?.invoiceNo || '').trim()
  try {
    const preview = await posApi.createPreviewSession(invoices)
    if (preview?.previewKey) {
      await router.push({
        path: '/allclass',
        query: {
          previewKey: preview.previewKey,
          ...(autoPrint ? { autoPrint: '1' } : {}),
        },
      })
      return
    }
  } catch {
    // Fall through to invoice-no route when preview session is unavailable.
  }

  if (!invoiceNo) {
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
      invoiceNo,
      ...(autoPrint ? { autoPrint: '1' } : {}),
    },
  })
}

async function goToInvoice(row: Record<string, unknown>) {
  await createPreviewAndGo([mapRowToInvoicePayload(row)])
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

        <template #studentId-cell="{ row }">
          <span class="text-sm tabular-nums text-muted-foreground">
            {{
              row.original.studentId != null && row.original.studentId > 0
                ? row.original.studentId
                : '—'
            }}
          </span>
        </template>
        <template #date-cell="{ row }">
          <span class="text-sm text-muted-foreground">{{ formatDate(row.original.date) }}</span>
        </template>
        <template #amount-cell="{ row }">
          <span class="text-sm font-medium">{{ formatCurrency(row.original.amount, 'USD') }}</span>
        </template>
        <template #seller-cell="{ row }">
          <UBadge color="primary" variant="soft" class="font-normal">
            {{ row.original.seller }}
          </UBadge>
        </template>
        <template #product-cell="{ row }">
          <UBadge color="neutral" variant="soft" class="font-normal">
            {{ row.original.product }}
          </UBadge>
        </template>
        <template #source-cell="{ row }">
          <UBadge color="primary" variant="soft" class="font-normal">
            {{ row.original.source }}
          </UBadge>
        </template>
        <template #address-cell="{ row }">
          <span class="text-sm text-foreground line-clamp-2" :title="row.original.address">
            {{ row.original.address || '—' }}
          </span>
        </template>
        <template #invoiceNo-cell="{ row }">
          <div class="flex items-center gap-2">
            <span class="text-sm font-medium">{{ row.original.invoiceNo }}</span>
            <UButton
              icon="i-lucide-receipt-text"
              color="primary"
              variant="ghost"
              size="xs"
              @click="goToInvoice(row.original as unknown as Record<string, unknown>)"
            />
          </div>
        </template>
      </TableApptable>

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
