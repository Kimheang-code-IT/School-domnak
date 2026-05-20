/**
 * Canonical English names — must match keys under `provinces` in `en.json` / `km.json`.
 * Stored in forms/API as this string; UI labels come from `t('provinces.' + name)`.
 */
export const CAMBODIA_PROVINCE_NAMES = [
  'Banteay Meanchey',
  'Battambang',
  'Kampong Cham',
  'Kampong Chhnang',
  'Kampong Speu',
  'Kampong Thom',
  'Kampot',
  'Kandal',
  'Kep',
  'Koh Kong',
  'Kratie',
  'Mondul Kiri',
  'Oddar Meanchey',
  'Pailin',
  'Phnom Penh',
  'Preah Sihanouk',
  'Preah Vihear',
  'Prey Veng',
  'Pursat',
  'Ratanak Kiri',
  'Siemreap',
  'Stung Treng',
  'Svay Rieng',
  'Takeo',
  'Tboung Khmum',
] as const

const CANONICAL_SET = new Set<string>(CAMBODIA_PROVINCE_NAMES)

/** Slugs / aliases seen in older data (e.g. all-student table) → canonical name. */
const SLUG_TO_CANONICAL: Record<string, string> = {
  'phnom-penh': 'Phnom Penh',
  'phnom penh': 'Phnom Penh',
  battambang: 'Battambang',
  sihanoukville: 'Preah Sihanouk',
  'preah sihanouk': 'Preah Sihanouk',
  'kampong-som': 'Preah Sihanouk',
  kampongsom: 'Preah Sihanouk',
  'kampong-cham': 'Kampong Cham',
  'kampong-chhnang': 'Kampong Chhnang',
  'kampong-speu': 'Kampong Speu',
  'kampong-thom': 'Kampong Thom',
}

export function normalizeCambodiaProvince(raw: string): string {
  const s = String(raw ?? '').trim()
  if (!s) return ''
  if (CANONICAL_SET.has(s)) return s
  const key = s.toLowerCase()
  const mapped = SLUG_TO_CANONICAL[key]
  if (mapped) return mapped
  const byCi = CAMBODIA_PROVINCE_NAMES.find((p) => p.toLowerCase() === key)
  if (byCi) return byCi
  const hyphen = key.replace(/-/g, ' ')
  const byHyphen = CAMBODIA_PROVINCE_NAMES.find((p) => p.toLowerCase() === hyphen)
  return byHyphen ?? ''
}
