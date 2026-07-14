<script setup lang="ts">
import type { Product } from '~/types'
import { formatCurrency } from '~/utils/format/currency'
import { clampExchangeRate, formatKhr } from '~/utils/format/paymentCurrency'
import { formatDateShort } from '~/utils/format/date'
import { formatClassDuration, normalizeIsoDate } from '~/utils/format/duration'
import logo from '~/assets/images/logoapp.png'
const { t, te, locale } = useI18n()
const authStore = useAuthStore()

interface ReportInvoice {
  id?: number | string
  invoiceNo: string
  date: string
  startDate?: string
  endDate?: string
  registeredAt?: string
  product?: string
  courseName?: string
  timeSlot?: string
  timeIn?: string
  timeOut?: string
  durationMonths?: string | number | null
  classDuration?: string | number | null
  studentName?: string
  nameKm?: string
  nameEn?: string
  customer: string
  phoneCustomer: string
  seller: string
  grandTotal?: number
  subtotal?: number
  discountAmount?: number
  paymentNote?: string
  paymentMethod?: string
  amountPaid?: number
  amountOwn?: number
  exchangeRate?: number
}

interface CartItem {
  product: Product
  qty: number
}

const props = withDefaults(
  defineProps<{
    cart: CartItem[]
    customerName: string
    customerNameKm?: string
    customerNameEn?: string
    customerPhone: string
    deliveryType: string
    deliveryPrice: number
    selectedReportInvoice: ReportInvoice | null
    checkoutInvoiceNo?: string
    displaySubtotal: number
    displayDiscount: number
    displayTotal: number
    /** Optional checkout note shown where QR codes used to be. */
    note?: string
  }>(),
  {
    note: '',
  },
)

/** Study start/end from student form (checkout) or saved invoice preview. */
const displayStartDate = computed(() => {
  return (
    normalizeIsoDate(props.selectedReportInvoice?.startDate) ||
    props.selectedReportInvoice?.date ||
    ''
  )
})

const displayEndDate = computed(() => {
  return normalizeIsoDate(props.selectedReportInvoice?.endDate) || ''
})

const firstInvoiceProduct = computed(() => props.cart[0]?.product)
const invoiceProducts = computed(() => props.cart.map((item) => item.product).filter(Boolean))

function uniqueText(values: Array<unknown>) {
  return Array.from(
    new Set(
      values
        .map((value) => String(value || '').trim())
        .filter(Boolean)
    )
  )
}

function splitCombinedStudentName(value: string) {
  const parts = value
    .split(/\s*[·/]\s*/)
    .map((part) => part.trim())
    .filter(Boolean)
  return {
    km: parts[0] || '',
    en: parts.length > 1 ? parts.slice(1).join(' · ') : ''
  }
}

function localizedStudentName(kmValue?: string, enValue?: string, fallbackValue?: string) {
  const km = String(kmValue || '').trim()
  const en = String(enValue || '').trim()
  const fallback = String(fallbackValue || '').trim()
  const split = splitCombinedStudentName(fallback)
  const isKhmer = String(locale.value || '').toLowerCase().startsWith('km')

  if (isKhmer) return km || split.km || en || split.en || fallback || 'N/A'
  return en || split.en || km || split.km || fallback || 'N/A'
}

const invoiceDisplayNo = computed(() => {
  const report = props.selectedReportInvoice
  return (
    String(report?.invoiceNo || '').trim() ||
    String(props.checkoutInvoiceNo || '').trim() ||
    '-'
  )
})

const invoiceCourse = computed(() => {
  const report = props.selectedReportInvoice
  const courses = uniqueText(invoiceProducts.value.map((product) => product.courseName || product.name))
  return report?.courseName || report?.product || courses.join(', ') || 'N/A'
})

const invoiceClassDuration = computed(() => {
  const report = props.selectedReportInvoice
  if (report?.durationMonths != null && report.durationMonths !== '') {
    return formatClassDuration(report.durationMonths, t, te) || 'N/A'
  }
  const durations = uniqueText(
    invoiceProducts.value.map((product) => {
      const raw =
        product.durationMonths ||
        product.classDuration ||
        product.durationClass ||
        product.courseDuration ||
        product.duration
      return raw ? formatClassDuration(raw, t, te) : ''
    })
  )
  return durations.join(', ') || 'N/A'
})

const invoiceTimeInOut = computed(() => {
  const report = props.selectedReportInvoice
  if (report?.timeSlot) return report.timeSlot

  const times = uniqueText(
    invoiceProducts.value.map((product) => {
      if (product.timeSlot) return product.timeSlot
      return [product.timeIn, product.timeOut].map((value) => String(value || '').trim()).filter(Boolean).join(' - ')
    })
  )
  if (times.length) return times.join(', ')

  const reportTime = [report?.timeIn, report?.timeOut].filter(Boolean).join(' - ')
  return reportTime || 'N/A'
})

const invoiceStudentName = computed(() =>
  localizedStudentName(
    props.selectedReportInvoice?.nameKm || props.customerNameKm,
    props.selectedReportInvoice?.nameEn || props.customerNameEn,
    props.selectedReportInvoice?.studentName || props.selectedReportInvoice?.customer || props.customerName
  )
)

function weekdayLabel(day: string) {
  const normalized = day.trim().toLowerCase()
  const key = `pages.allclass.weekdays.${normalized}`
  return te(key) ? t(key) : day
}

const invoiceShiftDays = computed(() => {
  const days = invoiceProducts.value.flatMap((product) =>
    Array.isArray(product.daysOfWeek) ? product.daysOfWeek : []
  )
  const labels = days
    .map((day) => String(day || '').trim())
    .filter(Boolean)
    .map(weekdayLabel)
  const uniqueLabels = uniqueText(labels)
  if (uniqueLabels.length) return uniqueLabels.join(', ')
  return uniqueText(invoiceProducts.value.map((product) => {
    const raw = product.timeIn
    if (!raw) return ''
    const hour = parseInt(raw.split(':')[0] ?? '', 10)
    if (isNaN(hour)) return ''
    if (hour < 12) return t('pages.courses.shift.morning')
    if (hour < 17) return t('pages.courses.shift.afternoon')
    return t('pages.courses.shift.evening')
  })).join(', ') || 'N/A'
})

const displayNote = computed(() => {
  const note = String(props.selectedReportInvoice?.paymentNote || props.note || '').trim()
  return note || '—'
})

const invoiceExchangeRate = computed(() =>
  clampExchangeRate(props.selectedReportInvoice?.exchangeRate),
)

const displayAmountPaid = computed(() => {
  const method = String(props.selectedReportInvoice?.paymentMethod || '').toLowerCase()
  const paid = Number(props.selectedReportInvoice?.amountPaid ?? 0)
  const own = Number(props.selectedReportInvoice?.amountOwn ?? 0)
  if (method === 'own' || own > 0 || paid > 0) return Math.max(0, paid)
  return 0
})

const displayAmountOwn = computed(() => {
  const method = String(props.selectedReportInvoice?.paymentMethod || '').toLowerCase()
  const own = Number(props.selectedReportInvoice?.amountOwn ?? 0)
  if (method === 'own' || own > 0) return Math.max(0, own)
  return 0
})

const showOwnPaymentBreakdown = computed(
  () => displayAmountOwn.value > 0 || String(props.selectedReportInvoice?.paymentMethod || '').toLowerCase() === 'own',
)

const displayDiscountAmount = computed(() =>
  Number(props.displayDiscount ?? props.selectedReportInvoice?.discountAmount ?? 0) || 0,
)
</script>

<template>
  <div class="h-full min-h-0 overflow-y-auto">
    <div class="w-[153.846%] sm:w-full origin-top-left scale-[0.65] sm:scale-100">
      <UCard :ui="{ body: 'p-0 sm:p-0' }" class="max-w-2xl mx-auto w-full text-slate-900 rounded-none border-0 ring-0 shadow-none">
        <div class="px-6 pb-4 flex flex-col gap-5 bg-white">
          <div class="flex justify-between items-start">
            <div class="flex items-center gap-3 mt-2">
              <img :src="logo" alt="Learn Computer logo" class="w-36 h-20 shrink-0 object-contain" loading="eager" decoding="sync">
            </div>
            <h1 class="text-2xl font-black text-slate-800 uppercase italic mr-10 mt-8">{{ t('pages.school.invoice.title') }}</h1>
          </div>

          <div class="grid grid-cols-2 text-sm">
            <div class="space-y-1">
              <div class="flex justify-between border-b border-slate-100 pb-1">
                <span class="text-slate-500 font-bold uppercase text-[10px]">{{ t('pages.school.invoice.section.invoiceInfo') }}</span>
              </div>
              <div class="grid grid-cols-[80px_1fr] gap-2 pt-2">
                <span class="text-slate-600 font-bold">{{ t('pages.school.invoice.fields.invoiceNo') }}:</span>
                <span class="font-bold text-slate-900">{{ invoiceDisplayNo }}</span>
                <span class="text-slate-600 font-bold">{{ t('pages.school.invoice.fields.startDate') }}:</span>
                <span class="font-bold text-slate-900">{{ formatDateShort(displayStartDate) }}</span>
                <span class="text-slate-600 font-bold">{{ t('pages.school.invoice.fields.endDate') }}:</span>
                <span class="font-bold text-slate-900">{{ formatDateShort(displayEndDate) }}</span>
                <span class="text-slate-600 font-bold">{{ t('pages.school.invoice.fields.registered') }}:</span>
                <span class="font-bold text-slate-900">{{ formatDateShort(selectedReportInvoice?.registeredAt || '') }}</span>
                <span class="text-slate-600 font-bold">{{ t('pages.school.invoice.fields.duration') }}:</span>
                <span class="font-bold text-slate-900">{{ invoiceClassDuration }}</span>
              </div>
            </div>

            <div class="space-y-1">
              <div class="flex justify-between border-b border-slate-100 pb-1">
                <span class="text-slate-500 font-bold uppercase text-[10px]">{{ t('pages.school.invoice.section.customer') }}</span>
              </div>
              <div class="grid grid-cols-[60px_1fr] gap-2 pt-2">
                <span class="text-slate-600 font-bold">{{ t('pages.school.invoice.fields.name') }}:</span>
                <span class="font-bold text-slate-900">{{ invoiceStudentName }}</span>
                <span class="text-slate-600 font-bold">{{ t('pages.school.invoice.fields.phone') }}:</span>
                <span class="font-bold text-slate-900">{{ selectedReportInvoice?.phoneCustomer || customerPhone || 'N/A' }}</span>
                <span class="text-slate-600 font-bold">{{ t('pages.courses.columns.course') }}:</span>
                <span class="font-bold text-md text-slate-900">{{ invoiceCourse }}</span>
                <span class="text-slate-600 font-bold">{{ t('pages.allclass.fields.time') }}:</span>
                <span class="font-bold text-slate-900">{{ invoiceTimeInOut }}</span>
                <span class="text-slate-600 font-bold">{{ t('pages.school.invoice.fields.shift') }}:</span>
                <span class="font-bold text-xs text-slate-900">{{ invoiceShiftDays }}</span>

              </div>
            </div>
          </div>

          <div class="flex-1 overflow-x-auto">
            <table class="w-full border-collapse table-auto">
              <thead>
                <tr class="bg-primary text-white text-[9px] sm:text-[10px] uppercase font-bold text-left">
                  <th
                    class="px-2 sm:px-3 py-1 border-[0.5px] border-primary-foreground/20 w-10 sm:w-12 text-center whitespace-nowrap">
                    {{ t('pages.school.invoice.table.noKm') }}<br>{{ t('pages.school.invoice.table.no') }}</th>
                  <th class="px-2 text-center sm:px-3 py-1 border-[0.5px] border-primary-foreground/20 min-w-[140px]">
                    {{ t('pages.school.invoice.table.descriptionKm') }}<br>{{ t('pages.school.invoice.table.description') }}</th>
                  <th class="px-2 text-center sm:px-3 py-1 border-[0.5px] border-primary-foreground/20 whitespace-nowrap">
                    {{ t('pages.school.invoice.table.priceKm') }}<br>{{ t('pages.school.invoice.table.price') }}</th>
                  <th class="px-2 text-center sm:px-3 py-1 border-[0.5px] border-primary-foreground/20 whitespace-nowrap">
                    {{ t('pages.school.invoice.table.qtyKm') }}<br>{{ t('pages.school.invoice.table.qty') }}</th>
                  <th class="px-2 text-center sm:px-3 py-1 border-[0.5px] border-primary-foreground/20 whitespace-nowrap">
                    {{ t('pages.school.invoice.table.totalKm') }}<br>{{ t('pages.school.invoice.table.total') }}</th>
                </tr>
              </thead>
              <tbody class="text-xs sm:text-sm">
                <tr v-for="(item, index) in cart" :key="item.product.id" class="border-[0.5px] border-slate-200">
                  <td class="px-2 sm:px-3 py-2 text-center border-[0.5px] border-slate-200 text-slate-400 font-medium">{{
                    String(index + 1).padStart(2, '0') }}</td>
                  <td class="px-2 sm:px-3 py-2 border-[0.5px] border-slate-200">
                    <p class="font-bold text-slate-800 wrap-break-word">{{ item.product.name }}</p>
                  </td>
                  <td class="px-2 sm:px-3 py-2 text-center border-[0.5px] border-slate-200 text-slate-600 whitespace-nowrap">{{
                    formatCurrency(item.product.outPrice, 'USD') }}</td>
                  <td class="px-2 sm:px-3 py-2 text-center border-[0.5px] border-slate-200 text-slate-600 whitespace-nowrap">{{
                    item.qty }}</td>
                  <td class="px-2 text-center sm:px-3 py-2 font-black text-slate-900 whitespace-nowrap">{{
                    formatCurrency(item.product.outPrice * item.qty, 'USD') }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="w-[133.333%] sm:w-full origin-top-left scale-[0.75] sm:scale-100">
            <div class="grid grid-cols-[1fr_250px] gap-8">
              <div class="space-y-4">
                <div class="space-y-1">
                  <h3 class="text-[10px] font-bold text-slate-500 uppercase tracking-widest">{{ t('pages.school.invoice.terms.title') }}</h3>
                  <p class="text-[11px] text-slate-600 font-bold">{{ t('pages.school.invoice.terms.km') }}</p>
                  <p class="text-[11px] text-slate-400 font-bold">{{ t('pages.school.invoice.terms.en') }}</p>
                </div>

                <div class="min-h-20 rounded-sm border border-slate-200 bg-white p-2">
                  <p class="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                    {{ t('pages.allclass.payment.note') }}
                  </p>
                  <p class="mt-1 text-[11px] font-bold text-slate-700 whitespace-pre-wrap break-words">
                    {{ displayNote }}
                  </p>
                </div>
              </div>

              <div class="space-y-2">
                <div class="flex justify-between text-xs text-slate-500 px-1">
                  <span class="font-bold">{{ t('pages.school.invoice.summary.subtotal') }}</span>
                  <span class="font-black text-slate-800">{{ formatCurrency(displaySubtotal, 'USD') }}</span>
                </div>

                <div class="flex justify-between text-xs text-slate-500 px-1">
                  <span class="font-bold">{{ t('pages.school.invoice.summary.discount') }}</span>
                  <span class="font-black text-slate-800">{{ formatCurrency(displayDiscountAmount, 'USD') }}</span>
                </div>
                <div class="flex justify-between items-center bg-slate-100 p-2 rounded-sm">
                  <span class="text-sm font-black text-slate-900">{{ t('pages.school.invoice.summary.grandTotal') }}</span>
                  <span class="text-right">
                    <span class="block text-lg font-black text-slate-900">{{ formatCurrency(displayTotal, 'USD') }}</span>
                    <span class="block text-[10px] font-bold text-slate-500">{{ formatKhr(displayTotal, invoiceExchangeRate) }}</span>
                  </span>
                </div>
                <template v-if="showOwnPaymentBreakdown">
                  <div class="flex justify-between items-center px-1 text-xs text-slate-500">
                    <span class="font-bold">{{ t('pages.allclass.payment.payAmount') }}</span>
                    <span class="text-right font-black text-slate-800">
                      <span class="block">{{ formatCurrency(displayAmountPaid, 'USD') }}</span>
                      <span class="block text-[10px] text-slate-500">{{ formatKhr(displayAmountPaid, invoiceExchangeRate) }}</span>
                    </span>
                  </div>
                  <div class="flex justify-between items-center bg-amber-50 border border-amber-200 p-2 rounded-sm">
                    <span class="text-sm font-black text-amber-800">{{ t('pages.allclass.payment.ownAmount') }}</span>
                    <span class="text-right">
                      <span class="block text-base font-black text-amber-800">{{ formatCurrency(displayAmountOwn, 'USD') }}</span>
                      <span class="block text-[10px] font-bold text-amber-700">{{ formatKhr(displayAmountOwn, invoiceExchangeRate) }}</span>
                    </span>
                  </div>
                  <p class="text-[10px] text-slate-400 px-1 font-bold">
                    {{ t('pages.allclass.payment.fxHint', { rate: invoiceExchangeRate }) }}
                  </p>
                </template>

                <USeparator class="mt-4" />

                <div class="grid grid-cols-2 gap-4 text-center">
                  <div>
                    <p class="text-[14px] font-black text-slate-900">{{ invoiceStudentName }}</p>
                    <p class="text-[10px] mt-2 text-slate-400 uppercase font-bold">{{ t('pages.school.invoice.footer.customer') }}</p>
                  </div>
                  <div>
                    <p class="text-[14px] font-black text-slate-900">{{ selectedReportInvoice?.seller || authStore.user?.name || 'Seller' }}
                    </p>
                    <p class="text-[10px] mt-2 text-slate-400 uppercase font-bold">{{ t('pages.school.invoice.footer.seller') }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="w-[133.333%] sm:w-full origin-top-left scale-[0.75] sm:scale-100">
            <div class="bg-primary text-white px-2 py-2.5 flex justify-between items-center gap-3 text-[10px] font-bold">
              <span class="font-bold text-sm flex items-center gap-1.5">
                <UIcon name="i-lucide-phone-call" class="size-3.5 shrink-0" />
                0962943472
              </span>
              <span class="font-bold text-xs flex items-center gap-1.5 text-right">
                <UIcon name="i-lucide-map-pin" class="size-3.5 shrink-0" />
                សង្កាត់កាកាបទី១ ខណ្ឌពោធិ៍សែនជ័យ រាជធានីភ្នំពេញ
              </span>
            </div>
          </div>
        </div>
      </UCard>
    </div>
  </div>
</template>
