export function formatCurrency(amount: number | string | undefined | null, currency = 'USD'): string {
  const n = Number(amount)
  if (!Number.isFinite(n)) return '—'
  try {
    return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(n)
  } catch {
    return `${currency} ${n.toFixed(2)}`
  }
}
