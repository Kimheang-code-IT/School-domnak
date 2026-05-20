import { ref, computed } from 'vue'
import type { TableColumn } from '~/types/nuxt-ui'
import type { FinanceEntry } from '~/types'
import { useFinanceApi } from '~/utils/api'
import { formatCurrency } from '~/utils/format/currency'
import { useServerListTable } from '~/composables/table/useServerListTable'
import { buildExportListQuery } from '~/composables/table/useExportListQuery'

export function useFinance() {
  const { t } = useI18n()
  const financeApi = useFinanceApi()
  const data = ref<FinanceEntry[]>([])
  const { sorting, columnFilters, pagination, searchQuery, mergedServerQuery, resource } =
    useServerListTable<FinanceEntry>({
    resourceKey: 'finance-view',
    initialSorting: [{ id: 'className', desc: false }],
    localData: data,
    listFn: async (query, signal) => {
      const res = await financeApi.list(query, signal)
      const data = Array.isArray(res.data)
        ? res.data.map((row) => ({
            ...row,
            id: String(row.id),
            className: row.className ?? row.productName,
            productName: row.productName ?? row.className,
          }))
        : []
      return { ...res, data }
    },
  })
  const groupingOptions = ref({})
  const grouping = ref<string[]>([])
  const effectiveRows = computed(() => resource.rows.value)

  function resolvedFinalPrice(row: FinanceEntry): number {
    const explicit = row.finalPrice
    if (explicit != null && Number.isFinite(Number(explicit))) {
      return Number(explicit)
    }
    return (
      Number(row.inPriceForPos ?? 0) -
      Number(row.totalCommission ?? 0) -
      Number(row.facebook ?? 0) -
      Number(row.other ?? 0)
    )
  }

  const financeSummary = computed(() => {
    const rows = effectiveRows.value
    const sumBy = (selector: (row: FinanceEntry) => number) =>
      rows.reduce((total, row) => total + Number(selector(row) || 0), 0)

    const electricitySum = sumBy((row) => row.electricity ?? 0)
    const waterSum = sumBy((row) => row.water ?? 0)
    const internetSum = sumBy((row) => row.internet ?? 0)
    const totalCommissionSum = sumBy((row) => row.totalCommission)
    const facebookSum = sumBy((row) => row.facebook)
    const otherSum = sumBy((row) => row.other)
    const amountSum = sumBy((row) => row.amount ?? row.printPrice ?? 0)
    const finalPriceSum = rows.reduce((total, row) => total + resolvedFinalPrice(row), 0)

    return {
      count: rows.length,
      electricitySum,
      waterSum,
      internetSum,
      totalCommissionSum,
      facebookSum,
      otherSum,
      amountSum,
      finalPriceSum
    }
  })

  const isSlideoverOpen = ref(false)
  const editingRow = ref<FinanceEntry | null>(null)

  const editFields = computed(() => [
    { key: 'className', label: t('pages.finance.columns.className'), readonly: true },
    { key: 'electricity', label: t('pages.finance.columns.electricity'), type: 'number', currency: true },
    { key: 'water', label: t('pages.finance.columns.water'), type: 'number', currency: true },
    { key: 'internet', label: t('pages.finance.columns.internet'), type: 'number', currency: true },
    { key: 'facebook', label: t('pages.finance.columns.facebook'), type: 'number', currency: true },
    { key: 'other', label: t('pages.finance.columns.other'), type: 'number', currency: true },
  ])

  function openEdit(row: FinanceEntry) {
    editingRow.value = { ...row }
    isSlideoverOpen.value = true
  }

  async function handleUpdate(updatedData: any) {
    if (!editingRow.value?.id) return
    try {
      await financeApi.update(Number(editingRow.value?.id || 0), {
        electricity: Number(updatedData.electricity || 0),
        water: Number(updatedData.water || 0),
        internet: Number(updatedData.internet || 0),
        facebook: Number(updatedData.facebook || 0),
        other: Number(updatedData.other || 0),
      })
      resource.refresh()
      isSlideoverOpen.value = false
      editingRow.value = null
    } catch (err) {
      console.error('Update failed:', err)
    }
  }

  async function fetchExportData(args: { startDate?: string; endDate?: string }) {
    const exportQuery = buildExportListQuery(mergedServerQuery, args)
    const res = await financeApi.exportCsv(exportQuery)
    const rows = Array.isArray(res.data) ? res.data : []
    return rows.map((row) => {
      const entry = row as FinanceEntry
      return {
        className: entry.className ?? entry.productName ?? '',
        electricity: Number(entry.electricity ?? 0),
        water: Number(entry.water ?? 0),
        internet: Number(entry.internet ?? 0),
        totalCommission: Number(entry.totalCommission ?? 0),
        facebook: Number(entry.facebook ?? 0),
        other: Number(entry.other ?? 0),
        amount: Number(entry.amount ?? entry.printPrice ?? 0),
        finalPrice: resolvedFinalPrice(entry),
      }
    })
  }

  const columns = computed<TableColumn<FinanceEntry>[]>(() => [
    {
      id: 'className',
      header: t('pages.finance.columns.className'),
      accessorFn: (row) => String(row.className ?? row.productName ?? ''),
      footer: `Count: ${financeSummary.value.count}`
    },
    {
      accessorKey: 'electricity',
      header: t('pages.finance.columns.electricity'),
      footer: formatCurrency(financeSummary.value.electricitySum, 'USD')
    },
    {
      accessorKey: 'water',
      header: t('pages.finance.columns.water'),
      footer: formatCurrency(financeSummary.value.waterSum, 'USD')
    },
    {
      accessorKey: 'internet',
      header: t('pages.finance.columns.internet'),
      footer: formatCurrency(financeSummary.value.internetSum, 'USD')
    },
    {
      accessorKey: 'totalCommission',
      header: t('pages.finance.columns.totalCommission'),
      footer: formatCurrency(financeSummary.value.totalCommissionSum, 'USD')
    },
    {
      accessorKey: 'facebook',
      header: t('pages.finance.columns.facebook'),
      footer: formatCurrency(financeSummary.value.facebookSum, 'USD')
    },
    {
      accessorKey: 'other',
      header: t('pages.finance.columns.other'),
      footer: formatCurrency(financeSummary.value.otherSum, 'USD')
    },
    {
      id: 'amount',
      header: t('pages.finance.columns.amount'),
      accessorFn: (row) => Number(row.amount ?? row.printPrice ?? 0),
      footer: formatCurrency(financeSummary.value.amountSum, 'USD')
    },
    {
      id: 'finalPrice',
      header: t('pages.finance.columns.finalPrice'),
      accessorFn: (row) => resolvedFinalPrice(row),
      footer: formatCurrency(financeSummary.value.finalPriceSum, 'USD'),
      meta: {
        class: {
          th: '',
          td: ' font-medium'
        }
      }
    },
    {
      id: 'actions',
      header: '',
      meta: {
        class: {
          th: 'w-10',
          td: 'text-right'
        }
      }
    }
  ])

  return {
    data: effectiveRows,
    isLoading: resource.isLoading,
    sorting,
    searchQuery,
    columnFilters,
    pagination,
    totalRows: resource.totalRows,
    columns,
    groupingOptions,
    grouping,
    isSlideoverOpen,
    editingRow,
    editFields,
    openEdit,
    handleUpdate,
    fetchExportData,
  }
}



