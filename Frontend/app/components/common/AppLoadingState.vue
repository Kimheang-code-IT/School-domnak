<script setup lang="ts">
withDefaults(
  defineProps<{
    /** Override label; defaults to common.loading. */
    label?: string
    showLabel?: boolean
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
    compact: false,
    small: false,
    inline: false,
  },
)
</script>

<template>
  <div
    class="flex items-center justify-center gap-3 text-primary"
    :class="[
      inline ? 'flex-row py-0 min-h-0' : 'flex-col',
      inline ? (compact ? 'px-3 py-4' : '') : compact ? 'py-8' : 'py-14 min-h-[10rem]',
      $props.class,
    ]"
  >
    <CommonAppMatrixLoader :box-class="small ? 'size-4' : 'size-8'" :gap="small ? 2 : 3" />
    <p v-if="showLabel" class="text-sm font-medium text-muted-foreground">
      {{ label || $t('common.loading') }}
    </p>
  </div>
</template>
