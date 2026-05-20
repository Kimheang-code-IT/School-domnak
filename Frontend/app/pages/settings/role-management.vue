<script setup lang="ts">
import { useSystemRoleManagement } from '~/composables/settings/useRole'
import { PERMISSIONS } from '~/utils/auth/permissions'

const auth = useAuthStore()
const {
    rowSelection, sorting, searchQuery, columnVisibility, columnFilters,
    pagination, isFormOpen, isConfirmOpen,
    totalRows,
    selectedRole, filteredRoles, confirmConfig,
    roleFormFields, columns, roleFilterItems, selectedRoles,
    getDropdownActions, handleSaveRequest, finalizeAction, handleAddNew,
} = useSystemRoleManagement()

const canCreateRole = computed(() => auth.hasPermission(PERMISSIONS.settingsRoleCreate))
const canSaveRole = computed(() =>
  selectedRole.value?.id
    ? auth.hasPermission(PERMISSIONS.settingsRoleUpdate)
    : auth.hasPermission(PERMISSIONS.settingsRoleCreate),
)

function onSubmitRole(data: Record<string, any>) {
    if (!canSaveRole.value) return
    handleSaveRequest(data as any)
}
</script>

<template>
    <div class="flex flex-col h-full bg-background overflow-hidden text-foreground tracking-tight">
        <LayoutAppHeader :title="$t('pages.roleManagement.title')" show-datepicker>
            <template #right>
                <UButton
                    v-if="canCreateRole"
                    icon="i-lucide-shield-plus"
                    color="primary"
                    variant="solid"
                    class="font-normal shadow-sm shrink-0"
                    @click="handleAddNew"
                >
                    <span class="hidden sm:inline">{{ $t('pages.roleManagement.addBtn') }}</span>
                </UButton>
            </template>
        </LayoutAppHeader>

        <div class="flex-1 p-2 overflow-hidden">
            <TableApptable :title="$t('pages.roleManagement.tableTitle')" v-model:row-selection="rowSelection"
                v-model:sorting="sorting"
                v-model:column-visibility="columnVisibility" v-model:pagination="pagination"
                v-model:column-filters="columnFilters" v-model:filter-value="selectedRoles"
                :filter-items="roleFilterItems"
                :filter-placeholder="$t('pages.roleManagement.filterByRole')"
                :data="filteredRoles"
                :columns="columns"
                :selectable="true"
                :total-rows="totalRows"
                :get-row-actions="getDropdownActions">
                <template #header>
                    <div class="w-full max-w-[280px]">
                        <CommonAppSearch v-model="searchQuery" />
                    </div>
                </template>
                <template #name-cell="{ row }">
                    <div class="flex items-center gap-2">
                        <span>{{ row.original.name }}</span>
                    </div>
                </template>
                <template #pageAccess-cell="{ row }">
                    <div class="flex flex-wrap gap-1 max-w-md">
                        <template v-if="(row.original.pageAccess || []).includes('ALL_PAGES')">
                            <UBadge variant="solid" color="primary" size="md">Full System Access</UBadge>
                        </template>
                        <template v-else>
                            <UBadge v-for="page in (row.original.pageAccess || [])" :key="page" variant="soft" color="neutral"
                                size="md">{{ page }}</UBadge>
                        </template>
                    </div>
                </template>
            </TableApptable>
        </div>
        <CommonAppSlideoverForm v-model:open="isFormOpen" :data="selectedRole || undefined" :fields="roleFormFields"
            :title="selectedRole ? $t('actions.edit') : $t('pages.roleManagement.addBtn')"
            :submit-label="selectedRole ? $t('actions.save') : $t('actions.confirm')" @submit="onSubmitRole" />
        <CommonAppModalCURD v-model:open="isConfirmOpen" v-bind="confirmConfig" @submit="finalizeAction" />
    </div>
</template>
