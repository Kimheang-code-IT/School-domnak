import type { Product } from '~/types'

export type PosCartItem = {
  product: Product
  qty: number
}

export function mapCartToApiLines(cart: PosCartItem[]) {
  return cart.map((item) => ({
    productId: item.product.id,
    qty: item.qty
  }))
}

export function buildCheckoutPayload(input: {
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
  discountPercent: number
  paymentMethod: string
  deliveryStatus: string
  sellerId?: number
  durationMonths?: number | null
  startDate?: string
  lines: Array<{ productId: number; qty: number }>
}) {
  return {
    studentId: input.studentId,
    image: input.image,
    nameKm: input.nameKm,
    nameEn: input.nameEn,
    gender: input.gender,
    birthdate: input.birthdate || undefined,
    province: input.province,
    customerName: input.customerName,
    customerPhone: input.customerPhone,
    customerAddress: input.customerAddress,
    source: input.source,
    deliveryType: input.deliveryType,
    deliveryPrice: Number(input.deliveryPrice || 0),
    deliveryDate: input.deliveryDate,
    discountPercent: Number(input.discountPercent || 0),
    paymentMethod: input.paymentMethod || 'cash',
    deliveryStatus: input.deliveryStatus || 'pending',
    sellerId: input.sellerId,
    durationMonths: input.durationMonths,
    startDate: input.startDate || undefined,
    lines: input.lines
  }
}

export function handleApiError(error: any, fallback = 'Request failed') {
  return String(error?.data?.message || error?.message || fallback)
}

export function resetCustomerForm() {
  return {
    customerType: 'Customer',
    customerName: '',
    customerPhone: '',
    customerAddress: '',
    deliveryType: 'VET',
    deliveryPrice: 2,
    deliveryDate: new Date().toISOString(),
    paymentMethod: 'cash',
    deliveryStatus: 'pending',
    source: 'other',
    sellerId: undefined as number | undefined
  }
}
