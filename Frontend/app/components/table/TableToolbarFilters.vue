<script setup lang="ts">
import { unref, type Ref } from 'vue'
import type { FilterItem, FilterSelection } from '~/utils/filters/tableFilters'

export type TableToolbarFilterConfig = {
  key: string
  model: Ref<FilterSelection[]> | undefined
  items: FilterItem[] | Ref<FilterItem[]>
  placeholder: string
  class?: string
}

const props = defineProps<{
  filters: TableToolbarFilterConfig[]
}>()
</script>

<template>
  <CommonAppMutilSelect
    v-for="filter in props.filters"
    :key="filter.key"
    :model-value="filter.model?.value ?? []"
    :items="unref(filter.items)"
    :placeholder="filter.placeholder"
    :class="filter.class || 'w-24 sm:w-36'"
    @update:model-value="(value) => { if (filter.model) filter.model.value = (value ?? []) as FilterSelection[] }"
  />
</template>
