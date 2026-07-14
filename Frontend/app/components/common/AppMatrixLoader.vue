<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    /** Grid dimension (size × size dots). */
    size?: number
    /** Gap between dots in px. */
    gap?: number
    /** Tailwind size class for the grid box (e.g. size-4, size-8). */
    boxClass?: string
    /** Optional title under the loader (e.g. chart / wait message). */
    title?: string
    /** Optional Lucide icon above the matrix (e.g. i-lucide-chart-column). */
    icon?: string
    /** Show icon when `icon` is set (default true). */
    showIcon?: boolean
    /** Show title when `title` is set (default true). */
    showTitle?: boolean
    /** Layout: dots only, or centered stack with icon + title. */
    layout?: 'dots' | 'stack' | 'inline'
    /** Extra classes on the outer wrapper when layout is not `dots`. */
    class?: string
  }>(),
  {
    size: 4,
    gap: 2,
    boxClass: 'size-4',
    showIcon: true,
    showTitle: true,
    layout: 'dots',
  },
)

const totalDots = computed(() => props.size * props.size)

const hasChrome = computed(
  () =>
    props.layout !== 'dots' ||
    Boolean((props.showIcon && props.icon) || (props.showTitle && props.title)),
)

const patterns = [
  [[0], [1], [2], [3], [7], [11], [15], [14], [13], [12], [8], [4], [5], [6], [10], [9]],
  [[0, 4, 8, 12], [1, 5, 9, 13], [2, 6, 10, 14], [3, 7, 11, 15]],
  [[5, 6, 9, 10], [1, 4, 7, 8, 11, 14], [0, 3, 12, 15], [1, 4, 7, 8, 11, 14], [5, 6, 9, 10]],
  [[0], [1, 4], [2, 5, 8], [3, 6, 9, 12], [7, 10, 13], [11, 14], [15]],
]

const activeDots = ref<Set<number>>(new Set())
let patternIndex = 0
let stepIndex = 0

function nextStep() {
  const pattern = patterns[patternIndex]
  if (!pattern) return

  activeDots.value = new Set(pattern[stepIndex])
  stepIndex++

  if (stepIndex >= pattern.length) {
    stepIndex = 0
    patternIndex = (patternIndex + 1) % patterns.length
  }
}

let matrixInterval: ReturnType<typeof setInterval> | undefined

onMounted(() => {
  nextStep()
  matrixInterval = setInterval(nextStep, 120)
})

onUnmounted(() => {
  if (matrixInterval) clearInterval(matrixInterval)
})
</script>

<template>
  <div
    v-if="hasChrome"
    class="flex items-center justify-center text-primary"
    :class="[
      layout === 'inline' ? 'flex-row gap-3' : 'flex-col gap-3',
      $props.class,
    ]"
    role="status"
    aria-busy="true"
    :aria-label="title || undefined"
  >
    <div class="flex items-center gap-2.5 shrink-0">
      <UIcon
        v-if="showIcon && icon"
        :name="icon"
        class="size-5 shrink-0 text-primary"
        :class="icon.includes('loader') ? 'animate-spin' : 'animate-pulse'"
      />
      <div
        class="shrink-0 grid text-primary"
        :class="boxClass"
        :style="{
          gridTemplateColumns: `repeat(${size}, 1fr)`,
          gap: `${gap}px`,
        }"
      >
        <span
          v-for="i in totalDots"
          :key="i"
          class="rounded-sm bg-current transition-opacity duration-100"
          :class="activeDots.has(i - 1) ? 'opacity-100' : 'opacity-20'"
        />
      </div>
    </div>
    <p
      v-if="showTitle && title"
      class="text-sm font-medium text-muted-foreground text-center max-w-[16rem]"
    >
      {{ title }}
    </p>
  </div>

  <div
    v-else
    class="shrink-0 grid text-primary"
    :class="boxClass"
    :style="{
      gridTemplateColumns: `repeat(${size}, 1fr)`,
      gap: `${gap}px`,
    }"
    role="status"
    aria-busy="true"
  >
    <span
      v-for="i in totalDots"
      :key="i"
      class="rounded-sm bg-current transition-opacity duration-100"
      :class="activeDots.has(i - 1) ? 'opacity-100' : 'opacity-20'"
    />
  </div>
</template>
