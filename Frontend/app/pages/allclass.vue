<script setup lang="ts">
import type { ComponentPublicInstance } from 'vue'
import type { Product } from '~/types'
import { useAllClassPage } from '~/composables/table/useAllClassPage'
import { usePosInvoicePreview } from '~/composables/classes/useInvoicePreview'
import { useInvoicePrinter } from '~/composables/useInvoicePrinter'
import { waitForCheckoutPrintReady } from '~/composables/classes/useCheckoutPrintJob'
import {
    cartLinesFromBundle,
    previewHeaderFromBundle,
    type InvoicePreviewRow,
} from '~/utils/helpers/invoicePreview'

const TOTAL_WIZARD_STEPS = 3

const { t } = useI18n()
const {
    previewBundles,
    selectedReportInvoice,
    currentPreviewIndex,
    currentPreviewLines,
    currentPreviewHeader,
    hasReportPreviewInvoices,
    hasMultiplePreviewInvoices,
    previewInvoiceCount,
    isLoadingPreview,
    previewError,
    canGoPrevPreview,
    canGoNextPreview,
    goToPrevPreview,
    goToNextPreview,
    goToPreviewIndex,
    exitPreviewMode,
} = usePosInvoicePreview()

const {
    currentStep,
    enrollmentStepItems,
    enrollmentInvoiceNo,
    toggleEnrollmentClassSelect,
    isProductInEnrollmentCart,
    customerType,
    customerName,
    nameKm,
    nameEn,
    gender,
    birthdate,
    province,
    enrollmentDurationMonths,
    enrollmentStartDate,
    enrollmentEndDateIso,
    checkoutInvoiceDisplay,
    enrollmentClassDurationMax,
    enrollmentStudentMonths,
    enrollmentProratedSubtotal,
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
    enrollmentCartLines,
    enrollmentDiscountMode,
    enrollmentDiscountPercent,
    enrollmentDiscountFixed,
    enrollmentItemCount,
    enrollmentSubtotal,
    enrollmentDiscountAmount,
    enrollmentTotal,
    isFinishing,
    clearEnrollmentCart,
    removeEnrollmentItem,
    goNextStep,
    finishEnrollmentCheckout,
    resetEnrollmentWizard,
    isLoadingProducts,
    filteredProducts,
    loadMoreProducts,
    selectedCategoryId,
    categoryTabs,
    searchQuery,
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
    isClassStudentsModalOpen,
    classStudentsProduct,
    classStudentsRows,
    classStudentsLoading,
    classStudentsTotal,
    classStudentsPagination,
    classStudentsDateRange,
    openClassStudentsModal,
    continueClassFromEnrollmentRow,
    confirmCancelEnrollmentFromClass,
} = useAllClassPage()

const { invoicePrintRef, printInvoice, printElement } = useInvoicePrinter()
const isCheckoutSuccessOpen = ref(false)
const completedInvoiceNo = ref('')
const isPrintingInvoice = ref(false)
const checkoutJobId = ref<string | null>(null)

const reportPreviewCart = computed(() => currentPreviewLines.value)

const reportPreviewSubtotal = computed(() =>
    reportPreviewCart.value.reduce((sum, line) => sum + Number(line.product.outPrice || 0) * line.qty, 0)
)

const previewCounterLabel = computed(() =>
    t('pages.allclass.previewNav.counter', {
        current: currentPreviewIndex.value + 1,
        total: previewInvoiceCount.value,
    }),
)

type ReportInvoiceDisplay = {
    invoiceNo: string
    date: string
    customer: string
    phoneCustomer: string
    seller: string
    grandTotal?: number
    startDate?: string
    endDate?: string
    registeredAt?: string
    product?: string
    courseName?: string
    timeSlot?: string
    timeIn?: string
    timeOut?: string
    studentName?: string
    nameKm?: string
    nameEn?: string
    source?: string
}

function buildReportInvoiceDisplay(row: InvoicePreviewRow | null | undefined): ReportInvoiceDisplay | null {
    if (!row) return null
    return {
        invoiceNo: String(row.invoiceNo || ''),
        date: String(row.date || ''),
        startDate: row.startDate,
        endDate: row.endDate,
        registeredAt: row.registeredAt,
        product: row.product,
        courseName: row.courseName,
        timeSlot: row.timeSlot,
        timeIn: row.timeIn,
        timeOut: row.timeOut,
        studentName: row.studentName,
        nameKm: row.nameKm,
        nameEn: row.nameEn,
        customer: String(row.customer || row.studentName || ''),
        phoneCustomer: String(row.phoneCustomer || ''),
        seller: String(row.seller || ''),
        source: row.source,
        grandTotal: Number(row.grandTotal ?? row.amount ?? 0),
    }
}

const reportInvoiceForDisplay = computed(() =>
    buildReportInvoiceDisplay(currentPreviewHeader.value || selectedReportInvoice.value),
)

const activeInvoiceForDisplay = computed(() =>
    hasReportPreviewInvoices.value
        ? reportInvoiceForDisplay.value
        : buildReportInvoiceDisplay(checkoutInvoiceDisplay.value as unknown as InvoicePreviewRow),
)

const previewInvoiceSlides = computed(() =>
    previewBundles.value.map((bundle, index) => {
        const header = previewHeaderFromBundle(bundle)
        const cart = cartLinesFromBundle(bundle)
        const subtotal = cart.reduce(
            (sum, line) => sum + Number(line.product.outPrice || 0) * line.qty,
            0,
        )
        return {
            index,
            key: `${String(header?.invoiceNo || 'invoice')}-${index}`,
            header,
            cart,
            subtotal,
            display: buildReportInvoiceDisplay(header),
        }
    }),
)

const previewScrollRef = ref<HTMLElement | null>(null)
const previewSectionEls = ref<(HTMLElement | null)[]>([])
const suppressPreviewScrollSync = ref(false)
let previewIntersectionObserver: IntersectionObserver | null = null

function resolvePreviewSectionEl(el: Element | ComponentPublicInstance | null): HTMLElement | null {
    if (!el) return null
    if (el instanceof HTMLElement) return el
    const root = (el as ComponentPublicInstance).$el
    return root instanceof HTMLElement ? root : null
}

function setPreviewSectionEl(el: Element | ComponentPublicInstance | null, index: number) {
    previewSectionEls.value[index] = resolvePreviewSectionEl(el)
}

function teardownPreviewScrollObserver() {
    previewIntersectionObserver?.disconnect()
    previewIntersectionObserver = null
}

function setupPreviewScrollObserver() {
    teardownPreviewScrollObserver()
    const root = previewScrollRef.value
    if (!root || !hasMultiplePreviewInvoices.value) return

    previewIntersectionObserver = new IntersectionObserver(
        (entries) => {
            if (suppressPreviewScrollSync.value) return
            let best: { index: number; ratio: number } | null = null
            for (const entry of entries) {
                if (!entry.isIntersecting) continue
                const index = previewSectionEls.value.indexOf(entry.target as HTMLElement)
                if (index < 0) continue
                const ratio = entry.intersectionRatio
                if (!best || ratio > best.ratio) best = { index, ratio }
            }
            if (best && best.index !== currentPreviewIndex.value) {
                suppressPreviewScrollSync.value = true
                goToPreviewIndex(best.index)
                void nextTick(() => {
                    suppressPreviewScrollSync.value = false
                    updateActiveInvoicePrintTarget()
                })
            }
        },
        { root, threshold: [0.35, 0.5, 0.65, 0.85] },
    )

    for (const section of previewSectionEls.value) {
        if (section) previewIntersectionObserver.observe(section)
    }
}

function scrollPreviewToIndex(index: number, behavior: ScrollBehavior = 'smooth') {
    const section = previewSectionEls.value[index]
    if (!section) return
    suppressPreviewScrollSync.value = true
    section.scrollIntoView({ behavior, block: 'start' })
    window.setTimeout(() => {
        suppressPreviewScrollSync.value = false
    }, behavior === 'smooth' ? 450 : 0)
}

function updateActiveInvoicePrintTarget() {
    if (!hasMultiplePreviewInvoices.value) return
    const section = previewSectionEls.value[currentPreviewIndex.value]
    const inner = section?.querySelector('.invoice-slide-inner') as HTMLElement | null
    invoicePrintRef.value = inner ?? section ?? null
}

watch(currentPreviewIndex, (index) => {
    if (!hasMultiplePreviewInvoices.value) return
    void nextTick(() => {
        updateActiveInvoicePrintTarget()
        if (suppressPreviewScrollSync.value) return
        scrollPreviewToIndex(index)
    })
})

watch(
    () => previewInvoiceSlides.value.map((slide) => slide.key).join('|'),
    () => {
        if (!hasMultiplePreviewInvoices.value) {
            teardownPreviewScrollObserver()
            return
        }
        previewSectionEls.value = []
        void nextTick(() => {
            setupPreviewScrollObserver()
            updateActiveInvoicePrintTarget()
        })
    },
)

onBeforeUnmount(() => {
    teardownPreviewScrollObserver()
})

const enrollmentMobilePanel = ref<'main' | 'payment'>('main')
const enrollmentMobilePanelItems = computed(() => [
    {
        label: currentStep.value === 2
            ? t('pages.allclass.steps.invoice')
            : t('pages.allclass.steps.studentInfo'),
        value: 'main',
    },
    {
        label: t('pages.allclass.steps.payment'),
        value: 'payment',
    },
])
const mobileEnrollmentStepItems = computed(() =>
    enrollmentStepItems.value.map((item) => ({
        ...item,
        title: '',
    }))
)

watch(hasReportPreviewInvoices, (hasPreview) => {
    if (hasPreview) currentStep.value = 2
}, { immediate: true })

watch(currentStep, () => {
    enrollmentMobilePanel.value = 'main'
})

function onSubmitClass(data: Record<string, unknown>) {
    handleSaveRequest(data)
}

function onToggleEnrollmentSelect(classItem: Product, selected: boolean) {
    toggleEnrollmentClassSelect(classItem, selected)
}

function onInvoiceDone() {
    isCheckoutSuccessOpen.value = false
    completedInvoiceNo.value = ''
    resetEnrollmentWizard()
}

async function onEnrollmentPaymentNext() {
    await goNextStep()
}

async function runBackgroundPrint(jobId: string | null) {
    isPrintingInvoice.value = true
    try {
        await waitForCheckoutPrintReady(jobId)
        await nextTick()
        await printInvoice()
    } finally {
        isPrintingInvoice.value = false
    }
}

async function onEnrollmentFinish() {
    const result = await finishEnrollmentCheckout()
    if (!result?.invoiceNo) return
    completedInvoiceNo.value = result.invoiceNo
    checkoutJobId.value = result.jobId
    isCheckoutSuccessOpen.value = true
    void runBackgroundPrint(result.jobId)
}

async function onPrintCompletedInvoice() {
    if (isPrintingInvoice.value) return
    await runBackgroundPrint(checkoutJobId.value)
    onInvoiceDone()
}

function onViewClass(classItem: Product) {
    openClassStudentsModal(classItem)
}

async function printCurrentPreviewInvoice() {
    updateActiveInvoicePrintTarget()
    await printInvoice()
}

async function printAllPreviewInvoices() {
    const container = previewScrollRef.value
    if (!container) return

    const clone = container.cloneNode(true) as HTMLElement
    clone.classList.add('invoice-print-target')
    clone.querySelectorAll<HTMLElement>('.invoice-preview-slide').forEach((section) => {
        section.classList.add('print-invoice-page')
    })

    await printElement(clone)
}
</script>

<template>
    <div class="flex flex-col h-full bg-background text-foreground overflow-hidden tracking-tight">

        <LayoutAppHeader :title="hasReportPreviewInvoices ? t('pages.allclass.previewNav.title') : t('pages.allclass.title')">
            <template #right>
                <div class="flex flex-wrap items-center gap-2 justify-end w-full">
                    <template v-if="hasReportPreviewInvoices && hasMultiplePreviewInvoices">
                        <UButton
                            icon="i-lucide-chevron-left"
                            color="neutral"
                            variant="outline"
                            size="sm"
                            class="font-normal shrink-0"
                            :disabled="!canGoPrevPreview"
                            @click="goToPrevPreview"
                        />
                        <span class="text-xs font-semibold text-muted-foreground tabular-nums px-1 shrink-0 min-w-18 text-center">
                            {{ previewCounterLabel }}
                        </span>
                        <UButton
                            icon="i-lucide-chevron-right"
                            color="neutral"
                            variant="outline"
                            size="sm"
                            class="font-normal shrink-0"
                            :disabled="!canGoNextPreview"
                            @click="goToNextPreview"
                        />
                        <UButton
                            icon="i-lucide-printer"
                            color="neutral"
                            variant="subtle"
                            size="sm"
                            class="font-normal shrink-0"
                            :title="t('pages.allclass.previewNav.printAll')"
                            @click="printAllPreviewInvoices"
                        >
                            <span class="hidden sm:inline">{{ t('pages.allclass.previewNav.printAll') }}</span>
                        </UButton>
                        <UButton
                            icon="i-lucide-x"
                            color="neutral"
                            variant="ghost"
                            size="sm"
                            class="font-normal shrink-0"
                            @click="exitPreviewMode"
                        />
                    </template>
                    <template v-else-if="hasReportPreviewInvoices">
                        <UButton
                            icon="i-lucide-printer"
                            color="neutral"
                            variant="subtle"
                            size="sm"
                            class="font-normal shrink-0"
                            @click="printCurrentPreviewInvoice"
                        />
                        <UButton
                            icon="i-lucide-x"
                            color="neutral"
                            variant="ghost"
                            size="sm"
                            class="font-normal shrink-0"
                            @click="exitPreviewMode"
                        />
                    </template>
                    <template v-else>
                        <UStepper v-model="currentStep" :items="mobileEnrollmentStepItems" size="xs" :linear="false"
                            class="flex w-[132px] shrink-0 sm:hidden" />
                        <UStepper v-model="currentStep" :items="enrollmentStepItems" size="xs" :linear="false"
                            class="hidden w-[280px] shrink-0 sm:flex" />
                        <UButton v-if="currentStep === 0 && enrollmentItemCount > 0" trailing-icon="i-lucide-arrow-right"
                            color="primary" variant="solid" class="font-normal shadow-sm shrink-0" @click="goNextStep">
                            <span class="hidden sm:inline">{{ t('pages.allclass.nav.next') }}</span>
                        </UButton>
                        <UButton icon="i-lucide-circle-plus" color="primary" variant="solid"
                            class="font-normal shadow-sm shrink-0" @click="handleAddNew">
                            <span class="hidden sm:inline">{{ t('pages.allclass.addBtn') }}</span>
                        </UButton>
                    </template>
                </div>
            </template>
        </LayoutAppHeader>

        <div class="flex flex-1 flex-col min-h-0 overflow-hidden">
            <!-- Step 0: full-width grid only — multi-select classes, no cart (Next → student info) -->
            <!-- Steps 1–2: narrower main column + cart / payment sidebar -->
            <div v-if="currentStep !== 0 && !hasReportPreviewInvoices"
                class="lg:hidden border-b border-default px-2 py-2 bg-background">
                <UTabs v-model="enrollmentMobilePanel" :items="enrollmentMobilePanelItems" :content="false"
                    color="primary" size="xs" class="w-full" />
            </div>
            <div class="flex flex-1 flex-col min-h-0 overflow-hidden lg:flex-row">
                <div class="flex-1 min-h-0 min-w-0 flex-col overflow-hidden border-b border-default" :class="[
                    currentStep === 0 || hasReportPreviewInvoices || enrollmentMobilePanel === 'main' ? 'flex' : 'hidden',
                    currentStep === 0 ? 'lg:w-full' : 'lg:flex lg:basis-[65%] lg:max-w-[65%] lg:border-r lg:border-b-0',
                    currentStep === 2 ? 'bg-muted/10' : ''
                ]">

                    <!-- Step 0: select class -->
                    <div v-show="currentStep === 0" class="flex flex-1 flex-col min-h-0 overflow-hidden">
                        <div
                            class="flex flex-col gap-3 border-b border-default shrink-0 bg-background/80 p-4 backdrop-blur-sm sm:flex-row sm:flex-wrap sm:items-center sm:p-3">
                            <div class="min-w-0 w-full overflow-x-auto sm:flex-1">
                                <UTabs v-model="selectedCategoryId" :items="categoryTabs" size="xs" color="primary"
                                    :content="false" default-value="All" class="w-max min-w-full" />
                            </div>
                            <div class="flex w-full items-center gap-2 sm:ml-auto sm:w-auto">
                                <CommonAppSearch v-model="searchQuery" :placeholder="t('common.search')"
                                    class="w-full sm:w-52" />
                            </div>
                        </div>

                        <div class="flex-1 min-h-0 overflow-y-auto p-4 relative flex flex-col sm:p-3">
                            <div v-if="filteredProducts.length === 0"
                                class="flex flex-1 min-h-[240px] flex-col items-center justify-center gap-3 py-12 text-muted-foreground">
                                <UIcon name="i-lucide-layout-grid" class="size-12 opacity-30" />
                                <p class="text-sm">{{ t('pages.allclass.empty') }}</p>
                            </div>

                            <template v-else>
                                <div
                                    class="grid w-full grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                                    <CommonAppClassCard v-for="classItem in filteredProducts" :key="classItem.id"
                                        variant="school" :class-item="classItem"
                                        :selected-for-enrollment="isProductInEnrollmentCart(classItem.id)"
                                        @toggle-enrollment-select="onToggleEnrollmentSelect" @view="onViewClass"
                                        @edit="openEditClass" @delete="requestDeleteClass" />
                                </div>

                                <div class="mt-3 flex justify-center shrink-0">
                                    <UButton v-if="filteredProducts.length >= 60" color="neutral" variant="soft"
                                        size="sm" :loading="isLoadingProducts" @click="loadMoreProducts">
                                        {{ t('pages.allclass.loadMore') }}
                                    </UButton>
                                </div>
                            </template>
                        </div>
                    </div>

                    <!-- Step 1: student -->
                    <div v-show="currentStep === 1"
                        class="h-full min-h-0 flex-1 overflow-y-auto [&>div]:max-w-none [&>div]:mx-0 [&>div]:border-r-0">
                        <CommonAppStudentForm v-model:customer-type="customerType" v-model:customer-name="customerName"
                            v-model:name-km="nameKm" v-model:name-en="nameEn" v-model:gender="gender"
                            v-model:birthdate="birthdate" v-model:province="province"
                            v-model:enrollment-duration-months="enrollmentDurationMonths"
                            v-model:enrollment-start-date="enrollmentStartDate"
                            :class-duration-max-months="enrollmentClassDurationMax"
                            v-model:student-image="studentImage" v-model:selected-student-id="selectedStudentId" v-model:customer-phone="customerPhone"
                            v-model:customer-address="customerAddress" v-model:delivery-type="deliveryType"
                            v-model:delivery-price="deliveryPrice" v-model:delivery-date="deliveryDate"
                            v-model:delivery-status="deliveryStatus" v-model:seller-id="sellerId" />
                    </div>

                    <!-- Step 2: invoice -->
                    <div
                        v-show="currentStep === 2"
                        :class="[
                            'flex h-full min-h-0 flex-1 flex-col',
                            hasReportPreviewInvoices && hasMultiplePreviewInvoices
                                ? 'overflow-hidden'
                                : 'overflow-y-auto p-3 sm:p-4',
                        ]"
                    >
                        <CommonAppLoadingState
                            v-if="isLoadingPreview"
                            class="flex-1 min-h-[200px]"
                        />
                        <div v-else-if="previewError" class="flex flex-1 flex-col items-center justify-center gap-3 py-12 text-center">
                            <UIcon name="i-lucide-triangle-alert" class="size-10 text-error" />
                            <p class="text-sm text-muted-foreground max-w-sm">{{ previewError }}</p>
                        </div>
                        <div
                            v-else-if="hasReportPreviewInvoices && hasMultiplePreviewInvoices"
                            class="flex min-h-0 flex-1 flex-col overflow-hidden"
                        >
                            <p class="shrink-0 border-b border-default bg-background/90 px-4 py-2 text-center text-xs text-muted-foreground backdrop-blur-sm">
                                <span class="font-semibold tabular-nums text-foreground">{{ previewCounterLabel }}</span>
                                <span class="mx-2 text-border">·</span>
                                <span>{{ t('pages.allclass.previewNav.scrollHint') }}</span>
                            </p>
                            <div
                                ref="previewScrollRef"
                                class="invoice-preview-scroll flex-1 min-h-0 overflow-y-auto snap-y snap-mandatory scroll-smooth"
                            >
                                <section
                                    v-for="slide in previewInvoiceSlides"
                                    :key="slide.key"
                                    :ref="(el) => setPreviewSectionEl(el, slide.index)"
                                    class="invoice-preview-slide print-invoice-page flex min-h-full snap-start snap-always flex-col border-b border-default last:border-b-0"
                                >
                                    <div class="invoice-slide-inner invoice-print-target mx-auto w-full max-w-4xl flex-1 px-3 py-6 sm:px-4 sm:py-8">
                                        <CommonAppInvoice
                                            :cart="slide.cart"
                                            :customer-name="slide.header?.customer || slide.header?.studentName || ''"
                                            :customer-name-km="slide.header?.nameKm || ''"
                                            :customer-name-en="slide.header?.nameEn || ''"
                                            :customer-phone="slide.header?.phoneCustomer || ''"
                                            :delivery-type="deliveryType"
                                            :delivery-price="0"
                                            :selected-report-invoice="slide.display"
                                            checkout-invoice-no=""
                                            :display-subtotal="slide.subtotal"
                                            :display-discount="0"
                                            :display-total="slide.subtotal"
                                            class="min-h-0 w-full"
                                        />
                                    </div>
                                </section>
                            </div>
                        </div>
                        <div v-else ref="invoicePrintRef" class="invoice-print-target min-h-0 w-full max-w-4xl mx-auto">
                            <CommonAppInvoice
                                :cart="hasReportPreviewInvoices ? reportPreviewCart : enrollmentCartLines"
                                :customer-name="hasReportPreviewInvoices ? (currentPreviewHeader?.customer || currentPreviewHeader?.studentName || '') : customerName"
                                :customer-name-km="hasReportPreviewInvoices ? (currentPreviewHeader?.nameKm || nameKm) : nameKm"
                                :customer-name-en="hasReportPreviewInvoices ? (currentPreviewHeader?.nameEn || nameEn) : nameEn"
                                :customer-phone="hasReportPreviewInvoices ? (currentPreviewHeader?.phoneCustomer || customerPhone) : customerPhone"
                                :delivery-type="deliveryType"
                                :delivery-price="hasReportPreviewInvoices ? 0 : deliveryPrice"
                                :selected-report-invoice="activeInvoiceForDisplay"
                                :checkout-invoice-no="enrollmentInvoiceNo"
                                :display-subtotal="hasReportPreviewInvoices ? reportPreviewSubtotal : enrollmentSubtotal"
                                :display-discount="hasReportPreviewInvoices ? 0 : enrollmentDiscountAmount"
                                :display-total="hasReportPreviewInvoices ? reportPreviewSubtotal : enrollmentTotal"
                                class="min-h-0 w-full"
                            />
                        </div>
                    </div>
                </div>

                <div v-if="currentStep !== 0 && !hasReportPreviewInvoices" :class="[
                    enrollmentMobilePanel === 'payment' ? 'flex' : 'hidden',
                    'w-full min-h-0 flex-1 shrink-0 flex-col overflow-hidden border-t border-default lg:flex lg:basis-[35%] lg:max-w-[35%] lg:border-t-0 lg:border-l'
                ]">
                    <CommonAppPayment
                        v-model:discount-mode="enrollmentDiscountMode"
                        v-model:discount-percent="enrollmentDiscountPercent"
                        v-model:discount-fixed-amount="enrollmentDiscountFixed"
                        v-model:payment-method="paymentMethod" v-model:source="source" :cart="enrollmentCartLines"
                        :item-count="enrollmentItemCount" :subtotal="enrollmentSubtotal"
                        :discount-amount="enrollmentDiscountAmount" :total="enrollmentTotal" :current-step="currentStep"
                        :total-steps="TOTAL_WIZARD_STEPS" :loading="isFinishing" class="h-full min-h-0" @clear-cart="clearEnrollmentCart"
                        @remove-item="removeEnrollmentItem" @next="onEnrollmentPaymentNext" @finish="onEnrollmentFinish" />
                </div>
            </div>
        </div>

        <CommonAppSlideoverForm v-model:open="isFormOpen" :fields="classFormFields" :data="classFormData"
            :title="classFormData ? t('pages.allclass.editTitle') : t('pages.allclass.addBtn')"
            :submit-label="t('actions.confirm')" @submit="onSubmitClass" />
        <CommonAppModalCURD v-model:open="isConfirmOpen" v-bind="confirmConfig" @submit="finalizeAction" />
        <CommonAppModalCURD v-model:open="isDeleteClassConfirmOpen" v-bind="deleteClassConfirmConfig"
            :loading="deleteClassSubmitting" @submit="confirmDeleteClass" @cancel="dismissDeleteClassConfirm" />
        <CommonAppModalCURD
            v-model:open="isCheckoutSuccessOpen"
            :title="t('pages.school.cart.checkoutSuccessTitle')"
            :description="isPrintingInvoice ? t('pages.school.cart.printingInvoiceDescription') : t('pages.school.cart.checkoutSuccessDescription')"
            :submit-label="isPrintingInvoice ? t('pages.school.cart.printingInvoice') : t('pages.school.cart.printInvoice')"
            :cancel-label="t('pages.school.cart.done')"
            :loading="isPrintingInvoice"
            type="primary"
            @submit="onPrintCompletedInvoice"
            @cancel="onInvoiceDone"
        >
            <div class="rounded-lg border border-default bg-muted/40 px-4 py-3 space-y-3">
                <div>
                    <p class="text-xs font-semibold uppercase text-muted-foreground">Invoice No</p>
                    <p class="mt-1 text-xl font-black text-primary tabular-nums">{{ completedInvoiceNo || enrollmentInvoiceNo }}</p>
                </div>
                <p v-if="isPrintingInvoice" class="text-sm text-muted-foreground flex items-center gap-2">
                    <UIcon name="i-lucide-loader-circle" class="size-4 animate-spin shrink-0" />
                    {{ t('pages.school.cart.printingInvoice') }}
                </p>
            </div>
        </CommonAppModalCURD>

        <CommonAppStudentClassModal v-model:open="isClassStudentsModalOpen" v-model:range="classStudentsDateRange"
            v-model:pagination="classStudentsPagination" :class-id="String(classStudentsProduct?.id ?? '')"
            :class-name="classStudentsProduct?.name ?? ''" :data="classStudentsRows" :loading="classStudentsLoading"
            :total="classStudentsTotal" @continue-class="continueClassFromEnrollmentRow"
            @cancel-class="confirmCancelEnrollmentFromClass" />
    </div>
</template>

<style scoped>
.invoice-preview-scroll {
    scroll-padding-top: 0;
}

.invoice-preview-slide {
    scroll-snap-stop: always;
}
</style>
