<script setup lang="ts">
import type { AuthFormField, FormSubmitEvent } from '~/types/nuxt-ui'
import { z } from 'zod'

definePageMeta({
  layout: 'auth'
})

const { t } = useI18n()
const router = useRouter()
const toast = useToast()
const auth = useAuthStore()

const REMEMBER_ENABLED_KEY = 'login_remember_enabled'
const REMEMBER_EMAIL_KEY = 'login_remember_email'

useSeoMeta({
  title: () => t('pages.auth.loginTitle'),
  description: () => t('pages.auth.loginDesc')
})

const fields: AuthFormField[] = [{
  name: 'email',
  type: 'email',
  size: 'lg',
  label: t('pages.auth.email'),
  placeholder: t('pages.auth.emailPlaceholder'),
  defaultValue: import.meta.client ? localStorage.getItem(REMEMBER_EMAIL_KEY) || undefined : undefined,
  required: true
}, {
  name: 'password',
  label: t('pages.auth.password'),
  type: 'password',
  size: 'lg',
  placeholder: t('pages.auth.passwordPlaceholder'),
  required: true
}, {
  name: 'remember',
  label: t('pages.auth.remember'),
  type: 'checkbox'
}]

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
  remember: z.boolean().optional()
})

type Schema = {
  email: string
  password: string
  remember?: boolean
}

async function onSubmit(payload: FormSubmitEvent<Schema>) {
  const { email, password, remember } = payload.data

  try {
    await auth.login({ email, password })

    if (import.meta.client) {
      if (remember) {
        localStorage.setItem(REMEMBER_ENABLED_KEY, '1')
        localStorage.setItem(REMEMBER_EMAIL_KEY, email)
      } else {
        localStorage.removeItem(REMEMBER_ENABLED_KEY)
        localStorage.removeItem(REMEMBER_EMAIL_KEY)
      }
    }

    await router.push('/')
  } catch (error) {
    const message = error && typeof error === 'object' && 'data' in error
      ? String((error as { data?: { detail?: string } }).data?.detail || t('pages.auth.loginFailedDesc'))
      : t('pages.auth.loginFailedDesc')

    toast.add({
      title: t('pages.auth.loginFailedTitle'),
      description: message,
      color: 'error'
    })
  }
}
</script>

<template>
  <div class="flex flex-col items-center justify-center">

    <UAuthForm :schema="schema" :description="t('pages.auth.loginDesc')" icon="i-lucide-lock" :fields="fields"
      :submit="{ label: t('pages.auth.loginBtn'), class: 'w-full h-10! text-xl font-normal' }" @submit="onSubmit">
      <template #leading>
        <img src="/assets/images/logo.png" alt="Logo" class="h-20 w-auto mx-auto " />
      </template>

      <template #footer>
        <div class="text-center">
          <span class="font-black">© <span class="font-normal text-sm">{{ $t('pages.auth.departmentLine')
              }}</span></span>
        </div>
      </template>
    </UAuthForm>

  </div>
</template>
