<script setup lang="ts">
import { useAnalyticsDashboard } from '~/composables/table/useDashboard'
import { useDashboardCharts } from '~/composables/dashboard/useDashboardCharts'

const dashboard = useAnalyticsDashboard()

const {
  stats: apiStats,
  allClasses,
  filteredClasses,
  dashboardChartsReady,
  chartsRenderKey,
  categoryItems,
  courseItems,
  classItems,
  selectedCategories,
  selectedCourses,
  selectedClasses,
} = dashboard

const {
  chartsLoading,
  provinceStudentData,
  classEnrollmentNested,
  classEnrollmentBar,
} = useDashboardCharts({
  chartsReady: dashboardChartsReady,
  selectedCategories,
  selectedCourses,
  selectedClasses,
  courseItems,
  filteredClasses,
  allClasses,
})

const { t } = useI18n()
const pieInnerSeriesName = computed(() => t('pages.dashboard.pieInnerCourse'))
const pieOuterSeriesName = computed(() => t('pages.dashboard.pieOuterClass'))
const barSeriesName = computed(() => t('pages.dashboard.barSeriesStudents'))
const lineSeriesName = computed(() => t('pages.dashboard.barSeriesSeats'))
const barAxisName = computed(() => t('pages.dashboard.barAxisStudents'))
const lineAxisName = computed(() => t('pages.dashboard.barAxisSeats'))

const SECTION_HEIGHT = {
  MAP_PIE: 'clamp(480px, calc(100vh - 340px), 640px)',
  BAR: 'clamp(420px, 52vh, 560px)',
}

const summaryStats = computed(() => apiStats.value ?? [])
</script>

<template>
  <div class="flex flex-col h-full bg-background text-foreground tracking-tight">
    <div class="sticky top-0 z-30 border-b border-default/80 bg-white dark:bg-gray-900">
      <LayoutAppHeader :title="$t('pages.dashboard.title')" show-datepicker>
        <template #right>
          <div class="flex flex-wrap items-center justify-end gap-2">
            <CommonAppMutilSelect
              v-model="selectedCategories"
              :items="categoryItems"
              :placeholder="$t('pages.dashboard.filterCategory')"
            />
            <CommonAppMutilSelect
              v-model="selectedCourses"
              :items="courseItems"
              :placeholder="$t('pages.dashboard.filterCourse')"
            />
            <CommonAppMutilSelect
              v-model="selectedClasses"
              :items="classItems"
              :placeholder="$t('pages.dashboard.filterClass')"
            />
          </div>
        </template>
      </LayoutAppHeader>
    </div>

    <div class="flex-1 p-2 space-y-3">
      <UPageGrid class="grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <template v-for="(stat, idx) in summaryStats" :key="idx">
          <UCard class="shadow-sm border-accented">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-primary/10 rounded-lg">
                <UIcon :name="stat.icon" class="size-6 text-primary" />
              </div>
              <div class="min-w-0 flex-1">
                <p class="text-sm font-bold text-muted-foreground text-gray-500">
                  {{ stat.label }}
                </p>
                <h3 class="text-2xl font-black tracking-tight text-foreground truncate">
                  {{ stat.value }}
                </h3>
              </div>
            </div>
          </UCard>
        </template>
      </UPageGrid>

      <!-- Map + Pie: equal height row -->
      <div
        class="grid grid-cols-1 lg:grid-cols-12 gap-3 items-stretch"
        :style="{ minHeight: SECTION_HEIGHT.MAP_PIE }"
      >
        <UCard
          class="lg:col-span-8 shadow-sm border-accented flex flex-col overflow-hidden h-full"
          :style="{ minHeight: SECTION_HEIGHT.MAP_PIE }"
          :ui="{ body: 'p-0 flex-1 min-h-0 flex flex-col' }"
        >
          <template #header>
            <div class="flex items-center gap-2">
              <UIcon name="i-lucide-map" class="size-5 text-primary" />
              <h2 class="font-normal text-foreground">
                {{ $t('pages.dashboard.studentsByProvince') }}
              </h2>
            </div>
          </template>
          <div class="w-full relative flex-1 min-h-0">
            <CommonAppLoadingState
              v-if="chartsLoading"
              icon="i-lucide-map"
              :label="$t('components.loadingMap')"
              class="absolute inset-0"
            />
            <ChartAppChartMap
              v-else
              :key="`map-${chartsRenderKey}`"
              :data="provinceStudentData"
              :label="$t('pages.dashboard.studentCount')"
            />
          </div>
        </UCard>

        <UCard
          class="lg:col-span-4 shadow-sm border-accented relative overflow-hidden flex flex-col h-full"
          :style="{ minHeight: SECTION_HEIGHT.MAP_PIE }"
          :ui="{ body: 'p-2 flex-1 min-h-0 flex flex-col' }"
        >
          <template #header>
            <h3 class="font-normal text-sm">
              {{ $t('pages.dashboard.studentsByCourseClass') }}
            </h3>
          </template>
          <div class="w-full relative flex-1 min-h-0">
            <CommonAppLoadingState
              v-if="chartsLoading"
              compact
              icon="i-lucide-chart-pie"
              :label="$t('common.loadingChart')"
              class="absolute inset-0"
            />
            <ChartAppChartPie
              v-else
              :key="`pie-${chartsRenderKey}`"
              :data="classEnrollmentNested"
              :inner-series-name="pieInnerSeriesName"
              :outer-series-name="pieOuterSeriesName"
            />
          </div>
        </UCard>
      </div>

      <!-- Bar: full width under map + pie -->
      <UCard
        class="shadow-sm border-accented relative overflow-hidden flex flex-col"
        :style="{ minHeight: SECTION_HEIGHT.BAR }"
        :ui="{ body: 'p-2 flex-1 min-h-0 flex flex-col' }"
      >
        <template #header>
          <div class="flex items-center gap-2">
            <UIcon name="i-lucide-chart-column" class="size-5 text-primary" />
            <h3 class="font-normal text-sm">
              {{ $t('pages.dashboard.studentsByClass') }}
            </h3>
          </div>
        </template>
        <div class="w-full relative flex-1 min-h-0" :style="{ minHeight: '360px' }">
          <CommonAppLoadingState
            v-if="chartsLoading"
            compact
            icon="i-lucide-chart-column"
            :label="$t('common.loadingChart')"
            class="absolute inset-0"
          />
          <ChartAppChartBar
            v-else
            :key="`bar-${chartsRenderKey}`"
            :data="classEnrollmentBar"
            :bar-series-name="barSeriesName"
            :line-series-name="lineSeriesName"
            :bar-axis-name="barAxisName"
            :line-axis-name="lineAxisName"
          />
        </div>
      </UCard>
    </div>
  </div>
</template>
