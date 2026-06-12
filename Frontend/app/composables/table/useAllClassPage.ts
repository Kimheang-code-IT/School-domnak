import { computed, onMounted, ref, watch } from 'vue'
import type { StepperItem } from '~/types/nuxt-ui'
import type { Course, FormField, Product, SystemUser } from '~/types'
import { usePosCheckout } from '~/composables/classes/useCheckout'
import { usePosProducts } from '~/composables/classes/useAllClass'
import { useBaseTable } from '~/composables/table/useBaseTable'
import {
  useCategoryApi,
  useCoursesApi,
  useProductApi,
  usePosApi,
  useSystemUserApi
} from '~/utils/api'
import { useMutation } from '~/composables/data/useMutation'
import { extractApiArray } from '~/utils/helpers/extractApiArray'
import { fileToDataUrl, resolveFirstUploadFile } from '~/utils/helpers/uploadFile'
import { parseDurationMonths } from '~/utils/format/duration'
import { clampApiPageLimit } from '~/utils/constants/apiPagination'

export function useAllClassPage() {
  const { t, toast, isFormOpen, isConfirmOpen } = useBaseTable({})

  /** Enrollment wizard: 0 select class → 1 student info → 2 invoice */
  const currentStep = ref(0)

  const enrollmentInvoiceNo = ref('')

  const enrollmentStepItems = computed<StepperItem[]>(() => [
    { title: t('pages.allclass.steps.selectClass'), icon: 'i-lucide-layout-grid' },
    { title: t('pages.allclass.steps.studentInfo'), icon: 'i-lucide-user' },
    { title: t('pages.allclass.steps.invoice'), icon: 'i-lucide-file-text' }
  ])

  const productsState = usePosProducts()

  /** `AppStudentForm` models (same shape as POS customer form). */
  const customerType = ref('Customer')
  const customerName = ref('')
  const nameKm = ref('')
  const nameEn = ref('')
  const gender = ref('')
  const birthdate = ref('')
  const province = ref('')
  const studentImage = ref<string | undefined>(undefined)
  const selectedStudentId = ref<number | undefined>(undefined)
  const customerPhone = ref('')
  const customerAddress = ref('')
  const deliveryType = ref('VET')
  const deliveryPrice = ref(2)
  const deliveryDate = ref('')
  const paymentMethod = ref('cash')
  const deliveryStatus = ref('pending')
  const source = ref('other')
  const sellerId = ref<number | undefined>(undefined)

  const paymentNote = ref('')
  const editingClass = ref<Product | null>(null)
  const isDeleteClassConfirmOpen = ref(false)
  const deleteClassSubmitting = ref(false)
  const pendingDeleteClass = ref<Product | null>(null)

  watch([nameKm, nameEn, customerType], () => {
    if (customerType.value === 'walkIn') return
    const km = nameKm.value.trim()
    const en = nameEn.value.trim()
    customerName.value = [km, en].filter(Boolean).join(' · ')
  })

  /** Right panel (`AppPayment`) — mirrors selected class as a one-line cart. */
  type CartLine = { product: Product; qty: number }
  const enrollmentCartLines = ref<CartLine[]>([])
  const enrollmentDiscountMode = ref<'percent' | 'usd'>('percent')
  const enrollmentDiscountPercent = ref(0)
  const enrollmentDiscountFixed = ref(0)

  const enrollmentItemCount = computed(() =>
    enrollmentCartLines.value.reduce((sum, line) => sum + line.qty, 0)
  )

  const enrollmentSubtotal = computed(() =>
    enrollmentCartLines.value.reduce(
      (sum, line) => sum + Number(line.product.outPrice || 0) * line.qty,
      0
    )
  )

  const enrollmentDiscountAmount = computed(() => {
    const sub = enrollmentSubtotal.value
    if (enrollmentDiscountMode.value === 'usd') {
      return Math.min(sub, Math.max(0, Number(enrollmentDiscountFixed.value || 0)))
    }
    const pct = Math.min(100, Math.max(0, Number(enrollmentDiscountPercent.value || 0)))
    return sub * (pct / 100)
  })

  /** Checkout API uses percent; derive from USD amount when needed. */
  const enrollmentCheckoutDiscountPercent = computed(() => {
    const sub = enrollmentSubtotal.value
    if (sub <= 0) return 0
    if (enrollmentDiscountMode.value === 'usd') {
      const amt = enrollmentDiscountAmount.value
      return Math.min(100, (amt / sub) * 100)
    }
    return Math.min(100, Math.max(0, Number(enrollmentDiscountPercent.value || 0)))
  })

  const enrollmentTotal = computed(() =>
    Math.max(0, enrollmentSubtotal.value - enrollmentDiscountAmount.value)
  )

  function clearEnrollmentCart() {
    enrollmentCartLines.value = []
  }

  /** One product id checked on the enrollment grid maps to presence in cart. */
  function isProductInEnrollmentCart(productId: number) {
    return enrollmentCartLines.value.some((line) => line.product.id === productId)
  }

  function removeEnrollmentItem(productId: number) {
    enrollmentCartLines.value = enrollmentCartLines.value.filter(
      (line) => line.product.id !== productId
    )
  }

  const categoryApi = useCategoryApi()
  const coursesApi = useCoursesApi()
  const userApi = useSystemUserApi()
  const productApi = useProductApi('classes')
  const posApi = usePosApi()
  const checkoutState = usePosCheckout()
  const mutation = useMutation()

  const isClassStudentsModalOpen = ref(false)
  const classStudentsProduct = ref<Product | null>(null)
  const classStudentsRows = ref<Record<string, unknown>[]>([])
  const classStudentsLoading = ref(false)
  const classStudentsTotal = ref(0)
  const classStudentsPagination = ref({ pageIndex: 0, pageSize: 50 })
  const classStudentsDateRange = ref<{ start?: unknown; end?: unknown }>({
    start: undefined,
    end: undefined
  })

  async function loadClassStudents() {
    const product = classStudentsProduct.value
    if (!product) {
      classStudentsRows.value = []
      classStudentsTotal.value = 0
      return
    }
    classStudentsLoading.value = true
    try {
      const toISO = (val: unknown) => {
        if (!val) return undefined
        const d = new Date(val as Date | string | number)
        return Number.isNaN(d.getTime()) ? undefined : d.toISOString()
      }

      const res = await productApi.listEnrollments(product.id, {
        page: classStudentsPagination.value.pageIndex + 1,
        limit: clampApiPageLimit(classStudentsPagination.value.pageSize),
        dateFrom: toISO(classStudentsDateRange.value.start),
        dateTo: toISO(classStudentsDateRange.value.end),
      })
      const raw = res as { data?: unknown[]; total?: number }
      const list = raw?.data
      classStudentsRows.value = Array.isArray(list)
        ? (list as Record<string, unknown>[])
        : []
      classStudentsTotal.value = Number(raw?.total ?? classStudentsRows.value.length)
    } catch {
      classStudentsRows.value = []
      classStudentsTotal.value = 0
    } finally {
      classStudentsLoading.value = false
    }
  }

  function openClassStudentsModal(product: Product) {
    classStudentsProduct.value = product
    classStudentsPagination.value = { ...classStudentsPagination.value, pageIndex: 0 }
    isClassStudentsModalOpen.value = true
  }

  watch(isClassStudentsModalOpen, (open) => {
    if (!open) {
      classStudentsProduct.value = null
      classStudentsRows.value = []
      classStudentsTotal.value = 0
    }
  })

  /** Reset pager when modal date filters change (runs before reload watch). */
  watch(
    () => [classStudentsDateRange.value.start, classStudentsDateRange.value.end],
    () => {
      if (!isClassStudentsModalOpen.value || !classStudentsProduct.value) return
      classStudentsPagination.value = {
        ...classStudentsPagination.value,
        pageIndex: 0,
      }
    },
    { deep: true },
  )

  watch(
    [
      isClassStudentsModalOpen,
      () => classStudentsProduct.value?.id,
      classStudentsPagination,
      classStudentsDateRange,
    ],
    ([open, productId]) => {
      if (!open || productId == null) return
      void loadClassStudents()
    },
    { deep: true },
  )

  function pickEnrollmentRowStr(row: Record<string, unknown>, keys: string[]): string {
    for (const k of keys) {
      const v = row[k]
      if (v != null && String(v).trim() !== '') return String(v).trim()
    }
    return ''
  }

  function normalizeEnrollmentGender(raw: unknown): string {
    const v = String(raw ?? '')
      .trim()
      .toLowerCase()
    if (['male', 'm', 'ប្រុស'].includes(v)) return 'male'
    if (['female', 'f', 'ស្រី'].includes(v)) return 'female'
    return v
  }

  function resolveProductForEnrollmentCart(product: Product): Product {
    const fromList = productsState.filteredProducts.value.find((p) => p.id === product.id)
    return fromList ?? product
  }

  const isCancelEnrollmentConfirmOpen = ref(false)
  const pendingCancelEnrollmentRow = ref<Record<string, unknown> | null>(null)
  const cancelEnrollmentConfirmSubmitting = ref(false)

  const studentNameForConfirm = (row: Record<string, unknown> | null) =>
    row
      ? pickEnrollmentRowStr(row, [
          'studentName',
          'student_name',
          'name',
          'nameEn',
          'nameKm',
        ])
      : ''

  const cancelEnrollmentConfirmConfig = computed(() => {
    const nm = studentNameForConfirm(pendingCancelEnrollmentRow.value)
    return {
      title: t('pages.allclass.studentListModal.confirm.cancelTitle'),
      description: t('pages.allclass.studentListModal.confirm.cancelDescription', {
        name: nm || '—',
      }),
      type: 'error' as const,
      submitLabel: t('pages.allclass.studentListModal.actions.cancelClass'),
      icon: 'i-lucide-user-minus' as const,
    }
  })

  function dismissCancelEnrollmentConfirm() {
    pendingCancelEnrollmentRow.value = null
  }

  function continueClassFromEnrollmentRow(row: Record<string, unknown>) {
    const cls = classStudentsProduct.value
    if (!cls) {
      toast.add({
        title: t('common.error'),
        description: t('pages.allclass.studentListModal.toast.noClassContext'),
        color: 'warning',
      })
      return
    }

    enrollmentCartLines.value = [{ product: resolveProductForEnrollmentCart(cls), qty: 1 }]
    enrollmentDiscountMode.value = 'percent'
    enrollmentDiscountPercent.value = 0
    enrollmentDiscountFixed.value = 0

    customerType.value = 'Customer'

    const nameKmStr = pickEnrollmentRowStr(row, ['nameKm', 'name_km'])
    const nameEnStr = pickEnrollmentRowStr(row, ['nameEn', 'name_en'])
    const combinedName = pickEnrollmentRowStr(row, ['studentName', 'student_name', 'name'])

    if (nameKmStr || nameEnStr) {
      nameKm.value = nameKmStr
      nameEn.value = nameEnStr
    } else if (combinedName.includes('/') || combinedName.includes('·')) {
      const parts = combinedName.split(/\s*[\/·]\s*/).map((s) => s.trim()).filter(Boolean)
      nameKm.value = parts[0] ?? ''
      nameEn.value = parts.length > 1 ? parts.slice(1).join(' · ') : (parts[0] ?? '')
    } else {
      nameKm.value = ''
      nameEn.value = combinedName
    }

    gender.value = normalizeEnrollmentGender(row.gender ?? row.studentGender)
    birthdate.value = pickEnrollmentRowStr(row, ['birthdate', 'birthDate', 'dateOfBirth'])
    province.value = pickEnrollmentRowStr(row, ['province', 'studentProvince'])
    customerPhone.value = pickEnrollmentRowStr(row, [
      'phone',
      'studentPhone',
      'customerPhone',
      'tel',
    ])
    const existingStudentId = Number(row.studentId ?? row.student_id)
    selectedStudentId.value = Number.isFinite(existingStudentId) && existingStudentId > 0 ? existingStudentId : undefined
    customerAddress.value = pickEnrollmentRowStr(row, ['address', 'customerAddress'])
    const avatar = pickEnrollmentRowStr(row, ['image', 'avatar', 'studentImage'])
    studentImage.value = avatar || undefined

    isClassStudentsModalOpen.value = false
    currentStep.value = 1
    toast.add({
      title: t('pages.allclass.studentListModal.toast.continueReady'),
      color: 'primary',
    })
  }

  function openCancelEnrollmentConfirm(row: Record<string, unknown>) {
    pendingCancelEnrollmentRow.value = row
    isCancelEnrollmentConfirmOpen.value = true
  }

  async function confirmCancelEnrollmentFromClass(rowArg?: Record<string, unknown>) {
    const cls = classStudentsProduct.value
    const row = rowArg ?? pendingCancelEnrollmentRow.value
    if (!cls || !row) {
      isCancelEnrollmentConfirmOpen.value = false
      pendingCancelEnrollmentRow.value = null
      return
    }
    const eid = String(row.id ?? row.enrollmentId ?? '').trim()
    if (!eid) {
      toast.add({
        title: t('common.error'),
        description: t('pages.allclass.studentListModal.toast.missingEnrollmentId'),
        color: 'error',
      })
      isCancelEnrollmentConfirmOpen.value = false
      pendingCancelEnrollmentRow.value = null
      return
    }
    cancelEnrollmentConfirmSubmitting.value = true
    try {
      await productApi.withdrawStudentFromClassRoster(cls.id, eid)
      toast.add({
        title: t('pages.allclass.studentListModal.toast.withdrawSuccess'),
        description: t('pages.allclass.studentListModal.toast.withdrawHistoryHint'),
        color: 'primary',
      })
      await loadClassStudents()
    } catch (err: unknown) {
      const e = err as { data?: { message?: string }; message?: string }
      toast.add({
        title: t('pages.allclass.studentListModal.toast.withdrawFailed'),
        description: e?.data?.message || e?.message || '',
        color: 'error',
      })
    } finally {
      cancelEnrollmentConfirmSubmitting.value = false
      isCancelEnrollmentConfirmOpen.value = false
      pendingCancelEnrollmentRow.value = null
    }
  }

  const courseRows = ref<Course[]>([])
  const teacherRows = ref<SystemUser[]>([])
  const categorySelectItems = ref<{ label: string; value: string }[]>([])

  const pendingPayload = ref<Record<string, unknown> | null>(null)
  const pendingImageFile = ref<File | null>(null)

  const courseSelectItems = computed(() =>
    courseRows.value.map((c) => ({
      label: c.courseName,
      value: String(c.id)
    }))
  )

  const teacherSelectItems = computed(() =>
    teacherRows.value.map((u) => ({
      label: u.name,
      value: String(u.id)
    }))
  )

  const dayOfWeekItems = computed(() => [
    { label: t('pages.allclass.weekdays.monday'), value: 'monday' },
    { label: t('pages.allclass.weekdays.tuesday'), value: 'tuesday' },
    { label: t('pages.allclass.weekdays.wednesday'), value: 'wednesday' },
    { label: t('pages.allclass.weekdays.thursday'), value: 'thursday' },
    { label: t('pages.allclass.weekdays.friday'), value: 'friday' },
    { label: t('pages.allclass.weekdays.saturday'), value: 'saturday' },
    { label: t('pages.allclass.weekdays.sunday'), value: 'sunday' },
  ])

  function resolveCourseId(classItem: Product) {
    if (classItem.courseId) return String(classItem.courseId)
    return String(courseRows.value.find((c) => c.courseName === classItem.courseName)?.id ?? '')
  }

  function resolveTeacherId(classItem: Product) {
    if (classItem.teacherId) return String(classItem.teacherId)
    return String(teacherRows.value.find((u) => u.name === classItem.teacherName)?.id ?? '')
  }

  function parseTimeSlot(slot: string | undefined) {
    const [start = '', end = ''] = String(slot || '').split(/\s*-\s*/)
    return {
      timeIn: start.trim(),
      timeOut: end.trim(),
    }
  }

  const classFormData = computed<Record<string, unknown> | undefined>(() => {
    const classItem = editingClass.value
    if (!classItem) return undefined
    const parsed = parseTimeSlot(classItem.timeSlot)
    const selectedDays = (classItem.daysOfWeek || []).map((day) => {
      const value = String(day || '').trim()
      return dayOfWeekItems.value.find((item) => item.value === value) ?? { label: value, value }
    })
    return {
      image: classItem.image,
      name: classItem.name,
      categoryId: classItem.categoryId,
      courseId: resolveCourseId(classItem),
      teacherId: resolveTeacherId(classItem),
      level: classItem.level || classItem.classLevel || classItem.courseLevel || '',
      levelKm: classItem.levelKm || '',
      classDuration: (() => {
        const raw =
          classItem.classDuration ||
          classItem.duration ||
          classItem.durationClass ||
          classItem.courseDuration ||
          ''
        const months = parseDurationMonths(raw)
        return months != null ? String(months) : String(raw || '')
      })(),
      daysOfWeek: selectedDays,
      timeIn: classItem.timeIn || parsed.timeIn,
      timeOut: classItem.timeOut || parsed.timeOut,
      fullPrice: classItem.fullPrice ?? classItem.outPrice,
      discountAmount: classItem.discountAmount ?? 0,
    }
  })

  const classFormFields = computed<FormField[]>(() => [
    {
      key: 'image',
      label: t('product.image'),
      type: 'file',
      placeholder: t('pages.allclass.placeholders.image'),
      required: false
    },
    {
      key: 'name',
      label: t('pages.allclass.fields.className'),
      type: 'input',
      required: true,
      placeholder: t('pages.allclass.placeholders.className')
    },
    {
      key: 'categoryId',
      label: t('product.category'),
      type: 'select',
      items: categorySelectItems.value,
      required: true
    },
    {
      key: 'courseId',
      label: t('pages.courses.columns.courseName'),
      type: 'select',
      items: courseSelectItems.value,
      required: true
    },
    {
      key: 'teacherId',
      label: t('pages.allclass.fields.teacher'),
      type: 'select',
      items: teacherSelectItems.value,
      required: true
    },
    {
      key: 'level',
      label: t('pages.allclass.fields.level'),
      type: 'input',
      required: false,
      placeholder: t('pages.allclass.placeholders.level')
    },
    {
      key: 'levelKm',
      label: t('pages.allclass.fields.levelKm'),
      type: 'input',
      required: false,
      placeholder: t('pages.allclass.placeholders.levelKm')
    },
    {
      key: 'classDuration',
      label: t('pages.allclass.fields.duration'),
      type: 'integer',
      required: false,
      placeholder: t('pages.allclass.placeholders.duration'),
      trailing: t('pages.allclass.fields.durationUnit')
    },
    {
      key: 'daysOfWeek',
      label: t('pages.allclass.fields.daysOfWeek'),
      type: 'select',
      items: dayOfWeekItems.value,
      multiple: true,
      class: 'w-full min-w-full',
      required: true,
      placeholder: t('pages.allclass.placeholders.daysOfWeek')
    },
    {
      key: 'timeIn',
      label: t('pages.allclass.fields.timeIn'),
      type: 'time',
      required: true,
      placeholder: t('pages.allclass.placeholders.timeIn')
    },
    {
      key: 'timeOut',
      label: t('pages.allclass.fields.timeOut'),
      type: 'time',
      required: true,
      placeholder: t('pages.allclass.placeholders.timeOut')
    },
    {
      key: 'fullPrice',
      label: t('pages.allclass.fields.fullPrice'),
      type: 'number',
      currency: true,
      required: true,
      placeholder: '0.00'
    },
    {
      key: 'discountAmount',
      label: t('pages.allclass.fields.discountPrice'),
      type: 'number',
      discount: true,
      discountBaseKey: 'fullPrice',
      required: false,
      placeholder: '0.00'
    }
  ])

  const confirmConfig = computed(() => ({
    title: editingClass.value ? t('pages.allclass.editTitle') : t('pages.allclass.addBtn'),
    description: editingClass.value
      ? t('pages.allclass.confirmSaveEdit')
      : t('pages.allclass.confirmSaveAdd'),
    type: 'primary' as const,
    submitLabel: t('actions.confirm'),
    icon: 'i-lucide-check-circle'
  }))

  const deleteClassConfirmConfig = computed(() => ({
    title: t('pages.allclass.confirmDeleteTitle'),
    description: t('pages.allclass.confirmDeleteDescription', {
      name: pendingDeleteClass.value?.name || '—',
    }),
    type: 'error' as const,
    submitLabel: t('actions.delete'),
    icon: 'i-lucide-trash-2' as const,
  }))

  async function loadLookupData() {
    try {
      const [catRes, courseRes, userRes] = await Promise.all([
        categoryApi.list({ page: 1, limit: 200, sortBy: 'name', sortOrder: 'asc' }),
        coursesApi.list({ page: 1, limit: 200, sortBy: 'courseName', sortOrder: 'asc' }),
        userApi.list({ page: 1, limit: 200, sortBy: 'name', sortOrder: 'asc' })
      ])

      const cats = extractApiArray<{ id?: string; name?: string }>(catRes)
        .map((item) => ({
          id: String(item?.id || '').trim(),
          name: String(item?.name || '').trim()
        }))
        .filter((item) => item.id && item.name && item.name.toLowerCase() !== 'all')

      categorySelectItems.value = cats.map((item) => ({
        label: item.name,
        value: item.id
      }))

      courseRows.value = extractApiArray<Course>(courseRes)
      teacherRows.value = extractApiArray<SystemUser>(userRes)
    } catch {
      categorySelectItems.value = []
      courseRows.value = []
      teacherRows.value = []
    }
  }

  const enrollmentClassSelectItems = computed(() =>
    productsState.filteredProducts.value.map((p) => ({
      label: p.name,
      value: p.id
    }))
  )

  const paymentMethodItems = computed(() => [
    { label: t('pages.allclass.payment.cash'), value: 'cash' },
    { label: t('pages.allclass.payment.bankTransfer'), value: 'bank_transfer' },
    { label: t('pages.allclass.payment.other'), value: 'other' }
  ])

  async function loadNextEnrollmentInvoiceNo() {
    if (enrollmentInvoiceNo.value) return true
    try {
      const res = await posApi.getNextInvoiceNo()
      enrollmentInvoiceNo.value = String(res?.invoiceNo || '').trim()
      return Boolean(enrollmentInvoiceNo.value)
    } catch (err: unknown) {
      const e = err as { data?: { message?: string }; message?: string }
      toast.add({
        title: t('common.error'),
        description: e?.data?.message || e?.message || 'Could not load invoice number',
        color: 'error'
      })
      return false
    }
  }

  async function goNextStep() {
    if (currentStep.value === 0) {
      if (enrollmentCartLines.value.length === 0) {
        toast.add({
          title: t('common.error'),
          description: t('pages.allclass.pickClassFirst'),
          color: 'warning'
        })
        return
      }
      currentStep.value = 1
      return
    }
    if (currentStep.value === 1) {
      const displayName =
        customerType.value === 'walkIn'
          ? customerName.value.trim()
          : [nameKm.value, nameEn.value].map((s) => String(s || '').trim()).filter(Boolean).join(' · ').trim()
      if (!displayName) {
        toast.add({
          title: t('common.error'),
          description: t('pages.allclass.studentNameRequired'),
          color: 'warning'
        })
        return
      }
      if (enrollmentCartLines.value.length === 0) {
        toast.add({
          title: t('common.error'),
          description: t('pages.allclass.pickClassFirst'),
          color: 'warning'
        })
        return
      }
      const hasInvoiceNo = await loadNextEnrollmentInvoiceNo()
      if (!hasInvoiceNo) return
      currentStep.value = 2
    }
  }

  async function finishEnrollmentCheckout() {
    if (enrollmentCartLines.value.length === 0) {
      toast.add({
        title: t('common.error'),
        description: t('pages.allclass.pickClassFirst'),
        color: 'warning'
      })
      return ''
    }

    try {
      const response = await checkoutState.checkout({
        cart: enrollmentCartLines.value,
        discountPercent: enrollmentCheckoutDiscountPercent.value,
        customer: {
          customerName: customerName.value,
          customerPhone: customerPhone.value,
          customerAddress: customerAddress.value.trim() || province.value.trim(),
          source: source.value,
          deliveryType: deliveryType.value,
          deliveryPrice: deliveryPrice.value,
          deliveryDate: deliveryDate.value,
          paymentMethod: paymentMethod.value,
          deliveryStatus: deliveryStatus.value,
          sellerId: sellerId.value,
          studentId: selectedStudentId.value,
          image: studentImage.value,
          nameKm: nameKm.value,
          nameEn: nameEn.value,
          gender: gender.value,
          birthdate: birthdate.value,
          province: province.value,
        },
      })
      const invoiceNo = String(response?.data?.invoiceNo || checkoutState.checkoutInvoiceNo.value || '').trim()
      if (invoiceNo) enrollmentInvoiceNo.value = invoiceNo
      await productsState.refreshProducts()
      return invoiceNo
    } catch (err: unknown) {
      const e = err as { message?: string; data?: { message?: string } }
      toast.add({
        title: t('common.error'),
        description: e?.data?.message || e?.message || 'Checkout failed',
        color: 'error'
      })
      return ''
    }
  }

  /** Toggle one class row in/out of `enrollmentCartLines` (multi-class cart). */
  function toggleEnrollmentClassSelect(product: Product, selected: boolean) {
    const id = product.id
    const lines = enrollmentCartLines.value
    if (!selected) {
      enrollmentCartLines.value = lines.filter((line) => line.product.id !== id)
      return
    }
    if (lines.some((line) => line.product.id === id)) return
    const synced =
      productsState.filteredProducts.value.find((p) => p.id === id) ?? product
    enrollmentCartLines.value = [...lines, { product: synced, qty: 1 }]
  }

  function goPrevStep() {
    if (currentStep.value > 0) currentStep.value -= 1
  }

  function resetEnrollmentWizard() {
    currentStep.value = 0
    customerType.value = 'Customer'
    customerName.value = ''
    nameKm.value = ''
    nameEn.value = ''
    gender.value = ''
    birthdate.value = ''
    province.value = ''
    studentImage.value = undefined
    selectedStudentId.value = undefined
    customerPhone.value = ''
    customerAddress.value = ''
    deliveryType.value = 'VET'
    deliveryPrice.value = 2
    deliveryDate.value = ''
    paymentMethod.value = 'cash'
    deliveryStatus.value = 'pending'
    source.value = 'other'
    sellerId.value = undefined
    paymentNote.value = ''
    enrollmentInvoiceNo.value = ''
    enrollmentCartLines.value = []
    enrollmentDiscountMode.value = 'percent'
    enrollmentDiscountPercent.value = 0
    enrollmentDiscountFixed.value = 0
  }

  onMounted(() => {
    loadLookupData()
  })

  function handleAddNew() {
    editingClass.value = null
    isFormOpen.value = true
  }

  function openEditClass(classItem: Product) {
    editingClass.value = classItem
    isFormOpen.value = true
  }

  function requestDeleteClass(classItem: Product) {
    pendingDeleteClass.value = classItem
    isDeleteClassConfirmOpen.value = true
  }

  function dismissDeleteClassConfirm() {
    pendingDeleteClass.value = null
  }

  async function confirmDeleteClass() {
    const target = pendingDeleteClass.value
    if (!target) {
      isDeleteClassConfirmOpen.value = false
      return
    }
    deleteClassSubmitting.value = true
    try {
      await mutation.run(() => productApi.remove(target.id), 'products-view')
      removeEnrollmentItem(target.id)
      await productsState.refreshProducts()
      toast.add({
        title: t('pages.allclass.deleted'),
        color: 'primary',
      })
    } catch (err: unknown) {
      const e = err as { data?: { message?: string }; message?: string }
      toast.add({
        title: t('common.error'),
        description: e?.data?.message || e?.message || '',
        color: 'error',
      })
    } finally {
      deleteClassSubmitting.value = false
      isDeleteClassConfirmOpen.value = false
      pendingDeleteClass.value = null
    }
  }

  function handleSaveRequest(data: Record<string, unknown>) {
    const name = String(data.name ?? '').trim()
    const categoryId = String(data.categoryId ?? '').trim()
    const courseId = String(data.courseId ?? '').trim()
    const teacherId = String(data.teacherId ?? '').trim()
    const level = String(data.level ?? '').trim()
    const levelKm = String(data.levelKm ?? '').trim()
    const durationRaw = String(data.classDuration ?? '').trim().replace(/\D/g, '')
    const classDuration = durationRaw ? String(Math.max(1, Number.parseInt(durationRaw, 10) || 0)) : ''
    const timeIn = String(data.timeIn ?? '').trim()
    const timeOut = String(data.timeOut ?? '').trim()
    const selectedDays = Array.isArray(data.daysOfWeek) ? data.daysOfWeek : []
    const daysOfWeek = selectedDays
      .map((item) => {
        if (typeof item === 'string' || typeof item === 'number') return String(item)
        if (item && typeof item === 'object' && 'value' in item) return String(item.value ?? '')
        return ''
      })
      .map((day) => day.trim())
      .filter(Boolean)
    const fullPrice = Number(data.fullPrice ?? 0)
    const discountAmount = Number(data.discountAmount ?? 0)
    const outPrice = Math.max(0, fullPrice - discountAmount)

    if (!name || !categoryId || !courseId || !teacherId || !timeIn || !timeOut || daysOfWeek.length === 0) {
      toast.add({
        title: t('common.error'),
        description: t('pages.allclass.validation.required'),
        color: 'error'
      })
      return
    }

    if (
      !Number.isFinite(fullPrice) ||
      !Number.isFinite(discountAmount) ||
      fullPrice <= 0 ||
      discountAmount < 0 ||
      discountAmount > fullPrice
    ) {
      toast.add({
        title: t('common.error'),
        description: t('pages.allclass.validation.price'),
        color: 'error'
      })
      return
    }

    const course = courseRows.value.find((c) => String(c.id) === courseId)
    const teacher = teacherRows.value.find((u) => String(u.id) === teacherId)

    if (!course || !teacher) {
      toast.add({
        title: t('common.error'),
        description: t('pages.allclass.validation.lookup'),
        color: 'error'
      })
      return
    }

    pendingImageFile.value = resolveFirstUploadFile(data.image)

    pendingPayload.value = {
      name,
      categoryId,
      courseId,
      courseName: course.courseName,
      teacherId,
      teacherName: teacher.name,
      ...(level ? { level } : {}),
      levelKm,
      ...(classDuration ? { classDuration } : {}),
      daysOfWeek,
      timeIn,
      timeOut,
      timeSlot: `${timeIn} - ${timeOut}`,
      inPrice: 0,
      outPrice,
      commission: 0,
      totalStock: 0,
      inStock: 0,
      sold: 0,
      added: 0,
      damaged: 0,
      fullPrice,
      discountAmount,
      status: 'active' as Product['status']
    }

    isConfirmOpen.value = true
  }

  async function finalizeAction() {
    if (!pendingPayload.value) {
      isConfirmOpen.value = false
      return
    }

    try {
      let imageField: string | undefined
      if (pendingImageFile.value) {
        imageField = await fileToDataUrl(pendingImageFile.value)
      }

      const body = {
        ...pendingPayload.value,
        ...(imageField ? { image: imageField } : {})
      }

      const target = editingClass.value
      await mutation.run(
        () =>
          target
            ? productApi.update(target.id, body as Partial<Product>)
            : productApi.create(body as Partial<Product>),
        'products-view'
      )
      await productsState.refreshProducts()
      toast.add({
        title: target ? t('pages.allclass.updated') : t('pages.allclass.created'),
        color: 'primary'
      })
      isFormOpen.value = false
      editingClass.value = null
    } catch (err: unknown) {
      const e = err as { data?: { message?: string }; message?: string }
      toast.add({
        title: t('common.error'),
        description: e?.data?.message || e?.message || '',
        color: 'error'
      })
    } finally {
      isConfirmOpen.value = false
      pendingPayload.value = null
      pendingImageFile.value = null
    }
  }

  return {
    ...productsState,
    currentStep,
    enrollmentStepItems,
    enrollmentInvoiceNo,
    enrollmentClassSelectItems,
    toggleEnrollmentClassSelect,
    isProductInEnrollmentCart,
    customerType,
    customerName,
    nameKm,
    nameEn,
    gender,
    birthdate,
    province,
    studentImage,
    selectedStudentId,
    customerPhone,
    customerAddress,
    deliveryType,
    deliveryPrice,
    deliveryDate,
    paymentMethod,
    deliveryStatus,
    source,
    sellerId,
    paymentNote,
    paymentMethodItems,
    enrollmentCartLines,
    enrollmentDiscountMode,
    enrollmentDiscountPercent,
    enrollmentDiscountFixed,
    enrollmentItemCount,
    enrollmentSubtotal,
    enrollmentDiscountAmount,
    enrollmentTotal,
    isFinishing: checkoutState.isFinishing,
    clearEnrollmentCart,
    removeEnrollmentItem,
    goNextStep,
    goPrevStep,
    finishEnrollmentCheckout,
    resetEnrollmentWizard,
    isFormOpen,
    isConfirmOpen,
    classFormFields,
    classFormData,
    confirmConfig,
    isDeleteClassConfirmOpen,
    deleteClassConfirmConfig,
    deleteClassSubmitting,
    handleAddNew,
    openEditClass,
    requestDeleteClass,
    confirmDeleteClass,
    dismissDeleteClassConfirm,
    handleSaveRequest,
    finalizeAction,
    reloadLookups: loadLookupData,
    isClassStudentsModalOpen,
    classStudentsProduct,
    classStudentsRows,
    classStudentsLoading,
    classStudentsTotal,
    classStudentsPagination,
    classStudentsDateRange,
    openClassStudentsModal,
    continueClassFromEnrollmentRow,
    openCancelEnrollmentConfirm,
    confirmCancelEnrollmentFromClass,
    isCancelEnrollmentConfirmOpen,
    cancelEnrollmentConfirmConfig,
    cancelEnrollmentConfirmSubmitting,
    dismissCancelEnrollmentConfirm,
  }
}
