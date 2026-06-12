<script setup lang="ts">
defineOptions({ inheritAttrs: false })

type SelectItem = string | number | Record<string, any>

const modelValue = defineModel<SelectItem[] | undefined>({ default: undefined })

const props = defineProps<{
  items: SelectItem[]
  placeholder?: string
}>()

const attrs = useAttrs()

const passthroughAttrs = computed(() => {
  const { class: _class, ...rest } = attrs
  return rest
})

const wantsFullWidth = computed(() => {
  const cls = attrs.class
  if (typeof cls === 'string') return /\b(?:w-full|min-w-full)\b/.test(cls)
  if (Array.isArray(cls)) return cls.some((entry) => String(entry).includes('w-full') || String(entry).includes('min-w-full'))
  if (cls && typeof cls === 'object') return Boolean((cls as Record<string, unknown>)['w-full'] || (cls as Record<string, unknown>)['min-w-full'])
  return false
})

function itemLabel(item: SelectItem) {
  if (typeof item === 'string' || typeof item === 'number') return String(item)
  return String((item as any).label ?? (item as any).name ?? (item as any).value ?? '')
}

function isChecked(item: SelectItem) {
  return (modelValue.value || []).some((selected) => itemLabel(selected) === itemLabel(item))
}

function toggleItem(item: SelectItem) {
  const current = [...(modelValue.value || [])]
  const idx = current.findIndex((selected) => itemLabel(selected) === itemLabel(item))
  if (idx >= 0) {
    current.splice(idx, 1)
  } else {
    current.push(item)
  }
  modelValue.value = current
}

const triggerLabel = computed(() => {
  const selected = modelValue.value || []
  if (selected.length === 0) return props.placeholder ?? $t('components.select')
  if (selected.length === 1) return itemLabel(selected[0] as SelectItem)
  return `${selected.length} selected`
})
</script>

<template>
  <UPopover :content="{ align: 'start' }">
    <UButton
      color="neutral"
      variant="subtle"
      icon="i-lucide-filter"
      trailing-icon="i-lucide-chevron-down"
      :class="[
        wantsFullWidth ? 'w-full min-w-full justify-between' : 'w-20 sm:w-40 justify-center sm:justify-between',
        'font-normal px-3',
        attrs.class,
      ]"
      size="md"
      v-bind="passthroughAttrs"
    >
      <span :class="wantsFullWidth ? 'inline truncate' : 'hidden sm:inline truncate'">{{ triggerLabel }}</span>
    </UButton>

    <template #content>
      <div class="w-72 max-h-80 overflow-auto p-2">
        <button
          v-for="(item, idx) in props.items"
          :key="idx"
          type="button"
          class="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left transition-colors"
          :class="isChecked(item) ? 'bg-primary/10' : 'hover:bg-muted'"
          @click="toggleItem(item)"
        >
          <UCheckbox
            :model-value="isChecked(item)"
            @update:model-value="() => toggleItem(item)"
          />
          <span class="text-sm">{{ itemLabel(item) }}</span>
        </button>
      </div>
    </template>
  </UPopover>
</template>
