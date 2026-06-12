<script setup lang="ts">
import { useTotalRevenue } from '~/composables/table/useCategory'

const {
    rowSelection, sorting, searchQuery, columnVisibility, columnFilters,
    pagination, selectedClassifications,
    filteredEntries, columns, totalRows,
    newName, newDescription, handleAdd,
    isConfirmOpen, confirmConfig, finalizeAction,
    getDropdownActions,
} = useTotalRevenue()

const isExportOpen = ref(false)
const mobileView = ref<'table' | 'form'>('table')
const mobileViewItems = computed(() => [
    { label: $t('category.tableTitle'), value: 'table' },
    { label: $t('category.addTitle'), value: 'form' }
])

// Generate avatar color from name
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
        <LayoutAppHeader :title="$t('category.tableTitle')" />
        <div class="lg:hidden px-2 pt-2">
            <UTabs
                v-model="mobileView"
                :items="mobileViewItems"
                :content="false"
                color="primary"
                class="w-full"
            />
        </div>
        <!-- Split Layout -->
        <div class="flex flex-col lg:flex-row flex-1 gap-3 p-2 overflow-hidden min-h-0">
            <!-- Left: Add Form Panel -->
            <div
                :class="[
                    mobileView === 'form' ? 'flex' : 'hidden',
                    'lg:flex w-full lg:w-[30%] lg:shrink-0 flex-col gap-4 p-5 border border-default overflow-y-auto'
                ]"
            >
                <h2 class="text-base font-semibold text-foreground">{{ $t('category.addTitle') }}</h2>
                <div class="w-full h-px bg-border" />
                <!-- Category Name -->
                <div class="flex flex-col gap-1.5">
                    <label class="text-sm font-medium text-foreground">
                        {{ $t('category.name') }}
                        <span class="text-red-500 ml-0.5">*</span>
                    </label>
                    <UInput
                        v-model="newName"
                        :placeholder="$t('category.namePlaceholder')"
                        class="w-full"
                        size="md"
                    />
                </div>

                <!-- Description -->
                <div class="flex flex-col gap-1.5">
                    <label class="text-sm font-medium text-foreground">
                        {{ $t('category.description') }}
                    </label>
                    <UTextarea
                        v-model="newDescription"
                        :placeholder="$t('category.descriptionPlaceholder')"
                        :rows="7"
                        class="w-full resize-y"
                        size="md"
                    />
                </div>
                <!-- Add Button -->
                <UButton
                    block
                    color="primary"
                    variant="solid"
                    size="md"
                    class="mt-auto font-medium"
                    :disabled="!newName.trim()"
                    @click="handleAdd"
                >
                    {{ $t('actions.add') }}
                </UButton>
            </div>

            <!-- Right: Table Panel -->
            <div
                :class="[
                    mobileView === 'table' ? 'flex' : 'hidden',
                    'lg:flex w-full flex-1 overflow-hidden'
                ]"
            >
                <TableApptable
                    :title="$t('category.tableTitle')"
                    v-model:row-selection="rowSelection"
                    v-model:sorting="sorting"
                    v-model:column-visibility="columnVisibility"
                    v-model:pagination="pagination"
                    v-model:column-filters="columnFilters"
                    v-model:filter-value="selectedClassifications"
                    :data="filteredEntries"
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

                    <!-- Auto row number (frontend only) -->
                    <template #id-cell="{ row }">
                        {{ pagination.pageIndex * pagination.pageSize + row.index + 1 }}
                    </template>

                    <!-- Name with avatar -->
                    <template #name-cell="{ row }">
                        <div class="flex items-center gap-2.5">
                            <span
                                class="flex items-center justify-center w-8 h-8 rounded-full text-white text-sm font-bold shrink-0"
                                :style="{ backgroundColor: getAvatarColor(row.original.name) }"
                            >
                                {{ getInitial(row.original.name) }}
                            </span>
                            <span class="font-medium text-foreground truncate max-w-[180px]">
                                {{ row.original.name }}
                            </span>
                        </div>
                    </template>

                    <!-- Description -->
                    <template #description-cell="{ row }">
                        <span :class="row.original.description ? 'text-foreground' : 'text-muted-foreground/40 italic text-sm'">
                            {{ row.original.description || '—' }}
                        </span>
                    </template>

                    <!-- Total -->
                    <template #total-cell="{ row }">
                        <UBadge variant="soft" color="primary" size="md">
                            {{ row.original.total }} {{ $t('common.items') }}
                        </UBadge>
                    </template>

                </TableApptable>
            </div>
        </div>

        <!-- Modals -->
        <CommonAppModalCURD v-model:open="isConfirmOpen" v-bind="confirmConfig" @submit="finalizeAction" />
        <CommonAppExport v-model:open="isExportOpen" :data="filteredEntries" filename="categories" />
    </div>
</template>
