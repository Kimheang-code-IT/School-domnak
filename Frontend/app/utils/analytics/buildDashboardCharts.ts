import type { ComissionEntry, Product, ReportRow } from '~/types'
import { normalizeCambodiaProvince } from '~/utils/constants/cambodiaProvinces'

export type ChartPoint = { name: string; value: number }
export type NestedPieChild = { name: string; value: number }
export type NestedPieGroup = {
  name: string
  value: number
  children?: NestedPieChild[]
}
export type BarChartData = {
  labels: string[]
  /** Left-axis bars (e.g. enrolled students). */
  values: number[]
  /** Right-axis line (e.g. available seats). Optional — falls back to values. */
  lineValues?: number[]
}

function classStudentCount(row: Product): number {
  return Number(row.studentCount ?? row.sold ?? row.totalStock ?? 0)
}

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

/** Active enrollments per class (bars only for classes that have students). */
export function buildClassEnrollmentBar(classes: Product[], limit = 24): BarChartData {
  const items = classes
    .map((row) => {
      const students = classStudentCount(row)
      const seats = Number(row.inStock ?? 0)
      return {
        name: String(row.name || row.courseName || '—').trim() || '—',
        students,
        seats: Number.isFinite(seats) ? Math.max(0, seats) : 0,
      }
    })
    .filter((item) => item.students > 0)
    .sort((a, b) => b.students - a.students || b.seats - a.seats)
    .slice(0, limit)

  return {
    labels: items.map((item) => item.name),
    values: items.map((item) => item.students),
    lineValues: items.map((item) => item.seats),
  }
}

/**
 * Nested pie: inner = course totals, outer = classes under each course.
 * Uses enrollment counts from class rows.
 */
export function buildClassEnrollmentNested(
  classes: Product[],
  outerLimit = 24,
): NestedPieGroup[] {
  type Acc = { total: number; children: Map<string, number> }
  const byCourse = new Map<string, Acc>()

  for (const row of classes) {
    const count = classStudentCount(row)
    if (count <= 0) continue

    const course =
      String(row.courseName || row.category || '—').trim() || '—'
    const className = String(row.name || '—').trim() || '—'

    let group = byCourse.get(course)
    if (!group) {
      group = { total: 0, children: new Map() }
      byCourse.set(course, group)
    }
    group.total += count
    group.children.set(className, (group.children.get(className) || 0) + count)
  }

  const groups = Array.from(byCourse.entries())
    .map(([name, group]) => ({
      name,
      value: group.total,
      children: Array.from(group.children.entries())
        .map(([childName, value]) => ({ name: childName, value }))
        .sort((a, b) => b.value - a.value),
    }))
    .sort((a, b) => b.value - a.value)

  // Cap outer slices while keeping course totals consistent with visible children.
  let remaining = outerLimit
  const capped: NestedPieGroup[] = []

  for (const group of groups) {
    if (remaining <= 0) break
    const children = group.children!.slice(0, remaining)
    remaining -= children.length
    const value = children.reduce((sum, c) => sum + c.value, 0)
    if (value <= 0) continue
    capped.push({ name: group.name, value, children })
  }

  return capped
}
