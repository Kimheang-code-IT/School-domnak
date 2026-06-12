<script setup lang="ts">
import { ref } from 'vue'

const modelValue = defineModel<string[] | undefined>({ default: undefined })

const props = withDefaults(defineProps<{
  pages: string[]
  actions: string[]
}>(), {
  pages: () => [],
  actions: () => ['view', 'edit', 'update']
})

const expandedPages = ref<string[]>([])

function getKey(page: string, action: string) {
  return `${page}:${action}`
}

function hasAction(page: string, action: string) {
  return (modelValue.value || []).includes(getKey(page, action))
}

function hasAnyAction(page: string) {
  return props.actions.some((action) => hasAction(page, action))
}

function togglePage(page: string) {
  const selected = new Set(modelValue.value || [])
  if (hasAnyAction(page)) {
    props.actions.forEach((action) => selected.delete(getKey(page, action)))
    modelValue.value = [...selected]
    expandedPages.value = expandedPages.value.filter((p) => p !== page)
    return
  }

  // Default first action when page is selected.
  selected.add(getKey(page, props.actions[0] || 'view'))
  modelValue.value = [...selected]
  if (!expandedPages.value.includes(page)) {
    expandedPages.value.push(page)
  }
}

function toggleAction(page: string, action: string) {
  const key = getKey(page, action)
  const selected = new Set(modelValue.value || [])
  if (selected.has(key)) {
    selected.delete(key)
  } else {
    selected.add(key)
  }
  modelValue.value = [...selected]
}

function toggleExpand(page: string) {
  if (expandedPages.value.includes(page)) {
    expandedPages.value = expandedPages.value.filter((p) => p !== page)
  } else {
    expandedPages.value.push(page)
  }
}

function prettyName(value: string) {
  return value
    .replaceAll(':', ' / ')
    .replaceAll('-', ' ')
    .replaceAll('_', ' ')
}
</script>

<template>
  <div class="space-y-2 rounded-lg border border-default p-2">
    <div
      v-for="page in pages"
      :key="page"
      class="rounded-md border border-default"
    >
      <div class="flex items-center justify-between px-2 py-1.5">
        <label class="flex items-center gap-2 cursor-pointer">
          <UCheckbox :model-value="hasAnyAction(page)" @update:model-value="togglePage(page)" />
          <span class="text-sm font-medium">{{ prettyName(page) }}</span>
        </label>
        <UButton
          icon="i-lucide-chevron-down"
          color="neutral"
          variant="ghost"
          size="xs"
          :class="{ 'rotate-180': expandedPages.includes(page) }"
          @click="toggleExpand(page)"
        />
      </div>

      <div v-if="expandedPages.includes(page) || hasAnyAction(page)" class="px-2 pb-2">
        <div class="grid grid-cols-1 gap-1 pl-6">
          <label
            v-for="action in actions"
            :key="`${page}:${action}`"
            class="flex items-center gap-2 cursor-pointer rounded px-2 py-1"
            :class="hasAction(page, action) ? 'bg-primary/10' : 'hover:bg-muted/60'"
          >
            <UCheckbox
              :model-value="hasAction(page, action)"
              @update:model-value="toggleAction(page, action)"
            />
            <span class="text-sm capitalize">{{ action }}</span>
          </label>
        </div>
      </div>
    </div>
  </div>
</template>
