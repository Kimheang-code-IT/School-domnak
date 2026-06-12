import { ref, computed } from 'vue'
import type { DropdownMenuItem } from '~/types/nuxt-ui'
import { useBaseTable } from "~/composables/table/useBaseTable"
import { useTableQuery } from "~/composables/table/useTableQuery"
import type { AuditLog } from '~/types'
import { useHistoryApi, type ApiQueryParams } from '~/utils/api'
import { useServerTableResource } from '~/composables/table/useServerTable'
import { useTableSearchDateQuery } from '~/composables/table/useTableSearchDateQuery'

/** Canonical API/filter values — must stay in English for backend. */
const HISTORY_ACTION_VALUES = ['Login', 'Logout', 'Create', 'Update', 'Delete', 'Export'] as const

function historyActionSlug(value: string) {
  return value.slice(0, 1).toLowerCase() + value.slice(1)
}

function filterItemValue(entry: unknown): string {
  if (entry !== null && typeof entry === 'object' && 'value' in entry) {
    return String((entry as { value: unknown }).value ?? '')
  }
  return String(entry ?? '')
}

export function useAuditHistory() {
    const useBackendApi = useBackendMode()
    const historyApi = useHistoryApi()
    const { t, te } = useI18n()
    const { formattedRange } = useGlobalFilter()
    const {
      rowSelection,
      columnVisibility,
      isDetailOpen,
    } = useBaseTable({});
  
    const {
      sorting,
      columnFilters,
      pagination,
      serverQuery,
    } = useTableQuery({ initialSorting: [{ id: 'id', desc: true }] });
    const searchQuery = ref('')

    const selectedLog = ref<AuditLog | null>(null)

    /** Labelled items for CommonAppMutilSelect; selection stores full objects matching API codes in `value`. */
    const actionItems = computed(() =>
      HISTORY_ACTION_VALUES.map((value) => ({
        value,
        label: t(`pages.history.actionTypes.${historyActionSlug(value)}`),
      })),
    )
    const selectedActions = ref<{ label: string; value: string }[]>([])
    const selectedActionCodes = computed(() =>
      selectedActions.value.map((x) => x?.value ?? filterItemValue(x)).filter(Boolean),
    )

    const logs = ref<AuditLog[]>([])
    const historyExtraQuery = computed((): Partial<ApiQueryParams> => ({
        action: selectedActionCodes.value.length ? selectedActionCodes.value.join(',') : undefined,
    }))
    const { mergedServerQuery } = useTableSearchDateQuery(
        serverQuery,
        searchQuery,
        pagination,
        formattedRange,
        historyExtraQuery
    )
    const resource = useServerTableResource<AuditLog, ApiQueryParams>({
        resourceKey: 'histories',
        useBackendApi,
        serverQuery: mergedServerQuery,
        localData: logs,
        listFn: (query, signal) => historyApi.list(query, signal),
        debounceMs: 220
    })
    const effectiveLogs = computed(() => resource.rows.value)

    const filteredLogs = computed(() => {
        if (!selectedActionCodes.value.length) return effectiveLogs.value
        const set = new Set(selectedActionCodes.value)
        return effectiveLogs.value.filter((l) => set.has(l.typeAction))
    })

    /** Display string for toolbar/badges; falls back to raw API value */
    function actionTypeLabel(raw: string) {
      const slug = historyActionSlug(raw || '')
      const path = `pages.history.actionTypes.${slug}`
      return te(path) ? t(path) : raw
    }

    function getDropdownActions(log: AuditLog): DropdownMenuItem[][] {
        return [[
            {
                label: t('pages.history.actions.viewDetails'), icon: 'i-lucide-eye',
                onSelect: () => {
                   selectedLog.value = log
                   isDetailOpen.value = true
                }
            }
        ]]
    }

    return {
        rowSelection, sorting, searchQuery, columnVisibility, columnFilters,
        pagination, isDetailOpen,
        isLoading: resource.isLoading,
        totalRows: resource.totalRows,
        selectedLog, logs: effectiveLogs,
        actionItems, selectedActions,
        filteredLogs,
        getDropdownActions,
        formatHistoryAction: actionTypeLabel,
    }
}
