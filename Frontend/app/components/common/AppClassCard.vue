<script setup lang="ts">
import type { DropdownMenuItem } from "@nuxt/ui";
import type { Product } from "~/types";
import { formatCurrency } from "~/utils/format/currency";
import { formatClassDuration, parseDurationMonthsDecimal } from "~/utils/format/duration";
import { resolveUploadUrl } from "~/utils/helpers/mediaUrl";

/** Same row shape as product grid / API; named for class-card UI semantics. */
const props = withDefaults(
  defineProps<{
    classItem: Product;
    inCart?: boolean;
    cartQty?: number;
    /** `school`: class selected for enrollment (checkbox checked). */
    selectedForEnrollment?: boolean;
    /** `school` hides POS cart and stock badge; pricing is still shown. */
    variant?: "default" | "school";
  }>(),
  {
    variant: "default",
    selectedForEnrollment: false,
  },
);

const isSchool = computed(() => props.variant === "school");

const emit = defineEmits<{
  (e: "add", classItem: Product): void;
  (e: "view", classItem: Product): void;
  (e: "edit", classItem: Product): void;
  (e: "delete", classItem: Product): void;
  /** School flow: checkbox to choose class before header Next adds to enrollment cart */
  (
    e: "toggle-enrollment-select",
    classItem: Product,
    selected: boolean,
  ): void;
}>();

const { t, te } = useI18n();

const CATEGORY_BADGE_COLORS = [
  "primary",
  "secondary",
  "success",
  "info",
  "warning",
  "error",
  "neutral",
] as const;

function categoryBadgeColor(categoryId: string) {
  const id = categoryId?.trim() || "—";
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
  return CATEGORY_BADGE_COLORS[h % CATEGORY_BADGE_COLORS.length];
}

function pickStudentTotal(classItem: Product) {
  const row = classItem as Product & {
    totalStudent?: number;
    totalStudents?: number;
    studentCount?: number;
    studentsCount?: number;
    enrollmentCount?: number;
    enrolledStudents?: number;
  };
  const value =
    row.totalStudents ??
    row.totalStudent ??
    row.studentCount ??
    row.studentsCount ??
    row.enrollmentCount ??
    row.enrolledStudents ??
    row.sold;
  const n = Number(value ?? 0);
  return Number.isFinite(n) && n > 0 ? n : 0;
}

const classStudentTotal = computed(() => pickStudentTotal(props.classItem));

const classImageSrc = computed(() => resolveUploadUrl(props.classItem.image));

function pickFirstText(values: Array<unknown>) {
  for (const value of values) {
    const text = String(value ?? "").trim();
    if (text) return text;
  }
  return "";
}

const classLevel = computed(() =>
  pickFirstText([
    props.classItem.levelNameEn,
    props.classItem.level,
    props.classItem.classLevel,
    props.classItem.courseLevel,
  ]),
);

const classDurationLabel = computed(() => {
  const raw = pickFirstText([props.classItem.classDuration]);
  if (!raw) return "";
  const formatted = formatClassDuration(raw, t, te);
  if (formatted) return formatted;
  const months = parseDurationMonthsDecimal(raw);
  return months != null ? String(months) : raw;
});

const rowClass = "flex flex-row gap-2 items-start sm:gap-3";
const labelClass =
  "shrink-0 pt-0.5 w-[5.5rem] text-[11px] font-medium tracking-wide text-muted sm:w-[7rem] sm:text-xs";
const valueClass = "min-w-0 flex-1 text-xs leading-snug text-foreground sm:text-sm";

const cardUi = {
  body: "p-0 overflow-hidden rounded-none",
  root: [
    "rounded-none overflow-hidden border border-default/70 bg-card",
    "shadow-sm transition-all duration-300 ease-out",
    "hover:border-primary/30 hover:shadow-lg hover:-translate-y-1",
    "group",
  ].join(" "),
};

const heroImageClass =
  "absolute inset-0 h-full w-full object-contain object-center transition-transform duration-500 ease-out group-hover:scale-[1.03]";

/** Derive shift label from time_in hour: Morning <12, Afternoon 12-17, Evening >=17 */
const computedShift = computed(() => {
  const raw = props.classItem.timeIn;
  if (!raw) return null;
  const [hourStr] = raw.split(':');
  const hour = parseInt(hourStr ?? '0', 10);
  if (isNaN(hour)) return null;
  if (hour < 12) return t('pages.courses.shift.morning');
  if (hour < 17) return t('pages.courses.shift.afternoon');
  return t('pages.courses.shift.evening');
});

function weekdayLabel(day: string) {
  const normalized = day.trim().toLowerCase();
  const key = `pages.allclass.weekdays.${normalized}`;
  return te(key) ? t(key) : day;
}

const classDaysOfWeek = computed(() => {
  const days = props.classItem.daysOfWeek;
  if (!Array.isArray(days)) return [];
  return days
    .map((day) => String(day || "").trim())
    .filter(Boolean);
});

const showFullPriceRow = computed(() => {
  const c = props.classItem;
  return c.fullPrice != null && c.fullPrice !== c.outPrice;
});

const discountLine = computed(() => {
  const c = props.classItem;
  const parts: string[] = [];
  if (c.discountPercent != null && c.discountPercent > 0) {
    parts.push(`${c.discountPercent}%`);
  }
  if (c.discountAmount != null && c.discountAmount > 0) {
    parts.push(formatCurrency(c.discountAmount, "USD"));
  }
  if (parts.length === 0 && c.fullPrice != null && c.fullPrice > c.outPrice) {
    parts.push(formatCurrency(c.fullPrice - c.outPrice, "USD"));
  }
  return parts.join(" · ");
});

const showDiscountRow = computed(() => discountLine.value.length > 0);

const fullPriceClass = computed(() => {
  const c = props.classItem;
  if (c.fullPrice == null) return "";
  return c.fullPrice > c.outPrice
    ? "line-through text-muted"
    : "text-foreground";
});

const showPricingSeparator = computed(
  () => showFullPriceRow.value || showDiscountRow.value,
);

const hasScheduleBadges = computed(
  () =>
    !!(
      computedShift.value ||
      props.classItem.timeSlot ||
      classDaysOfWeek.value.length > 0
    ),
);

/** Dashed line above pricing when there are discount/list rows or schedule chips above. */
const showSeparatorAbovePricing = computed(
  () => showPricingSeparator.value || hasScheduleBadges.value,
);

const classActionItems = computed<DropdownMenuItem[][]>(() => [
  [
    {
      label: t("pages.school.classCard.view"),
      icon: "i-lucide-eye",
      onSelect: () => emit("view", props.classItem),
    },
    {
      label: t("actions.edit"),
      icon: "i-lucide-pencil",
      onSelect: () => emit("edit", props.classItem),
    },
    {
      label: t("actions.delete"),
      icon: "i-lucide-trash",
      color: "error" as const,
      onSelect: () => emit("delete", props.classItem),
    },
  ],
]);
</script>

<template>
  <UCard
    :ui="cardUi"
    :class="[
      'rounded-none',
      !isSchool && inCart
        ? 'ring-2 ring-primary/45 shadow-md shadow-primary/10 border-primary/35'
        : '',
      isSchool && props.selectedForEnrollment
        ? 'ring-2 ring-primary/45 shadow-md shadow-primary/10 border-primary/35'
        : '',
    ]"
  >
    <div class="flex flex-col sm:-m-6 rounded-none">
      <div class="relative h-32 w-full shrink-0 bg-muted overflow-hidden sm:h-44">
        <img
          v-if="classImageSrc"
          :src="classImageSrc"
          :alt="classItem.name"
          loading="lazy"
          :class="heroImageClass"
        />
        <div
          v-else
          class="absolute inset-0 flex items-center justify-center text-muted-foreground"
          aria-hidden="true"
        >
          <UIcon name="i-lucide-image" class="size-14 opacity-35" />
        </div>
        <div
          class="pointer-events-none absolute inset-0 bg-linear-to-t from-black/65 via-black/15 to-transparent"
          aria-hidden="true"
        />
        <div class="absolute top-2 left-2 z-10 flex max-w-[calc(100%-5.5rem)] items-center gap-2 sm:top-3 sm:left-3">
          <label
            v-if="isSchool"
            class="flex min-w-0 cursor-pointer select-none items-center gap-1.5 rounded-lg bg-background/92 px-1.5 py-1 shadow-md ring-1 ring-white/20 backdrop-blur-sm transition-colors hover:bg-background dark:bg-background/85 sm:gap-2 sm:px-2.5 sm:py-1.5"
            :aria-label="$t('pages.allclass.card.selectClassForEnrollment')"
            @click.stop.prevent="
              emit(
                'toggle-enrollment-select',
                classItem,
                !props.selectedForEnrollment,
              )
            "
          >
            <UCheckbox :model-value="props.selectedForEnrollment" class="pointer-events-none shrink-0" tabindex="-1" />
            <span class="max-w-20 truncate text-[11px] font-medium text-foreground sm:max-w-28 sm:text-xs">{{ $t('pages.allclass.card.selectClass') }}</span>
          </label>

          <UDropdownMenu :items="classActionItems" :content="{ align: 'start' }">
            <UButton
              icon="i-lucide-ellipsis-vertical"
              color="neutral"
              variant="solid"
              size="xs"
              square
              class="shadow-md bg-background/90 backdrop-blur-sm ring-1 ring-white/15 dark:bg-background/80"
              :aria-label="$t('common.actions')"
              @click.stop
            />
          </UDropdownMenu>
        </div>
        <UBadge
          :color="classStudentTotal > 0 ? 'primary' : 'neutral'"
          variant="solid"
          size="xs"
          class="absolute top-2 right-2 z-10 shadow-md backdrop-blur-[2px] sm:top-3 sm:right-3"
        >
          <span class="inline-flex items-center gap-1">
            <UIcon name="i-lucide-users" class="size-3.5 shrink-0" />
            <span class="hidden sm:inline">{{ $t("pages.school.classCard.students", { count: classStudentTotal }) }}</span>
            <span class="sm:hidden">{{ classStudentTotal }}</span>
          </span>
        </UBadge>
        <div class="absolute inset-x-0 bottom-0 px-2.5 pb-2.5 pt-10 sm:px-3 sm:pb-3 sm:pt-12">
          <p
            class="text-sm font-bold leading-snug text-white drop-shadow-md line-clamp-2 sm:text-base"
          >
            {{ classItem.name }}
          </p>
        </div>
      </div>

      <div class="flex flex-col gap-2 p-2.5 sm:gap-2 sm:px-3 sm:py-2">
        <!-- Category (display-only, stable color from category id) -->
        <div :class="rowClass">
          <div :class="labelClass">
            <span class="inline-flex items-center gap-1">
              <UIcon
                name="i-lucide-swatch-book"
                class="size-3.5 opacity-70 shrink-0"
              />
              {{ $t("pages.courses.columns.category") }}
            </span>
          </div>
          <UBadge
            :color="categoryBadgeColor(classItem.categoryId)"
            variant="subtle"
            size="sm"
            class="min-w-0 max-w-full justify-start font-medium"
          >
            <span class="truncate">{{ classItem.category }}</span>
          </UBadge>
        </div>

        <!-- Course -->
        <div v-if="classItem.courseName" :class="rowClass">
          <div :class="labelClass">
            <span class="inline-flex items-center gap-1">
              <UIcon
                name="i-lucide-book-open"
                class="size-3.5 opacity-70 shrink-0"
              />
              {{ $t("pages.courses.columns.course") }}
            </span>
          </div>
          <span :class="['font-medium line-clamp-2', valueClass]">{{
            classItem.courseName
          }}</span>
        </div>

        <!-- Teacher -->
        <div v-if="classItem.teacherName" :class="rowClass">
          <div :class="labelClass">
            <span class="inline-flex items-center gap-1">
              <UIcon
                name="i-lucide-user"
                class="size-3.5 opacity-70 shrink-0"
              />
              {{ $t("pages.courses.columns.teacherName") }}
            </span>
          </div>
          <span :class="['line-clamp-2', valueClass]">{{
            classItem.teacherName
          }}</span>
        </div>

        <!-- Level, duration, shift, time & days — one row -->
        <div
          v-if="classLevel || classDurationLabel || hasScheduleBadges"
          class="flex flex-wrap items-center gap-1.5 sm:gap-2"
        >
          <UBadge
            v-if="classLevel"
            color="secondary"
            variant="subtle"
            size="sm"
            class="font-medium"
          >
            <span class="inline-flex items-center gap-1.5">
              <UIcon name="i-lucide-layers-3" class="size-3.5 opacity-90" />
              {{ $t("pages.allclass.fields.level") }}: {{ classLevel }}
            </span>
          </UBadge>
          <UBadge
            v-if="classDurationLabel"
            color="warning"
            variant="subtle"
            size="sm"
            class="font-medium"
          >
            <span class="inline-flex items-center gap-1.5">
              <UIcon name="i-lucide-hourglass" class="size-3.5 opacity-90" />
              {{ classDurationLabel }}
            </span>
          </UBadge>
          <UBadge
            v-if="computedShift"
            color="primary"
            variant="subtle"
            size="sm"
            class="max-w-full font-medium"
          >
            <span class="inline-flex items-center gap-1.5">
              <UIcon name="i-lucide-sun" class="size-3.5 opacity-90" />
              {{ computedShift }}
            </span>
          </UBadge>
          <UBadge
            v-if="classItem.timeSlot"
            color="neutral"
            variant="subtle"
            size="sm"
            class="font-medium"
          >
            <span class="inline-flex items-center gap-1.5">
              <UIcon name="i-lucide-clock" class="size-3.5 opacity-90" />
              {{ classItem.timeSlot }}
            </span>
          </UBadge>
          <UBadge
            v-if="classDaysOfWeek.length > 0"
            color="info"
            variant="subtle"
            size="sm"
            class="max-w-full font-medium"
          >
            <span class="inline-flex items-center gap-1.5 min-w-0">
              <UIcon name="i-lucide-calendar-days" class="size-3.5 shrink-0 opacity-90" />
              <span class="truncate">
                {{ classDaysOfWeek.map(weekdayLabel).join(', ') }}
              </span>
            </span>
          </UBadge>
        </div>

        <USeparator
          v-if="showSeparatorAbovePricing"
          type="dashed"
          size="sm"
          class="opacity-70"
        />

        <!-- Pricing (same for default & school — list price, discount, tuition/final) -->
        <div
          class="rounded-none border border-default/80 bg-linear-to-b from-primary/5 to-muted/30 p-2.5 space-y-1 sm:px-3 sm:py-2.5 sm:space-y-1.5"
          :class="showPricingSeparator || !hasScheduleBadges ? '' : 'mt-0.5'"
        >
          <div v-if="showFullPriceRow" :class="rowClass">
            <div :class="labelClass">
              <span>{{ $t("pages.courses.columns.fullPrice") }}</span>
            </div>
            <span :class="[fullPriceClass, valueClass]">{{
              formatCurrency(classItem.fullPrice!, "USD")
            }}</span>
          </div>

          <div v-if="showDiscountRow" :class="rowClass">
            <div :class="labelClass">
              <span>{{ $t("pages.courses.columns.discount") }}</span>
            </div>
            <span :class="['font-semibold text-success', valueClass]">{{
              discountLine
            }}</span>
          </div>

          <div
            class="flex flex-wrap items-end justify-between gap-2 border-t border-default/50 pt-0.5 mt-1 sm:gap-3"
          >
            <span class="text-xs font-semibold tracking-wide text-muted">
              {{ $t("pages.courses.columns.finalPrice") }}
            </span>
            <span class="text-base font-bold tabular-nums text-primary sm:text-xl">
              {{ formatCurrency(classItem.outPrice, "USD") }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </UCard>
</template>
