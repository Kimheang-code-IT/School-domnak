import {
  clampExchangeRate,
  DEFAULT_USD_TO_KHR,
  type PaymentCurrency,
} from '~/utils/format/paymentCurrency'

/** Shared editable USD→KHR rate (cookie) + display currency preference. */
export function useExchangeRate() {
  const exchangeRate = useCookie<number>('usd-to-khr-rate', {
    default: () => DEFAULT_USD_TO_KHR,
    sameSite: 'lax',
  })

  const paymentCurrency = useCookie<PaymentCurrency>('payment-display-currency', {
    default: () => 'USD',
    sameSite: 'lax',
  })

  const rate = computed({
    get: () => clampExchangeRate(exchangeRate.value),
    set: (value: number) => {
      exchangeRate.value = clampExchangeRate(value)
    },
  })

  const currency = computed({
    get: () => (paymentCurrency.value === 'KHR' ? 'KHR' : 'USD'),
    set: (value: PaymentCurrency) => {
      paymentCurrency.value = value === 'KHR' ? 'KHR' : 'USD'
    },
  })

  return {
    exchangeRate: rate,
    paymentCurrency: currency,
    DEFAULT_USD_TO_KHR,
  }
}
