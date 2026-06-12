<script setup lang="ts">
import { computed } from 'vue'
const open = defineModel<boolean>('open')

interface Props {
  title?: string
  description?: string
  submitLabel?: string
  cancelLabel?: string
  type?: 'primary' | 'error' | 'warning' | 'neutral'
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  type: 'primary',
  loading: false
})

const emit = defineEmits<{
  (e: 'submit'): void
  (e: 'cancel'): void
}>()

const typeConfig = computed(() => {
  switch (props.type) {
    case 'error':
      return {
        color: 'error' as const
      }
    case 'warning':
      return {
        color: 'warning' as const
      }
    case 'primary':
      return {
        color: 'primary' as const
      }
    default:
      return {
        color: 'neutral' as const
      }
  }
})

const modalUi = {
  content: 'max-w-md w-[95vw] sm:w-full',
  header: 'border-none p-0'
} as const

const resolvedTitle = computed(() => props.title || $t('components.confirmAction'))
const resolvedDescription = computed(() => props.description || $t('components.confirmDesc'))
const resolvedCancelLabel = computed(() => props.cancelLabel || $t('components.cancel'))
const resolvedSubmitLabel = computed(() => props.submitLabel || $t('components.proceed'))

function onCancel() {
  if (props.loading) return
  open.value = false
  emit('cancel')
}

function onSubmit() {
  if (props.loading) return
  emit('submit')
}
</script>

<template>
  <UModal v-model:open="open" :dismissible="false" :ui="modalUi">
    <template #header>
      <div class="flex items-center justify-between w-full p-4">
        <div class="flex items-center gap-2">
          <h3 class="text-xl font-bold text-highlighted tracking-tight leading-tight">
            {{ resolvedTitle }}
          </h3>
        </div>
        <UButton v-if="!loading" icon="i-lucide-x" color="neutral" variant="ghost" size="md" sm:size="lg"
          @click="onCancel" />
      </div>
    </template>

    <template #body>
      <div class="-mt-6 px-4">
        <!-- Message -->
        <p class="text-sm text-muted-foreground font-medium leading-relaxed ">
          {{ resolvedDescription }}
        </p>

        <!-- Optional Custom Content Slot -->
        <div v-if="$slots.default" class="w-full">
          <slot />
        </div>
      </div>
    </template>

    <template #footer>
      <div class="flex items-center justify-end gap-3 w-full">
        <UButton :label="resolvedCancelLabel" color="neutral" variant="soft" size="lg" class="font-semibold"
          :disabled="loading" @click="onCancel" />
        <UButton :label="resolvedSubmitLabel" :color="typeConfig.color" variant="solid" size="lg" class="font-semibold"
          :loading="loading" @click="onSubmit" />
      </div>
    </template>
  </UModal>
</template>
