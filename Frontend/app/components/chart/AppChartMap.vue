<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps<{
    data: { name: string; value: number }[]
    label?: string
    width?: string | number
    showPercent?: boolean
}>()

const emit = defineEmits(['select-province'])
const appConfig = useAppConfig()

// Province shortcut mapping
const PROVINCE_SHORTCUTS: Record<string, string> = {
    'Banteay Meanchey': 'BMC',
    'Battambang': 'BTB',
    'Kampong Cham': 'KPC',
    'Kampong Chhnang': 'KCH',
    'Kampong Speu': 'KPS',
    'Kampong Thom': 'KPT',
    'Kampot': 'KMP',
    'Kandal': 'KND',
    'Kep': 'KEP',
    'Koh Kong': 'KKG',
    'Kratie': 'KRT',
    'Mondul Kiri': 'MDK',
    'Oddar Meanchey': 'OMC',
    'Pailin': 'PLN',
    'Phnom Penh': 'PP',
    'Preah Sihanouk': 'SHV',
    'Preah Vihear': 'PVH',
    'Prey Veng': 'PVG',
    'Pursat': 'PUR',
    'Ratanak Kiri': 'RTK',
    'Siemreap': 'SRP',
    'Stung Treng': 'STR',
    'Svay Rieng': 'SVR',
    'Takeo': 'TKO',
    'Tboung Khmum': 'TBK'
}

const geojson = ref<any>(null)
const isMapLoaded = ref(false)
const mapLoadError = ref(false)
const mapContainer = ref<HTMLElement | null>(null)
const hoveredProvince = ref<any>(null)
const mousePos = ref({ x: 0, y: 0 })
let handleMouseMove: ((e: MouseEvent) => void) | null = null
let mouseFrame = 0

interface StaticProvinceMeta {
    name: string
    path: string
    shortName: string
    centroid: [number, number]
}

// Map dimensions for projection scaling
const widthInt = 800
const heightInt = 600
const viewBox = `0 0 ${widthInt} ${heightInt}`

// ─── GeoJSON Fetching ───────────────────────────────────────────────
onMounted(async () => {
    try {
        const khMapModule = await import('~/data/kh.json')
        geojson.value = khMapModule.default
        isMapLoaded.value = true
        
        // Track mouse for tooltip positioning
        if (mapContainer.value) {
            handleMouseMove = (e: MouseEvent) => {
                if (mouseFrame) return
                mouseFrame = window.requestAnimationFrame(() => {
                    const rect = (mapContainer.value as HTMLElement).getBoundingClientRect()
                    mousePos.value = {
                        x: e.clientX - rect.left,
                        y: e.clientY - rect.top
                    }
                    mouseFrame = 0
                })
            }
            mapContainer.value.addEventListener('mousemove', handleMouseMove)
        }
    } catch (err) {
        mapLoadError.value = true
        console.error('Failed to load Cambodia map data:', err)
    }
})

onUnmounted(() => {
    if (mapContainer.value && handleMouseMove) {
        mapContainer.value.removeEventListener('mousemove', handleMouseMove)
    }
    if (mouseFrame) {
        window.cancelAnimationFrame(mouseFrame)
        mouseFrame = 0
    }
})

// ─── Projection Logic ───────────────────────────────────────────────

function mercatorProject(lon: number, lat: number): [number, number] {
    const x = (lon + 180) * (256 / 360)
    const latRad = (lat * Math.PI) / 180
    const y = (256 / 2) - (256 * Math.log(Math.tan(Math.PI / 4 + latRad / 2)) / (2 * Math.PI))
    return [x, y]
}

function getBounds(gj: any) {
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
    
    const processCoords = (coords: any): void => {
        if (Array.isArray(coords) && typeof coords[0] === 'number' && typeof coords[1] === 'number') {
            const projected = mercatorProject(coords[0], coords[1])
            const x = projected[0]
            const y = projected[1]
            minX = Math.min(minX, x)
            minY = Math.min(minY, y)
            maxX = Math.max(maxX, x)
            maxY = Math.max(maxY, y)
        } else if (Array.isArray(coords)) {
            coords.forEach(processCoords)
        }
    }
    
    gj.features.forEach((f: any) => {
        if (f.geometry?.coordinates) {
            processCoords(f.geometry.coordinates)
        }
    })
    
    return { minX, minY, maxX, maxY }
}

const projectionParams = computed(() => {
    if (!geojson.value?.features?.length) return null
    
    const bounds = getBounds(geojson.value)
    const bWidth = bounds.maxX - bounds.minX
    const bHeight = bounds.maxY - bounds.minY
    const padding = 1
    
    const scale = Math.min(
        (widthInt - padding * 2) / bWidth,
        (heightInt - padding * 2) / bHeight
    )
    
    const offsetX = (widthInt - bWidth * scale) / 2 - bounds.minX * scale
    const offsetY = (heightInt - bHeight * scale) / 2 - bounds.minY * scale
    
    return { scale, offsetX, offsetY }
})

function project(lon: number, lat: number): [number, number] {
    if (!projectionParams.value) return [0, 0]
    const projected = mercatorProject(lon, lat)
    const x = projected[0]
    const y = projected[1]
    const { scale, offsetX, offsetY } = projectionParams.value
    return [x * scale + offsetX, y * scale + offsetY]
}

function geometryToPath(geometry: any) {
    if (!geometry) return ''
    
    const coordsToPath = (coords: any, isFirst = true) => {
        if (typeof coords[0] === 'number' && typeof coords[1] === 'number') {
            const p = project(coords[0], coords[1])
            const px = p[0]
            const py = p[1]
            return `${isFirst ? 'M' : 'L'}${px.toFixed(2)},${py.toFixed(2)}`
        }
        return coords.map((c: any, i: number) => coordsToPath(c, i === 0)).join(' ')
    }
    
    if (geometry.type === 'Polygon') {
        return geometry.coordinates.map((ring: any) => coordsToPath(ring) + 'Z').join(' ')
    }
    if (geometry.type === 'MultiPolygon') {
        return geometry.coordinates.map((poly: any) => 
            poly.map((ring: any) => coordsToPath(ring) + 'Z').join(' ')
        ).join(' ')
    }
    return ''
}

function calculateCentroid(geometry: any) {
    if (!geometry) return [0, 0]
    let sumX = 0, sumY = 0, count = 0
    const processCoords = (coords: any) => {
        if (typeof coords[0] === 'number' && typeof coords[1] === 'number') {
            const p = project(coords[0], coords[1])
            const px = p[0]
            const py = p[1]
            sumX += px
            sumY += py
            count++
        } else if (Array.isArray(coords)) {
            coords.forEach(processCoords)
        }
    }
    if (geometry.coordinates) processCoords(geometry.coordinates)
    return count > 0 ? [sumX / count, sumY / count] : [0, 0]
}

// ─── Data Preparation ───────────────────────────────────────────────

function getFeatureName(feature: any) {
    const p = feature.properties || {}
    return p.shapeName || p.NAME_1 || p.name || p.NAME || ''
}

const staticProvinceMeta = computed<StaticProvinceMeta[]>(() => {
    if (!geojson.value?.features || !projectionParams.value) return []
    return geojson.value.features.map((feature: any) => {
        const name = getFeatureName(feature)
        return {
            name,
            path: geometryToPath(feature.geometry),
            shortName: PROVINCE_SHORTCUTS[name] || name.substring(0, 3).toUpperCase(),
            centroid: calculateCentroid(feature.geometry)
        }
    })
})

/**
 * API-ready input normalization:
 * - handles null/undefined names safely
 * - trims province names from backend payloads
 * - converts values to numbers with fallback 0
 */
const normalizedData = computed(() =>
    props.data
        .map((item) => ({
            name: String(item?.name || '').trim(),
            value: Number(item?.value) || 0
        }))
        .filter((item) => item.name.length > 0)
)

const provinceDataMap = computed(() => {
    const dataMap = new Map<string, { name: string; value: number }>()
    // Aggregate duplicates once for stable rendering with large API payloads.
    normalizedData.value.forEach((item) => {
        const value = item.value
        const existing = dataMap.get(item.name)
        if (existing) {
            existing.value += value
        } else {
            dataMap.set(item.name, { name: item.name, value })
        }
    })
    return dataMap
})

const provinces = computed(() => {
    return staticProvinceMeta.value.map((province: StaticProvinceMeta) => {
        const d = provinceDataMap.value.get(province.name) || { value: 0 }
        return {
            name: province.name,
            path: province.path,
            value: Number(d.value) || 0
        }
    })
})

const provincesWithCentroids = computed(() => {
    return staticProvinceMeta.value.map((province: StaticProvinceMeta) => {
        const d = provinceDataMap.value.get(province.name) || { value: 0 }
        return {
            name: province.name,
            shortName: province.shortName,
            centroid: province.centroid,
            value: Number(d.value) || 0
        }
    })
})

const maxValue = computed(() => {
    if (!provinceDataMap.value.size) return 0
    return Math.max(...Array.from(provinceDataMap.value.values()).map((d) => d.value))
})

function parseColorToRgbTriplet(colorValue: string, fallback: string) {
    const value = (colorValue || fallback).trim()
    if (/^#([0-9a-fA-F]{6})$/.test(value)) {
        const hex = value.slice(1)
        const r = parseInt(hex.slice(0, 2), 16)
        const g = parseInt(hex.slice(2, 4), 16)
        const b = parseInt(hex.slice(4, 6), 16)
        return `${r}, ${g}, ${b}`
    }
    if (/^#([0-9a-fA-F]{3})$/.test(value)) {
        const hex = value.slice(1)
        const h0 = hex.charAt(0)
        const h1 = hex.charAt(1)
        const h2 = hex.charAt(2)
        const r = parseInt(h0 + h0, 16)
        const g = parseInt(h1 + h1, 16)
        const b = parseInt(h2 + h2, 16)
        return `${r}, ${g}, ${b}`
    }
    const rgbMatch = value.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/)
    if (rgbMatch) return `${rgbMatch[1]}, ${rgbMatch[2]}, ${rgbMatch[3]}`
    return fallback
}

function getThemeTokenColor(token: string, shade: string, fallbackHex: string) {
    if (!import.meta.client) return fallbackHex
    const cssVar = getComputedStyle(document.documentElement)
        .getPropertyValue(`--color-${token}-${shade}`)
        .trim()
    return cssVar || fallbackHex
}

const primaryToken = computed(() => String((appConfig.ui as any).colors?.primary || 'blue'))
const neutralToken = computed(() => String((appConfig.ui as any).colors?.neutral || 'zinc'))
const primaryRgb = computed(() =>
    parseColorToRgbTriplet(getThemeTokenColor(primaryToken.value, '500', '#03386e'), '3, 56, 110')
)
const primaryDarkRgb = computed(() =>
    parseColorToRgbTriplet(getThemeTokenColor(primaryToken.value, '900', '#011426'), '1, 20, 38')
)
const primaryLightRgb = computed(() =>
    parseColorToRgbTriplet(getThemeTokenColor(primaryToken.value, '50', '#eef3f8'), '238, 243, 248')
)
const neutralRgb = computed(() =>
    parseColorToRgbTriplet(getThemeTokenColor(neutralToken.value, '400', '#94a3b8'), '148, 163, 184')
)

const mapThemeVars = computed(() => ({
    '--map-primary-rgb': primaryRgb.value,
    '--map-primary-dark-rgb': primaryDarkRgb.value,
    '--map-primary-light-rgb': primaryLightRgb.value,
    '--map-neutral-rgb': neutralRgb.value
}))

function getProvinceColor(value: number) {
    if (!maxValue.value || !value) return `rgba(${neutralRgb.value}, 0.15)`
    const intensity = Math.min(0.9, Math.max(0.15, value / maxValue.value))
    return `rgba(${primaryRgb.value}, ${intensity})`
}

function formatValue(value: number) {
    return new Intl.NumberFormat('en-US').format(value)
}

function formatCompactValue(value: number) {
    if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M'
    if (value >= 1000) return (value / 1000).toFixed(1) + 'K'
    return value.toLocaleString()
}

// ─── Tooltip Styling ───────────────────────────────────────────────

const tooltipStyle = computed(() => {
    if (!hoveredProvince.value) return {}
    // Position tooltip relative to mouse
    return {
        left: `${mousePos.value.x}px`,
        top: `${mousePos.value.y - 40}px`,
        transform: 'translateX(-50%)'
    }
})

</script>

<template>
    <div 
        class="flex flex-col relative w-full h-full bg-transparent overflow-hidden"
        :class="{ 'overflow-x-auto': width === 'w-2000' }"
        :style="mapThemeVars"
    >
        <div 
            ref="mapContainer" 
            class="relative transition-all duration-300 ease-in-out h-full"
            :style="{ 
                width: width === 'w-2000' ? '2000px' : '100%'
            }"
        >
            <svg
                v-if="isMapLoaded"
                ref="svgRef"
                :viewBox="viewBox"
                class="w-full h-full drop-shadow-sm"
                preserveAspectRatio="xMidYMid meet"
            >
                <g>
                    <!-- Province paths -->
                    <path
                        v-for="(province, index) in provinces"
                        :key="province.name || index"
                        :d="province.path"
                        :fill="getProvinceColor(province.value)"
                        :stroke="`rgba(${neutralRgb}, 0.5)`"
                        stroke-width="0.5"
                        class="province-path cursor-pointer transition-all duration-300"
                        :class="{ 'hovered-province': hoveredProvince?.name === province.name }"
                        @mouseenter="hoveredProvince = province"
                        @mouseleave="hoveredProvince = null"
                        @click="$emit('select-province', province.name)"
                    />
                    
                    <!-- Province labels with values -->
                    <g class="pointer-events-none select-none">
                        <template v-for="(province, index) in provincesWithCentroids" :key="'label-' + index">
                            <text
                                :x="province.centroid[0]"
                                :y="province.centroid[1] - 4"
                                text-anchor="middle"
                                class="province-name-label font-bold tracking-tighter"
                            >{{ province.shortName }}</text>
                            <text
                                :x="province.centroid[0]"
                                :y="province.centroid[1] + 10"
                                text-anchor="middle"
                                class="province-value-label font-medium opacity-80"
                            >{{ formatCompactValue(province.value) }}</text>
                        </template>
                    </g>
                </g>
            </svg>

            <!-- Loading State -->
            <CommonAppLoadingState
                v-else-if="!mapLoadError"
                compact
                class="h-full min-h-[200px]"
                :label="$t('components.loadingMap')"
            />
            <div v-else class="flex flex-col items-center justify-center h-full gap-4 text-muted-foreground">
                <UIcon name="i-lucide-map-x" class="size-8" />
                <p class="text-xs">{{ $t('common.noData') }}</p>
            </div>

            <!-- Legend Overlay -->
            <div class="absolute bottom-2 p-1 rounded-lg bg-background/80 backdrop-blur-sm border border-accented shadow-sm select-none">
                <div class="flex items-center gap-1.5 mb-2">
                    <UIcon name="i-lucide-trending-up" class="size-3 text-primary" />
                    <div class="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">{{ label || $t('components.scale') }}</div>
                </div>
                <div
                    class="h-1.5 w-32 rounded-full border border-white/10 mb-1"
                    :style="{ backgroundImage: `linear-gradient(to right, rgba(${primaryLightRgb},0.5), rgb(${primaryRgb}), rgb(${primaryDarkRgb}))` }"
                />
                <div class="flex justify-between w-full text-[9px] font-bold text-muted-foreground/60 px-0.5">
                    <span>{{ $t('components.min') }}</span>
                    <span>{{ $t('components.max') }}</span>
                </div>
            </div>

            <!-- Floating Tooltip (Matches Nuxt UI standard) -->
            <div
                v-if="hoveredProvince"
                class="absolute pointer-events-none bg-neutral-900 dark:bg-[#18191a] text-white text-[11px] px-2.5 py-1.5 rounded shadow-lg z-50 border border-neutral-700 ring-1 ring-black/5 flex flex-col gap-1 min-w-[120px] animate-in fade-in zoom-in-95 duration-100"
                :style="tooltipStyle"
            >
                <div class="font-bold border-b border-white/10 pb-1 mb-0.5 truncate">
                    {{ $t('provinces.' + hoveredProvince.name) }}
                </div>
                <div class="flex justify-between gap-4">
                    <span class="text-neutral-400 capitalize">{{ label || $t('common.revenueUsd') }}</span>
                    <span class="text-primary-400 font-bold">{{ formatValue(hoveredProvince.value) }}</span>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.province-path:hover {
    fill: rgb(var(--map-primary-rgb)) !important;
    stroke: #ffffff;
    stroke-width: 1.5;
    filter: drop-shadow(0 0 8px rgba(var(--map-primary-rgb), 0.4));
}

.province-name-label {
    font-size: 10px;
    fill: #0f172a;
    paint-order: stroke;
    stroke: #ffffff;
    stroke-width: 3px;
    stroke-linecap: round;
    stroke-linejoin: round;
}

.province-value-label {
    font-size: 8px;
    fill: #475569;
    paint-order: stroke;
    stroke: #ffffff;
    stroke-width: 2.5px;
    stroke-linecap: round;
    stroke-linejoin: round;
}

:deep(.dark) .province-name-label {
    fill: #f8fafc;
    stroke: #0f172a;
}

:deep(.dark) .province-value-label {
    fill: #94a3b8;
    stroke: #0f172a;
}

.province-path {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.hovered-province {
    fill: rgba(var(--map-primary-rgb), 0.9) !important;
    transform: scale(1.005);
}
</style>
