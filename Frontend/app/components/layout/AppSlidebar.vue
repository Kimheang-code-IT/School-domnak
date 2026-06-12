<script setup lang="ts">
import logo from '~/assets/images/logo.png'
import { useMenu } from '~/composables/layout/useMenu'
const { open, links } = useMenu()
</script>

<template>
  <UDashboardSidebar
    id="default"
    v-model:open="open"
    collapsible
    class="bg-elevated/25 backdrop-blur-sm dark:bg-gray-900"
    :ui="{ 
      header: 'h-auto flex-col items-stretch gap-4 px-4 shrink-0',
      footer: 'lg:border-t lg:border-default' 
    }"
  >
    <template #header="{ collapsed }">
      <NuxtLink
        to="/"
        class="flex items-center gap-3 py-2"
      >
        <img
          :src="logo"
          alt="PDME-Revenue logo"
          class="w-60 h-16 shrink-0 rounded-full object-contain"
        >
      </NuxtLink>

      <UDashboardSearchButton :collapsed="collapsed" class="bg-transparent ring-default mb-2" />
    </template>

    <template #default="{ collapsed }">
      <UNavigationMenu
        :collapsed="collapsed"
        :items="links[0]"
        orientation="vertical"
        tooltip
        popover
      />

      <UNavigationMenu
        :collapsed="collapsed"
        :items="links[1]"
        orientation="vertical"
        tooltip
      />
    </template>

    <template #footer="{ collapsed }">
      <LayoutUserMenu :collapsed="collapsed" />
    </template>
  </UDashboardSidebar>
</template>
