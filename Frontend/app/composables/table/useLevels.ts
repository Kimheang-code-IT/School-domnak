import { ref, computed, watch } from 'vue'
import type { DropdownMenuItem, TableColumn } from '~/types/nuxt-ui'
import { useBaseTable } from '~/composables/table/useBaseTable'
import { useTableQuery } from '~/composables/table/useTableQuery'
import type { Level } from '~/types'
import { useLevelsApi } from '~/utils/api'
import type { ApiQueryParams } from '~/utils/api'
import { useServerTableResource } from '~/composables/table/useServerTable'
import { useMutation } from '~/composables/data/useMutation'

export function useLevels() {
  const useBackendApi = useBackendMode()
  const levelsApi = useLevelsApi()
  const { t, toast, rowSelection, columnVisibility, isConfirmOpen } = useBaseTable({})

  const { sorting, columnFilters, pagination, serverQuery } = useTableQuery({
    initialSorting: [{ id: 'createdAt', desc: true }]
  })
  const searchQuery = ref('')

  const entries = ref<Level[]>([])
  const mutation = useMutation()

  const newLevelNameKm = ref('')
  const newLevelNameEn = ref('')
  const newLevelDescription = ref('')
  const editingId = ref<string | null>(null)
  const editingSnapshot = ref<{ totalClass: number } | null>(null)

  const pendingPayload = ref<Level | null>(null)
  const pendingDeleteId = ref<string | null>(null)
  const confirmMode = ref<'add' | 'edit' | 'delete'>('add')

  const mergedServerQuery = computed(() => ({
    ...serverQuery.value,
    search: searchQuery.value.trim() || undefined
  }))
  watch(searchQuery, () => {
    pagination.value.pageIndex = 0
  })

  const resource = useServerTableResource<Level, ApiQueryParams>({
    resourceKey: 'levels',
    useBackendApi,
    serverQuery: mergedServerQuery,
    localData: entries,
    listFn: (query, signal) => levelsApi.list(query, signal),
    debounceMs: 220
  })

  const filteredLevels = computed(() => resource.rows.value)

  const levelsSummary = computed(() => {
    const rows = filteredLevels.value
    const count = rows.length
    const totalClassSum = rows.reduce((sum, row) => sum + Number(row.totalClass || 0), 0)
    return { count, totalClassSum }
  })

  const columns = computed<TableColumn<Level>[]>(() => [
    { accessorKey: 'id', header: t('pages.levels.columns.no') },
    {
      accessorKey: 'levelNameKm',
      header: t('pages.levels.columns.levelNameKm'),
      footer: t('pages.levels.footerCount', { count: levelsSummary.value.count })
    },
    { accessorKey: 'levelNameEn', header: t('pages.levels.columns.levelNameEn') },
    { accessorKey: 'description', header: t('pages.levels.columns.description') },
    {
      accessorKey: 'totalClass',
      header: t('pages.levels.columns.totalClass'),
      footer: t('pages.levels.footerTotalClassSum', { sum: levelsSummary.value.totalClassSum })
    },
    { id: 'action', header: t('common.actions') }
  ])

  function resetForm() {
    newLevelNameKm.value = ''
    newLevelNameEn.value = ''
    newLevelDescription.value = ''
    editingId.value = null
    editingSnapshot.value = null
    pendingPayload.value = null
  }

  function handleAdd() {
    const nameEn = newLevelNameEn.value.trim()
    const nameKm = newLevelNameKm.value.trim()
    if (!nameEn || !nameKm) return

    pendingPayload.value = {
      id: editingId.value ?? '',
      levelNameKm: nameKm,
      levelNameEn: nameEn,
      description: newLevelDescription.value.trim() || undefined,
      totalClass: editingSnapshot.value?.totalClass ?? 0,
      createdAt: ''
    }
    confirmMode.value = editingId.value ? 'edit' : 'add'
    isConfirmOpen.value = true
  }

  const confirmConfig = computed(() => {
    if (confirmMode.value === 'delete') {
      return {
        title: t('actions.delete'),
        description: t('pages.levels.confirmDelete'),
        type: 'error' as const,
        submitLabel: t('actions.delete'),
        icon: 'i-lucide-trash-2'
      }
    }
    if (confirmMode.value === 'edit') {
      return {
        title: t('actions.save'),
        description: t('pages.levels.confirmSaveEditNamed', {
          name: pendingPayload.value?.levelNameEn ?? ''
        }),
        type: 'primary' as const,
        submitLabel: t('actions.save'),
        icon: 'i-lucide-check-circle'
      }
    }
    return {
      title: t('actions.add'),
      description: t('pages.levels.confirmSaveAddNamed', {
        name: pendingPayload.value?.levelNameEn ?? ''
      }),
      type: 'primary' as const,
      submitLabel: t('actions.confirm'),
      icon: 'i-lucide-check-circle'
    }
  })

  function getDropdownActions(entry: Level): DropdownMenuItem[][] {
    return [
      [
        {
          label: t('actions.edit'),
          icon: 'i-lucide-edit',
          onSelect: () => {
            newLevelNameKm.value = entry.levelNameKm ?? ''
            newLevelNameEn.value = entry.levelNameEn ?? ''
            newLevelDescription.value = entry.description ?? ''
            editingId.value = entry.id
            editingSnapshot.value = { totalClass: entry.totalClass }
          }
        },
        {
          label: t('actions.delete'),
          icon: 'i-lucide-trash',
          color: 'error' as const,
          onSelect: () => {
            pendingDeleteId.value = entry.id
            confirmMode.value = 'delete'
            isConfirmOpen.value = true
          }
        }
      ]
    ]
  }

  async function finalizeAction() {
    try {
      if (confirmMode.value === 'delete' && pendingDeleteId.value !== null) {
        await mutation.run(() => levelsApi.remove(pendingDeleteId.value!), 'levels')
        await resource.refresh()
        toast.add({ title: t('pages.levels.deleted'), color: 'error' })
        pendingDeleteId.value = null
      } else if (confirmMode.value === 'edit' && pendingPayload.value?.id) {
        const p = pendingPayload.value
        await mutation.run(
          () =>
            levelsApi.update(p.id, {
              levelNameKm: p.levelNameKm,
              levelNameEn: p.levelNameEn,
              description: p.description ?? ''
            }),
          'levels'
        )
        await resource.refresh()
        toast.add({ title: t('pages.levels.updated'), color: 'primary' })
        resetForm()
      } else if (confirmMode.value === 'add' && pendingPayload.value) {
        const p = pendingPayload.value
        await mutation.run(
          () =>
            levelsApi.create({
              levelNameKm: p.levelNameKm,
              levelNameEn: p.levelNameEn,
              description: p.description ?? ''
            }),
          'levels'
        )
        await resource.refresh()
        toast.add({ title: t('pages.levels.created'), color: 'primary' })
        resetForm()
      }
    } catch (err: unknown) {
      const e = err as { data?: { message?: string }; message?: string }
      toast.add({
        title: t('common.error'),
        description: e?.data?.message || e?.message || '',
        color: 'error'
      })
    } finally {
      isConfirmOpen.value = false
    }
  }

  return {
    rowSelection,
    sorting,
    searchQuery,
    columnVisibility,
    columnFilters,
    pagination,
    isLoading: resource.isLoading,
    totalRows: resource.totalRows,
    filteredLevels,
    columns,
    newLevelNameKm,
    newLevelNameEn,
    newLevelDescription,
    handleAdd,
    isConfirmOpen,
    confirmConfig,
    finalizeAction,
    getDropdownActions
  }
}
