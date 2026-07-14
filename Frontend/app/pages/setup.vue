<script setup lang="ts">
import { z } from 'zod'
import logo from '~/assets/images/logoapp.png'

definePageMeta({
  layout: 'auth'
})

const { t } = useI18n()
const router = useRouter()
const toast = useToast()
const auth = useAuthStore()

useSeoMeta({
  title: () => t('pages.auth.setupTitle'),
})

const state = reactive({
  name: '',
  email: '',
  password: '',
  confirmPassword: '',
})

const schema = z.object({
  name: z.string().min(1, t('pages.auth.nameRequired')),
  email: z.string().email(t('pages.auth.emailInvalid')),
  password: z.string().min(6, t('pages.auth.passwordMin')),
  confirmPassword: z.string().min(6, t('pages.auth.passwordMin')),
}).refine((data) => data.password === data.confirmPassword, {
  message: t('pages.auth.passwordMismatch'),
  path: ['confirmPassword'],
})

type Schema = z.output<typeof schema>

async function onSubmit(event: { data: Schema }) {
  const { name, email, password } = event.data

  try {
    const user = await auth.setup({ name, email, password })
    const needsSetup = useState<boolean | null>('auth-needs-setup', () => null)
    needsSetup.value = false

    toast.add({
      title: t('pages.auth.setupSuccessTitle'),
      description: t('pages.auth.setupSuccessDesc', { name: user.name }),
      color: 'success',
    })

    await router.push('/')
  } catch (error: any) {
    const message =
      error?.data?.detail ||
      error?.data?.message ||
      error?.message ||
      t('pages.auth.setupFailedDesc')
    toast.add({
      title: t('pages.auth.setupFailedTitle'),
      description: String(message),
      color: 'error',
    })
  }
}
</script>

<template>
  <div class="flex w-full flex-col items-center justify-center gap-4">
    <img :src="logo" alt="Learn Computer logo" class="mx-auto h-20 w-auto" />
    <h2 class="text-center text-lg font-semibold text-foreground">
      {{ t('pages.auth.setupTitle') }}
    </h2>

    <UForm
      :schema="schema"
      :state="state"
      class="w-full space-y-4"
      @submit="onSubmit"
    >
      <UFormField :label="t('pages.auth.name')" name="name" required>
        <UInput
          v-model="state.name"
          type="text"
          size="lg"
          class="w-full"
          autocomplete="name"
          :placeholder="t('pages.auth.namePlaceholder')"
        />
      </UFormField>

      <UFormField :label="t('pages.auth.email')" name="email" required>
        <UInput
          v-model="state.email"
          type="email"
          size="lg"
          class="w-full"
          autocomplete="email"
          :placeholder="t('pages.auth.emailPlaceholder')"
        />
      </UFormField>

      <UFormField :label="t('pages.auth.password')" name="password" required>
        <UInput
          v-model="state.password"
          type="password"
          size="lg"
          class="w-full"
          autocomplete="new-password"
          :placeholder="t('pages.auth.passwordPlaceholder')"
        />
      </UFormField>

      <UFormField :label="t('pages.auth.confirmPassword')" name="confirmPassword" required>
        <UInput
          v-model="state.confirmPassword"
          type="password"
          size="lg"
          class="w-full"
          autocomplete="new-password"
          :placeholder="t('pages.auth.confirmPasswordPlaceholder')"
        />
      </UFormField>

      <UButton
        type="submit"
        block
        size="lg"
        class="h-10! w-full text-xl font-normal"
        :loading="auth.loading"
      >
        {{ t('pages.auth.setupBtn') }}
      </UButton>
    </UForm>

    <div class="text-center">
      <span class="font-black">
        ©
        <span class="text-sm font-normal">{{ t('pages.auth.departmentLine') }}</span>
      </span>
    </div>
  </div>
</template>
