import { ref } from 'vue'
import { formatDate } from '~/utils/format/date'
import { resetCustomerForm } from '~/composables/classes/helpers'

export function usePosCustomer() {
  const initial = resetCustomerForm()
  const customerType = ref(initial.customerType)
  const customerName = ref(initial.customerName)
  const customerPhone = ref(initial.customerPhone)
  const customerAddress = ref(initial.customerAddress)
  const source = ref(initial.source)
  const deliveryType = ref(initial.deliveryType)
  const deliveryPrice = ref(initial.deliveryPrice)
  const deliveryDate = ref(formatDate(new Date()))
  const paymentMethod = ref(initial.paymentMethod)
  const deliveryStatus = ref(initial.deliveryStatus)
  const sellerId = ref<number | undefined>(initial.sellerId)

  function reset() {
    const next = resetCustomerForm()
    customerType.value = next.customerType
    customerName.value = next.customerName
    customerPhone.value = next.customerPhone
    customerAddress.value = next.customerAddress
    source.value = next.source
    deliveryType.value = next.deliveryType
    deliveryPrice.value = next.deliveryPrice
    deliveryDate.value = formatDate(new Date())
    paymentMethod.value = next.paymentMethod
    deliveryStatus.value = next.deliveryStatus
    sellerId.value = next.sellerId
  }

  return {
    customerType,
    customerName,
    customerPhone,
    customerAddress,
    source,
    deliveryType,
    deliveryPrice,
    deliveryDate,
    paymentMethod,
    deliveryStatus,
    sellerId,
    reset
  }
}
