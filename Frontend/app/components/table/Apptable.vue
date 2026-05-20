<template>
  <div class="flex flex-col w-full h-full overflow-hidden border border-default rounded-xs bg-background shadow-sm">
    <!-- Header Toolbar -->
    <div
      v-if="title || $slots.header || $slots.filters || globalFilter !== undefined || columnVisibility !== undefined || filterValue !== undefined || filterValueSecondary !== undefined"
      class="flex flex-row items-center justify-between gap-2 px-3 py-2.5 border-b border-accented shrink-0 overflow-hidden">
      <div class="flex flex-1 items-center gap-2 min-w-0">
        <ClientOnly>
          <div v-if="title" class="min-w-0 hidden md:block">
            <h2 v-if="title" class="font-medium text-foreground tracking-tight leading-none truncate">{{ title }}
            </h2>
          </div>
        </ClientOnly>

      </div>

      <div class="flex flex-nowrap items-center justify-end gap-2 ml-auto max-w-full overflow-hidden shrink-0">
        <slot name="filters" />

        <!-- Multi-Select Filters -->
        <CommonAppMutilSelect v-if="filterValue !== undefined && filterItems" v-model="filterValue" :items="filterItems"
          :placeholder="filterPlaceholder || $t('components.search')" />
        <CommonAppMutilSelect v-if="filterValueSecondary !== undefined && filterItemsSecondary"
          v-model="filterValueSecondary" :items="filterItemsSecondary"
          :placeholder="filterPlaceholderSecondary || $t('components.search')" />

        <!-- Global Filter Input -->
        <div v-if="globalFilter !== undefined" class="min-w-30 sm:min-w-50 shrink-0">
          <CommonAppSearch v-model="globalFilter" />
        </div>

        <!-- Toolbar actions (search, etc.) -->
        <div v-if="$slots.header" class="min-w-30 sm:min-w-50 max-w-[280px] shrink-0">
          <slot name="header" />
        </div>
      </div>
    </div>

    <!-- Main Table Component -->
    <UTable ref="table" v-bind="$attrs" v-model:sorting="sorting" v-model:column-filters="columnFilters"
      v-model:global-filter="globalFilter" v-model:row-selection="rowSelection"
      v-model:column-visibility="columnVisibility" v-model:grouping="grouping" v-model:column-pinning="columnPinning"
      v-model:pagination="pagination" :pagination-options="mergedPaginationOptions" :data="data"
      :columns="processedColumns" :loading="loading" :loading-options="{
        color: 'primary',
        animation: 'carousel'
      }" :virtualize="virtualize ? { estimateSize: 44, overscan: 10 } : false"
      :sticky="virtualize ? false : ($attrs.sticky as any ?? 'header')"
      class="flex-1 overflow-auto min-h-0 relative scroll-shadow-right" :ui="{
        thead: 'sticky top-0 inset-x-0 z-10 bg-neutral-100 dark:bg-gray-900',
        th: 'py-2 px-3 text-sm font-normal text-muted-foreground bg-neutral-100 dark:bg-gray-900 whitespace-nowrap',
        tfoot: 'sticky bottom-0 inset-x-0 z-10 bg-muted/70 backdrop-blur-sm',
        tr: 'border-b border-accented/50 last:border-b-0',
        td: 'py-2 px-3 text-sm font-normal'
      }">
      <template #loading-state>
        <CommonAppLoadingState compact class="w-full min-h-[280px]" />
      </template>

      <!-- Action Cell Implementation -->
      <template #action-cell="{ row }">
        <slot name="action-cell" :row="row">
          <UDropdownMenu v-if="getRowActions" :items="getRowActions(row.original)" :content="{ align: 'end' }">
            <UButton icon="i-lucide-ellipsis-vertical" color="neutral" variant="ghost" class="rounded-md" size="sm" />
          </UDropdownMenu>
        </slot>
      </template>

      <!-- Forward other slots -->
      <template v-for="(_, slotName) in $slots" #[slotName]="slotProps">
        <slot v-if="!['action-cell', 'header', 'footer'].includes(slotName as string)" :name="slotName"
          v-bind="slotProps" />
      </template>

      <!-- Empty State -->
      <template #empty>
        <slot name="empty">
          <div
            class="flex flex-col items-center justify-center flex-1 h-full w-full py-28 text-muted-foreground opacity-60">
            <UIcon name="i-lucide-database" class="size-20 mb-3" />
            <p class="text-xl font-normal italic">{{ $t('common.noData') }}</p>
          </div>
        </slot>
      </template>
    </UTable>

    <!-- Unified Footer Pagination -->
    <ClientOnly>
      <CommonAppFooterPagin v-if="pagination" v-model:pagination="pagination" :total="props.totalRows ?? data.length"
        :selectable="selectable" :selected-count="Object.keys(rowSelection || {}).length"
        :all-selected="table?.table?.getIsAllRowsSelected() || false"
        @toggle-select-all="(val) => table?.table?.toggleAllRowsSelected(val)" />
    </ClientOnly>
  </div>
</template>

<script setup lang="ts" generic="T">
import { h, computed, onMounted, useTemplateRef, resolveComponent } from 'vue'
import { useInfiniteScroll } from '@vueuse/core'
import type { DropdownMenuItem, TableColumn } from '~/types/nuxt-ui'
import { getPaginationRowModel } from '@tanstack/vue-table'
import type { Column } from '@tanstack/vue-table'
import AppHeaderCell from './AppHeaderCell.vue'


// Forward other slots
const props = withDefaults(defineProps<{
  data: T[]
  columns: TableColumn<T>[]
  loading?: boolean
  canLoadMore?: boolean
  virtualize?: boolean
  // getRowActions should return a flat array for NavigationMenu or Nested for Dropdown
  // In Nuxt UI v4, DropdownMenu items are DropdownMenuItem[][]
  getRowActions?: (item: T) => DropdownMenuItem[][]
  filterItems?: any[]
  filterPlaceholder?: string
  filterItemsSecondary?: any[]
  filterPlaceholderSecondary?: string
  title?: string
  selectable?: boolean
  totalRows?: number
  /** When true, `data` is already sliced for the current server page; pagination uses `totalRows`. */
  serverPagination?: boolean
}>(), {
  canLoadMore: true,
  virtualize: true,
  selectable: true, // Default to true if rowSelection is provided
  serverPagination: false,
})

// V-Models for TanStack Table state
const filterValue = defineModel<any[]>('filterValue')
const filterValueSecondary = defineModel<any[]>('filterValueSecondary')
const sorting = defineModel<any>('sorting')
const columnFilters = defineModel<any>('columnFilters')
const globalFilter = defineModel<string>('globalFilter')
const rowSelection = defineModel<any>('rowSelection')
const columnVisibility = defineModel<any>('columnVisibility')
const grouping = defineModel<any>('grouping')
const columnPinning = defineModel<any>('columnPinning')
const pagination = defineModel<any>('pagination', {
  default: () => ({ pageIndex: 0, pageSize: 15 })
})

const mergedPaginationOptions = computed(() => {
  if (props.serverPagination) {
    const pageSize = Math.max(1, Number(pagination.value?.pageSize ?? 15))
    const total = Math.max(0, Number(props.totalRows ?? 0))
    const pageCount = Math.max(1, Math.ceil(total / pageSize))
    return {
      manualPagination: true,
      pageCount,
    }
  }
  return { getPaginationRowModel: getPaginationRowModel() }
})

const emit = defineEmits<{
  (e: 'load-more'): void
}>()

const table = useTemplateRef<any>('table')

/**
 * Recursive logic to allow merged headers and apply Cell Registry.
 */
function processColumnDefinitions(cols: any[]): any[] {
  return cols.map(col => {
    if (col.columns && Array.isArray(col.columns)) {
      return {
        ...col,
        columns: processColumnDefinitions(col.columns)
      }
    }

    // Process new column definition
    const processed = { ...col }



    // Wrap sortable string headers with reusable AppHeaderCell (supports multi-sort logic)
    if (
      typeof processed.header === 'string' &&
      processed.header.trim() !== '' &&
      processed.id !== 'action' &&
      processed.accessorKey !== 'action' &&
      processed.enableSorting !== false
    ) {
      const label = processed.header
      const icon = processed.icon
      processed.header = ({ column }: { column: Column<T, any> }) => h(AppHeaderCell as any, {
        column,
        label,
        icon: icon as string | undefined
      })
    }

    // Action column — render label as plain styled text (no sorting)
    if (typeof processed.header === 'string' && (processed.id === 'action' || processed.accessorKey === 'action')) {
      const label = processed.header
      const icon = processed.icon
      processed.header = () => h('div', { class: 'flex items-center gap-1 px-[3px]' }, [
        icon ? h(resolveComponent('UIcon') as any, { name: icon as string, class: 'w-3 h-3 shrink-0' }) : null,
        h('span', { class: 'text-sm font-medium whitespace-nowrap' }, label)
      ].filter(Boolean))
    }

    // Footer: allow simple string footer values in column definitions.
    if (typeof processed.footer === 'string') {
      const footerLabel = processed.footer
      processed.footer = () => h('span', { class: 'text-sm font-semibold whitespace-nowrap' }, footerLabel)
    }
    return processed
  })
}

let lastColumnsRef: TableColumn<T>[] | null = null
let lastProcessedColumns: TableColumn<T>[] = []
const processedColumns = computed(() => {
  if (lastColumnsRef === props.columns) return lastProcessedColumns
  lastColumnsRef = props.columns
  lastProcessedColumns = processColumnDefinitions(props.columns) as TableColumn<T>[]
  return lastProcessedColumns
})


onMounted(() => {
  // Infinite Scroll logic for hybrid mode
  const scrollEl = table.value?.$el?.querySelector('.overflow-auto') || table.value?.$el
  if (scrollEl) {
    useInfiniteScroll(scrollEl, () => emit('load-more'),
      { distance: 200, canLoadMore: () => !props.loading && props.canLoadMore }
    )
  }
})

defineOptions({ inheritAttrs: false })
</script>
