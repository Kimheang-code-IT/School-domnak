import type { ComissionEntry, Product, ReportRow } from '~/types'
import { normalizeCambodiaProvince } from '~/utils/constants/cambodiaProvinces'

export type ChartPoint = { name: string; value: number }
export type BarChartData = { labels: string[]; values: number[] }

function studentKey(row: ReportRow): string {
  const phone = String(row.phoneCustomer || row.studentPhone || '').trim()
  if (phone) return `phone:${phone}`
  const name = String(row.studentName || row.customer || '').trim()
  if (name) return `name:${name}`
  return `invoice:${String(row.invoiceNo || '')}`
}

/** Unique students per province from report `address` (falls back to normalized province text). */
export function buildProvinceStudentCounts(rows: ReportRow[]): ChartPoint[] {
  const byProvince = new Map<string, Set<string>>()

  for (const row of rows) {
    const province = normalizeCambodiaProvince(String(row.address || '').trim())
    if (!province) continue
    let keys = byProvince.get(province)
    if (!keys) {
      keys = new Set()
      byProvince.set(province, keys)
    }
    keys.add(studentKey(row))
  }

  return Array.from(byProvince.entries())
    .map(([name, keys]) => ({ name, value: keys.size }))
    .sort((a, b) => b.value - a.value)
}

/** Commission totals grouped by teacher (seller). */
export function buildCommissionByTeacher(rows: ComissionEntry[]): ChartPoint[] {
  const totals = new Map<string, number>()

  for (const row of rows) {
    const teacher = String(row.teacherName || '').trim() || '—'
    const amount = Number(row.commission ?? 0)
    totals.set(teacher, (totals.get(teacher) || 0) + (Number.isFinite(amount) ? amount : 0))
  }

  return Array.from(totals.entries())
    .map(([name, value]) => ({ name, value: Math.round(value * 100) / 100 }))
    .filter((item) => item.value > 0)
    .sort((a, b) => b.value - a.value)
}

/** Active enrollments per class (`studentCount` on class rows). */
export function buildClassEnrollmentBar(classes: Product[], limit = 14): BarChartData {
  const items = classes
    .map((row) => ({
      name: String(row.name || row.courseName || '—').trim() || '—',
      count: Number(row.studentCount ?? row.sold ?? row.totalStock ?? 0),
    }))
    .filter((item) => item.count > 0)
    .sort((a, b) => b.count - a.count)
    .slice(0, limit)

  return {
    labels: items.map((item) => item.name),
    values: items.map((item) => item.count),
  }
}
