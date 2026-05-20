<script setup lang="ts">
interface Props {
  title: string
  showDatepicker?: boolean
}

withDefaults(defineProps<Props>(), {
  showDatepicker: false
})
</script>

<template>
  <ClientOnly>
    <UDashboardNavbar :title="title">
      <template #leading>
        <UDashboardSidebarCollapse />
      </template>

      <div class="flex-1" />

      <template #right>
        <div class="flex flex-nowrap items-center justify-end gap-2 px-2">
          <slot name="right" />
          <CommonAppDatepicker v-if="showDatepicker" class="shrink-0" />
        </div>
      </template>
    </UDashboardNavbar>
  </ClientOnly>
</template>
