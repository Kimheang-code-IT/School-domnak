<script setup lang="ts">
import type { NuxtError } from '#app'

const props = defineProps<{
  error: NuxtError
}>()

const { t, locale } = useI18n()

const statusCode = computed(() => {
  const raw = props.error.statusCode ?? props.error.status
  const n = Number(raw)
  return Number.isFinite(n) && n > 0 ? n : 500
})

const displayError = computed(() => {
  const code = statusCode.value

  if (code === 404) {
    return {
      statusCode: 404,
      statusMessage: t('errors.notFound.statusMessage'),
      message: t('errors.notFound.message'),
    }
  }

  if (code === 403) {
    return {
      statusCode: 403,
      statusMessage: t('errors.forbidden.statusMessage'),
      message: t('errors.forbidden.message'),
    }
  }

  if (code >= 500) {
    return {
      statusCode: code,
      statusMessage: t('errors.server.statusMessage'),
      message: props.error.message || t('errors.server.message'),
    }
  }

  return {
    statusCode: code,
    statusMessage:
      props.error.statusMessage ||
      props.error.statusText ||
      t('errors.default.statusMessage'),
    message: props.error.message || t('errors.default.message'),
  }
})

const pageTitle = computed(() => {
  const code = statusCode.value
  if (code === 404) return t('errors.notFound.statusMessage')
  if (code === 403) return t('errors.forbidden.statusMessage')
  if (code >= 500) return t('errors.server.statusMessage')
  return t('errors.default.statusMessage')
})

useSeoMeta({
  title: pageTitle,
  description: () => displayError.value.message,
})

useHead({
  htmlAttrs: {
    lang: locale,
  },
})
</script>

<template>
  <UApp>
    <UError redirect="/" :error="displayError" />
  </UApp>
</template>
