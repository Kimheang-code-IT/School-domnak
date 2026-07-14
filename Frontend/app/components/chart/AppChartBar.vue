<script setup lang="ts">
import { computed } from "vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart, LineChart } from "echarts/charts";
import {
  GridComponent,
  LegendComponent,
  ToolboxComponent,
  TooltipComponent,
} from "echarts/components";
import type { EChartsOption } from "echarts";

use([
  CanvasRenderer,
  BarChart,
  LineChart,
  GridComponent,
  LegendComponent,
  ToolboxComponent,
  TooltipComponent,
]);

const props = withDefaults(
  defineProps<{
    data: {
      labels: string[];
      values: number[];
      lineValues?: number[];
    };
    barSeriesName?: string;
    lineSeriesName?: string;
    barAxisName?: string;
    lineAxisName?: string;
  }>(),
  {
    barSeriesName: "Students",
    lineSeriesName: "Available seats",
    barAxisName: "Students",
    lineAxisName: "Seats",
  },
);

const appConfig = useAppConfig();

function getThemeTokenColor(token: string, shade: string, fallbackHex: string) {
  if (!import.meta.client) return fallbackHex;
  const cssVar = getComputedStyle(document.documentElement)
    .getPropertyValue(`--color-${token}-${shade}`)
    .trim();
  return cssVar || fallbackHex;
}

const primaryToken = computed(() =>
  String((appConfig.ui as any).colors?.primary || "blue"),
);
const barColor = computed(() =>
  getThemeTokenColor(primaryToken.value, "500", "#5470c6"),
);
const lineColor = computed(() => "#91cc75");

const categories = computed(() => props.data.labels);
const barData = computed(() =>
  props.data.values.map((v) => Number(v) || 0),
);
const lineData = computed(() => {
  const lines = props.data.lineValues;
  if (lines?.length) return lines.map((v) => Number(v) || 0);
  return barData.value;
});

const chartOption = computed<EChartsOption>(() => {
  const indexLabels = categories.value.map((_, i) => String(i));

  return {
    color: [barColor.value, lineColor.value],
    tooltip: {
      trigger: "axis",
      axisPointer: {
        type: "cross",
        label: { backgroundColor: "#283b56" },
      },
    },
    legend: {
      data: [props.barSeriesName, props.lineSeriesName],
      bottom: 0,
      textStyle: { fontSize: 11 },
    },
    toolbox: {
      show: true,
      right: 4,
      top: 0,
      feature: {
        dataView: { readOnly: true, title: "Data" },
        restore: { title: "Restore" },
        saveAsImage: { title: "Save", pixelRatio: 2 },
      },
      iconStyle: { borderColor: "#64748b" },
    },
    grid: {
      top: 36,
      right: 48,
      bottom: 48,
      left: 12,
      containLabel: true,
    },
    xAxis: [
      {
        type: "category",
        boundaryGap: true,
        data: categories.value,
        axisLabel: {
          interval: 0,
          rotate: categories.value.length > 6 ? 28 : 0,
          fontSize: 10,
          hideOverlap: true,
        },
        axisTick: { alignWithLabel: true },
      },
      {
        type: "category",
        boundaryGap: true,
        data: indexLabels,
        position: "top",
        axisLabel: { fontSize: 10, color: "#94a3b8" },
        axisTick: { show: false },
        axisLine: { show: false },
      },
    ],
    yAxis: [
      {
        type: "value",
        name: props.barAxisName,
        nameTextStyle: { fontSize: 10, color: barColor.value },
        position: "left",
        scale: true,
        min: 0,
        alignTicks: true,
        axisLine: {
          show: true,
          lineStyle: { color: barColor.value },
        },
        splitLine: { lineStyle: { color: "#e2e8f0" } },
        axisLabel: { fontSize: 10 },
      },
      {
        type: "value",
        name: props.lineAxisName,
        nameTextStyle: { fontSize: 10, color: lineColor.value },
        position: "right",
        scale: true,
        min: 0,
        alignTicks: true,
        axisLine: {
          show: true,
          lineStyle: { color: lineColor.value },
        },
        splitLine: { show: false },
        axisLabel: { fontSize: 10 },
      },
    ],
    series: [
      {
        name: props.barSeriesName,
        type: "bar",
        data: barData.value,
        barMaxWidth: 36,
        itemStyle: {
          color: barColor.value,
          borderRadius: [4, 4, 0, 0],
        },
      },
      {
        name: props.lineSeriesName,
        type: "line",
        yAxisIndex: 1,
        data: lineData.value,
        smooth: false,
        symbol: "circle",
        symbolSize: 8,
        lineStyle: { width: 2, color: lineColor.value },
        itemStyle: { color: lineColor.value },
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
        <CommonAppLoadingState
          compact
          icon="i-lucide-chart-column"
          :label="$t('common.loadingChart')"
          class="h-full min-h-[200px]"
        />
      </template>
    </ClientOnly>
  </div>
</template>
