import { ref, computed, watch } from "vue";
import type { TableColumn, DropdownMenuItem } from "@nuxt/ui";
import { useBaseTable } from "~/composables/table/useBaseTable";
import { useTableQuery } from "~/composables/table/useTableQuery";
import type { Category } from "~/types";
import { useCategoryApi } from '~/utils/api'
import type { ApiQueryParams } from '~/utils/api'
import { useServerTableResource } from "~/composables/table/useServerTable";

export function useTotalRevenue() {
  const useBackendApi = useBackendMode();
  const categoryApi = useCategoryApi();
  const { t, toast, rowSelection, columnVisibility, isConfirmOpen } =
    useBaseTable({});

  const { sorting, columnFilters, pagination, serverQuery } = useTableQuery({
    initialSorting: [{ id: "id", desc: false }],
  });
  const searchQuery = ref("");

  // --- Data ---
  const entries = ref<Category[]>([]);

  // --- Add Form State ---
  const newName = ref("");
  const newDescription = ref("");

  // --- Confirm State ---
  const editingId = ref<string | null>(null);
  const pendingDeleteId = ref<string | null>(null);
  const confirmMode = ref<"add" | "edit" | "delete">("add");
  const pendingPayload = ref<{ id?: string; name: string; description: string } | null>(null);
  const selectedClassifications = ref<string[]>([]);

  // --- Computed ---
  const filteredEntries = computed(() => resource.rows.value);
  const mergedServerQuery = computed(() => ({
    ...serverQuery.value,
    search: searchQuery.value.trim() || undefined,
  }));
  watch(searchQuery, () => {
    pagination.value.pageIndex = 0;
  });
  const resource = useServerTableResource<Category, ApiQueryParams>({
    resourceKey: 'categories',
    useBackendApi,
    serverQuery: mergedServerQuery,
    localData: entries,
    listFn: (query, signal) => categoryApi.list(query, signal),
    debounceMs: 250
  })

  /** Sum of linked-item counts (`Category.total`) for rows on the current table page only. */
  const categoryTotalsSumOnPage = computed(() =>
    (resource.rows.value ?? []).reduce(
      (acc, row) => acc + Number(row.total ?? 0),
      0,
    ),
  )

  // --- Columns ---
  const columns = computed<TableColumn<Category>[]>(() => [
    { accessorKey: "id", header: t("category.id") },
    {
      accessorKey: "name",
      header: t("category.name"),
      footer: t("pages.category.footer.categoryCount", {
        count: resource.totalRows.value,
      }),
    },
    { accessorKey: "description", header: t("category.description") },
    {
      accessorKey: "total",
      header: t("category.total"),
      footer: `${categoryTotalsSumOnPage.value} ${t("common.items")}`,
    },
    { id: "action", header: t("common.actions") },
  ]);

  // --- Row Actions ---
  function getDropdownActions(entry: Category): DropdownMenuItem[][] {
    return [
      [
        {
          label: t("actions.edit"),
          icon: "i-lucide-edit",
          onSelect: () => {
            newName.value = entry.name;
            newDescription.value = entry.description;
            editingId.value = entry.id;
          },
        },
        {
          label: t("actions.delete"),
          icon: "i-lucide-trash",
          color: "error" as const,
          onSelect: () => {
            pendingDeleteId.value = entry.id;
            confirmMode.value = "delete";
            isConfirmOpen.value = true;
          },
        },
      ],
    ];
  }

  // --- Request Intent (open confirm first) ---
  async function handleAdd() {
    const name = newName.value.trim();
    if (!name) return;

    pendingPayload.value = {
      id: editingId.value ?? undefined,
      name,
      description: newDescription.value.trim(),
    };
    confirmMode.value = editingId.value !== null ? "edit" : "add";
    isConfirmOpen.value = true;
  }

  function resetForm() {
    newName.value = "";
    newDescription.value = "";
    editingId.value = null;
    pendingPayload.value = null;
  }

  async function createCategory(payload: { name: string; description: string }) {
    await categoryApi.create(payload);
    toast.add({ title: t("pages.category.toast.added"), color: "primary" });
  }

  async function updateCategory(id: string, payload: { name: string; description: string }) {
    await categoryApi.update(id, payload);
    toast.add({ title: t("pages.category.toast.updated"), color: "primary" });
  }

  async function deleteCategory(id: string) {
    await categoryApi.remove(id);
    toast.add({ title: t("pages.category.toast.deleted"), color: "error" });
  }

  // --- Finalize Confirmed Action (API-first) ---
  async function finalizeAction() {
    try {
      if (confirmMode.value === "delete" && pendingDeleteId.value !== null) {
        await deleteCategory(pendingDeleteId.value);
        pendingDeleteId.value = null;
      } else if (confirmMode.value === "edit" && pendingPayload.value?.id) {
        await updateCategory(pendingPayload.value.id, {
          name: pendingPayload.value.name,
          description: pendingPayload.value.description,
        });
        resetForm();
      } else if (confirmMode.value === "add" && pendingPayload.value) {
        await createCategory({
          name: pendingPayload.value.name,
          description: pendingPayload.value.description,
        });
        resetForm();
      }

      await resource.refresh();
    } catch (err: any) {
      console.error('Action failed:', err)
      const msg = err.data?.message || err.message || t("pages.category.error.tryAgain");
      toast.add({
        title: t("pages.category.error.requestFailed"),
        description: msg,
        color: "error",
      });
    }

    isConfirmOpen.value = false;
  }

  const confirmConfig = computed(() => {
    if (confirmMode.value === "delete") {
      return {
        title: t("actions.delete"),
        description: t("pages.category.confirm.deleteDescription"),
        type: "error" as const,
        submitLabel: t("actions.delete"),
      };
    }
    if (confirmMode.value === "edit") {
      return {
        title: t("actions.save"),
        description: t("pages.category.confirm.editNamed", {
          name: pendingPayload.value?.name || "",
        }),
        type: "primary" as const,
        submitLabel: t("actions.save"),
      };
    }
    return {
      title: t("actions.add"),
      description: t("pages.category.confirm.addNamed", {
        name: pendingPayload.value?.name || "",
      }),
      type: "primary" as const,
      submitLabel: t("actions.confirm"),
    };
  });

  return {
    // Table
    rowSelection,
    sorting,
    searchQuery,
    columnVisibility,
    columnFilters,
    pagination,
    selectedClassifications,
    // Data
    entries,
    isLoading: resource.isLoading,
    totalRows: resource.totalRows,
    filteredEntries,
    columns,
    // Add Form
    newName,
    newDescription,
    handleAdd,
    // Delete
    isConfirmOpen,
    confirmConfig,
    finalizeAction,
    // Row actions
    getDropdownActions,
  };
}
