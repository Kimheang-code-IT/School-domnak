import { ref, computed, onMounted, watch } from "vue";
import { useTableSearchDateQuery } from "~/composables/table/useTableSearchDateQuery";
import { fileToDataUrl, resolveFirstUploadFile } from "~/utils/helpers/uploadFile";
import type { TableColumn, DropdownMenuItem } from "@nuxt/ui";
import { useBaseTable } from "~/composables/table/useBaseTable";
import { useTableQuery } from "~/composables/table/useTableQuery";
import type { Product, FormField, StudentEnrollmentRow } from "~/types";
import { formatCurrency } from "~/utils/format/currency";
import { useProductApi, useProductsViewApi } from "~/utils/api";
import { useTableFilterCatalog } from "~/composables/filters/useTableFilterCatalog";
import { useServerTableFilters } from "~/composables/filters/useServerTableFilters";
import type { ApiQueryParams } from "~/utils/api";
import { useServerTableResource } from "~/composables/table/useServerTable";
import { useMutation } from "~/composables/data/useMutation";
import { mapProductViewStudentRow } from "~/utils/helpers/mapProductViewStudentRow";
import { mapStudentEnrollmentRow } from "~/utils/helpers/mapStudentEnrollmentRow";
import { normalizeCambodiaProvince } from "~/utils/constants/cambodiaProvinces";
import { clampApiPageLimit } from "~/utils/constants/apiPagination";

type ProductFormPayload = Omit<Product, "image"> & {
  image?: unknown;
  imageCurrent?: string;
};
type ProductApiPayload = {
  name: string;
  categoryId: string;
  inPrice: number;
  outPrice: number;
  commission: number;
  totalStock: number;
  inStock: number;
  sold: number;
  added: number;
  damaged: number;
  status: Product["status"];
  image?: string;
  stockNote?: string;
  nameKm?: string;
  nameEn?: string;
  gender?: string;
  birthdate?: string;
  phone?: string;
  province?: string;
  totalCourse?: number;
};

export function useProduct() {
  const { locale } = useI18n();
  const useBackendApi = useBackendMode();
  const productApi = useProductApi('students');
  const productsViewApi = useProductsViewApi('students');
  const filterCatalog = useTableFilterCatalog({
    provinces: true,
    genders: true,
    classes: true,
    courses: true,
  });
  const { selections: filterSelections, queryParams: filterQueryParams } =
    useServerTableFilters(['province', 'gender', 'classId', 'courseId']);
  const { formattedRange } = useGlobalFilter();
  const {
    t,
    toast,
    rowSelection,
    columnVisibility,
    isAnalyticsOpen,
    isFormOpen,
    isDetailOpen,
    isConfirmOpen,
  } = useBaseTable({});

  const { sorting, columnFilters, pagination, serverQuery } = useTableQuery({
    initialSorting: [{ id: "studentCode", desc: false }],
  });
  const searchQuery = ref("");

  // --- Context States ---
  const selectedEntry = ref<Product | null>(null);
  const pendingEntry = ref<Product | null>(null);
  /** New image file chosen in the form; sent as data URL on save (backend persists under `/uploads`). */
  const pendingImageFile = ref<File | null>(null);
  const confirmMode = ref<"save" | "delete">("save");
  const isStockAdjustOpen = ref(false);
  const stockAdjustMode = ref<"added" | "damaged">("added");
  const stockAdjustQty = ref<number>(0);
  const stockAdjustNote = ref("");
  const stockAdjustTarget = ref<Product | null>(null);
  const isHistoryOpen = ref(false);
  const historyType = ref<"added" | "damaged">("added");
  const historyEntries = ref<any[]>([]);
  const isHistoryLoading = ref(false);
  const historyTotalRows = ref(0);
  const historyPagination = ref({ pageIndex: 0, pageSize: 50 });
  const historyDateRange = ref({
    start: undefined as any,
    end: undefined as any,
  });

  const isEnrollmentModalOpen = ref(false);
  const enrollmentStudentId = ref("");
  const enrollmentStudentName = ref("");
  const enrollmentStudentGender = ref("");
  const enrollmentStudentBirthdate = ref("");
  const enrollmentStudentImage = ref("");
  const enrollmentRows = ref<StudentEnrollmentRow[]>([]);
  const isEnrollmentLoading = ref(false);
  const enrollmentTotalRows = ref(0);
  const enrollmentPagination = ref({ pageIndex: 0, pageSize: 50 });
  const enrollmentDateRange = ref({
    start: undefined as any,
    end: undefined as any,
  });

  const entries = ref<Product[]>([]);
  const mutation = useMutation();
  const { mergedServerQuery } = useTableSearchDateQuery(
    serverQuery,
    searchQuery,
    pagination,
    formattedRange,
    filterQueryParams,
  );
  const resource = useServerTableResource<Product, ApiQueryParams>({
    resourceKey: "products-view",
    useBackendApi,
    serverQuery: mergedServerQuery,
    localData: entries,
    listFn: async (query, signal) => {
      const res = await productsViewApi.list(query, signal);
      const data = Array.isArray(res.data)
        ? res.data.map((row: Product) => mapProductViewStudentRow(row))
        : [];
      return { ...res, data };
    },
    debounceMs: 220,
  });
  const effectiveEntries = computed(() => resource.rows.value);

  // --- Computed ---
  const footerTotals = computed(() => {
    const data = effectiveEntries.value;
    const sum = (key: keyof Product) =>
      data.reduce((total, item) => total + Number(item[key] || 0), 0);

    return {
      inPrice: formatCurrency(sum("inPrice"), "USD"),
      outPrice: formatCurrency(sum("outPrice"), "USD"),
      commission: formatCurrency(sum("commission"), "USD"),
      totalStock: sum("totalStock").toLocaleString(),
      inStock: sum("inStock").toLocaleString(),
      sold: sum("sold").toLocaleString(),
      added: sum("added").toLocaleString(),
      damaged: sum("damaged").toLocaleString(),
    };
  });

  const confirmConfig = computed(() => {
    if (confirmMode.value === "delete") {
      return {
        title: t("actions.delete"),
        description: t("pages.allstudent.confirm.deleteDescription", {
          id: selectedEntry.value?.id ?? "",
        }),
        type: "error" as const,
        submitLabel: t("actions.delete"),
        icon: "i-lucide-trash-2",
      };
    }
    return {
      title: selectedEntry.value
        ? t("pages.dataEntry.formTitleEdit")
        : t("pages.dataEntry.formTitleNew"),
      description: selectedEntry.value
        ? t("pages.allstudent.confirm.saveEditDescription", {
            id: pendingEntry.value?.id ?? "",
          })
        : t("pages.allstudent.confirm.saveAddDescription", {
            name:
              [pendingEntry.value?.nameKm, pendingEntry.value?.nameEn]
                .map((s) => String(s || "").trim())
                .filter(Boolean)
                .join(" · ") ||
              String(pendingEntry.value?.name || "").trim() ||
              "",
          }),
      type: "primary" as const,
      submitLabel: selectedEntry.value
        ? t("actions.save")
        : t("actions.confirm"),
      icon: "i-lucide-check-circle",
    };
  });

  // --- Configs ---
  const columns = computed<TableColumn<Product>[]>(() => [
    { accessorKey: "studentCode", header: t("product.id") },
    { accessorKey: "image", header: t("product.image") },
    {
      accessorKey: "nameKm",
      header: t("product.nameKm"),
      footer: t("pages.allstudent.footerTotalStudents", {
        count: resource.totalRows.value,
      }),
    },
    { accessorKey: "nameEn", header: t("product.nameEn") },
    { accessorKey: "gender", header: t("product.gender") },
    { accessorKey: "birthdate", header: t("product.birthdate") },
    { accessorKey: "phone", header: t("product.phone") },
    { accessorKey: "province", header: t("product.province")},
    { accessorKey: "totalCourse", header: t("product.totalCourse")},
    { accessorKey: "createdAt", header: t("product.createdAt") },
    { id: "action", header: t("common.actions") },
  ]);

  const entryFormFields = computed<FormField[]>(() => {
    return [
    {
      key: "image",
      label: t("product.image"),
      type: "file",
      placeholder: t("pages.allstudent.placeholders.imageDrop"),
      required: false,
    },
    {
      key: "nameKm",
      label: t("product.nameKm"),
      type: "input",
      placeholder: t("pages.allstudent.placeholders.nameKm"),
      required: true,
    },
    {
      key: "nameEn",
      label: t("product.nameEn"),
      type: "input",
      placeholder: t("pages.allstudent.placeholders.nameEn"),
      required: true,
    },
    {
      key: "gender",
      label: t("product.gender"),
      type: "select",
      items: filterCatalog.genderItems.value,
      required: true,
    },
    {
      key: "birthdate",
      label: t("product.birthdate"),
      type: "date",
      placeholder: t("pages.allstudent.placeholders.birthdate"),
      required: true,
    },
    {
      key: "phone",
      label: t("product.phone"),
      type: "tel",
      inputmode: "numeric",
      autocomplete: "tel",
      maxlength: 11,
      pattern: "[0-9]*",
      placeholder: t("pages.allstudent.placeholders.phone"),
      required: true,
    },
    {
      key: "province",
      label: t("product.province"),
      type: "select",
      items: filterCatalog.provinceItems.value,
      required: true,
    },
  ];
  });

  // --- Row Actions ---
  function getDropdownActions(entry: Product): DropdownMenuItem[][] {
    return [
      [
        {
          label: t("actions.edit"),
          icon: "i-lucide-edit",
          onSelect: () => {
            selectedEntry.value = { ...entry };
            isFormOpen.value = true;
          },
        },
        {
          label: t("actions.delete"),
          icon: "i-lucide-trash",
          color: "error" as const,
          onSelect: () => {
            selectedEntry.value = entry;
            confirmMode.value = "delete";
            isConfirmOpen.value = true;
          },
        },
      ],
    ];
  }

  function resolveImageForSave(data: ProductFormPayload): string {
    const uploadedFile = resolveFirstUploadFile(data.image);
    if (uploadedFile) {
      // Local mode fallback: use object URL as previewable saved image.
      return URL.createObjectURL(uploadedFile);
    }

    const currentImage = String(data.imageCurrent || "").trim();
    const incomingImage = String(data.image || "").trim();

    // Edit mode: keep existing image if user did not select a new one.
    if (selectedEntry.value?.id) {
      if (currentImage) return currentImage;
      if (incomingImage) return incomingImage;
      return String(selectedEntry.value.image || "");
    }

    // New mode: use uploaded image if available, otherwise keep empty.
    return currentImage || incomingImage;
  }

  function handleSaveRequest(data: ProductFormPayload) {
    pendingImageFile.value = resolveFirstUploadFile(data.image);
    const { imageCurrent: _imageCurrent, ...restData } = data;
    const parsedInStock = Number(data.inStock ?? 0);
    const rawTotal = (data as Record<string, unknown>).totalStock;
    const totalStock =
      rawTotal !== undefined && rawTotal !== null && rawTotal !== ""
        ? Number(rawTotal)
        : parsedInStock;
    pendingEntry.value = {
      ...(restData as Partial<Product>),
      image: resolveImageForSave(data),
      inStock: parsedInStock,
      sold: Number(data.sold ?? 0),
      added: Number(data.added ?? 0),
      damaged: Number(data.damaged ?? 0),
      totalStock,
      inPrice: Number(data.inPrice ?? 0),
      outPrice: Number(data.outPrice ?? 0),
      commission: Number(data.commission ?? 0),
    } as Product;
    confirmMode.value = "save";
    isConfirmOpen.value = true;
  }

  function toProductApiPayload(
    data: Partial<Product> | null | undefined,
  ): ProductApiPayload {
    const fromNames = [
      String(data?.nameKm || "").trim(),
      String(data?.nameEn || "").trim(),
    ]
      .filter(Boolean)
      .join(" · ");
    const legacyName = String(data?.name || "").trim();
    const displayName = legacyName || fromNames || "";

    const numCourse = data?.totalCourse;
    const totalCourseParsed =
      numCourse !== undefined &&
      numCourse !== null &&
      String(numCourse) !== ""
        ? Number(numCourse)
        : undefined;

    const base: ProductApiPayload = {
      name: displayName || "Student",
      categoryId: String(data?.categoryId ?? "").trim(),
      inPrice: Number(data?.inPrice ?? 0),
      outPrice: Number(data?.outPrice ?? 0),
      commission: Number(data?.commission ?? 0),
      totalStock: Number(data?.totalStock ?? 0),
      inStock: Number(data?.inStock ?? 0),
      sold: Number(data?.sold ?? 0),
      added: Number(data?.added ?? 0),
      damaged: Number(data?.damaged ?? 0),
      status: (String(data?.status || "active").trim() ||
        "active") as Product["status"],
      stockNote: (data as Record<string, unknown>)?.stockNote
        ? String((data as Record<string, unknown>).stockNote)
        : undefined,
    };

    const nameKm = String(data?.nameKm || "").trim();
    const nameEn = String(data?.nameEn || "").trim();
    if (nameKm) base.nameKm = nameKm;
    if (nameEn) base.nameEn = nameEn;
    const gender = String(data?.gender || "").trim();
    if (gender) base.gender = gender;
    const birthdate = String(data?.birthdate || "").trim();
    if (birthdate) base.birthdate = birthdate;
    const phone = String(data?.phone || "").trim();
    if (phone) base.phone = phone;
    const province = normalizeCambodiaProvince(String(data?.province || ""));
    if (province) base.province = province;
    if (totalCourseParsed !== undefined && Number.isFinite(totalCourseParsed))
      base.totalCourse = totalCourseParsed;

    return base;
  }

  async function toProductApiPayloadForSave(
    data: Partial<Product> | null | undefined,
    newImageFile: File | null,
  ): Promise<ProductApiPayload> {
    const base = toProductApiPayload(data);
    if (newImageFile) {
      base.image = await fileToDataUrl(newImageFile);
    }
    return base;
  }

  async function finalizeAction() {
    if (confirmMode.value === "delete" && selectedEntry.value) {
      await mutation.run(
        () => productApi.remove(selectedEntry.value!.id),
        "products-view",
      );
      await resource.refresh();
      toast.add({
        title: t("pages.allstudent.toast.deleted"),
        description: t("pages.allstudent.toast.deletedDescription", {
          id: selectedEntry.value.id,
        }),
        color: "error",
      });
    } else if (confirmMode.value === "save" && pendingEntry.value) {
      const payload = await toProductApiPayloadForSave(
        pendingEntry.value,
        pendingImageFile.value,
      );
      pendingImageFile.value = null;
      if (!pendingEntry.value.id || pendingEntry.value.id === 0) {
        await mutation.run(() => productApi.create(payload), "products-view");
        await resource.refresh();
        toast.add({
          title: t("pages.allstudent.toast.added"),
          description: t("pages.allstudent.toast.addedDescription"),
          color: "primary",
        });
      } else {
        await mutation.run(
          () => productApi.update(pendingEntry.value!.id, payload),
          "products-view",
        );
        await resource.refresh();
        toast.add({
          title: t("pages.allstudent.toast.updated"),
          description: t("pages.allstudent.toast.updatedDescription", {
            id: pendingEntry.value.id,
          }),
          color: "primary",
        });
      }
    }
    isConfirmOpen.value = false;
    isFormOpen.value = false;
    selectedEntry.value = null;
    pendingEntry.value = null;
  }

  function handleAddNew() {
    selectedEntry.value = null;
    pendingImageFile.value = null;
    isFormOpen.value = true;
  }

  function openStockAdjustDialog(entry: Product, mode: "added" | "damaged") {
    stockAdjustTarget.value = entry;
    stockAdjustMode.value = mode;
    stockAdjustQty.value = 0;
    isStockAdjustOpen.value = true;
  }

  async function applyStockAdjust() {
    const target = stockAdjustTarget.value;
    const qty = Number(stockAdjustQty.value);
    if (!target || !Number.isFinite(qty) || qty <= 0) return;

    const deltaAdded = stockAdjustMode.value === "added" ? qty : 0;
    const deltaDamaged = stockAdjustMode.value === "damaged" ? qty : 0;

    const nextAdded = Number(target.added || 0) + deltaAdded;
    const nextDamaged = Number(target.damaged || 0) + deltaDamaged;
    const nextInStock = Number(target.inStock || 0) + deltaAdded - deltaDamaged;
    const nextTotalStock = Number(target.totalStock || 0) + deltaAdded;

    const payload = toProductApiPayload({
      ...target,
      added: nextAdded,
      damaged: nextDamaged,
      inStock: nextInStock,
      totalStock: nextTotalStock,
      stockNote: stockAdjustNote.value,
    });

    await productApi.update(target.id, payload);
    await resource.refresh();

    toast.add({
      title:
        stockAdjustMode.value === "added"
          ? t("pages.allstudent.toast.stockAdded")
          : t("pages.allstudent.toast.stockDamaged"),
      description: t("pages.allstudent.toast.stockAdjustedDescription", {
        id: target.id,
      }),
      color: stockAdjustMode.value === "added" ? "primary" : "warning",
    });

    isStockAdjustOpen.value = false;
    stockAdjustTarget.value = null;
    stockAdjustQty.value = 0;
    stockAdjustNote.value = "";
  }

  async function openHistory(entry: Product, type: "added" | "damaged") {
    selectedEntry.value = entry;
    historyType.value = type;
    historyPagination.value.pageIndex = 0;
    isHistoryOpen.value = true;
    await loadHistory();
  }

  async function loadHistory() {
    if (!selectedEntry.value) return;
    isHistoryLoading.value = true;
    try {
      const toISO = (val: any) => {
        if (!val) return undefined;
        const d = new Date(val);
        return isNaN(d.getTime()) ? undefined : d.toISOString();
      };

      const params: ApiQueryParams = {
        page: historyPagination.value.pageIndex + 1,
        limit: clampApiPageLimit(historyPagination.value.pageSize),
        dateFrom: toISO(historyDateRange.value.start),
        dateTo: toISO(historyDateRange.value.end),
      };
      const res =
        historyType.value === "added"
          ? await productApi.listStockAdditions(selectedEntry.value.id, params)
          : await productApi.listDamages(selectedEntry.value.id, params);

      if (res) {
        historyEntries.value = res.data || [];
        historyTotalRows.value = res.total || 0;
      }
    } catch (err) {
      console.error("Failed to load history:", err);
      toast.add({
        title: t("pages.allstudent.toast.historyLoadFailed"),
        color: "error",
      });
    } finally {
      isHistoryLoading.value = false;
    }
  }

  watch(
    [historyPagination, historyDateRange],
    () => {
      if (isHistoryOpen.value) loadHistory();
    },
    { deep: true },
  );

  function openEnrollmentModal(entry: Product) {
    enrollmentStudentId.value = String(entry.id ?? "").trim();
    enrollmentStudentName.value = [entry.nameKm, entry.nameEn]
      .map((s) => String(s || "").trim())
      .filter(Boolean)
      .join(" · ") || String(entry.name || "").trim();
    enrollmentStudentGender.value = String(entry.gender || "").trim();
    enrollmentStudentBirthdate.value = String(entry.birthdate || "").trim();
    enrollmentStudentImage.value = String(entry.image || "").trim();
    enrollmentPagination.value = {
      ...enrollmentPagination.value,
      pageIndex: 0,
    };
    isEnrollmentModalOpen.value = true;
  }

  async function loadStudentEnrollments() {
    const id = enrollmentStudentId.value.trim();
    if (!id || !isEnrollmentModalOpen.value) return;
    isEnrollmentLoading.value = true;
    try {
      const toISO = (val: any) => {
        if (!val) return undefined;
        const d = new Date(val);
        return isNaN(d.getTime()) ? undefined : d.toISOString();
      };
      const params: ApiQueryParams = {
        page: enrollmentPagination.value.pageIndex + 1,
        limit: clampApiPageLimit(enrollmentPagination.value.pageSize),
        dateFrom: toISO(enrollmentDateRange.value.start),
        dateTo: toISO(enrollmentDateRange.value.end),
      };
      const res = await productApi.listStudentEnrollments(id, params);
      const rawList = Array.isArray(res?.data) ? res.data : [];
      enrollmentRows.value = rawList.map((r: unknown) =>
        mapStudentEnrollmentRow(r as unknown as Record<string, unknown>),
      );
      enrollmentTotalRows.value = res?.total ?? enrollmentRows.value.length;
    } catch (err) {
      console.error("Failed to load student enrollments:", err);
      enrollmentRows.value = [];
      enrollmentTotalRows.value = 0;
      toast.add({
        title: t("pages.allstudent.toast.enrollmentLoadFailed"),
        color: "error",
      });
    } finally {
      isEnrollmentLoading.value = false;
    }
  }

  watch(
    [
      isEnrollmentModalOpen,
      enrollmentStudentId,
      enrollmentPagination,
      enrollmentDateRange,
    ],
    () => {
      if (isEnrollmentModalOpen.value && enrollmentStudentId.value.trim())
        void loadStudentEnrollments();
    },
    { deep: true },
  );

  const isEnrollmentDeleteConfirmOpen = ref(false);
  const pendingEnrollmentDeleteRow = ref<StudentEnrollmentRow | null>(null);
  const enrollmentDeleteSubmitting = ref(false);

  const enrollmentDeleteConfirmConfig = computed(() => ({
    title: t("pages.allstudent.enrollmentModal.confirm.deleteTitle"),
    description: t("pages.allstudent.enrollmentModal.confirm.deleteDescription", {
      course: pendingEnrollmentDeleteRow.value?.courseName ?? "—",
    }),
    type: "error" as const,
    submitLabel: t("actions.delete"),
    icon: "i-lucide-trash-2" as const,
  }));

  function dismissEnrollmentDeleteConfirm() {
    pendingEnrollmentDeleteRow.value = null;
  }

  function requestDeleteEnrollment(row: StudentEnrollmentRow) {
    pendingEnrollmentDeleteRow.value = row;
    isEnrollmentDeleteConfirmOpen.value = true;
  }

  async function confirmDeleteEnrollment() {
    const row = pendingEnrollmentDeleteRow.value;
    const sid = enrollmentStudentId.value.trim();
    if (!row || !sid) {
      isEnrollmentDeleteConfirmOpen.value = false;
      pendingEnrollmentDeleteRow.value = null;
      return;
    }
    const eid = String(row.id ?? "").trim();
    if (!eid) {
      toast.add({
        title: t("common.error"),
        color: "error",
      });
      isEnrollmentDeleteConfirmOpen.value = false;
      pendingEnrollmentDeleteRow.value = null;
      return;
    }
    enrollmentDeleteSubmitting.value = true;
    try {
      await productApi.deleteStudentEnrollment(sid, eid);
      toast.add({
        title: t("pages.allstudent.enrollmentModal.toast.enrollmentDeleted"),
        color: "primary",
      });
      await loadStudentEnrollments();
      await resource.refresh();
    } catch (err: unknown) {
      const e = err as { data?: { message?: string }; message?: string };
      toast.add({
        title: t("pages.allstudent.enrollmentModal.toast.enrollmentDeleteFailed"),
        description: e?.data?.message || e?.message || "",
        color: "error",
      });
    } finally {
      enrollmentDeleteSubmitting.value = false;
      isEnrollmentDeleteConfirmOpen.value = false;
      pendingEnrollmentDeleteRow.value = null;
    }
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
    isAnalyticsOpen,
    isFormOpen,
    isConfirmOpen,
    isStockAdjustOpen,
    selectedEntry,
    filterCatalog,
    filterSelections,
    entries: effectiveEntries,
    totalRows: resource.totalRows,
    isLoading: resource.isLoading,
    // Computed/Configs
    confirmConfig,
    columns,
    entryFormFields,
    // Actions
    getDropdownActions,
    handleSaveRequest,
    finalizeAction,
    handleAddNew,
    stockAdjustMode,
    stockAdjustQty,
    stockAdjustNote,
    stockAdjustTarget,
    openStockAdjustDialog,
    applyStockAdjust,
    // History
    isHistoryOpen,
    historyType,
    historyEntries,
    isHistoryLoading,
    historyTotalRows,
    historyPagination,
    historyDateRange,
    openHistory,
    loadHistory,
    // Enrollments (courses / classes for one student)
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
  };
}
