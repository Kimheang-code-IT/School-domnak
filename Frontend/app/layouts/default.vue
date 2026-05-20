<script setup lang="ts">
import { computed } from 'vue'
import { useMenu } from '~/composables/layout/useMenu'
import { useTelegramBotStatus } from '~/composables/useTelegramBotStatus'

const { links } = useMenu()
const { t } = useI18n()
const { busy: telegramBusy, queueLength, processing } = useTelegramBotStatus()

const telegramLoadingLabel = computed(() => {
  if (queueLength.value > 0) {
    return t('telegram.processingBanner', { count: queueLength.value })
      + (processing.value ? ` — ${t('telegram.processingNow')}` : '')
  }
  return t('telegram.loadingOverlay')
})

const searchGroups = computed(() => {
  const items: any[] = []
  
  const navLinks = links.value?.[0] || []
  navLinks.forEach((link: any) => {
    if (link.children) {
      link.children.forEach((child: any) => {
        items.push({
          id: child.to,
          label: child.label,
          icon: child.icon || link.icon,
          to: child.to
        })
      })
    } else {
      items.push({
        id: link.to,
        label: link.label,
        icon: link.icon,
        to: link.to
      })
    }
  })

  return [{
    id: 'navigation',
    label: 'Pages',
    items
  }]
})
</script>

<template>
  <UDashboardGroup unit="rem" class="h-screen overflow-hidden bg-background">
    <!-- Navigation Sidebar -->
    <LayoutAppSlidebar />
    <!-- Global search modal -->
    <UDashboardSearch :groups="searchGroups" />
    <!-- Main Content Area -->
    <main class="flex-1 flex flex-col h-full overflow-y-auto relative">
      <Transition
        enter-active-class="transition-opacity duration-200"
        leave-active-class="transition-opacity duration-200"
        enter-from-class="opacity-0"
        leave-to-class="opacity-0"
      >
        <div
          v-if="telegramBusy"
          class="fixed inset-0 z-[100] flex items-center justify-center bg-background/80 backdrop-blur-sm"
          role="status"
          aria-busy="true"
        >
          <CommonAppLoadingState
            :label="telegramLoadingLabel"
            class="!min-h-0 py-0"
          />
        </div>
      </Transition>
      <slot />
    </main>
  </UDashboardGroup>
</template>
