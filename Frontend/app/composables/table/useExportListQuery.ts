import type { ComputedRef } from 'vue'
import type { ApiQueryParams } from '~/utils/api'

export function buildExportListQuery(
  mergedServerQuery: ComputedRef<ApiQueryParams>,
  args: { startDate?: string; endDate?: string },
): Omit<ApiQueryParams, 'page' | 'limit'> {
  const q = mergedServerQuery.value
  const { page: _page, limit: _limit, ...rest } = {
    ...q,
    dateFrom: args.startDate?.slice(0, 10) ?? q.dateFrom,
    dateTo: args.endDate?.slice(0, 10) ?? q.dateTo,
  }
  return rest
}
