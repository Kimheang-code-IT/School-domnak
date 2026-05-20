import { ref } from 'vue'
import { usePosApi } from '~/utils/api'
import { buildCheckoutPayload, handleApiError, mapCartToApiLines, type PosCartItem } from '~/composables/classes/helpers'

type PosCustomerInput = {
  studentId?: number
  image?: string
  nameKm?: string
  nameEn?: string
  gender?: string
  birthdate?: string
  province?: string
  customerName: string
  customerPhone: string
  customerAddress: string
  source: string
  deliveryType: string
  deliveryPrice: number
  deliveryDate: string
  paymentMethod: string
  deliveryStatus: string
  sellerId?: number
}

export function usePosCheckout() {
  const posApi = usePosApi()
  const isFinishing = ref(false)
  const checkoutInvoiceNo = ref('')
  const lastInvoiceData = ref<any | null>(null)

  async function checkout(args: {
    cart: PosCartItem[]
    discountPercent: number
    durationMonths?: number | null
    startDate?: string
    customer: PosCustomerInput
  }) {
    if (isFinishing.value) return null
    isFinishing.value = true
    try {
      const payload = buildCheckoutPayload({
        ...args.customer,
        discountPercent: args.discountPercent,
        durationMonths: args.durationMonths,
        startDate: args.startDate,
        lines: mapCartToApiLines(args.cart)
      })
      const response = await posApi.checkout(payload)
      checkoutInvoiceNo.value = String(response?.data?.invoiceNo || '')
      lastInvoiceData.value = response?.data?.invoice || null
      return response
    } catch (error: any) {
      throw new Error(handleApiError(error, 'Checkout failed'))
    } finally {
      isFinishing.value = false
    }
  }

  return {
    isFinishing,
    checkoutInvoiceNo,
    lastInvoiceData,
    checkout
  }
}
