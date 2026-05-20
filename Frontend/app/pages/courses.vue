<script setup lang="ts">
import { useCourses } from '~/composables/table/useCourses'

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
  filteredCourses,
  columns,
  newCourseName,
  newCourseNameKm,
  newCourseDescription,
  handleAdd,
  isConfirmOpen,
  confirmConfig,
  finalizeAction,
  getDropdownActions,
} = useCourses()

const mobileView = ref<'table' | 'form'>('table')
const mobileViewItems = computed(() => [
  { label: t('pages.courses.tableTitle'), value: 'table' },
  { label: t('pages.courses.addTitle'), value: 'form' },
])

function getAvatarColor(name: string) {
  const colors = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
}

function getInitial(name: string) {
  return name.charAt(0).toUpperCase()
}
</script>

<template>
  <div class="flex flex-col h-full bg-background overflow-hidden text-foreground tracking-tight">
    <LayoutAppHeader :title="t('pages.courses.title')" />

    <div class="lg:hidden px-2 pt-2">
      <UTabs
        v-model="mobileView"
        :items="mobileViewItems"
        :content="false"
        color="primary"
        class="w-full"
      />
    </div>

    <div class="flex flex-col lg:flex-row flex-1 gap-3 p-2 overflow-hidden min-h-0">
      <!-- Left: add / edit form -->
      <div
        :class="[
          mobileView === 'form' ? 'flex' : 'hidden',
          'lg:flex w-full lg:w-[30%] lg:shrink-0 flex-col gap-4 p-5 border border-default overflow-y-auto',
        ]"
      >
        <h2 class="text-base font-semibold text-foreground">{{ t('pages.courses.addTitle') }}</h2>
        <div class="w-full h-px bg-border" />

        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-medium text-foreground">
            {{ t('pages.courses.columns.courseName') }}
            <span class="text-red-500 ml-0.5">*</span>
          </label>
          <UInput
            v-model="newCourseName"
            :placeholder="t('pages.courses.placeholders.courseName')"
            class="w-full"
            size="md"
          />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-medium text-foreground">
            {{ t('pages.courses.columns.courseNameKm') }}
          </label>
          <UInput
            v-model="newCourseNameKm"
            :placeholder="t('pages.courses.placeholders.courseNameKm')"
            class="w-full"
            size="md"
          />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-sm font-medium text-foreground">
            {{ t('pages.courses.columns.description') }}
          </label>
          <UTextarea
            v-model="newCourseDescription"
            :placeholder="t('pages.courses.placeholders.description')"
            :rows="7"
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
          :disabled="!newCourseName.trim()"
          @click="handleAdd"
        >
          {{ t('actions.add') }}
        </UButton>
      </div>

      <!-- Right: table -->
      <div
        :class="[
          mobileView === 'table' ? 'flex' : 'hidden',
          'lg:flex w-full flex-1 overflow-hidden',
        ]"
      >
        <TableApptable
          :title="t('pages.courses.tableTitle')"
          v-model:row-selection="rowSelection"
          v-model:sorting="sorting"
          v-model:column-visibility="columnVisibility"
          v-model:pagination="pagination"
          v-model:column-filters="columnFilters"
          :data="filteredCourses"
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

          <template #courseName-cell="{ row }">
            <div class="flex items-center gap-2.5">
              <span
                class="flex items-center justify-center w-8 h-8 rounded-full text-white text-sm font-bold shrink-0"
                :style="{ backgroundColor: getAvatarColor(row.original.courseName) }"
              >
                {{ getInitial(row.original.courseName) }}
              </span>
              <span class="font-medium text-foreground truncate max-w-[180px]">
                {{ row.original.courseName }}
              </span>
            </div>
          </template>

          <template #description-cell="{ row }">
            <span
              :class="
                row.original.description ? 'text-foreground' : 'text-muted-foreground/40 italic text-sm'
              "
            >
              {{ row.original.description || t('pages.courses.emptyDescription') }}
            </span>
          </template>

          <template #totalClass-cell="{ row }">
            <UBadge variant="soft" color="primary" size="md">
              {{ row.original.totalClass }} {{ t('pages.courses.units.classes') }}
            </UBadge>
          </template>
        </TableApptable>
      </div>
    </div>

    <CommonAppModalCURD v-model:open="isConfirmOpen" v-bind="confirmConfig" @submit="finalizeAction" />
  </div>
</template>
