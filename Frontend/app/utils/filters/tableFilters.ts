import { unref, type Ref } from 'vue'
import type { ApiQueryParams } from '~/utils/api'

export type FilterItem = { label: string; value: string }

export type FilterSelection = string | FilterItem

export function filterQueryValues(selected: FilterSelection[]): string[] {
  return selected
    .map((entry) =>
      entry && typeof entry === 'object' && 'value' in entry
        ? String(entry.value)
        : String(entry),
    )
    .filter(Boolean)
}

/** Build API query fields with comma-separated multi-select values. */
export function buildCommaSeparatedFilterQuery(
  mapping: Record<string, FilterSelection[] | Ref<FilterSelection[]>>,
): Partial<ApiQueryParams> {
  const query: Record<string, string | undefined> = {}
  for (const [param, selected] of Object.entries(mapping)) {
    const values = filterQueryValues(unref(selected))
    query[param] = values.length ? values.join(',') : undefined
  }
  return query
}

export function toFilterItems(values: readonly string[]): FilterItem[] {
  return values.map((value) => ({ label: value, value }))
}
