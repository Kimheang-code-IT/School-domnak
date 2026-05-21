<script setup lang="ts">
import { ref, watch, computed, onBeforeUnmount } from 'vue'
import { parseDate } from '@internationalized/date'
import type { FormField } from '~/types'
import { normalizeCambodiaPhone } from '~/utils/format/phone'
import { resolveUploadUrl } from '~/utils/helpers/mediaUrl'
const open = defineModel<boolean>('open')
type FormRecord = Record<string, any>

const props = defineProps<{
    data?: FormRecord
    title?: string
    submitLabel?: string
    fields?: FormField[]
}>()

const emit = defineEmits<{
    (e: 'submit', data: FormRecord): void
}>()

// Internal form state
const formData = ref<FormRecord>({})
const filePreviewSources = ref<Record<string, string>>({})
const filePreviewObjectUrls = ref<Record<string, string>>({})
const lastSelectedFiles = ref<Record<string, File | null>>({})
const fileUploadRenderKeys = ref<Record<string, number>>({})
const visiblePasswordFields = ref<Record<string, boolean>>({})
const discountModes = ref<Record<string, 'percent' | 'usd'>>({})
const discountPercentValues = ref<Record<string, string>>({})

const PRICE_FIELD_KEYS = new Set([
  'fullPrice',
  'outPrice',
  'inPrice',
  'discountAmount',
  'discountPrice',
  'amount',
  'price',
  'deliveryPrice',
  'electricity',
  'water',
  'internet',
  'totalCommission',
  'facebook',
  'other',
  'finalPrice',
  'inPriceForPos',
  'printPrice',
])

function isTelField(field: FormField) {
  return field.type === 'tel' || field.key === 'phone'
}

function isPriceField(field: FormField) {
  return Boolean(field.currency) || PRICE_FIELD_KEYS.has(field.key)
}

/** Resolves render/save behavior when `type` is omitted (e.g. finance cost fields). */
function fieldRenderType(field: FormField) {
  if (isDiscountField(field) || isCommissionField(field)) return 'discount'
  if (isTelField(field)) return 'tel'
  if (field.type === 'password') return 'password'
  if (field.type === 'time') return 'time'
  if (field.type === 'number' || isPriceField(field)) return 'number'
  if (field.type === 'integer') return 'integer'
  if (field.type === 'select') return 'select'
  if (field.type === 'permission-tree') return 'permission-tree'
  if (field.type === 'textarea') return 'textarea'
  if (field.type === 'date') return 'date'
  if (field.type === 'file') return 'file'
  return field.type || 'input'
}

// Fields are now required to be passed as props for maximum flexibility across all pages
const activeFields = computed(() => props.fields || [])

function isDiscountField(field: FormField) {
  return field.discount === true || field.type === 'discount'
}

function isCommissionField(field: FormField) {
  return field.commission === true
}

function isPercentUsdToggleField(field: FormField) {
  return isDiscountField(field) || isCommissionField(field)
}

function discountBaseKey(field: FormField) {
  return field.discountBaseKey || 'fullPrice'
}

function resolveNumberTrailing(field: FormField) {
  if (field.trailing) return field.trailing
  if (isPriceField(field)) return 'USD'
  return undefined
}

function getDiscountBaseAmount(field: FormField) {
  return Math.max(0, Number(formData.value[discountBaseKey(field)] ?? 0))
}

function initDiscountFieldState(field: FormField, source: FormRecord) {
  const key = field.key
  const amount = Math.max(0, Number(source[key] ?? 0))
  const base = Math.max(0, Number(source[discountBaseKey(field)] ?? 0))
  discountModes.value[key] = 'usd'
  discountPercentValues.value[key] =
    base > 0 ? String(Math.round((amount / base) * 10000) / 100) : '0'
}

function initCommissionFieldState(field: FormField, source: FormRecord) {
  const key = field.key
  const modeRaw = String(source.teacherCommissionMode ?? 'usd').toLowerCase()
  const mode: 'percent' | 'usd' = modeRaw === 'percent' ? 'percent' : 'usd'
  discountModes.value[key] = mode
  if (mode === 'percent') {
    const pct = Number(source.teacherCommissionPercent ?? 0)
    discountPercentValues.value[key] = Number.isFinite(pct) && pct > 0 ? String(pct) : ''
    source[key] = ''
  } else {
    discountPercentValues.value[key] = ''
    const usd = Math.max(0, Number(source.teacherCommission ?? source[key] ?? 0))
    source[key] = usd > 0 ? normalizeNumberInput(String(usd)) : ''
  }
}

function setDiscountMode(field: FormField, mode: 'percent' | 'usd') {
  const key = field.key
  const prev = discountModes.value[key] || 'usd'
  if (mode === prev) return

  if (isCommissionField(field)) {
    if (mode === 'percent') {
      discountPercentValues.value[key] = discountPercentValues.value[key] || ''
    } else {
      formData.value[key] = normalizeNumberInput(String(formData.value[key] ?? ''))
    }
    discountModes.value[key] = mode
    return
  }

  const base = getDiscountBaseAmount(field)
  if (mode === 'percent') {
    const amt = Math.max(0, Number(normalizeNumberInput(formData.value[key]) || 0))
    discountPercentValues.value[key] =
      base > 0 ? String(Math.round((amt / base) * 10000) / 100) : '0'
  } else {
    const pct = Math.min(100, Math.max(0, Number(discountPercentValues.value[key] || 0)))
    const usd = base > 0 ? (base * pct) / 100 : 0
    formData.value[key] = usd > 0 ? normalizeNumberInput(String(usd)) : ''
  }
  discountModes.value[key] = mode
}

function clampDiscountUsdField(field: FormField) {
  const key = field.key
  const max = getDiscountBaseAmount(field)
  let n = Number(normalizeNumberInput(formData.value[key]))
  if (!Number.isFinite(n) || n < 0) n = 0
  if (n > max) n = max
  formData.value[key] = n > 0 ? normalizeNumberInput(String(n)) : ''
}

function onDiscountPercentInput(field: FormField, event: Event) {
  const target = event.target as HTMLInputElement | null
  let pct = Number(normalizeNumberInput(target?.value ?? ''))
  if (!Number.isFinite(pct) || pct < 0) pct = 0
  if (pct > 100) pct = 100
  discountPercentValues.value[field.key] = pct > 0 ? String(pct) : ''
}
function getCurrentImageKey(fieldKey: string) {
    return `${fieldKey}Current`
}

function resolveFirstFile(value: any): File | null {
    if (!value) return null
    if (value instanceof File) return value
    if (Array.isArray(value) && value.length > 0) {
        const first = value[0]
        if (first instanceof File) return first
        if (first?.file instanceof File) return first.file
    }
    if (value?.file instanceof File) return value.file
    return null
}

function normalizeFileUploadValue(value: any): File[] {
    const selectedFile = resolveFirstFile(value)
    return selectedFile ? [selectedFile] : []
}

function revokePreviewUrl(fieldKey: string) {
    const objectUrl = filePreviewObjectUrls.value[fieldKey]
    if (!objectUrl) return
    URL.revokeObjectURL(objectUrl)
    delete filePreviewObjectUrls.value[fieldKey]
}

function syncFilePreview(fieldKey: string) {
    const selectedFile = resolveFirstFile(formData.value[fieldKey])
    if (selectedFile) {
        if (lastSelectedFiles.value[fieldKey] !== selectedFile) {
            revokePreviewUrl(fieldKey)
            filePreviewObjectUrls.value[fieldKey] = URL.createObjectURL(selectedFile)
            lastSelectedFiles.value[fieldKey] = selectedFile
        }
        filePreviewSources.value[fieldKey] = String(filePreviewObjectUrls.value[fieldKey] ?? '')
        return
    }

    lastSelectedFiles.value[fieldKey] = null
    revokePreviewUrl(fieldKey)
    filePreviewSources.value[fieldKey] = resolveUploadUrl(
        String(formData.value[getCurrentImageKey(fieldKey)] || ''),
    )
}

function reloadImagePreview(fieldKey: string) {
    const src = String(filePreviewSources.value[fieldKey] || '')
    if (!src || src.startsWith('blob:')) return

    try {
        const url = new URL(src, window.location.origin)
        url.searchParams.set('_ts', String(Date.now()))
        filePreviewSources.value[fieldKey] = url.toString()
    } catch {
        const separator = src.includes('?') ? '&' : '?'
        filePreviewSources.value[fieldKey] = `${src}${separator}_ts=${Date.now()}`
    }
}

function resetFileUpload(fieldKey: string) {
    // Clear selected file and re-render upload input so same file can be selected again.
    formData.value[fieldKey] = []
    lastSelectedFiles.value[fieldKey] = null
    revokePreviewUrl(fieldKey)
    filePreviewSources.value[fieldKey] = String(formData.value[getCurrentImageKey(fieldKey)] || '')
    fileUploadRenderKeys.value[fieldKey] = (fileUploadRenderKeys.value[fieldKey] || 0) + 1
}

function clearImageSelection(fieldKey: string) {
    // Clear both new selection and existing image reference.
    formData.value[fieldKey] = []
    formData.value[getCurrentImageKey(fieldKey)] = ''
    lastSelectedFiles.value[fieldKey] = null
    revokePreviewUrl(fieldKey)
    filePreviewSources.value[fieldKey] = ''
    fileUploadRenderKeys.value[fieldKey] = (fileUploadRenderKeys.value[fieldKey] || 0) + 1
}

function selectDefaultForField(field: FormField) {
    const items = field.items
    if (!items || items.length === 0) return undefined
    const first = items[0] as Record<string, unknown> | string | number
    if (first && typeof first === 'object' && 'value' in first) {
        return first.value
    }
    return first as string | number | undefined
}

function initializeFormData(source?: FormRecord) {
    if (source) {
        const dataCopy: FormRecord = { ...source }
        activeFields.value.forEach(field => {
            if (field.type === 'date' && typeof dataCopy[field.key] === 'string' && dataCopy[field.key]) {
                try {
                    dataCopy[field.key] = parseDate(dataCopy[field.key])
                } catch {
                    dataCopy[field.key] = undefined
                }
            } else if (field.type === 'file') {
                dataCopy[getCurrentImageKey(field.key)] = dataCopy[field.key] || ''
                dataCopy[field.key] = []
                fileUploadRenderKeys.value[field.key] = (fileUploadRenderKeys.value[field.key] || 0) + 1
            } else if (isCommissionField(field)) {
                initCommissionFieldState(field, dataCopy)
            } else if (isDiscountField(field)) {
                initDiscountFieldState(field, dataCopy)
            } else if (isTelField(field)) {
                dataCopy[field.key] = normalizeCambodiaPhone(String(dataCopy[field.key] ?? ''))
            } else if (fieldRenderType(field) === 'number' && dataCopy[field.key] != null && dataCopy[field.key] !== '') {
                dataCopy[field.key] = normalizeNumberInput(String(dataCopy[field.key]))
            }
        })
        formData.value = dataCopy
        return
    }

    const initial: FormRecord = {}
    activeFields.value.forEach(field => {
        if (field.type === 'select' && field.items) {
            initial[field.key] = field.multiple ? [] : selectDefaultForField(field)
        } else if (field.type === 'permission-tree') {
            initial[field.key] = []
        } else if (field.type === 'date') {
            initial[field.key] = undefined
        } else if (field.type === 'file') {
            initial[field.key] = []
            initial[getCurrentImageKey(field.key)] = ''
            fileUploadRenderKeys.value[field.key] = (fileUploadRenderKeys.value[field.key] || 0) + 1
        } else {
            initial[field.key] = ''
        }
        if (isCommissionField(field)) {
            initCommissionFieldState(field, initial)
        } else if (isDiscountField(field)) {
            initDiscountFieldState(field, initial)
        }
    })
    formData.value = initial
}

function normalizeNumberInput(value: unknown) {
    const raw = String(value ?? '')
    // Allow only digits, optional leading minus, and one decimal point.
    let cleaned = raw.replace(/[^\d.-]/g, '')
    cleaned = cleaned.replace(/(?!^)-/g, '')
    const firstDot = cleaned.indexOf('.')
    if (firstDot !== -1) {
        cleaned = cleaned.slice(0, firstDot + 1) + cleaned.slice(firstDot + 1).replace(/\./g, '')
    }
    return cleaned
}

function normalizeIntegerInput(value: unknown) {
    return String(value ?? '').replace(/\D/g, '')
}

function onNumberInput(fieldKey: string, event: Event) {
    const target = event.target as HTMLInputElement | null
    formData.value[fieldKey] = normalizeNumberInput(target?.value ?? '')
}

function onIntegerInput(fieldKey: string, event: Event) {
    const target = event.target as HTMLInputElement | null
    formData.value[fieldKey] = normalizeIntegerInput(target?.value ?? '')
}

function setTelValue(fieldKey: string, value: unknown) {
    formData.value[fieldKey] = normalizeCambodiaPhone(String(value ?? ''))
}

function onTelInput(fieldKey: string, event: Event) {
    const target = event.target as HTMLInputElement | null
    const digits = normalizeCambodiaPhone(target?.value ?? '')
    formData.value[fieldKey] = digits
    if (target && target.value !== digits) target.value = digits
}

function togglePasswordVisibility(fieldKey: string) {
    visiblePasswordFields.value[fieldKey] = !visiblePasswordFields.value[fieldKey]
}

// Watch for data changes to sync form data
watch(() => props.data, (newVal) => {
    initializeFormData(newVal)
}, { immediate: true })

watch(open, (isOpen) => {
    if (!isOpen) return
    // Re-initialize every open so edit/new file upload always starts clean.
    initializeFormData(props.data)
})

watch([formData, activeFields], () => {
    activeFields.value
        .filter(field => field.type === 'file')
        .forEach(field => syncFilePreview(field.key))
    activeFields.value
        .filter(isDiscountField)
        .forEach((field) => {
            if ((discountModes.value[field.key] || 'usd') === 'usd') {
                clampDiscountUsdField(field)
            }
        })
}, { deep: true, immediate: true })

onBeforeUnmount(() => {
    Object.keys(filePreviewObjectUrls.value).forEach(revokePreviewUrl)
})

function onSave() {
    // Process form data back to plain objects (e.g. format dates back to string)
    const result = { ...formData.value }
    activeFields.value.forEach(field => {
        if (field.type === 'date' && result[field.key] && typeof result[field.key].toString === 'function') {
            result[field.key] = result[field.key].toString()
        } else if (isTelField(field)) {
            result[field.key] = normalizeCambodiaPhone(String(result[field.key] ?? ''))
        } else if (fieldRenderType(field) === 'number' || isPercentUsdToggleField(field)) {
            if (isCommissionField(field)) {
                const mode = discountModes.value[field.key] || 'usd'
                result.teacherCommissionMode = mode
                if (mode === 'percent') {
                    const pct = Math.min(
                        100,
                        Math.max(0, Number(discountPercentValues.value[field.key] || 0))
                    )
                    result.teacherCommissionPercent = pct
                    result.teacherCommission = 0
                    result[field.key] = 0
                } else {
                    const raw = normalizeNumberInput(result[field.key])
                    const amt = raw === '' ? 0 : Number(raw)
                    const usd = Math.max(0, Number.isFinite(amt) ? amt : 0)
                    result.teacherCommission = usd
                    result.teacherCommissionPercent = 0
                    result[field.key] = usd
                }
            } else if (isDiscountField(field)) {
                const base = Number(result[discountBaseKey(field)] ?? 0)
                const mode = discountModes.value[field.key] || 'usd'
                if (mode === 'percent') {
                    const pct = Math.min(
                        100,
                        Math.max(0, Number(discountPercentValues.value[field.key] || 0))
                    )
                    result[field.key] =
                        base > 0 ? Number(((base * pct) / 100).toFixed(2)) : 0
                } else {
                    const raw = normalizeNumberInput(result[field.key])
                    const amt = raw === '' ? 0 : Number(raw)
                    result[field.key] = Math.min(
                        Math.max(0, base),
                        Math.max(0, Number.isFinite(amt) ? amt : 0)
                    )
                }
            } else {
                const value = String(result[field.key] ?? '').trim()
                result[field.key] = value === '' ? 0 : Number(value)
            }
        } else if (field.type === 'integer') {
            const value = normalizeIntegerInput(result[field.key]).replace(/^0+(?=\d)/, '')
            result[field.key] = value
        } else if (field.type === 'file') {
            // Emit file fields as normalized File[] and keep `<fieldKey>Current`
            // so parent logic can distinguish unchanged image vs new selection.
            result[field.key] = normalizeFileUploadValue(result[field.key])
            result[getCurrentImageKey(field.key)] = String(result[getCurrentImageKey(field.key)] || '')
        }
    })
    emit('submit', result)
}
</script>

<template>
  <USlideover 
    v-model:open="open" 
    :title="title || $t('components.processData')"
    :dismissible="false"
    class="max-w-md"
  >
    <template #header>
      <div class="flex items-center justify-between w-full px-1">
        <h3 class="font-semibold text-highlighted">
          {{ title || $t('components.processData') }}
        </h3>
        <UButton
          icon="i-lucide-x"
          color="neutral"
          variant="ghost"
          size="sm"
          @click="open = false"
        />
      </div>
    </template>

    <template #body>
      <div class="flex flex-col space-y-3 px-1 w-full overflow-hidden">
        <template v-for="field in activeFields" :key="field.key">
            <UFormField 
                class="w-full"
            >
                <template #label>
                    <div class="flex items-center gap-1.5">
 
                        <span class="font-medium text-highlighted">{{ field.label }}</span>
                        <span v-if="field.required" class="text-error font-bold leading-none -mt-1">*</span>
                    </div>
                </template>

                <!-- TEL TYPE (Cambodia phone — digits only, e.g. 0123456789) -->
                <UInput
                    v-if="fieldRenderType(field) === 'tel'"
                    :model-value="String(formData[field.key] ?? '')"
                    type="tel"
                    :inputmode="field.inputmode || 'numeric'"
                    :autocomplete="field.autocomplete || 'tel'"
                    :maxlength="field.maxlength ?? 11"
                    :pattern="field.pattern || '[0-9]*'"
                    :placeholder="field.placeholder"
                    :disabled="field.readonly"
                    size="lg"
                    class="w-full"
                    @update:model-value="setTelValue(field.key, $event)"
                    @input="onTelInput(field.key, $event)"
                />

                <!-- INPUT TYPE -->
                <UInput 
                    v-else-if="fieldRenderType(field) === 'input' || fieldRenderType(field) === 'password' || fieldRenderType(field) === 'time'"
                    v-model="formData[field.key]"
                    :type="fieldRenderType(field) === 'password' ? (visiblePasswordFields[field.key] ? 'text' : 'password') : fieldRenderType(field) === 'time' ? 'time' : 'text'"
                    :placeholder="field.placeholder" 
                    :disabled="field.readonly"
                    size="lg" 
                    class="w-full" 
                >
                    <template v-if="fieldRenderType(field) === 'password'" #trailing>
                        <UButton
                            :icon="visiblePasswordFields[field.key] ? 'i-lucide-eye-off' : 'i-lucide-eye'"
                            color="neutral"
                            variant="ghost"
                            size="xs"
                            square
                            :aria-label="visiblePasswordFields[field.key] ? 'Hide password' : 'Show password'"
                            @click="togglePasswordVisibility(field.key)"
                        />
                    </template>
                </UInput>

                <!-- DISCOUNT TYPE (% / USD toggle) -->
                <div
                    v-else-if="isPercentUsdToggleField(field)"
                    class="flex flex-row-reverse items-center justify-between gap-2 w-full"
                >
                    <div
                        class="inline-flex w-fit rounded-md border border-default overflow-hidden"
                        role="group"
                        :aria-label="$t('pages.school.cart.discountMode')"
                    >
                        <UButton
                            type="button"
                            size="lg"
                            :variant="(discountModes[field.key] || 'usd') === 'percent' ? 'solid' : 'ghost'"
                            :color="(discountModes[field.key] || 'usd') === 'percent' ? 'primary' : 'neutral'"
                            class="rounded-none min-w-10 px-2"
                            @click="setDiscountMode(field, 'percent')"
                        >
                            %
                        </UButton>
                        <UButton
                            type="button"
                            size="lg"
                            :variant="(discountModes[field.key] || 'usd') === 'usd' ? 'solid' : 'ghost'"
                            :color="(discountModes[field.key] || 'usd') === 'usd' ? 'primary' : 'neutral'"
                            class="rounded-none min-w-16 px-2"
                            @click="setDiscountMode(field, 'usd')"
                        >
                            USD
                        </UButton>
                    </div>
                    <UInput
                        v-if="(discountModes[field.key] || 'usd') === 'percent'"
                        v-model="discountPercentValues[field.key]"
                        type="number"
                        inputmode="decimal"
                        min="0"
                        max="100"
                        :placeholder="field.placeholder"
                        :disabled="field.readonly"
                        size="lg"
                        class="w-full"
                        @input="onDiscountPercentInput(field, $event)"
                    >
                        <template #trailing>
                            <span class="text-sm text-muted">%</span>
                        </template>
                    </UInput>
                    <UInput
                        v-else
                        v-model="formData[field.key]"
                        type="number"
                        inputmode="decimal"
                        step="any"
                        :placeholder="field.placeholder"
                        :disabled="field.readonly"
                        size="lg"
                        class="w-full"
                        @input="onNumberInput(field.key, $event)"
                    >
                        <template #trailing>
                            <span class="text-sm text-muted">USD</span>
                        </template>
                    </UInput>
                </div>

                <!-- NUMBER TYPE (price fields get trailing USD via resolveNumberTrailing) -->
                <UInput
                    v-else-if="fieldRenderType(field) === 'number'"
                    v-model="formData[field.key]"
                    type="number"
                    inputmode="decimal"
                    step="any"
                    :placeholder="field.placeholder"
                    :disabled="field.readonly"
                    size="lg"
                    class="w-full"
                    @input="onNumberInput(field.key, $event)"
                >
                    <template v-if="resolveNumberTrailing(field)" #trailing>
                        <span class="text-sm text-muted">{{ resolveNumberTrailing(field) }}</span>
                    </template>
                </UInput>

                <!-- INTEGER TYPE (digits only) -->
                <UInput
                    v-else-if="field.type === 'integer'"
                    v-model="formData[field.key]"
                    type="text"
                    inputmode="numeric"
                    pattern="[0-9]*"
                    :placeholder="field.placeholder"
                    :disabled="field.readonly"
                    size="lg"
                    class="w-full"
                    @input="onIntegerInput(field.key, $event)"
                >
                    <template v-if="field.trailing" #trailing>
                        <span class="text-sm text-muted">{{ field.trailing }}</span>
                    </template>
                </UInput>

                <!-- SELECT TYPE -->
                <CommonAppMutilSelect
                    v-else-if="field.type === 'select' && field.multiple"
                    v-model="formData[field.key]"
                    :items="field.items || []"
                    :placeholder="field.placeholder || $t('components.select')"
                    :class="['w-full', field.class]"
                />

                <USelect 
                    v-else-if="field.type === 'select'"
                    v-model="formData[field.key]"
                    :items="field.items"
                    size="lg" 
                    class="w-full" 
                />

                <!-- PERMISSION TREE TYPE -->
                <CommonAppPermissionTreeSelect
                    v-else-if="field.type === 'permission-tree'"
                    v-model="formData[field.key]"
                    :pages="(field.items || []) as string[]"
                    :actions="(field.childItems || []) as string[]"
                    :catalog="field.catalog"
                />

                <!-- TEXTAREA TYPE -->
                <UTextarea 
                    v-else-if="field.type === 'textarea'"
                    v-model="formData[field.key]"
                    :placeholder="field.placeholder"
                    autoresize 
                    size="md"
                    class="w-full"
                />

                <!-- DATE TYPE -->
                <UPopover v-else-if="field.type === 'date'" class="w-full">
                    <UButton 
                        color="neutral" variant="soft" 
                        size="lg" class="w-full justify-start font-normal text-muted-foreground"
                        :label="formData[field.key] ? formData[field.key].toString() : (field.placeholder || $t('components.selectDate'))"
                    />
                    <template #content>
                        <UCalendar v-model="formData[field.key]" class="p-2" />
                    </template>
                </UPopover>

                <!-- FILE TYPE (IMAGE ONLY) -->
                <div v-else-if="field.type === 'file'" class="flex w-full justify-center">
                    <UFileUpload
                        :key="`${field.key}-${fileUploadRenderKeys[field.key] || 0}`"
                        v-model="formData[field.key]"
                        icon="i-lucide-image"
                        :label="field.placeholder || 'Drop your image here'"
                        description="SVG, PNG, JPG or GIF (max. 2MB)"
                        accept="image/*"
                        :multiple="false"
                        class="relative w-full"
                    >
                        <template #default>
                            <div
                                v-if="filePreviewSources[field.key]"
                                class="relative mx-auto flex h-48 w-full items-center justify-center overflow-hidden rounded-lg border border-default pointer-events-none"
                            >
                                <img
                                    :src="filePreviewSources[field.key]"
                                    alt="Current image"
                                    class="max-h-full max-w-full object-contain"
                                />
                                <div class="absolute inset-0 bg-black/25 flex items-end justify-center p-2">
                                    <span class="text-white text-xs font-medium">
                                        Click or drop to replace image
                                    </span>
                                </div>
                            </div>
                            <UButton
                                v-if="filePreviewSources[field.key]"
                                icon="i-lucide-x"
                                color="primary"
                                variant="solid"
                                size="xs"
                                class="absolute top-2 right-2 z-10 pointer-events-auto"
                                @click.stop.prevent="clearImageSelection(field.key)"
                            />
                        </template>
                    </UFileUpload>
                </div>
            </UFormField>
        </template>
      </div>
    </template>

    <template #footer>
      <div class="flex items-center justify-end gap-3 w-full px-1">
        <UButton :label="$t('components.cancel')" color="neutral" variant="soft" @click="open = false" />
        <UButton 
            :label="submitLabel || $t('components.saveChanges')" 
            color="primary" 
            variant="solid" 
            class="font-semibold shadow-sm px-6"
            @click="onSave" 
        />
      </div>
    </template>
  </USlideover>
</template>
