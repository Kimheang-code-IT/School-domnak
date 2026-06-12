<script setup lang="ts">
import { useSystemUserManagement } from '~/composables/settings/useUser'
import { formatDateOnly } from '~/utils/format/date'
import { PERMISSIONS } from '~/utils/auth/permissions'

const auth = useAuthStore()
const canCreateUser = computed(() => auth.hasPermission(PERMISSIONS.settingsUserCreate))

const {
    rowSelection, sorting, searchQuery, columnVisibility, columnFilters,
    pagination, isFormOpen, isConfirmOpen,
    totalRows,
    selectedUser, filteredUsers, confirmConfig,
    userFormFields, columns, roleItems, selectedRoles,
    getDropdownActions, handleSaveRequest, finalizeAction, handleAddNew,
} = useSystemUserManagement()

function onSubmitUser(data: Record<string, any>) {
    handleSaveRequest(data as any)
}
</script>

<template>
    <div class="flex flex-col h-full bg-background overflow-hidden text-foreground tracking-tight">
        <LayoutAppHeader :title="$t('pages.userManagement.title')" show-datepicker>
            <template #right>
                <UButton
                    v-if="canCreateUser"
                    icon="i-lucide-user-plus"
                    color="primary"
                    variant="solid"
                    class="font-normal shadow-sm shrink-0"
                    @click="handleAddNew"
                >
                    <span class="hidden sm:inline">{{ $t('pages.userManagement.addBtn') }}</span>
                </UButton>
            </template>
        </LayoutAppHeader>

        <div class="flex-1 p-2 overflow-hidden">
            <TableApptable :title="$t('pages.userManagement.tableTitle')" v-model:row-selection="rowSelection"
                v-model:sorting="sorting"
                v-model:column-visibility="columnVisibility" v-model:pagination="pagination"
                v-model:column-filters="columnFilters" v-model:filter-value="selectedRoles" :filter-items="roleItems"
                :data="filteredUsers" :columns="columns" :selectable="true" :total-rows="totalRows" :get-row-actions="getDropdownActions">
                <template #header>
                    <div class="w-full max-w-[280px]">
                        <CommonAppSearch v-model="searchQuery" />
                    </div>
                </template>
                <template #name-cell="{ row }">
                    <div class="flex items-center gap-3">
                        <span class="font-normal text-foreground">{{ row.original.name }}</span>
                    </div>
                </template>
                <template #role-cell="{ row }">
                    <UBadge
                        :color="row.original.role === 'Admin' || row.original.role === 'SuperAdmin' ? 'primary' : row.original.role === 'Editor' ? 'secondary' : 'neutral'"
                        variant="soft">
                        {{ row.original.role }}
                    </UBadge>
                </template>
                <template #email-cell="{ row }">
                    <span class="text-sm text-muted-foreground">{{ row.original.email }}</span>
                </template>
                <template #password-cell="{ row }">
                    <span class="text-sm tracking-widest text-muted-foreground opacity-50">••••••••</span>
                </template>
                <template #lastLogin-cell="{ row }">
                    <div class="flex items-center gap-1 text-sm text-primary">
                        {{ formatDateOnly(row.original.lastLogin) }}
                    </div>
                </template>
            </TableApptable>
        </div>

        <CommonAppSlideoverForm v-model:open="isFormOpen" :data="selectedUser || undefined" :fields="userFormFields"
            :title="selectedUser ? $t('actions.edit') : $t('pages.userManagement.addBtn')"
            :submit-label="selectedUser ? $t('actions.save') : $t('actions.confirm')" @submit="onSubmitUser" />
        <CommonAppModalCURD v-model:open="isConfirmOpen" v-bind="confirmConfig" @submit="finalizeAction" />
    </div>
</template>

