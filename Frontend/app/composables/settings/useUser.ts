import { ref, computed, watch, onMounted } from "vue";
import { useTableSearchDateQuery } from "~/composables/table/useTableSearchDateQuery";
import type { TableColumn, DropdownMenuItem } from "@nuxt/ui";
import { useBaseTable } from "~/composables/table/useBaseTable";
import { useTableQuery } from "~/composables/table/useTableQuery";
import type { SystemUser, FormField } from "~/types";
import { useSystemUserApi } from '~/utils/api'
import { useSystemRoleApi } from '~/utils/api'
import type { ApiQueryParams } from '~/utils/api'
import { useServerTableResource } from "~/composables/table/useServerTable";
import { useMutation } from "~/composables/data/useMutation";
import { PERMISSIONS } from "~/utils/auth/permissions";

/** Users with this role cannot be deleted from User Management (edit only). */
const USER_NON_DELETABLE_ROLE_NAMES = new Set(["admin"]);

function isNonDeletableUserRole(role?: string): boolean {
  return USER_NON_DELETABLE_ROLE_NAMES.has(String(role ?? "").trim().toLowerCase());
}

export function useSystemUserManagement() {
  const auth = useAuthStore()
  const useBackendApi = useBackendMode()
  const systemUserApi = useSystemUserApi()
  const systemRoleApi = useSystemRoleApi()
  const { formattedRange } = useGlobalFilter()
  const {
    t, toast, rowSelection, columnVisibility,
    isFormOpen, isConfirmOpen
  } = useBaseTable({
    initialVisibility: { password: false }
  });

  const {
    sorting, columnFilters, pagination, serverQuery
  } = useTableQuery({ initialSorting: [{ id: "id", desc: false }] });
  const searchQuery = ref("")

  // --- Context States ---
  const selectedUser = ref<SystemUser | null>(null);
  const pendingUser = ref<SystemUser | null>(null);
  const confirmMode = ref<"save" | "delete">("save");

  // --- Mock Data ---
  const users = ref<SystemUser[]>([]);
  const mutation = useMutation()
  const { mergedServerQuery } = useTableSearchDateQuery(
    serverQuery,
    searchQuery,
    pagination,
    formattedRange
  )
  const resource = useServerTableResource<SystemUser, ApiQueryParams>({
    resourceKey: 'users',
    useBackendApi,
    serverQuery: mergedServerQuery,
    localData: users,
    listFn: (query, signal) => systemUserApi.list(query, signal),
    debounceMs: 220
  })
  const effectiveUsers = computed(() => resource.rows.value)

  // --- Filter States ---
  const roleRecords = ref<Array<{ id: number; name: string }>>([])
  const roleItems = computed(() =>
    roleRecords.value.map((r) => r.name).filter(Boolean)
  )
  const selectedRoles = ref<string[]>([]);

  function toApiUserPayload(user: SystemUser) {
    const roleId = roleRecords.value.find((r) => r.name === user.role)?.id
    const payload: Record<string, unknown> = {
      name: user.name,
      email: user.email,
      roleId,
    }
    if (user.password?.trim()) {
      payload.password = user.password.trim()
    }
    return payload
  }

  async function loadRoleItems() {
    try {
      const res = await systemRoleApi.list({ page: 1, limit: 200, sortBy: 'name', sortOrder: 'asc' })
      roleRecords.value = (res.data || [])
        .map((r: { id?: number; name?: string }) => ({
          id: Number(r?.id),
          name: String(r?.name || '').trim(),
        }))
        .filter((r) => r.id > 0 && r.name)
    } catch {
      roleRecords.value = []
    }
  }
  onMounted(loadRoleItems)

  // --- Computed Logic ---
  const filteredUsers = computed(() => {
    if (selectedRoles.value.length === 0) return effectiveUsers.value;
    return effectiveUsers.value.filter((u) => selectedRoles.value.includes(u.role));
  });

  const userSummary = computed(() => ({
    count: filteredUsers.value.length
  }));

  const confirmConfig = computed(() => {
    if (confirmMode.value === "delete") {
      return {
        title: t("actions.delete"),
        description: `Confirm permanent removal of account for ${selectedUser.value?.name}.`,
        type: "error" as const,
        submitLabel: t("actions.delete"),
        icon: "i-lucide-user-minus",
      };
    }
    return {
      title: selectedUser.value ? t("actions.edit") : t("pages.userManagement.addBtn"),
      submitLabel: selectedUser.value
        ? t("actions.save")
        : t("actions.confirm"),
      type: "primary" as const,
      icon: "i-lucide-user-plus",
    };
  });

  // --- Table Columns (Translated & Reactive) ---
  const columns = computed<TableColumn<SystemUser>[]>(() => [
    { accessorKey: "id", header: t("common.rank") },
    {
      accessorKey: "name",
      header: t("pages.userManagement.columns.name"),
      footer: `Count: ${userSummary.value.count}`
    },
    { accessorKey: "role", header: t("pages.userManagement.columns.role") },
    { accessorKey: "email", header: t("pages.userManagement.columns.email") },
    {
      accessorKey: "password",
      header: t("pages.userManagement.columns.password"),
    },
    {
      accessorKey: "lastLogin",
      header: t("pages.userManagement.columns.lastLogin"),
    },
    { id: "action", header: t("common.actions") },
  ]);

  // --- Form Fields ---
  const userFormFields = computed<FormField[]>(() => [
    {
      key: "name",
      label: t("pages.userManagement.columns.name"),
      type: "input",
      icon: "i-lucide-user",
      required: true,
    },
    {
      key: "role",
      label: t("pages.userManagement.columns.role"),
      type: "select",
      items: roleItems.value as string[],
      icon: "i-lucide-shield-half",
      required: true,
    },
    {
      key: "email",
      label: t("pages.userManagement.columns.email"),
      type: "input",
      icon: "i-lucide-mail",
      required: true,
    },
    {
      key: "password",
      label: t("pages.userManagement.columns.password"),
      type: "password",
      icon: "i-lucide-lock",
      placeholder: "Min 8 chars...",
    }
  ]);

  // --- Actions ---
  function getDropdownActions(user: SystemUser): DropdownMenuItem[][] {
    const actions: DropdownMenuItem[] = []
    if (auth.hasPermission(PERMISSIONS.settingsUserUpdate)) {
      actions.push({
        label: t("actions.edit"),
        icon: "i-lucide-edit",
        onSelect: () => {
          selectedUser.value = { ...user };
          isFormOpen.value = true;
        },
      })
    }
    if (auth.hasPermission(PERMISSIONS.settingsUserDelete) && !isNonDeletableUserRole(user.role)) {
      actions.push({
        label: t("actions.delete"),
        icon: "i-lucide-trash",
        color: "error" as const,
        onSelect: () => {
          selectedUser.value = user;
          confirmMode.value = "delete";
          isConfirmOpen.value = true;
        },
      })
    }
    return actions.length ? [actions] : []
  }

  function handleSaveRequest(data: SystemUser) {
    pendingUser.value = { ...data };
    confirmMode.value = "save";
    isConfirmOpen.value = true;
  }

  async function finalizeAction() {
    if (confirmMode.value === "delete" && selectedUser.value) {
      if (isNonDeletableUserRole(selectedUser.value.role)) {
        toast.add({
          title: t("actions.delete"),
          description: "Users with the Admin role cannot be deleted.",
          color: "error",
        });
        isConfirmOpen.value = false;
        return;
      }
      await mutation.run(() => systemUserApi.remove(selectedUser.value!.id), 'users')
      await resource.refresh()
      toast.add({
        title: "Account Revoked",
        description: `Access revoked for ${selectedUser.value.name}.`,
        color: "error",
      });
    } else if (confirmMode.value === "save" && pendingUser.value) {
      const apiPayload = toApiUserPayload(pendingUser.value)
      if (!apiPayload.roleId) {
        toast.add({
          title: t("pages.userManagement.columns.role"),
          description: "Please select a valid role.",
          color: "error",
        });
        isConfirmOpen.value = false;
        return;
      }
      if (pendingUser.value.id === 0 || !pendingUser.value.id) {
        await mutation.run(() => systemUserApi.create(apiPayload as Partial<SystemUser>), 'users')
        await resource.refresh()
        toast.add({
          title: "Account Provisioned",
          description: "System credentials delivered.",
          color: "primary",
        });
      } else {
        await mutation.run(() => systemUserApi.update(pendingUser.value!.id, apiPayload as Partial<SystemUser>), 'users')
        await resource.refresh()
        toast.add({
          title: "Account Synchronized",
          description: "Profile changes applied successfully.",
          color: "primary",
        });
      }
    }
    isConfirmOpen.value = false;
    isFormOpen.value = false;
    selectedUser.value = null;
    pendingUser.value = null;
  }

  function handleAddNew() {
    if (!auth.hasPermission(PERMISSIONS.settingsUserCreate)) return
    selectedUser.value = null;
    isFormOpen.value = true;
  }

  return {
    // Table States
    rowSelection,
    sorting,
    searchQuery,
    columnVisibility,
    columnFilters,
    pagination,
    // Overlay States
    isFormOpen,
    isConfirmOpen,
    selectedUser,
    users: effectiveUsers,
    totalRows: resource.totalRows,
    isLoading: resource.isLoading,
    roleItems,
    selectedRoles,
    // Computed
    filteredUsers,
    confirmConfig,
    // Config
    columns,
    userFormFields,
    // Actions
    getDropdownActions,
    handleSaveRequest,
    finalizeAction,
    handleAddNew,
  };
}

