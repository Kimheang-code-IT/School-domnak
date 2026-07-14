<script setup lang="ts">
import { authService } from '~/services/authService'
import { formatDate } from '~/utils/format/date'

const open = defineModel<boolean>('open', { default: false })

const { t } = useI18n()
const auth = useAuthStore()
const toast = useToast()

const loadingProfile = ref(false)
const savingPassword = ref(false)
const showCurrent = ref(false)
const showNew = ref(false)
const showConfirm = ref(false)

const profile = ref({
  name: '',
  role: '',
  email: '',
  telegramKey: '',
  lastLogin: '',
})

const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
})

function resetPasswordForm() {
  passwordForm.currentPassword = ''
  passwordForm.newPassword = ''
  passwordForm.confirmPassword = ''
  showCurrent.value = false
  showNew.value = false
  showConfirm.value = false
}

async function loadProfile() {
  loadingProfile.value = true
  try {
    const me = await auth.fetchMe()
    profile.value = {
      name: String(me?.name || auth.user?.name || '—'),
      role: String(me?.role || auth.user?.role || '—') || '—',
      email: String(me?.email || auth.user?.email || '—'),
      telegramKey: String(me?.telegramKey || '').trim() || '—',
      lastLogin: me?.lastLogin ? formatDate(me.lastLogin) : '—',
    }
  } catch {
    profile.value = {
      name: String(auth.user?.name || '—'),
      role: String(auth.user?.role || '—') || '—',
      email: String(auth.user?.email || '—'),
      telegramKey: String(auth.user?.telegramKey || '').trim() || '—',
      lastLogin: auth.user?.lastLogin ? formatDate(auth.user.lastLogin) : '—',
    }
  } finally {
    loadingProfile.value = false
  }
}

watch(
  () => open.value,
  (isOpen) => {
    if (isOpen) {
      resetPasswordForm()
      void loadProfile()
    }
  },
)

async function submitPasswordChange() {
  const currentPassword = passwordForm.currentPassword.trim()
  const newPassword = passwordForm.newPassword.trim()
  const confirmPassword = passwordForm.confirmPassword.trim()

  if (!currentPassword) {
    toast.add({
      title: t('settings.profile.passwordError'),
      description: t('settings.profile.currentRequired'),
      color: 'warning',
    })
    return
  }
  if (newPassword.length < 6) {
    toast.add({
      title: t('settings.profile.passwordError'),
      description: t('pages.auth.passwordMin'),
      color: 'warning',
    })
    return
  }
  if (newPassword !== confirmPassword) {
    toast.add({
      title: t('settings.profile.passwordError'),
      description: t('pages.auth.passwordMismatch'),
      color: 'warning',
    })
    return
  }
  if (newPassword === currentPassword) {
    toast.add({
      title: t('settings.profile.passwordError'),
      description: t('settings.profile.passwordSame'),
      color: 'warning',
    })
    return
  }

  savingPassword.value = true
  try {
    await authService.changePassword({ currentPassword, newPassword })
    toast.add({
      title: t('settings.profile.title'),
      description: t('settings.profile.passwordUpdated'),
      color: 'success',
    })
    resetPasswordForm()
  } catch (error: any) {
    toast.add({
      title: t('settings.profile.passwordError'),
      description: String(error?.data?.detail || error?.message || t('common.error')),
      color: 'error',
    })
  } finally {
    savingPassword.value = false
  }
}
</script>

<template>
  <UModal
    v-model:open="open"
    :dismissible="!savingPassword"
    :ui="{ content: 'w-[min(96vw,480px)] max-w-[96vw]' }"
  >
    <template #header>
      <div class="flex items-center justify-between gap-3 p-4 w-full">
        <div class="min-w-0">
          <h3 class="text-lg font-semibold text-highlighted truncate">
            {{ $t('settings.profile.title') }}
          </h3>
        </div>
        <UButton
          icon="i-lucide-x"
          color="neutral"
          variant="ghost"
          size="sm"
          :disabled="savingPassword"
          @click="open = false"
        />
      </div>
    </template>

    <template #body>
      <div class="flex flex-col gap-5 p-4">
        <CommonAppLoadingState v-if="loadingProfile" compact />

        <div v-else class="grid gap-3 rounded-lg border border-default p-3 bg-muted/20">
          <div class="flex items-start justify-between gap-3">
            <span class="text-sm text-muted-foreground shrink-0">{{ $t('pages.userManagement.columns.name') }}</span>
            <span class="text-sm font-medium text-right break-all">{{ profile.name }}</span>
          </div>
          <div class="flex items-start justify-between gap-3">
            <span class="text-sm text-muted-foreground shrink-0">{{ $t('pages.userManagement.columns.role') }}</span>
            <UBadge color="primary" variant="soft" class="font-normal">{{ profile.role }}</UBadge>
          </div>
          <div class="flex items-start justify-between gap-3">
            <span class="text-sm text-muted-foreground shrink-0">{{ $t('pages.userManagement.columns.email') }}</span>
            <span class="text-sm font-medium text-right break-all">{{ profile.email }}</span>
          </div>
          <div class="flex items-start justify-between gap-3">
            <span class="text-sm text-muted-foreground shrink-0">{{ $t('pages.userManagement.columns.telegramKey') }}</span>
            <span class="text-sm font-mono text-right break-all">{{ profile.telegramKey }}</span>
          </div>
          <div class="flex items-start justify-between gap-3">
            <span class="text-sm text-muted-foreground shrink-0">{{ $t('pages.userManagement.columns.lastLogin') }}</span>
            <span class="text-sm font-medium text-right">{{ profile.lastLogin }}</span>
          </div>
        </div>

        <USeparator />

        <div class="flex flex-col gap-3">
          <h4 class="text-sm font-semibold text-foreground">
            {{ $t('settings.profile.changePassword') }}
          </h4>

          <UFormField :label="$t('settings.profile.currentPassword')" required>
            <UInput
              v-model="passwordForm.currentPassword"
              :type="showCurrent ? 'text' : 'password'"
              autocomplete="current-password"
              class="w-full"
              :disabled="savingPassword"
            >
              <template #trailing>
                <UButton
                  :icon="showCurrent ? 'i-lucide-eye-off' : 'i-lucide-eye'"
                  color="neutral"
                  variant="ghost"
                  size="xs"
                  @click="showCurrent = !showCurrent"
                />
              </template>
            </UInput>
          </UFormField>

          <UFormField :label="$t('settings.profile.newPassword')" required>
            <UInput
              v-model="passwordForm.newPassword"
              :type="showNew ? 'text' : 'password'"
              autocomplete="new-password"
              class="w-full"
              :disabled="savingPassword"
            >
              <template #trailing>
                <UButton
                  :icon="showNew ? 'i-lucide-eye-off' : 'i-lucide-eye'"
                  color="neutral"
                  variant="ghost"
                  size="xs"
                  @click="showNew = !showNew"
                />
              </template>
            </UInput>
          </UFormField>

          <UFormField :label="$t('settings.profile.confirmPassword')" required>
            <UInput
              v-model="passwordForm.confirmPassword"
              :type="showConfirm ? 'text' : 'password'"
              autocomplete="new-password"
              class="w-full"
              :disabled="savingPassword"
            >
              <template #trailing>
                <UButton
                  :icon="showConfirm ? 'i-lucide-eye-off' : 'i-lucide-eye'"
                  color="neutral"
                  variant="ghost"
                  size="xs"
                  @click="showConfirm = !showConfirm"
                />
              </template>
            </UInput>
          </UFormField>

          <UButton
            color="primary"
            block
            :loading="savingPassword"
            icon="i-lucide-key-round"
            @click="submitPasswordChange"
          >
            {{ $t('settings.profile.updatePassword') }}
          </UButton>
        </div>
      </div>
    </template>
  </UModal>
</template>
