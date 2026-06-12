<script setup lang="ts">
import { computed } from "vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  DatasetComponent,
  TransformComponent,
} from "echarts/components";
import type { EChartsOption } from "echarts";

use([
  CanvasRenderer,
  BarChart,
  GridComponent,
  TooltipComponent,
  DatasetComponent,
  TransformComponent,
]);

const props = defineProps<{
  data: {
    labels: string[];
    values: number[];
  };
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
const barColor = computed(() => getThemeTokenColor(primaryToken.value, '500', '#03386e'))

const chartOption = computed<EChartsOption>(() => {
  const source = props.data.labels.map((name, index) => [
    name,
    0,
    "Product",
    Number(props.data.values[index] || 0),
    "2026-01-01",
  ]);

  return {
    dataset: [
      {
        dimensions: ["name", "age", "profession", "score", "date"],
        source,
      },
      {
        transform: {
          type: "sort",
          config: { dimension: "score", order: "desc" },
        },
      },
    ],
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
    },
    grid: {
      top: 12,
      right: 8,
      bottom: 36,
      left: 8,
      containLabel: true,
    },
    xAxis: {
      type: "category",
      axisLabel: { interval: 0, rotate: 30, fontSize: 10 },
    },
    yAxis: {
      type: "value",
    },
    series: [
      {
        type: "bar",
        encode: { x: "name", y: "score" },
        datasetIndex: 1,
        itemStyle: {
          borderRadius: [6, 6, 0, 0],
          color: barColor.value,
        },
        barMaxWidth: 36,
      },
    ],
  };
});
</script>

<template>
  <div class="h-full w-full min-h-[200px]">
    <div
      v-if="!data.labels.length"
      class="h-full grid place-items-center text-xs text-muted-foreground"
    >
      {{ $t("common.noData") }}
    </div>
    <ClientOnly v-else>
      <VChart autoresize class="h-full w-full min-h-[220px]" :option="chartOption" />
      <template #fallback>
        <div class="h-full grid place-items-center text-xs text-muted-foreground">
          {{ $t("common.loading") }}
        </div>
      </template>
    </ClientOnly>
  </div>
</template>
