<script setup lang="ts">
import { useAuditHistory } from '~/composables/table/useHistory'
import { truncateText } from '~/utils/format/text'
import { formatDate } from '~/utils/format/date'
import { getActionColor } from '~/utils/helpers/common'

const { t } = useI18n()

const {
    rowSelection, sorting, searchQuery, columnVisibility, columnFilters,
    pagination, isDetailOpen,
    totalRows,
    selectedLog, filteredLogs,
    actionItems, selectedActions,
    getDropdownActions,
    formatHistoryAction,
} = useAuditHistory()

const isExportOpen = ref(false)

const localColumns = computed(() => [
    { accessorKey: 'id', header: t('common.rank') },
    { accessorKey: 'typeAction', header: t('pages.history.columns.typeAction') },
    { accessorKey: 'username', header: t('pages.history.columns.username') },
    { accessorKey: 'date', header: t('pages.history.columns.date') },
    { accessorKey: 'description', header: t('pages.history.columns.description') },
])
</script>

<template>
    <div class="flex flex-col h-full bg-background overflow-hidden text-foreground tracking-tight">
        <LayoutAppHeader :title="$t('pages.history.title')" show-datepicker>
            <template #right>
                <UButton @click="isExportOpen = true" icon="i-lucide-download" color="neutral" variant="subtle"
                    class="font-normal shadow-sm shrink-0">
                    <span class="hidden sm:inline">{{ $t('common.export') }}</span>
                </UButton>
            </template>
        </LayoutAppHeader>

        <div class="flex-1 p-2 overflow-hidden">
            <TableApptable :title="$t('pages.history.tableTitle')" v-model:row-selection="rowSelection"
                v-model:sorting="sorting" v-model:column-visibility="columnVisibility" v-model:pagination="pagination"
                v-model:column-filters="columnFilters" v-model:filter-value="selectedActions"
                :filter-items="actionItems" :data="filteredLogs" :total-rows="totalRows" :columns="localColumns"
                :selectable="true" :get-row-actions="getDropdownActions">
                <template #header>
                    <div class="w-full max-w-[280px]">
                        <CommonAppSearch v-model="searchQuery" />
                    </div>
                </template>
                <template #typeAction-cell="{ row }">
                    <UBadge :color="getActionColor(row.original.typeAction)" size="sm" class="font-extrabold uppercase">
                        {{ formatHistoryAction(row.original.typeAction) }}
                    </UBadge>
                </template>
                <template #username-cell="{ row }">
                    <div class="flex items-center gap-2">
                        <span class="font-normal text-foreground text-sm">{{ row.original.username }}</span>
                    </div>
                </template>
                <template #date-cell="{ row }">
                    <span class="text-sm text-muted-foreground tracking-normal">{{ formatDate(row.original.date)
                        }}</span>
                </template>
                <template #description-cell="{ row }">
                    <span class="text-sm text-muted-foreground line-clamp-1 max-w-lg">{{
                        truncateText(row.original.description, 40) }}</span>
                </template>
                <template #action-cell="{ row }">
                    <UButton icon="i-lucide-eye" color="neutral" variant="ghost" size="sm"
                        @click="selectedLog = row.original; isDetailOpen = true" />
                </template>
            </TableApptable>
        </div>

        <CommonAppSlideoverForm v-model:open="isDetailOpen" :data="selectedLog || undefined" :fields="[
            { key: 'typeAction', label: $t('pages.history.columns.typeAction'), type: 'input', icon: 'i-lucide-activity' },
            { key: 'username', label: $t('pages.history.columns.username'), type: 'input', icon: 'i-lucide-user' },
            { key: 'date', label: $t('pages.history.columns.date'), type: 'input', icon: 'i-lucide-calendar' },
            { key: 'description', label: $t('pages.history.columns.description'), type: 'textarea', icon: 'i-lucide-file-text' }
        ]" :title="$t('pages.history.detailTitle')" :submit-label="$t('pages.history.closeDetails')"
            @submit="isDetailOpen = false" />
        <CommonAppExport v-model:open="isExportOpen" :data="filteredLogs" filename="audit-history" date-field="date" />
    </div>
</template>
