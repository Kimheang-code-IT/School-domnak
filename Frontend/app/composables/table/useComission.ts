import { computed, ref } from 'vue'
import type { TableColumn } from '~/types/nuxt-ui'
import { getGroupedRowModel } from '@tanstack/vue-table'
import type { GroupingOptions } from '@tanstack/vue-table'
import type { ComissionEntry } from '~/types'
import { useComissionApi } from '~/utils/api'
import { useServerListTable } from '~/composables/table/useServerListTable'
import { mapCommissionViewRow } from '~/utils/helpers/mapReportCommissionRows'
import { useTableFilterCatalog } from '~/composables/filters/useTableFilterCatalog'
import { useServerTableFilters } from '~/composables/filters/useServerTableFilters'
import { buildExportListQuery } from '~/composables/table/useExportListQuery'

export function useComission() {
  const { t } = useI18n()
  const comissionApi = useComissionApi()
  const localRows = ref<ComissionEntry[]>([])

  const catalog = useTableFilterCatalog({ sources: true, classes: true })
  const { selections, queryParams } = useServerTableFilters(['source', 'classId'])

  const { sorting, columnFilters, pagination, searchQuery, mergedServerQuery, resource } =
    useServerListTable<ComissionEntry>({
      resourceKey: 'commission-view',
      initialSorting: [{ id: 'date', desc: true }],
      localData: localRows,
      extraQuery: queryParams,
      listFn: async (query, signal) => {
        const res = await comissionApi.list(query, signal)
        const data = Array.isArray(res.data)
          ? res.data.map((row: ComissionEntry) =>
              mapCommissionViewRow(row as unknown as Record<string, unknown>),
            )
          : []
        return { ...res, data }
      },
    })

  const columns = computed<TableColumn<ComissionEntry>[]>(() => [
    {
      id: 'title',
      header: t('pages.comission.groupOverview'),
      enableSorting: false,
      meta: {
        class: { td: 'w-full max-w-[min(100%,22rem)]' },
      },
    },
    {
      id: 'teacher_key',
      accessorKey: 'teacher_key',
      header: '',
      enableSorting: false,
    },
    { accessorKey: 'className', header: t('pages.comission.columns.className') },
    { accessorKey: 'studentName', header: t('pages.comission.columns.studentName') },
    { accessorKey: 'source', header: t('pages.comission.columns.source') },
    { accessorKey: 'date', header: t('pages.comission.columns.date') },
    { accessorKey: 'amount', header: t('pages.comission.columns.amount') },
    { accessorKey: 'commission', header: t('pages.comission.columns.commission') },
  ])

  const groupingOptions = ref<GroupingOptions>({
    groupedColumnMode: 'remove',
    getGroupedRowModel: getGroupedRowModel(),
  })
  const grouping = ref<string[]>(['teacher_key'])
  const expanded = ref(true)

  async function fetchExportData(args: { startDate?: string; endDate?: string }) {
    const exportQuery = buildExportListQuery(mergedServerQuery, args)
    const res = await comissionApi.exportCsv(exportQuery)
    const rows = Array.isArray(res.data) ? res.data : []
    return rows.map((row) => {
      const mapped = mapCommissionViewRow(row as unknown as Record<string, unknown>)
      return {
        teacherName: mapped.teacherName,
        className: mapped.className,
        studentName: mapped.studentName,
        source: mapped.source,
        date: mapped.date,
        amount: mapped.amount,
        commission: mapped.commission,
      }
    })
  }

  return {
    data: resource.rows,
    isLoading: resource.isLoading,
    totalRows: resource.totalRows,
    sorting,
    searchQuery,
    columnFilters,
    pagination,
    columns,
    groupingOptions,
    grouping,
    expanded,
    catalog,
    selections,
    fetchExportData,
  }
}
