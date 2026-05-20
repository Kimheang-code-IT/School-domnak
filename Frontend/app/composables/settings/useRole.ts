import { ref, computed } from 'vue'
import type { DropdownMenuItem, TableColumn } from '~/types/nuxt-ui'
import { useBaseTable } from '~/composables/table/useBaseTable'
import { useTableQuery } from '~/composables/table/useTableQuery'
import type { SystemRole, FormField } from '~/types'
import { PERMISSIONS } from '~/utils/auth/permissions'
import { mergeRolePermissionOptions } from '~/utils/auth/permissionCatalog'
import { useSystemRoleApi } from '~/utils/api'
import type { ApiQueryParams } from '~/utils/api'
import { useServerTableResource } from '~/composables/table/useServerTable'
import { useTableSearchDateQuery } from '~/composables/table/useTableSearchDateQuery'
import { useMutation } from '~/composables/data/useMutation'

function flattenPermissions(permissions?: Record<string, string[]>): string[] {
    if (!permissions || typeof permissions !== 'object') return []
    return Object.entries(permissions).flatMap(([page, actions]) =>
        Array.isArray(actions) ? actions.map(action => `${page}:${action}`) : []
    )
}

/** Built-in Admin role — hidden from Role Management UI. */
const ROLE_MANAGEMENT_HIDDEN_NAMES = new Set(['admin'])

function isHiddenSystemRole(name?: string): boolean {
    return ROLE_MANAGEMENT_HIDDEN_NAMES.has(String(name ?? '').trim().toLowerCase())
}

function expandPermissions(tokens: string[]): Record<string, string[]> {
    return tokens.reduce<Record<string, string[]>>((acc, token) => {
        const [page, action] = token.split(':')
        if (!page || !action) return acc
        acc[page] ||= []
        if (!acc[page].includes(action)) acc[page].push(action)
        return acc
    }, {})
}

export function useSystemRoleManagement() {
    const useBackendApi = useBackendMode()
    const systemRoleApi = useSystemRoleApi()
    const { formattedRange } = useGlobalFilter()
    const {
        t, toast, rowSelection,
        columnVisibility,
        isFormOpen,
        isConfirmOpen,
    } = useBaseTable({ });

    const {
        sorting,
        columnFilters,
        pagination,
        serverQuery,
    } = useTableQuery({ initialSorting: [{ id: 'id', desc: false }] });
    const searchQuery = ref('')

    // --- Context States ---
    const selectedRole = ref<SystemRole | null>(null)
    const pendingRole = ref<SystemRole | null>(null)
    const confirmMode = ref<'save' | 'delete'>('save')


    // --- Mock Data ---
    const roles = ref<SystemRole[]>([])
    const mutation = useMutation()
    const auth = useAuthStore()
    const { mergedServerQuery } = useTableSearchDateQuery(
        serverQuery,
        searchQuery,
        pagination,
        formattedRange
    )
    const resource = useServerTableResource<SystemRole, ApiQueryParams>({
        resourceKey: 'roles',
        useBackendApi,
        serverQuery: mergedServerQuery,
        localData: roles,
        listFn: (query, signal) => systemRoleApi.list(query, signal),
        debounceMs: 220
    })
    const effectiveRoles = computed(() =>
        resource.rows.value
            .filter(role => !isHiddenSystemRole(role.name))
            .map(role => ({
                ...role,
                pageAccess: Array.isArray(role.pageAccess) ? role.pageAccess : flattenPermissions(role.permissions)
            }))
    )

    const selectedRoles = ref<string[]>([])

    /** Role names from the table (updates when roles are loaded or changed). */
    const roleFilterItems = computed(() => {
        const names = effectiveRoles.value
            .map((r) => String(r.name || '').trim())
            .filter(Boolean)
        return [...new Set(names)].sort((a, b) => a.localeCompare(b))
    })

    const permissionOptions = computed(() =>
        mergeRolePermissionOptions(
            effectiveRoles.value.map((r) => ({ permissions: r.permissions })),
        ),
    )

    function selectedRoleFilterLabels(): string[] {
        return selectedRoles.value
            .map((item) => {
                if (typeof item === 'string') return item.trim()
                const row = item as { label?: string; value?: string; name?: string }
                return String(row.label ?? row.value ?? row.name ?? '').trim()
            })
            .filter(Boolean)
    }

    const filteredRoles = computed(() => {
        const picked = selectedRoleFilterLabels()
        if (picked.length === 0) return effectiveRoles.value
        const allowed = new Set(picked)
        return effectiveRoles.value.filter((r) => allowed.has(String(r.name || '').trim()))
    })

    const roleSummary = computed(() => ({
        count: filteredRoles.value.length
    }))

    const confirmConfig = computed(() => {
        if (confirmMode.value === 'delete') {
            return {
                title: t('actions.delete'),
                description: `Confirm permanent removal of the ${selectedRole.value?.name} role policy?`,
                type: 'error' as const,
                submitLabel: t('actions.delete'),
                icon: 'i-lucide-shield-off'
            }
        }
        return {
            title: t('actions.edit'),
            submitLabel: t('actions.save'),
            type: 'primary' as const,
            icon: 'i-lucide-save'
        }
    })

    // --- Table Columns ---
    const columns = computed<TableColumn<SystemRole>[]>(() => [
        { accessorKey: 'id', header: t('common.rank') },
        {
            accessorKey: 'name',
            header: t('pages.roleManagement.columns.name'),
            footer: `Count: ${roleSummary.value.count}`
        },
        { accessorKey: 'pageAccess', header: t('pages.roleManagement.columns.pageAccess') },
        { id: 'action', header: t('common.actions') }
    ])

    // --- Form Fields ---
    const roleFormFields = computed<FormField[]>(() => [
        {
            key: 'name',
            label: t('pages.roleManagement.columns.name'),
            type: 'input',
            icon: 'i-lucide-shield',
            required: true,
            readonly: isHiddenSystemRole(selectedRole.value?.name)
        },
        {
            key: 'pageAccess',
            label: t('pages.roleManagement.columns.pageAccess'),
            type: 'permission-tree',
            items: permissionOptions.value.pages,
            childItems: permissionOptions.value.actions,
            required: true
        }
    ])

    // --- Actions ---
    function getDropdownActions(role: SystemRole): DropdownMenuItem[][] {
        if (isHiddenSystemRole(role.name)) return []
        const actions: DropdownMenuItem[] = []
        if (auth.hasPermission(PERMISSIONS.settingsRoleUpdate)) {
            actions.push({
                label: t('actions.edit'), icon: 'i-lucide-edit',
                onSelect: () => {
                    selectedRole.value = { ...role, pageAccess: [...(role.pageAccess || [])] }
                    isFormOpen.value = true
                }
            })
        }
        if (auth.hasPermission(PERMISSIONS.settingsRoleDelete)) {
            actions.push({
                label: t('actions.delete'),
                icon: 'i-lucide-trash',
                color: 'error' as const,
                onSelect: () => {
                    selectedRole.value = role
                    confirmMode.value = 'delete'
                    isConfirmOpen.value = true
                }
            })
        }
        return actions.length ? [actions] : []
    }

    function handleSaveRequest(data: any) {
        if (Array.isArray(data.pageAccess)) {
            const pageAccess = data.pageAccess
                .map((s: any) => String(s).trim())
                .filter(Boolean)
                .map((s: string) => s.toLowerCase())
            data.permissions = expandPermissions(pageAccess)
            delete data.pageAccess
        } else {
            data.permissions = {}
        }

        pendingRole.value = { ...data }
        confirmMode.value = 'save'
        isConfirmOpen.value = true
    }

    async function finalizeAction() {
        if (confirmMode.value === 'delete' && selectedRole.value) {
            if (isHiddenSystemRole(selectedRole.value.name)) {
                toast.add({
                    title: t('actions.delete'),
                    description: 'This system role cannot be deleted.',
                    color: 'error'
                })
                isConfirmOpen.value = false
                return
            }
            await mutation.run(() => systemRoleApi.remove(selectedRole.value!.id), 'roles')
            await resource.refresh()
            toast.add({ title: 'Role Purged', description: 'Role removed successfully.', color: 'error' })
        } else if (confirmMode.value === 'save' && pendingRole.value) {
            if (!pendingRole.value.id || pendingRole.value.id === 0) {
                await mutation.run(() => systemRoleApi.create(pendingRole.value!), 'roles')
                await resource.refresh()
                toast.add({ title: 'Role Provisioned', description: 'New role policy is active.', color: 'primary' })
            } else {
                await mutation.run(() => systemRoleApi.update(pendingRole.value!.id, pendingRole.value!), 'roles')
                await resource.refresh()
                toast.add({ title: 'Role Synchronized', description: 'Policy updates synchronized.', color: 'primary' })
            }
        }
        isConfirmOpen.value = false
        isFormOpen.value = false
        selectedRole.value = null
        pendingRole.value = null
    }

    function handleAddNew() {
        if (!auth.hasPermission(PERMISSIONS.settingsRoleCreate)) return
        selectedRole.value = null
        isFormOpen.value = true
    }

    return {
        // Table States
        rowSelection, sorting, searchQuery, columnVisibility, columnFilters, pagination,
        // Overlay States
        isFormOpen, isConfirmOpen,
        selectedRole, roles: effectiveRoles, roleFilterItems, selectedRoles, isLoading: resource.isLoading,
        totalRows: resource.totalRows,
        // Computed
        filteredRoles, confirmConfig,
        // Config
        columns, roleFormFields,
        // Actions
        getDropdownActions, handleSaveRequest, finalizeAction, handleAddNew,
    }
}