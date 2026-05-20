<script setup lang="ts">
import { computed } from "vue";

type PiePoint = { name: string; value: number };

const props = defineProps<{
  data: PiePoint[];
}>();
const appConfig = useAppConfig()

function getThemeTokenColor(token: string, shade: string, fallbackHex: string) {
  if (!import.meta.client) return fallbackHex
  const cssVar = getComputedStyle(document.documentElement)
    .getPropertyValue(`--color-${token}-${shade}`)
    .trim()
  return cssVar || fallbackHex
}

const primaryToken = computed(() => String((appConfig.ui as any).colors?.primary || 'blue'))
const dynamicPalette = computed(() => [
  getThemeTokenColor(primaryToken.value, "500", "#03386e"),
  getThemeTokenColor(primaryToken.value, "400", "#5689b4"),
  getThemeTokenColor(primaryToken.value, "600", "#032f5c"),
  getThemeTokenColor(primaryToken.value, "300", "#86adce"),
  getThemeTokenColor(primaryToken.value, "700", "#02264a"),
  getThemeTokenColor(primaryToken.value, "200", "#b3cbe3"),
  getThemeTokenColor(primaryToken.value, "800", "#021d38"),
  getThemeTokenColor(primaryToken.value, "100", "#d6e3f1"),
]);

const total = computed(() =>
  props.data.reduce((sum, item) => sum + (Number(item.value) || 0), 0)
);

const conicGradient = computed(() => {
  if (!props.data.length || total.value <= 0) {
    return "conic-gradient(#cbd5e1 0deg 360deg)";
  }

  let start = 0;
  const segments = props.data.map((item, index) => {
    const end = start + (item.value / total.value) * 360;
    const color = dynamicPalette.value[index % dynamicPalette.value.length];
    const segment = `${color} ${start}deg ${end}deg`;
    start = end;
    return segment;
  });

  return `conic-gradient(${segments.join(", ")})`;
});

const legendItems = computed(() => {
  if (total.value <= 0) return [];

  return props.data.map((item) => ({
    ...item,
    percent: ((item.value / total.value) * 100).toFixed(1),
  }));
});
</script>

<template>
  <div class="h-full w-full flex gap-3 items-center">
    <div class="relative shrink-0">
      <div
        class="size-28 rounded-full"
        :style="{ background: conicGradient }"
      />
      <div
        class="absolute inset-4 rounded-full bg-white dark:bg-gray-950 grid place-items-center text-center"
      >
        <p class="text-[10px] text-muted-foreground leading-tight">Total</p>
        <p class="text-xs font-bold">{{ total.toLocaleString() }}</p>
      </div>
    </div>

    <div class="min-w-0 flex-1 overflow-y-auto h-full">
      <div v-if="!legendItems.length" class="h-full grid place-items-center text-xs text-muted-foreground">
        {{ $t("common.noData") }}
      </div>

      <div v-else class="space-y-1.5 text-[11px]">
        <div
          v-for="(item, idx) in legendItems"
          :key="item.name"
          class="flex items-center justify-between gap-2"
        >
          <div class="flex items-center gap-2 min-w-0">
            <span
              class="inline-block size-2 rounded-full shrink-0"
              :style="{
                background: dynamicPalette[idx % dynamicPalette.length],
              }"
            />
            <span class="truncate text-muted-foreground">{{ item.name }}</span>
          </div>
          <span class="font-semibold whitespace-nowrap">
            {{ item.percent }}%
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
