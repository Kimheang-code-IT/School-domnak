<script setup lang="ts">
import { useProduct } from '~/composables/table/useAllStudent'
import { useTableToolbarFilters } from '~/composables/filters/useTableToolbarFilters'
import { formatDate } from '~/utils/format/date'
import { formatStudentCode } from '~/utils/format/studentCode'
import { provinceDisplayLabel } from '~/utils/format/provinceDisplay'
import type { Product } from '~/types'
import { resolveUploadUrl } from '~/utils/helpers/mediaUrl'

const { t } = useI18n()

function genderLabel(g: string | undefined) {
  const v = String(g || '').trim().toLowerCase()
  if (!v) return '—'
  if (v === 'male' || v === 'm') return t('pages.allstudent.gender.male')
  if (v === 'female' || v === 'f') return t('pages.allstudent.gender.female')
  return g || '—'
}

const {
  rowSelection,
  sorting,
  searchQuery,
  columnVisibility,
  columnFilters,
  pagination,
  isFormOpen,
  isConfirmOpen,
  totalRows,
  isLoading,
  selectedEntry,
  entries,
  confirmConfig,
  columns,
  entryFormFields,
  filterCatalog,
  filterSelections,
  getDropdownActions,
  handleSaveRequest,
  finalizeAction,
  handleAddNew,
  isEnrollmentModalOpen,
  enrollmentStudentId,
  enrollmentStudentName,
  enrollmentStudentGender,
  enrollmentStudentBirthdate,
  enrollmentStudentImage,
  enrollmentRows,
  isEnrollmentLoading,
  enrollmentTotalRows,
  enrollmentPagination,
  enrollmentDateRange,
  openEnrollmentModal,
  isEnrollmentDeleteConfirmOpen,
  enrollmentDeleteConfirmConfig,
  enrollmentDeleteSubmitting,
  requestDeleteEnrollment,
  confirmDeleteEnrollment,
  dismissEnrollmentDeleteConfirm,
} = useProduct()

const toolbarFilters = useTableToolbarFilters(
  computed(() => [
    {
      key: 'province',
      model: filterSelections.province,
      items: filterCatalog.provinceItems,
      placeholder: t('product.province'),
      class: 'w-24 sm:w-36',
    },
    {
      key: 'gender',
      model: filterSelections.gender,
      items: filterCatalog.genderItems,
      placeholder: t('product.gender'),
      class: 'w-24 sm:w-32',
    },
    {
      key: 'classId',
      model: filterSelections.classId,
      items: filterCatalog.classItems,
      placeholder: t('pages.dashboard.filterClass'),
      class: 'w-24 sm:w-36',
    },
    {
      key: 'courseId',
      model: filterSelections.courseId,
      items: filterCatalog.courseItems,
      placeholder: t('pages.dashboard.filterCourse'),
      class: 'w-24 sm:w-36',
    },
  ]),
)

const isExportOpen = ref(false)

function onSubmitProduct(data: Record<string, any>) {
  handleSaveRequest(data as any)
}

function onProductImageError(event: Event) {
  const img = event.target as HTMLImageElement | null
  if (!img) return
  img.src = '/logo.png'
}

function displayName(row: Product) {
  return row.nameKm || row.nameEn || row.name || '—'
}
</script>

<template>
  <div class="flex flex-col h-full bg-background overflow-hidden text-foreground tracking-tight">
    <LayoutAppHeader :title="$t('pages.dataEntry.title')" show-datepicker>
      <template #right>
        <UButton
          icon="i-lucide-download"
          color="neutral"
          variant="subtle"
          class="font-normal shadow-sm shrink-0"
          @click="isExportOpen = true"
        >
          <span class="hidden sm:inline">{{ $t('common.export') }}</span>
        </UButton>
        <UButton
          icon="i-lucide-circle-plus"
          color="primary"
          variant="solid"
          class="font-normal shadow-sm shrink-0"
          @click="handleAddNew"
        >
          <span class="hidden sm:inline">{{ $t('pages.dataEntry.addBtn') }}</span>
        </UButton>
      </template>
    </LayoutAppHeader>

    <div class="flex-1 p-2 overflow-hidden">
      <TableApptable
        :title="$t('pages.dataEntry.tableTitle')"
        v-model:row-selection="rowSelection"
        v-model:sorting="sorting"
        v-model:column-visibility="columnVisibility"
        v-model:pagination="pagination"
        v-model:column-filters="columnFilters"
        :data="entries"
        :columns="columns"
        :loading="isLoading"
        :selectable="false"
        :total-rows="totalRows"
        server-pagination
        :get-row-actions="getDropdownActions"
      >
        <template #filters>
          <TableToolbarFilters :filters="toolbarFilters" />
        </template>
        <template #header>
          <div class="w-full max-w-[280px]">
            <CommonAppSearch v-model="searchQuery" />
          </div>
        </template>

        <template #studentCode-cell="{ row }">
          <span class="text-xs font-medium text-muted-foreground">
            {{
              row.original.studentCode ||
              row.original.studentId ||
              row.original.displayId ||
              formatStudentCode(row.original.id)
            }}
          </span>
        </template>

        <template #image-cell="{ row }">
          <img
            :src="resolveUploadUrl(row.original.image) || '/logo.png'"
            :alt="displayName(row.original)"
            loading="lazy"
            class="size-9 rounded-full object-cover border border-default bg-muted"
            @error="onProductImageError"
          />
        </template>

        <template #nameKm-cell="{ row }">
          <span class="font-medium text-foreground">{{ row.original.nameKm || '—' }}</span>
        </template>

        <template #nameEn-cell="{ row }">
          <span class="text-foreground">{{ row.original.nameEn || '—' }}</span>
        </template>

        <template #gender-cell="{ row }">
          <span class="text-sm text-muted-foreground">{{ genderLabel(row.original.gender) }}</span>
        </template>

        <template #birthdate-cell="{ row }">
          <span class="text-sm text-muted-foreground">
            {{ row.original.birthdate ? formatDate(row.original.birthdate) : '—' }}
          </span>
        </template>

        <template #phone-cell="{ row }">
          <span class="text-sm text-muted-foreground">{{ row.original.phone || '—' }}</span>
        </template>

        <template #province-cell="{ row }">
          <span class="text-sm text-foreground">
            {{ provinceDisplayLabel(t, row.original.province) }}
          </span>
        </template>

        <template #totalCourse-cell="{ row }">
          <UButton
            color="primary"
            variant="soft"
            size="xs"
            class="font-normal tabular-nums"
            :disabled="!Number(row.original.totalCourse || 0)"
            @click="openEnrollmentModal(row.original)"
          >
            {{ Number(row.original.totalCourse || 0) }}
          </UButton>
        </template>

        <template #createdAt-cell="{ row }">
          <span class="text-sm text-muted-foreground">
            {{ row.original.createdAt ? formatDate(row.original.createdAt) : '—' }}
          </span>
        </template>
      </TableApptable>

      <CommonAppExport
        v-model:open="isExportOpen"
        :data="entries"
        filename="students"
        date-field="createdAt"
      />
    </div>

    <CommonAppSlideoverForm
      v-model:open="isFormOpen"
      :data="selectedEntry || undefined"
      :fields="entryFormFields"
      :title="selectedEntry ? $t('pages.dataEntry.formTitleEdit') : $t('pages.dataEntry.formTitleNew')"
      :submit-label="selectedEntry ? $t('actions.save') : $t('actions.confirm')"
      @submit="onSubmitProduct"
    />
    <CommonAppModalCURD v-model:open="isConfirmOpen" v-bind="confirmConfig" @submit="finalizeAction" />

    <CommonAppStudentEnrollmentModal
      v-model:open="isEnrollmentModalOpen"
      v-model:range="enrollmentDateRange"
      v-model:pagination="enrollmentPagination"
      :student-id="enrollmentStudentId"
      :student-name="enrollmentStudentName"
      :student-gender="enrollmentStudentGender"
      :student-birthdate="enrollmentStudentBirthdate"
      :student-image="enrollmentStudentImage"
      :data="enrollmentRows"
      :loading="isEnrollmentLoading"
      :total="enrollmentTotalRows"
      @delete-enrollment="requestDeleteEnrollment"
    />

    <CommonAppModalCURD
      v-model:open="isEnrollmentDeleteConfirmOpen"
      v-bind="enrollmentDeleteConfirmConfig"
      :loading="enrollmentDeleteSubmitting"
      @submit="confirmDeleteEnrollment"
      @update:open="(open) => { if (!open) dismissEnrollmentDeleteConfirm() }"
    />
  </div>
</template>