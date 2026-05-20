<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { DropdownMenuItem } from '~/types/nuxt-ui'
import { formatDate } from '~/utils/format/date'

const open = defineModel<boolean>('open', { default: false })
const range = defineModel<{ start?: unknown; end?: unknown }>('range', {
    default: () => ({ start: undefined, end: undefined }),
})
const pagination = defineModel<any>('pagination', {
    default: () => ({ pageIndex: 0, pageSize: 50 })
})

const props = defineProps<{
    classId: string
    className?: string
    data: Record<string, unknown>[]
    loading?: boolean
    total: number
}>()

const { t } = useI18n()

const emit = defineEmits<{
    continueClass: [row: Record<string, unknown>]
    cancelClass: [row: Record<string, unknown>]
}>()

type PendingAction = 'continueClass' | 'cancelClass'

const isActionConfirmOpen = ref(false)
const pendingAction = ref<PendingAction | null>(null)
const pendingActionRow = ref<Record<string, unknown> | null>(null)

function studentName(row: Record<string, unknown> | null) {
    return row
        ? pickStr(row, [
            'studentName',
            'student_name',
            'name',
            'nameEn',
            'nameKm',
        ]) || '—'
        : '—'
}

const actionConfirmConfig = computed(() => {
    const isCancel = pendingAction.value === 'cancelClass'
    return {
        title: isCancel
            ? t('pages.allclass.studentListModal.confirm.cancelTitle')
            : t('pages.allclass.studentListModal.confirm.continueTitle'),
        description: t(
            isCancel
                ? 'pages.allclass.studentListModal.confirm.cancelDescription'
                : 'pages.allclass.studentListModal.confirm.continueDescription',
            { name: studentName(pendingActionRow.value) },
        ),
        type: isCancel ? 'error' as const : 'primary' as const,
        submitLabel: isCancel
            ? t('pages.allclass.studentListModal.actions.cancelClass')
            : t('pages.allclass.studentListModal.actions.continueClass'),
    }
})

function openActionConfirm(action: PendingAction, row: Record<string, unknown>) {
    pendingAction.value = action
    pendingActionRow.value = row
    isActionConfirmOpen.value = true
}

function dismissActionConfirm() {
    pendingAction.value = null
    pendingActionRow.value = null
}

function confirmPendingAction() {
    const action = pendingAction.value
    const row = pendingActionRow.value
    isActionConfirmOpen.value = false
    dismissActionConfirm()
    if (!action || !row) return
    if (action === 'continueClass') {
        emit('continueClass', row)
    } else {
        emit('cancelClass', row)
    }
}

/** Same pattern as `useAllStudent` → `allstudent.vue` (`:get-row-actions="getDropdownActions"`). */
function getDropdownActions(entry: Record<string, unknown>): DropdownMenuItem[][] {
    return [
        [
            {
                label: t('pages.allclass.studentListModal.actions.continueClass'),
                icon: 'i-lucide-square-play',
                onSelect: () => openActionConfirm('continueClass', entry),
            },
            {
                label: t('pages.allclass.studentListModal.actions.cancelClass'),
                icon: 'i-lucide-square-scissors',
                color: 'error' as const,
                onSelect: () => openActionConfirm('cancelClass', entry),
            },
        ],
    ]
}

function pickStr(row: Record<string, unknown>, keys: string[]): string {
    for (const k of keys) {
        const v = row[k]
        if (v != null && String(v).trim() !== '') return String(v).trim()
    }
    return ''
}

function cellDate(row: Record<string, unknown>, keys: string[]) {
    const raw = pickStr(row, keys)
    return formatDate(raw || undefined)
}

function isExpiresSoon(row: Record<string, unknown>) {
    return row.expiresSoon === true || row.expires_soon === true
}

function statusText(row: Record<string, unknown>) {
    return pickStr(row, ['status', 'enrollmentStatus']) || '—'
}

function statusClass(row: Record<string, unknown>) {
    const text = statusText(row)
    if (text.toLowerCase() === 'active' && isExpiresSoon(row)) {
        return 'text-sm font-semibold text-error'
    }
    return 'text-sm text-muted-foreground'
}

const columns = computed(() => [
    { accessorKey: 'id', header: t('pages.allclass.studentListModal.columns.id') },
    {
        accessorKey: 'studentName',
        header: t('pages.allclass.studentListModal.columns.studentName'),
        footer: t('pages.allclass.studentListModal.footer.studentCount', { count: props.total }),
    },
    { accessorKey: 'gender', header: t('pages.allclass.studentListModal.columns.gender') },
    { accessorKey: 'startdate', header: t('pages.allclass.studentListModal.columns.startdate') },
    { accessorKey: 'enddate', header: t('pages.allclass.studentListModal.columns.enddate') },
    { accessorKey: 'status', header: t('pages.allclass.studentListModal.columns.status') },
    /** Match `useAllStudent` (`{ id: "action", header: t("common.actions") }`). */
    { id: 'action', header: t('common.actions') },
])

watch(open, (isOpen) => {
    if (!isOpen) {
        isActionConfirmOpen.value = false
        dismissActionConfirm()
    }
})
</script>

<template>
    <UModal
        v-model:open="open"
        :dismissible="false"
        :ui="{ content: 'sm:max-w-7xl h-[90vh] flex flex-col' }"
    >
        <template #header>
            <div class="flex items-center justify-between w-full gap-3 flex-wrap">
                <div class="flex min-w-0 flex-1 items-center gap-2">
                    <h3 class="truncate font-semibold text-foreground">{{ className || $t('pages.allclass.title') }}</h3>
                </div>
                <div class="flex items-center gap-2 shrink-0">
                    <CommonAppDatepicker v-model:range="range" />
                    <UButton
                        icon="i-lucide-x"
                        color="neutral"
                        variant="ghost"
                        size="sm"
                        square
                        class="shrink-0"
                        :aria-label="$t('common.close')"
                        @click="open = false"
                    />
                </div>
            </div>
        </template>

        <template #body>
            <!-- Horizontal scroll wrapper: avoid `overflow-x-auto` + pinned columns on same node (sticky body cells collapse). -->
            <div class="flex min-h-0 flex-1 flex-col gap-3 min-w-0 overflow-x-auto">
                <TableApptable
                    :columns="columns"
                    :data="data"
                    :loading="loading"
                    :total-rows="total"
                    server-pagination
                    v-model:pagination="pagination"
                    :selectable="false"
                    :virtualize="false"
                    :get-row-actions="getDropdownActions"
                    class="min-h-0 flex-1 min-w-[940px]"
                    :ui="{ root: 'min-w-full', td: 'empty:p-2' }"
                >
                    <template #id-cell="{ row }">
                        <span class="text-xs text-muted-foreground">#{{ row.original.id }}</span>
                    </template>
                    <template #studentName-cell="{ row }">
                        <span class="text-sm text-foreground">
                            {{
                                pickStr(row.original, [
                                    'studentName',
                                    'student_name',
                                    'nameKm',
                                    'name_km',
                                    'nameEn',
                                    'name_en',
                                    'name',
                                ]) || '—'
                            }}
                        </span>
                    </template>
                    <template #gender-cell="{ row }">
                        <span class="text-sm text-muted-foreground">
                            {{ pickStr(row.original, ['gender', 'studentGender', 'sex']) || '—' }}
                        </span>
                    </template>
                    <template #startdate-cell="{ row }">
                        <span class="text-sm text-muted-foreground">
                            {{ cellDate(row.original, ['startdate', 'startDate', 'start_date']) }}
                        </span>
                    </template>
                    <template #enddate-cell="{ row }">
                        <span class="text-sm text-muted-foreground">
                            {{ cellDate(row.original, ['enddate', 'endDate', 'end_date']) }}
                        </span>
                    </template>
                    <template #status-cell="{ row }">
                        <span :class="statusClass(row.original)">
                            {{ statusText(row.original) }}
                        </span>
                    </template>
                </TableApptable>
            </div>
        </template>

    </UModal>

    <CommonAppModalCURD
        v-model:open="isActionConfirmOpen"
        v-bind="actionConfirmConfig"
        @submit="confirmPendingAction"
        @cancel="dismissActionConfirm"
    />
</template>
