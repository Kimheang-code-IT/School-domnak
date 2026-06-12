<script setup lang="ts">
import * as locales from '@nuxt/ui/locale'

const colorMode = useColorMode()
const { locale } = useI18n()
const availablePrimaryColors = [
  'slate', 'gray', 'zinc', 'neutral', 'stone',
  'red', 'orange', 'amber', 'yellow', 'lime',
  'green', 'emerald', 'teal', 'cyan', 'sky',
  'blue', 'indigo', 'violet', 'purple', 'fuchsia',
  'pink', 'rose'
]
const availableNeutralColors = ['slate', 'gray', 'zinc', 'neutral']

const primaryColor = useCookie<string>('ui-primary-color', {
  default: () => 'blue',
  sameSite: 'lax'
})
const neutralColor = useCookie<string>('ui-neutral-color', {
  default: () => 'zinc',
  sameSite: 'lax'
})

const resolvedPrimaryColor = computed(() =>
  availablePrimaryColors.includes(primaryColor.value || '') ? (primaryColor.value as string) : 'blue'
)
const resolvedNeutralColor = computed(() =>
  availableNeutralColors.includes(neutralColor.value || '') ? (neutralColor.value as string) : 'zinc'
)

if (primaryColor.value !== resolvedPrimaryColor.value) {
  primaryColor.value = resolvedPrimaryColor.value
}
if (neutralColor.value !== resolvedNeutralColor.value) {
  neutralColor.value = resolvedNeutralColor.value
}

updateAppConfig({
  ui: {
    colors: {
      primary: resolvedPrimaryColor.value,
      neutral: resolvedNeutralColor.value
    }
  }
})

const color = computed(() => colorMode.value === 'dark' ? '#1b1718' : 'white')
const lang = computed(() => locales[locale.value as keyof typeof locales]?.code || locale.value)
const dir = computed(() => locales[locale.value as keyof typeof locales]?.dir || 'ltr')

const currentLocale = computed(() => locales[locale.value as keyof typeof locales])

useHead({
  meta: [
    { charset: 'utf-8' },
    { name: 'viewport', content: 'width=device-width, initial-scale=1' },
    { key: 'theme-color', name: 'theme-color', content: color }
  ],
  link: [
    { rel: 'icon', type: 'image/png', href: '/logo.png' },
    { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
    { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
    { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Siemreap&family=Kantumruy+Pro:ital,wght@0,100..700;1,100..700&display=swap' }
  ],
  htmlAttrs: {
    lang,
    dir
  }
})

const title = 'PDME-Revenue'
const description = 'PDME-Revenue: Customs and Excise Cambodia management system.'

useSeoMeta({
  title,
  description,
  ogTitle: title,
  ogDescription: description,
  ogImage: '/assets/images/logo.png',
  twitterImage: '/assets/images/logo.png',
  twitterCard: 'summary_large_image'
})
</script>

<template>
  <UApp :locale="currentLocale">
    <NuxtLoadingIndicator />
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </UApp>
</template>
