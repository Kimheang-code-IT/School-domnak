/** Default school FX rate (editable in UI). */
export const DEFAULT_USD_TO_KHR = 4100

/** @deprecated Use DEFAULT_USD_TO_KHR — kept for older imports. */
export const USD_TO_KHR = DEFAULT_USD_TO_KHR

export type PaymentCurrency = 'USD' | 'KHR'

export function clampExchangeRate(rate: unknown, fallback = DEFAULT_USD_TO_KHR): number {
  const n = Number(rate)
  if (!Number.isFinite(n) || n <= 0) return fallback
  return Math.round(n)
}

export function usdToDisplay(
  usd: number,
  currency: PaymentCurrency,
  rate: number = DEFAULT_USD_TO_KHR,
): number {
  const n = Math.max(0, Number(usd) || 0)
  const fx = clampExchangeRate(rate)
  if (currency === 'KHR') return Math.round(n * fx)
  return Math.round(n * 100) / 100
}

export function displayToUsd(
  value: number,
  currency: PaymentCurrency,
  rate: number = DEFAULT_USD_TO_KHR,
): number {
  const n = Math.max(0, Number(value) || 0)
  const fx = clampExchangeRate(rate)
  if (currency === 'KHR') return Math.round((n / fx) * 100) / 100
  return Math.round(n * 100) / 100
}

export function formatKhr(usd: number, rate: number = DEFAULT_USD_TO_KHR): string {
  const khr = usdToDisplay(usd, 'KHR', rate)
  return `${khr.toLocaleString()} ៛`
}

export function formatPaymentCurrency(
  usd: number,
  currency: PaymentCurrency,
  rate: number = DEFAULT_USD_TO_KHR,
): string {
  if (currency === 'KHR') return formatKhr(usd, rate)
  return `$${usdToDisplay(usd, 'USD', rate).toFixed(2)}`
}

export function formatUsdWithKhr(usd: number, rate: number = DEFAULT_USD_TO_KHR): string {
  const amount = Math.max(0, Number(usd) || 0)
  return `$${amount.toFixed(2)} / ${formatKhr(amount, rate)}`
}
