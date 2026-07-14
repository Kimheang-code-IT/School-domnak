<script setup lang="ts">
withDefaults(
  defineProps<{
    /** Override label; defaults to common.loading. */
    label?: string
    showLabel?: boolean
    /** Optional icon (passed to AppMatrixLoader). */
    icon?: string
    /** Tighter padding for tables / dropdowns. */
    compact?: boolean
    /** Smaller dot grid (dropdowns). */
    small?: boolean
    /** Horizontal layout (search dropdowns, inline rows). */
    inline?: boolean
    /** Extra classes on the outer wrapper. */
    class?: string
  }>(),
  {
    showLabel: true,
    icon: 'i-lucide-loader-circle',
    compact: false,
    small: false,
    inline: false,
  },
)

const { t } = useI18n()
</script>

<template>
  <CommonAppMatrixLoader
    :layout="inline ? 'inline' : 'stack'"
    :box-class="small ? 'size-4' : 'size-8'"
    :gap="small ? 2 : 3"
    :icon="icon"
    :show-icon="Boolean(icon)"
    :title="showLabel ? (label || t('common.loading')) : undefined"
    :show-title="showLabel"
    :class="[
      inline ? 'flex-row py-0 min-h-0' : 'flex-col',
      inline ? (compact ? 'px-3 py-4' : '') : compact ? 'py-8' : 'py-14 min-h-[10rem]',
      $props.class,
    ]"
  />
</template>
