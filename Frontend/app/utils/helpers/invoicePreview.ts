import type { Product } from '~/types'
import { resolveUploadUrl } from '~/utils/helpers/mediaUrl'

export type InvoicePreviewRow = {
  invoiceNo?: string
  date?: string
  startDate?: string
  endDate?: string
  registeredAt?: string
  product?: string
  courseName?: string
  timeSlot?: string
  timeIn?: string
  timeOut?: string
  classDuration?: string
  daysOfWeek?: string[]
  classImage?: string
  studentName?: string
  nameKm?: string
  nameEn?: string
  customer?: string
  phoneCustomer?: string
  seller?: string
  source?: string
  address?: string
  amount?: number
  grandTotal?: number
  qty?: number
  description?: string
  lines?: InvoicePreviewRow[]
}

/** Line items for a single invoice bundle (does not merge multiple invoices). */
export function linesForPreviewBundle(bundle: InvoicePreviewRow | null | undefined): InvoicePreviewRow[] {
  if (!bundle) return []
  const lines = Array.isArray(bundle.lines) ? bundle.lines : []
  if (lines.length > 0) return lines
  return [bundle]
}

export function flattenPreviewInvoices(items: InvoicePreviewRow[]): InvoicePreviewRow[] {
  const rows: InvoicePreviewRow[] = []
  for (const item of items) {
    rows.push(...linesForPreviewBundle(item))
  }
  return rows
}

export function normalizePreviewBundles(items: InvoicePreviewRow[]): InvoicePreviewRow[] {
  return items
    .map((item) => {
      const lines = linesForPreviewBundle(item)
      const head = { ...item, ...lines[0] }
      return { ...head, lines }
    })
    .filter((item) => String(item.invoiceNo || '').trim() || linesForPreviewBundle(item).length > 0)
}

export function previewHeaderFrom(rows: InvoicePreviewRow[]): InvoicePreviewRow | null {
  if (!rows.length) return null
  return rows[0] ?? null
}

export function previewHeaderFromBundle(bundle: InvoicePreviewRow | null | undefined): InvoicePreviewRow | null {
  const lines = linesForPreviewBundle(bundle)
  return previewHeaderFrom(lines) || bundle || null
}

export function cartLinesFromBundle(bundle: InvoicePreviewRow | null | undefined) {
  return linesForPreviewBundle(bundle).map((row, index) => previewRowToCartLine(row, index))
}

export function previewRowToCartLine(row: InvoicePreviewRow, index: number) {
  const amount = Number(row.amount ?? row.grandTotal ?? 0)
  const qty = Math.max(1, Number(row.qty ?? 1))
  const unitPrice = qty > 0 ? amount / qty : amount

  const product = {
    id: -1 * (index + 1),
    image: resolveUploadUrl(String(row.classImage || '')),
    name: String(row.product || row.description || row.courseName || 'Class'),
    category: '',
    categoryId: '',
    courseName: String(row.courseName || row.product || ''),
    inPrice: unitPrice,
    outPrice: unitPrice,
    commission: 0,
    totalStock: 0,
    inStock: 0,
    sold: 0,
    added: 0,
    damaged: 0,
    status: 'active' as const,
    createdAt: String(row.date || new Date().toISOString()),
    classDuration: row.classDuration,
    daysOfWeek: Array.isArray(row.daysOfWeek) ? row.daysOfWeek : [],
    timeIn: row.timeIn,
    timeOut: row.timeOut,
    timeSlot: row.timeSlot,
  } satisfies Product

  return { product, qty }
}
