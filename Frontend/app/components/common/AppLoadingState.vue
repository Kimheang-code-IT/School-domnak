<script setup lang="ts">
withDefaults(
  defineProps<{
    /** Override label; defaults to common.loading. */
    label?: string
    showLabel?: boolean
    /** Optional Lucide icon (spins when name includes "loader"). */
    icon?: string
    /** Tighter padding for tables / dropdowns. */
    compact?: boolean
    /** Smaller icon (dropdowns). */
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
  <div
    class="flex items-center justify-center text-primary"
    :class="[
      inline ? 'flex-row gap-3' : 'flex-col gap-3',
      inline ? 'py-0 min-h-0' : '',
      inline ? (compact ? 'px-3 py-4' : '') : compact ? 'py-8' : 'py-14 min-h-[10rem]',
      $props.class,
    ]"
    role="status"
    aria-busy="true"
    :aria-label="showLabel ? (label || t('common.loading')) : undefined"
  >
    <UIcon
      v-if="icon"
      :name="icon"
      class="shrink-0 text-primary"
      :class="[
        small ? 'size-4' : 'size-8',
        icon.includes('loader') ? 'animate-spin' : 'animate-pulse',
      ]"
    />
    <p
      v-if="showLabel"
      class="text-sm font-medium text-muted-foreground text-center max-w-[16rem]"
    >
      {{ label || t('common.loading') }}
    </p>
  </div>
</template>
