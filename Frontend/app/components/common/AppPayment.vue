<script setup lang="ts">
import type { Product } from '~/types'
import { formatCurrency } from '~/utils/format/currency'
import { ENROLLMENT_SOURCE_OPTIONS } from '~/utils/constants/enrollmentSources'

interface CartItem {
  product: Product
  qty: number
}

const { t } = useI18n()

const discountMode = defineModel<'percent' | 'usd'>('discountMode', { default: 'percent' })
const discountPercent = defineModel<number>('discountPercent', { required: true })
const discountFixedAmount = defineModel<number>('discountFixedAmount', { default: 0 })
const paymentMethod = defineModel<string>('paymentMethod', { default: 'cash' })
const source = defineModel<string>('source', { default: 'other' })

const paymentMethodItems = computed(() => [
  { label: t('pages.allclass.payment.cash'), value: 'cash' },
  { label: t('pages.allclass.payment.bankTransfer'), value: 'bank_transfer' },
  { label: t('pages.allclass.payment.abaBank'), value: 'aba' },
  { label: t('pages.allclass.payment.other'), value: 'other' }
])

const sourceItems = [...ENROLLMENT_SOURCE_OPTIONS]

const props = withDefaults(defineProps<{
  cart: CartItem[]
  itemCount: number
  subtotal: number
  discountAmount: number
  total: number
  currentStep: number
  totalSteps: number
  allowFinishWithoutCart?: boolean
  loading?: boolean
}>(), {
  allowFinishWithoutCart: false,
  loading: false
})

const emit = defineEmits<{
  (e: 'clear-cart'): void
  (e: 'remove-item', productId: number): void
  (e: 'next'): void
  (e: 'finish'): void
}>()

const isFinishConfirmOpen = ref(false)
const isLastStep = computed(() => props.currentStep === props.totalSteps - 1)

function onPrimaryAction() {
  if (isLastStep.value) {
    isFinishConfirmOpen.value = true
    return
  }
  emit('next')
}

function onConfirmFinish() {
  isFinishConfirmOpen.value = false
  emit('finish')
}

function clampDiscountFixed() {
  const max = Math.max(0, Number(props.subtotal || 0))
  const n = Math.max(0, Number(discountFixedAmount.value || 0))
  if (n > max) discountFixedAmount.value = max
  else if (n !== discountFixedAmount.value) discountFixedAmount.value = n
}

function onDiscountFixedInput(event: Event) {
  const target = event.target as HTMLInputElement | null
  const raw = Number(target?.value ?? 0)
  discountFixedAmount.value = Number.isFinite(raw) ? raw : 0
  clampDiscountFixed()
}

watch(() => props.subtotal, () => {
  if (discountMode.value === 'usd') clampDiscountFixed()
})
</script>

<template>
  <div class="w-full flex flex-col bg-card overflow-hidden">
    <div class="flex items-center justify-between px-4 py-3.5 border-b border-default shrink-0">
      <div class="flex items-center gap-2">
        <UIcon name="i-lucide-shopping-cart" class="size-4 text-primary" />
        <span class="font-semibold text-base text-foreground">{{ $t('pages.school.cart.title') }}</span>
      </div>
      <div class="flex items-center gap-1.5">
        <UButton
          v-if="cart.length > 0"
          size="xs"
          color="error"
          variant="outline"
          icon="i-lucide-trash-2"
          @click="emit('clear-cart')"
        >
          {{ $t('pages.school.cart.clearAll') }}
        </UButton>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto min-h-0">
      <div
        v-if="cart.length === 0"
        class="flex flex-col items-center justify-center h-full gap-3 text-muted-foreground px-4"
      >
        <UIcon name="i-lucide-shopping-cart" class="size-10 opacity-20" />
        <p class="text-sm text-center">{{ $t('pages.school.cart.empty') }}</p>
      </div>

      <div v-else class="flex flex-col">
        <div
          v-for="item in cart"
          :key="item.product.id"
          class="flex items-start gap-3 px-4 py-3 hover:bg-muted/30 transition-colors border-b border-default"
        >
          <div class="flex-1 min-w-0">
            <p class="text-xs font-medium text-foreground leading-tight line-clamp-1">
              {{ item.product.name }}
            </p>
          </div>

          <div class="flex items-center gap-2 shrink-0">
            <p class="text-sm font-semibold text-foreground tabular-nums">
              {{ formatCurrency(item.product.outPrice * item.qty, 'USD') }}
            </p>
            <UButton
              size="xs"
              color="error"
              variant="ghost"
              icon="i-lucide-trash-2"
              class="size-6 p-0 min-w-0 items-center justify-center"
              @click="emit('remove-item', item.product.id)"
            />
          </div>
        </div>
      </div>
    </div>

    <div class="border-t border-default px-4 py-3 flex flex-col gap-2.5 bg-card shrink-0 mt-auto sticky bottom-0 z-10">
      <div class="flex justify-between text-sm text-muted-foreground">
        <span>{{ $t('pages.school.cart.items') }}</span>
        <UBadge v-if="itemCount > 0" color="primary" variant="solid" size="sm">
          {{ itemCount }}
        </UBadge>
      </div>
      <div class="flex justify-between text-sm text-muted-foreground">
        <span>{{ $t('pages.school.cart.subtotal') }}</span>
        <span class="font-medium text-foreground">{{ formatCurrency(subtotal, 'USD') }}</span>
      </div>

      <div class="flex items-center justify-between gap-2">
        <div class="flex items-center gap-2 shrink-0 min-w-0">
          <span class="text-sm text-muted-foreground">{{ $t('pages.school.cart.discount') }}</span>
          <div
            class="inline-flex rounded-md border border-default overflow-hidden shrink-0"
            role="group"
            :aria-label="$t('pages.school.cart.discountMode')"
          >
            <UButton
              type="button"
              size="xs"
              :variant="discountMode === 'percent' ? 'solid' : 'ghost'"
              :color="discountMode === 'percent' ? 'primary' : 'neutral'"
              class="rounded-none min-w-9 px-2"
              @click="discountMode = 'percent'"
            >
              %
            </UButton>
            <UButton
              type="button"
              size="xs"
              :variant="discountMode === 'usd' ? 'solid' : 'ghost'"
              :color="discountMode === 'usd' ? 'primary' : 'neutral'"
              class="rounded-none min-w-9 px-2"
              @click="discountMode = 'usd'"
            >
              USD
            </UButton>
          </div>
        </div>
        <div class="flex items-center gap-2 min-w-0">
          <UInput
            v-if="discountMode === 'percent'"
            v-model.number="discountPercent"
            type="number"
            size="xs"
            min="0"
            max="100"
            class="w-16 text-center shrink-0"
          />
          <UInput
            v-else
            v-model.number="discountFixedAmount"
            type="number"
            size="xs"
            min="0"
            :max="subtotal"
            step="0.01"
            class="w-20 text-center shrink-0"
            @input="onDiscountFixedInput"
          />
          <span class="text-sm font-medium text-red-500 w-16 text-right shrink-0 tabular-nums">
            -{{ formatCurrency(discountAmount, 'USD') }}
          </span>
        </div>
      </div>

      <div class="flex items-center justify-between gap-2">
        <span class="text-sm text-muted-foreground shrink-0">{{ $t('pages.allclass.payment.method') }}</span>
        <div class="flex min-w-0 flex-1 items-center justify-end gap-2">
          <USelectMenu
            v-model="paymentMethod"
            :items="paymentMethodItems"
            value-key="value"
            label-key="label"
            :placeholder="$t('pages.allclass.payment.method')"
            size="sm"
            class="max-w-44 w-full shrink-0"
          />
        </div>
      </div>

      <div class="flex items-center justify-between gap-2">
        <span class="text-sm text-muted-foreground shrink-0">{{ $t('pages.comission.columns.source') }}</span>
        <div class="flex min-w-0 flex-1 items-center justify-end gap-2">
          <USelect
            v-model="source as any"
            :items="sourceItems"
            size="sm"
            class="max-w-44 w-full shrink-0"
          />
        </div>
      </div>

      <USeparator />

      <div class="flex justify-between items-center">
        <span class="text-base font-bold text-foreground">{{ $t('pages.school.cart.total') }}</span>
        <span class="text-lg font-bold text-primary">{{ formatCurrency(total, 'USD') }}</span>
      </div>

      <UButton
        block
        size="md"
        :icon="isLastStep ? 'i-lucide-check' : 'i-lucide-corner-down-right'"
        color="primary"
        variant="solid"
        :disabled="(cart.length === 0 && !props.allowFinishWithoutCart) || props.loading"
        :loading="props.loading"
        class="font-semibold"
        @click="onPrimaryAction"
      >
        {{ isLastStep ? $t('pages.school.cart.finish') : $t('pages.school.cart.next') }}
      </UButton>
    </div>

    <CommonAppModalCURD
      v-model:open="isFinishConfirmOpen"
      :title="$t('pages.school.cart.confirmFinishTitle')"
      :description="$t('pages.school.cart.confirmFinishDescription')"
      :submit-label="$t('common.confirm')"
      :cancel-label="$t('components.cancel')"
      :loading="props.loading"
      @submit="onConfirmFinish"
    />
  </div>
</template>
