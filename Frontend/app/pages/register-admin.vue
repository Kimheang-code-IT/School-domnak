<script setup lang="ts">
import type { AuthFormField, FormSubmitEvent } from '~/types/nuxt-ui'
import { z } from 'zod'
import { authService } from '~/services/authService'

definePageMeta({
  layout: 'auth'
})

const { t } = useI18n()
const router = useRouter()
const toast = useToast()

useSeoMeta({
  title: () => t('pages.auth.registerAdminTitle'),
  description: () => t('pages.auth.registerAdminDesc')
})

onMounted(async () => {
  try {
    const status = await authService.setupStatus()
    if (!status.needsSetup) {
      await router.replace('/login')
    }
  } catch {
    toast.add({
      title: t('pages.auth.registerAdminFailedTitle'),
      description: t('pages.auth.setupStatusFailedDesc'),
      color: 'error'
    })
  }
})

const fields: AuthFormField[] = [{
  name: 'name',
  type: 'text',
  size: 'lg',
  label: t('pages.auth.name'),
  placeholder: t('pages.auth.namePlaceholder'),
  required: true
}, {
  name: 'email',
  type: 'email',
  size: 'lg',
  label: t('pages.auth.email'),
  placeholder: t('pages.auth.emailPlaceholder'),
  required: true
}, {
  name: 'password',
  type: 'password',
  size: 'lg',
  label: t('pages.auth.password'),
  placeholder: t('pages.auth.passwordPlaceholder'),
  required: true
}, {
  name: 'confirmPassword',
  type: 'password',
  size: 'lg',
  label: t('pages.auth.confirmPassword'),
  placeholder: t('pages.auth.confirmPasswordPlaceholder'),
  required: true
}]

const schema = z.object({
  name: z.string().min(1, t('pages.auth.nameRequired')),
  email: z.string().email(),
  password: z.string().min(6, t('pages.auth.passwordMin')),
  confirmPassword: z.string().min(6, t('pages.auth.passwordMin'))
}).refine(data => data.password === data.confirmPassword, {
  message: t('pages.auth.passwordMismatch'),
  path: ['confirmPassword']
})

type Schema = z.infer<typeof schema>

async function onSubmit(payload: FormSubmitEvent<Schema>) {
  const { name, email, password, confirmPassword } = payload.data

  try {
    const response = await authService.registerAdmin({
      name,
      email,
      password,
      confirmPassword
    })

    toast.add({
      title: t('pages.auth.registerAdminSuccessTitle'),
      description: response.message || t('pages.auth.registerAdminSuccessDesc'),
      color: 'success'
    })

    await router.push('/login')
  } catch (error) {
    const message = error && typeof error === 'object' && 'data' in error
      ? String((error as { data?: { detail?: string } }).data?.detail || t('pages.auth.registerAdminFailedDesc'))
      : t('pages.auth.registerAdminFailedDesc')

    toast.add({
      title: t('pages.auth.registerAdminFailedTitle'),
      description: message,
      color: 'error'
    })
  }
}
</script>

<template>
  <div class="flex flex-col items-center justify-center">
    <UAuthForm
      :schema="schema"
      :description="t('pages.auth.registerAdminDesc')"
      icon="i-lucide-shield-plus"
      :fields="fields"
      :submit="{ label: t('pages.auth.registerAdminBtn'), class: 'w-full h-10! text-xl font-normal' }"
      @submit="onSubmit"
    >
      <template #leading>
        <img src="/assets/images/logo.png" alt="Logo" class="h-20 w-auto mx-auto " />
      </template>

      <template #footer>
        <div class="text-center">
          <span class="font-black">© <span class="font-normal text-sm">{{ $t('pages.auth.departmentLine') }}</span></span>
        </div>
      </template>
    </UAuthForm>
  </div>
</template>
