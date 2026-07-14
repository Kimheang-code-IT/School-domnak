<script setup lang="ts">
import { computed } from "vue";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { PieChart } from "echarts/charts";
import { LegendComponent, TooltipComponent } from "echarts/components";
import type { EChartsOption } from "echarts";

use([CanvasRenderer, PieChart, LegendComponent, TooltipComponent]);

export type NestedPieChild = { name: string; value: number };
export type NestedPieGroup = {
  name: string;
  value: number;
  children?: NestedPieChild[];
};

const props = withDefaults(
  defineProps<{
    data: NestedPieGroup[];
    /** Series name shown on outer label cards (e.g. Class). */
    outerSeriesName?: string;
    /** Series name for the inner pie (e.g. Course). */
    innerSeriesName?: string;
  }>(),
  {
    outerSeriesName: "Class",
    innerSeriesName: "Course",
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

/** Varied palette so nested rings stay distinguishable (like ECharts nested pies). */
const palette = computed(() => [
  getThemeTokenColor(primaryToken.value, "500", "#5470c6"),
  "#91cc75",
  getThemeTokenColor(primaryToken.value, "400", "#73c0de"),
  "#fac858",
  "#ee6666",
  "#3ba272",
  "#fc8452",
  "#9a60b4",
  "#ea7ccc",
  getThemeTokenColor(primaryToken.value, "600", "#032f5c"),
]);

const hasData = computed(() =>
  props.data.some((item) => Number(item.value) > 0),
);

const innerData = computed(() =>
  props.data
    .filter((item) => Number(item.value) > 0)
    .map((item, index) => ({
      name: item.name,
      value: Number(item.value) || 0,
      itemStyle: { color: palette.value[index % palette.value.length] },
    })),
);

const outerData = computed(() => {
  const points: { name: string; value: number; itemStyle: { color: string } }[] =
    [];
  let colorIndex = 0;

  for (const group of props.data) {
    const children = group.children?.length
      ? group.children
      : [{ name: group.name, value: group.value }];

    for (const child of children) {
      const value = Number(child.value) || 0;
      if (value <= 0) continue;
      points.push({
        name: child.name,
        value,
        itemStyle: { color: palette.value[colorIndex % palette.value.length] },
      });
      colorIndex += 1;
    }
  }

  return points;
});

const legendNames = computed(() => {
  const names = new Set<string>();
  for (const item of innerData.value) names.add(item.name);
  for (const item of outerData.value) names.add(item.name);
  return Array.from(names);
});

const chartOption = computed<EChartsOption>(() => ({
  tooltip: {
    trigger: "item",
    formatter: "{a}<br/>{b}: {c} ({d}%)",
  },
  legend: {
    type: "scroll",
    bottom: 0,
    left: "center",
    itemWidth: 10,
    itemHeight: 10,
    textStyle: { fontSize: 10 },
    data: legendNames.value,
  },
  series: [
    {
      name: props.innerSeriesName,
      type: "pie",
      selectedMode: "single",
      radius: [0, "32%"],
      center: ["50%", "46%"],
      label: {
        position: "inner",
        fontSize: 11,
        color: "#fff",
        formatter: "{b}",
      },
      labelLine: { show: false },
      data: innerData.value,
    },
    {
      name: props.outerSeriesName,
      type: "pie",
      radius: ["45%", "60%"],
      center: ["50%", "46%"],
      labelLine: {
        length: 18,
        length2: 10,
      },
      label: {
        formatter:
          "{a|{a}}{abg|}\n{hr|}\n  {b|{b}: }{c}  {per|{d}%}  ",
        backgroundColor: "#F6F8FC",
        borderColor: "#8C8D8E",
        borderWidth: 1,
        borderRadius: 4,
        rich: {
          a: {
            color: "#6E7079",
            lineHeight: 20,
            align: "center",
            fontSize: 10,
          },
          hr: {
            borderColor: "#8C8D8E",
            width: "100%",
            borderWidth: 1,
            height: 0,
          },
          b: {
            color: "#4C5058",
            fontSize: 11,
            fontWeight: "bold",
            lineHeight: 28,
          },
          per: {
            color: "#fff",
            backgroundColor: "#4C5058",
            padding: [2, 3],
            borderRadius: 3,
            fontSize: 10,
          },
        },
      },
      data: outerData.value,
    },
  ],
}));
</script>

<template>
  <div class="h-full w-full min-h-[200px]">
    <div
      v-if="!hasData"
      class="h-full grid place-items-center text-xs text-muted-foreground"
    >
      {{ $t("common.noData") }}
    </div>
    <ClientOnly v-else>
      <VChart autoresize class="h-full w-full min-h-[220px]" :option="chartOption" />
      <template #fallback>
        <CommonAppLoadingState
          compact
          icon="i-lucide-chart-pie"
          :label="$t('common.loadingChart')"
          class="h-full min-h-[200px]"
        />
      </template>
    </ClientOnly>
  </div>
</template>
