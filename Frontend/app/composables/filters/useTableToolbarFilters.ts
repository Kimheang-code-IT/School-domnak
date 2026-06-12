import { computed, type ComputedRef, type Ref } from 'vue'
import type { TableToolbarFilterConfig } from '~/components/table/TableToolbarFilters.vue'
import type { FilterItem, FilterSelection } from '~/utils/filters/tableFilters'

type ToolbarFilterDef = {
  key: string
  model: Ref<FilterSelection[]> | undefined
  items: FilterItem[] | Ref<FilterItem[]> | ComputedRef<FilterItem[]>
  placeholder: string
  class?: string
}

export function useTableToolbarFilters(defs: ComputedRef<ToolbarFilterDef[]>) {
  return computed<TableToolbarFilterConfig[]>(() =>
    defs.value.map((def) => ({
      key: def.key,
      model: def.model,
      items: def.items,
      placeholder: def.placeholder,
      class: def.class,
    })),
  )
}
