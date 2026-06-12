<script setup lang="ts">
import { useFinance } from '~/composables/table/useFinance'
import { formatCurrency } from '~/utils/format/currency'
const { t } = useI18n()
const isExportOpen = ref(false)
const {
  data,
  columns,
  isLoading,
  sorting,
  searchQuery,
  columnFilters,
  pagination,
  totalRows,
  isSlideoverOpen,
  editingRow,
  editFields,
  openEdit,
  handleUpdate,
  fetchExportData,
} = useFinance()
</script>

<template>
  <div class="flex flex-col h-full bg-background overflow-hidden text-foreground tracking-tight">
    <LayoutAppHeader :title="t('pages.finance.title')" show-datepicker>
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
        :title="t('pages.finance.tableTitle')"
        :data="data"
        :columns="columns"
        :loading="isLoading"
        v-model:sorting="sorting"
        v-model:column-filters="columnFilters"
        v-model:pagination="pagination"
        :total-rows="totalRows"
        server-pagination
        :selectable="false"
      >
        <template #header>
          <div class="w-full max-w-[280px]">
            <CommonAppSearch v-model="searchQuery" />
          </div>
        </template>

        <template #actions-cell="{ row }">
          <div class="flex justify-center">
            <UButton
              icon="i-lucide-edit"
              variant="ghost"
              color="primary"
              size="sm"
              @click="openEdit(row.original)"
            />
          </div>
        </template>

        <template #className-cell="{ row }">
          <span class="text-sm font-medium text-foreground">
            {{ row.original.className || row.original.productName || '—' }}
          </span>
        </template>

        <template #electricity-cell="{ row }">
          <span class="text-sm">
            {{ formatCurrency(Number(row.getValue('electricity') ?? 0), 'USD') }}
          </span>
        </template>

        <template #water-cell="{ row }">
          <span class="text-sm">
            {{ formatCurrency(Number(row.getValue('water') ?? 0), 'USD') }}
          </span>
        </template>

        <template #internet-cell="{ row }">
          <span class="text-sm">
            {{ formatCurrency(Number(row.getValue('internet') ?? 0), 'USD') }}
          </span>
        </template>

        <template #totalCommission-cell="{ row }">
          <span class="text-sm font-medium text-primary">
            {{ formatCurrency(Number(row.getValue('totalCommission')), 'USD') }}
          </span>
        </template>

        <template #facebook-cell="{ row }">
          <span class="text-sm">{{ formatCurrency(Number(row.getValue('facebook')), 'USD') }}</span>
        </template>

        <template #other-cell="{ row }">
          <span class="text-sm">{{ formatCurrency(Number(row.getValue('other')), 'USD') }}</span>
        </template>

        <template #amount-cell="{ row }">
          <span class="text-sm font-medium">
            {{ formatCurrency(Number(row.getValue('amount')), 'USD') }}
          </span>
        </template>

        <template #finalPrice-cell="{ row }">
          <span class="text-sm font-semibold text-primary">
            {{ formatCurrency(Number(row.getValue('finalPrice')), 'USD') }}
          </span>
        </template>
      </TableApptable>

      <CommonAppExport
        v-model:open="isExportOpen"
        :data="data"
        :fetch-export-data="fetchExportData"
        filename="finance"
      />
    </div>

    <CommonAppSlideoverForm
      v-model:open="isSlideoverOpen"
      :title="t('pages.finance.editTitle')"
      :data="editingRow || undefined"
      :fields="editFields"
      @submit="handleUpdate"
    />
  </div>
</template>
