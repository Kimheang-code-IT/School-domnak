<script setup lang="ts">
import { useComission } from '~/composables/table/useComission'
import { useTableToolbarFilters } from '~/composables/filters/useTableToolbarFilters'
import { formatCurrency } from '~/utils/format/currency'
import { formatDate } from '~/utils/format/date'

const { t } = useI18n()
const isExportOpen = ref(false)
const {
  data,
  columns,
  groupingOptions,
  grouping,
  expanded,
  isLoading,
  sorting,
  searchQuery,
  columnFilters,
  pagination,
  totalRows,
  catalog,
  selections,
  fetchExportData,
} = useComission()

const toolbarFilters = useTableToolbarFilters(
  computed(() => [
    {
      key: 'source',
      model: selections.source,
      items: catalog.sourceItems,
      placeholder: t('pages.comission.columns.source'),
      class: 'w-24 sm:w-32',
    },
    {
      key: 'classId',
      model: selections.classId,
      items: catalog.classItems,
      placeholder: t('pages.dashboard.filterClass'),
      class: 'w-24 sm:w-36',
    },
  ]),
)
</script>

<template>
  <div class="flex flex-col h-full bg-background overflow-hidden text-foreground tracking-tight">
    <LayoutAppHeader :title="t('pages.comission.title')" show-datepicker>
      <template #right>
        <UButton
          icon="i-lucide-download"
          color="neutral"
          variant="subtle"
          class="font-normal shadow-sm shrink-0"
          @click="isExportOpen = true"
        >
          <span class="hidden sm:inline">{{ t('common.export') }}</span>
        </UButton>
      </template>
    </LayoutAppHeader>

    <div class="flex-1 p-2 overflow-hidden">
      <TableApptable
        :title="t('pages.comission.tableTitle')"
        :data="data"
        :columns="columns"
        :loading="isLoading"
        :total-rows="totalRows"
        server-pagination
        v-model:sorting="sorting"
        v-model:column-filters="columnFilters"
        v-model:pagination="pagination"
        v-model:grouping="grouping"
        v-model:expanded="expanded"
        :grouping-options="groupingOptions"
        :selectable="false"
        :ui="{
          root: 'min-w-full',
          td: 'empty:p-2',
        }"
      >
        <template #filters>
          <TableToolbarFilters :filters="toolbarFilters" />
        </template>
        <template #header>
          <div class="w-full max-w-[280px]">
            <CommonAppSearch v-model="searchQuery" />
          </div>
        </template>
        <template #title-cell="{ row }">
          <div v-if="row.getIsGrouped()" class="flex items-center py-0.5 min-w-0">
            <span class="inline-block shrink-0" :style="{ width: `calc(${row.depth} * 1rem)` }" />
            <UButton
              variant="outline"
              color="neutral"
              size="xs"
              class="mr-2 shrink-0"
              :icon="row.getIsExpanded() ? 'i-lucide-minus' : 'i-lucide-plus'"
              @click="row.toggleExpanded()"
            />
            <strong
              v-if="row.groupingColumnId === 'teacher_key'"
              class="truncate font-semibold text-foreground"
            >
              {{ row.getValue('teacher_key') }}
            </strong>
            <span class="text-muted-foreground shrink-0 text-xs whitespace-nowrap ml-2">
              ({{ row.subRows?.length || 0 }} {{ t('common.items') }})
            </span>
          </div>
        </template>

        <template #source-cell="{ row }">
          <UBadge v-if="!row.getIsGrouped()" color="primary" variant="soft" class="font-normal capitalize">
            {{ row.getValue('source') }}
          </UBadge>
        </template>

        <template #date-cell="{ row }">
          <span class="text-sm text-muted-foreground">
            {{ formatDate(String(row.getValue('date') || '')) }}
          </span>
        </template>

        <template #amount-cell="{ row }">
          <span class="font-medium">{{ formatCurrency(Number(row.getValue('amount')), 'USD') }}</span>
        </template>

        <template #commission-cell="{ row }">
          <UBadge color="primary" variant="soft" class="font-normal">
            {{ formatCurrency(Number(row.getValue('commission')), 'USD') }}
          </UBadge>
        </template>
      </TableApptable>

      <CommonAppExport
        v-model:open="isExportOpen"
        :data="data"
        :fetch-export-data="fetchExportData"
        filename="commission"
        date-field="date"
      />
    </div>
  </div>
</template>
