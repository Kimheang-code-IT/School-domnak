<script setup lang="ts">
import { useLevels } from '~/composables/table/useLevels'

const { t } = useI18n()

const {
  rowSelection,
  sorting,
  searchQuery,
  columnVisibility,
  columnFilters,
  pagination,
  isLoading,
  totalRows,
  filteredLevels,
  columns,
  newLevelNameKm,
  newLevelNameEn,
  newLevelDescription,
  handleAdd,
  isConfirmOpen,
  confirmConfig,
  finalizeAction,
  getDropdownActions,
} = useLevels()

const mobileView = ref<'table' | 'form'>('table')
const mobileViewItems = computed(() => [
  { label: t('pages.levels.tableTitle'), value: 'table' },
  { label: t('pages.levels.addTitle'), value: 'form' },
])

const canSubmit = computed(
  () => newLevelNameKm.value.trim().length > 0 && newLevelNameEn.value.trim().length > 0
)
</script>

<template>
  <div class="flex flex-col h-full bg-background overflow-hidden text-foreground tracking-tight">
    <LayoutAppHeader :title="t('pages.levels.title')" />

    <div class="lg:hidden px-2 pt-2">
      <UTabs v-model="mobileView" :items="mobileViewItems" :content="false" color="primary" class="w-full" />
    </div>

    <div class="flex flex-col lg:flex-row flex-1 gap-3 p-2 overflow-hidden min-h-0">
      <div
        :class="[
          mobileView === 'form' ? 'flex' : 'hidden',
          'lg:flex w-full lg:w-[30%] lg:shrink-0 flex-col gap-4 p-5 border border-default overflow-y-auto',
        ]"
      >
        <h2 class="text-base font-semibold text-foreground">{{ t('pages.levels.addTitle') }}</h2>
        <div class="w-full h-px bg-border" />

        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-medium text-foreground">
            {{ t('pages.levels.columns.levelNameEn') }}
            <span class="text-red-500 ml-0.5">*</span>
          </label>
          <UInput
            v-model="newLevelNameEn"
            :placeholder="t('pages.levels.placeholders.levelNameEn')"
            class="w-full"
            size="md"
          />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-medium text-foreground">
            {{ t('pages.levels.columns.levelNameKm') }}
            <span class="text-red-500 ml-0.5">*</span>
          </label>
          <UInput
            v-model="newLevelNameKm"
            :placeholder="t('pages.levels.placeholders.levelNameKm')"
            class="w-full"
            size="md"
          />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-medium text-foreground">
            {{ t('pages.levels.columns.description') }}
          </label>
          <UTextarea
            v-model="newLevelDescription"
            :placeholder="t('pages.levels.placeholders.description')"
            :rows="5"
            class="w-full resize-y"
            size="md"
          />
        </div>

        <UButton
          block
          color="primary"
          variant="solid"
          size="md"
          class="mt-auto font-medium"
          :disabled="!canSubmit"
          @click="handleAdd"
        >
          {{ t('actions.add') }}
        </UButton>
      </div>

      <div :class="[mobileView === 'table' ? 'flex' : 'hidden', 'lg:flex w-full flex-1 overflow-hidden']">
        <TableApptable
          :title="t('pages.levels.tableTitle')"
          v-model:row-selection="rowSelection"
          v-model:sorting="sorting"
          v-model:column-visibility="columnVisibility"
          v-model:pagination="pagination"
          v-model:column-filters="columnFilters"
          :data="filteredLevels"
          :loading="isLoading"
          :total-rows="totalRows"
          :columns="columns"
          :selectable="false"
          :get-row-actions="getDropdownActions"
        >
          <template #header>
            <div class="w-full max-w-[280px]">
              <CommonAppSearch v-model="searchQuery" />
            </div>
          </template>

          <template #id-cell="{ row }">
            {{ pagination.pageIndex * pagination.pageSize + row.index + 1 }}
          </template>

          <template #description-cell="{ row }">
            <span
              :class="
                row.original.description
                  ? 'text-sm text-foreground line-clamp-2'
                  : 'text-sm text-muted-foreground/40 italic'
              "
              :title="row.original.description || undefined"
            >
              {{ row.original.description || '—' }}
            </span>
          </template>

          <template #totalClass-cell="{ row }">
            <UBadge variant="soft" color="primary" size="md">
              {{ row.original.totalClass }} {{ t('pages.levels.units.classes') }}
            </UBadge>
          </template>
        </TableApptable>
      </div>
    </div>

    <CommonAppModalCURD v-model:open="isConfirmOpen" v-bind="confirmConfig" @submit="finalizeAction" />
  </div>
</template>
