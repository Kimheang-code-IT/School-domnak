<script setup lang="ts">
const open = defineModel<boolean>("open", { default: false });
const qty = defineModel<number>("qty", { default: 0 });
const note = defineModel<string>("note", { default: "" });

const props = withDefaults(
  defineProps<{
    mode?: "added" | "damaged";
    productName?: string;
  }>(),
  {
    mode: "added",
    productName: "",
  }
);

const emit = defineEmits<{
  (e: "apply"): void;
}>();
</script>

<template>
  <UModal v-model:open="open" :dismissible="false" :ui="{ content: 'max-w-md' }">
    <template #header>
      <div class="flex items-center justify-between w-full">
        <div class="flex items-center gap-2">
          <h3 class="font-semibold">{{ productName }}</h3>
          <UBadge :color="mode === 'added' ? 'primary' : 'error'" variant="soft" size="sm">
            {{ mode === "added" ? $t("components.stockAdjust.titleAdd") : $t("components.stockAdjust.titleDamaged") }}
          </UBadge>
        </div>
        <UButton icon="i-lucide-x" color="neutral" variant="ghost" size="sm" @click="open = false" />
      </div>
    </template>

    <template #body>
      <div class="space-y-3">

        <UFormField
          :label="mode === 'added' ? $t('components.stockAdjust.qtyToAdd') : $t('components.stockAdjust.qtyDamaged')">
          <UInput v-model.number="qty" type="number" min="1" step="1" placeholder="0" class="w-full" />
        </UFormField>

        <UFormField :label="$t('product.note')">
          <UTextarea v-model="note" :placeholder="$t('product.note')" class="w-full" :rows="3" />
        </UFormField>
      </div>
    </template>

    <template #footer>
      <div class="flex justify-end gap-2 w-full">
        <UButton color="neutral" variant="soft" @click="open = false">
          {{ $t("actions.cancel") }}
        </UButton>
        <UButton :color="mode === 'added' ? 'primary' : 'warning'" :disabled="!qty || qty <= 0" @click="emit('apply')">
          {{ $t("actions.confirm") }}
        </UButton>
      </div>
    </template>
  </UModal>
</template>
