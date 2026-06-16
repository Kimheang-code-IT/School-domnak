import { ref, computed, watch } from 'vue'
import type { DropdownMenuItem, TableColumn } from '~/types/nuxt-ui'
import { useBaseTable } from '~/composables/table/useBaseTable'
import { useTableQuery } from '~/composables/table/useTableQuery'
import type { Course } from '~/types'
import { useCoursesApi } from '~/utils/api'
import type { ApiQueryParams } from '~/utils/api'
import { useServerTableResource } from '~/composables/table/useServerTable'
import { useMutation } from '~/composables/data/useMutation'
import { PERMISSIONS } from '~/utils/auth/permissions'
import { isForbiddenError } from '~/utils/api/errors'

export function useCourses() {
  const auth = useAuthStore()
  const useBackendApi = useBackendMode()
  const coursesApi = useCoursesApi()
  const { t, toast, rowSelection, columnVisibility, isConfirmOpen } = useBaseTable({})

  const { sorting, columnFilters, pagination, serverQuery } = useTableQuery({
    initialSorting: [{ id: 'createdAt', desc: true }]
  })
  const searchQuery = ref('')

  const entries = ref<Course[]>([])
  const mutation = useMutation()

  const newCourseName = ref('')
  const newCourseNameKm = ref('')
  const newCourseDescription = ref('')
  const editingId = ref<string | null>(null)
  const editingSnapshot = ref<{ totalClass: number } | null>(null)

  const pendingPayload = ref<Course | null>(null)
  const pendingDeleteId = ref<string | null>(null)
  const confirmMode = ref<'add' | 'edit' | 'delete'>('add')

  const mergedServerQuery = computed(() => ({
    ...serverQuery.value,
    search: searchQuery.value.trim() || undefined,
  }))
  watch(searchQuery, () => {
    pagination.value.pageIndex = 0
  })

  const resource = useServerTableResource<Course, ApiQueryParams>({
    resourceKey: 'courses',
    useBackendApi,
    serverQuery: mergedServerQuery,
    localData: entries,
    listFn: (query, signal) => coursesApi.list(query, signal),
    debounceMs: 220
  })

  const filteredCourses = computed(() => resource.rows.value)

  const coursesSummary = computed(() => {
    const rows = filteredCourses.value
    const count = rows.length
    const totalClassSum = rows.reduce((sum, row) => sum + Number(row.totalClass || 0), 0)
    return { count, totalClassSum }
  })

  const columns = computed<TableColumn<Course>[]>(() => [
    { accessorKey: 'id', header: t('pages.courses.columns.no') },
    {
      accessorKey: 'courseName',
      header: t('pages.courses.columns.courseName'),
      footer: t('pages.courses.footerCount', { count: coursesSummary.value.count })
    },
    { accessorKey: 'courseNameKm', header: t('pages.courses.columns.courseNameKm') },
    { accessorKey: 'description', header: t('pages.courses.columns.description') },
    {
      accessorKey: 'totalClass',
      header: t('pages.courses.columns.totalClass'),
      footer: t('pages.courses.footerTotalClassSum', { sum: coursesSummary.value.totalClassSum })
    },
    { id: 'action', header: t('common.actions') }
  ])

  function resetForm() {
    newCourseName.value = ''
    newCourseNameKm.value = ''
    newCourseDescription.value = ''
    editingId.value = null
    editingSnapshot.value = null
    pendingPayload.value = null
  }

  const canCreateCourse = computed(() => auth.hasPermission(PERMISSIONS.coursesCreate))
  const canUpdateCourse = computed(() => auth.hasPermission(PERMISSIONS.coursesUpdate))
  const canDeleteCourse = computed(() => auth.hasPermission(PERMISSIONS.coursesDelete))

  function handleAdd() {
    if (editingId.value && !canUpdateCourse.value) return
    if (!editingId.value && !canCreateCourse.value) return
    const name = newCourseName.value.trim()
    if (!name) return

    pendingPayload.value = {
      id: editingId.value ?? '',
      courseName: name,
      courseNameKm: newCourseNameKm.value.trim(),
      description: newCourseDescription.value.trim(),
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
        description: t('pages.courses.confirmDelete'),
        type: 'error' as const,
        submitLabel: t('actions.delete'),
        icon: 'i-lucide-trash-2'
      }
    }
    if (confirmMode.value === 'edit') {
      return {
        title: t('actions.save'),
        description: t('pages.courses.confirmSaveEditNamed', {
          name: pendingPayload.value?.courseName ?? ''
        }),
        type: 'primary' as const,
        submitLabel: t('actions.save'),
        icon: 'i-lucide-check-circle'
      }
    }
    return {
      title: t('actions.add'),
      description: t('pages.courses.confirmSaveAddNamed', {
        name: pendingPayload.value?.courseName ?? ''
      }),
      type: 'primary' as const,
      submitLabel: t('actions.confirm'),
      icon: 'i-lucide-check-circle'
    }
  })

  function getDropdownActions(entry: Course): DropdownMenuItem[][] {
    const actions: DropdownMenuItem[] = []
    if (canUpdateCourse.value) {
      actions.push({
        label: t('actions.edit'),
        icon: 'i-lucide-edit',
        onSelect: () => {
          newCourseName.value = entry.courseName
          newCourseNameKm.value = entry.courseNameKm ?? ''
          newCourseDescription.value = entry.description ?? ''
          editingId.value = entry.id
          editingSnapshot.value = {
            totalClass: entry.totalClass
          }
        }
      })
    }
    if (canDeleteCourse.value) {
      actions.push({
        label: t('actions.delete'),
        icon: 'i-lucide-trash',
        color: 'error' as const,
        onSelect: () => {
          pendingDeleteId.value = entry.id
          confirmMode.value = 'delete'
          isConfirmOpen.value = true
        }
      })
    }
    return actions.length ? [actions] : []
  }

  async function finalizeAction() {
    try {
      if (confirmMode.value === 'delete' && pendingDeleteId.value !== null) {
        await mutation.run(() => coursesApi.remove(pendingDeleteId.value!), 'courses')
        await resource.refresh()
        toast.add({ title: t('pages.courses.deleted'), color: 'error' })
        pendingDeleteId.value = null
      } else if (confirmMode.value === 'edit' && pendingPayload.value?.id) {
        const p = pendingPayload.value
        await mutation.run(
          () =>
            coursesApi.update(p.id, {
              courseName: p.courseName,
              courseNameKm: p.courseNameKm,
              description: p.description
            }),
          'courses'
        )
        await resource.refresh()
        toast.add({ title: t('pages.courses.updated'), color: 'primary' })
        resetForm()
      } else if (confirmMode.value === 'add' && pendingPayload.value) {
        const p = pendingPayload.value
        await mutation.run(
          () =>
            coursesApi.create({
              courseName: p.courseName,
              courseNameKm: p.courseNameKm,
              description: p.description
            }),
          'courses'
        )
        await resource.refresh()
        toast.add({ title: t('pages.courses.created'), color: 'primary' })
        resetForm()
      }
    } catch (err: unknown) {
      if (isForbiddenError(err)) {
        isConfirmOpen.value = false
        return
      }
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
    filteredCourses,
    columns,
    newCourseName,
    newCourseNameKm,
    newCourseDescription,
    handleAdd,
    canCreateCourse,
    canUpdateCourse,
    isConfirmOpen,
    confirmConfig,
    finalizeAction,
    getDropdownActions
  }
}
