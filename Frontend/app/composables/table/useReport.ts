import { computed, ref, watch } from 'vue'
import type { TableColumn } from '~/types/nuxt-ui'
import { useBaseTable } from '~/composables/table/useBaseTable'
import { useReportApi } from '~/utils/api'
import { formatCurrency } from '~/utils/format/currency'
import type { ReportRow } from '~/types'
import { useServerListTable } from '~/composables/table/useServerListTable'
import { mapReportViewRow } from '~/utils/helpers/mapReportCommissionRows'
import { useTableFilterCatalog } from '~/composables/filters/useTableFilterCatalog'
import { useServerTableFilters } from '~/composables/filters/useServerTableFilters'
import { buildExportListQuery } from '~/composables/table/useExportListQuery'

export function useReport() {
  const { t } = useI18n()
  const reportApi = useReportApi()
  const { rowSelection, columnVisibility } = useBaseTable({})
  const reportRows = ref<ReportRow[]>([])

  const catalog = useTableFilterCatalog({
    provinces: true,
    sources: true,
    classes: true,
    courses: true,
    sellers: true,
  })
  const { selections, queryParams } = useServerTableFilters([
    'address',
    'seller',
    'source',
    'classId',
    'courseId',
  ])

  const { sorting, columnFilters, pagination, searchQuery, mergedServerQuery, resource } =
    useServerListTable<ReportRow>({
      resourceKey: 'reports-view',
      initialSorting: [{ id: 'date', desc: true }],
      localData: reportRows,
      extraQuery: queryParams,
      listFn: async (query, signal) => {
        const res = await reportApi.list(query, signal)
        const data = Array.isArray(res.data)
          ? res.data.map((row: ReportRow) =>
              mapReportViewRow(row as unknown as Record<string, unknown>),
            )
          : []
        return { ...res, data }
      },
    })

  const rows = computed(() => resource.rows.value)

  const selectedReportRows = computed<ReportRow[]>(() => {
    const selectedIndexes = Object.keys(rowSelection.value || {})
      .filter((key) => (rowSelection.value as Record<string, boolean>)[key])
      .map((key) => Number(key))
      .filter((value) => Number.isInteger(value) && value >= 0)

    return selectedIndexes
      .map((index) => rows.value[index])
      .filter((row): row is ReportRow => Boolean(row))
  })

  const allFilteredSelected = computed(() => {
    const list = rows.value
    if (!list.length) return false
    const selected = rowSelection.value as Record<string, boolean>
    return list.every((_, index) => Boolean(selected[String(index)]))
  })

  const someFilteredSelected = computed(() => {
    const list = rows.value
    if (!list.length) return false
    const selected = rowSelection.value as Record<string, boolean>
    const selectedCount = list.reduce(
      (count, _row, index) => (selected[String(index)] ? count + 1 : count),
      0,
    )
    return selectedCount > 0 && selectedCount < list.length
  })

  const reportSummary = computed(() => {
    const list = rows.value
    const invoiceCount = new Set(list.map((row) => row.invoiceNo)).size
    const amountSum = list.reduce((sum, row) => sum + Number(row.amount || 0), 0)
    return { invoiceCount, productCount: list.length, amountSum }
  })

  const columns = computed<TableColumn<ReportRow>[]>(() => [
    { accessorKey: 'no', header: t('pages.report.columns.no') },
    {
      accessorKey: 'invoiceNo',
      header: t('pages.report.columns.invoiceNo'),
      footer: t('pages.report.footer.invoiceCount', {
        count: reportSummary.value.invoiceCount,
      }),
    },
    { accessorKey: 'date', header: t('pages.report.columns.date') },
    { accessorKey: 'studentName', header: t('pages.report.columns.studentName') },
    { accessorKey: 'studentPhone', header: t('pages.report.columns.studentPhone') },
    { accessorKey: 'className', header: t('pages.report.columns.className') },
    { accessorKey: 'address', header: t('pages.report.columns.address') },
    { accessorKey: 'seller', header: t('pages.report.columns.seller') },
    { accessorKey: 'source', header: t('pages.report.columns.source') },
    {
      accessorKey: 'amount',
      header: t('pages.report.columns.studentPayment'),
      footer: formatCurrency(reportSummary.value.amountSum, 'USD'),
    },
  ])

  function toggleSelectAllFiltered(checked: boolean) {
    const list = rows.value
    if (!list.length) {
      rowSelection.value = {}
      return
    }
    if (checked) {
      const next: Record<string, boolean> = {}
      list.forEach((_row, index) => {
        next[String(index)] = true
      })
      rowSelection.value = next
      return
    }
    rowSelection.value = {}
  }

  watch(rows, (list) => {
    const current = rowSelection.value as Record<string, boolean>
    const next: Record<string, boolean> = {}
    list.forEach((_row, index) => {
      const key = String(index)
      if (current[key]) next[key] = true
    })
    rowSelection.value = next
  })

  async function fetchExportData(args: { startDate?: string; endDate?: string }) {
    const exportQuery = buildExportListQuery(mergedServerQuery, args)
    const res = await reportApi.exportCsv(exportQuery)
    const data = Array.isArray(res.data) ? res.data : []
    return data.map((row: ReportRow) =>
      mapReportViewRow(row as unknown as Record<string, unknown>),
    )
  }

  return {
    rowSelection,
    sorting,
    searchQuery,
    columnVisibility,
    columnFilters,
    pagination,
    isLoading: resource.isLoading,
    filteredReportRows: rows,
    catalog,
    selections,
    queryParams,
    selectedReportRows,
    allFilteredSelected,
    someFilteredSelected,
    toggleSelectAllFiltered,
    columns,
    totalRows: resource.totalRows,
    fetchExportData,
  }
}
