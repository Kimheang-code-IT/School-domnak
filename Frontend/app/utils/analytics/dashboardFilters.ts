import type { ComissionEntry, FinanceEntry, Product, ReportRow } from '~/types'

export type DashboardSelectOption = { label: string; value: string }

export function selectedFilterValues(items: DashboardSelectOption[]): string[] {
  return items.map((item) => String(item.value)).filter(Boolean)
}

export function hasDashboardFilters(
  categoryIds: string[],
  courseIds: string[],
  classIds: string[],
): boolean {
  return categoryIds.length > 0 || courseIds.length > 0 || classIds.length > 0
}

export function filterDashboardClasses(
  classes: Product[],
  opts: {
    categoryIds: string[]
    courseIds: string[]
    classIds: string[]
    courseNameById: Map<string, string>
  },
): Product[] {
  let list = classes

  if (opts.categoryIds.length > 0) {
    const allowed = new Set(opts.categoryIds)
    list = list.filter((row) => allowed.has(String(row.categoryId || '')))
  }

  if (opts.courseIds.length > 0) {
    const courseNames = new Set(
      opts.courseIds
        .map((id) => opts.courseNameById.get(id))
        .filter((name): name is string => Boolean(name)),
    )
    list = list.filter((row) => row.courseName != null && courseNames.has(row.courseName))
  }

  if (opts.classIds.length > 0) {
    const allowed = new Set(opts.classIds)
    list = list.filter((row) => allowed.has(String(row.id)))
  }

  return list
}

export function classNamesSet(classes: Product[]): Set<string> {
  return new Set(
    classes
      .map((row) => String(row.name || '').trim())
      .filter(Boolean),
  )
}

export function filterReportRowsByClassNames(
  rows: ReportRow[],
  names: Set<string> | null,
): ReportRow[] {
  if (!names || names.size === 0) return rows
  return rows.filter((row) => names.has(String(row.product || '').trim()))
}

export function filterCommissionRowsByClassNames(
  rows: ComissionEntry[],
  names: Set<string> | null,
): ComissionEntry[] {
  if (!names || names.size === 0) return rows
  return rows.filter((row) => names.has(String(row.className || '').trim()))
}

export function filterFinanceRowsByClassNames(
  rows: FinanceEntry[],
  names: Set<string> | null,
): FinanceEntry[] {
  if (!names || names.size === 0) return rows
  return rows.filter((row) => {
    const name = String(row.className || row.productName || '').trim()
    return names.has(name)
  })
}

export function productQueryParam(names: Set<string> | null): string | undefined {
  if (!names || names.size === 0) return undefined
  return Array.from(names).join(',')
}

/** Report / commission list query extras from dashboard filters. */
export function dashboardScopedQueryParams(opts: {
  courseIds: string[]
  classIds: string[]
  names: Set<string> | null
}): { product?: string; courseId?: string; classId?: string } {
  const out: { product?: string; courseId?: string; classId?: string } = {}
  const product = productQueryParam(opts.names)
  if (product) out.product = product
  if (opts.courseIds.length === 1) out.courseId = opts.courseIds[0]
  if (opts.classIds.length > 0) out.classId = opts.classIds.join(',')
  return out
}
