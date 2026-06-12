import { normalizeCambodiaProvince } from '~/utils/constants/cambodiaProvinces'

/** Display label for a province slug or canonical name stored on student/report rows. */
export function provinceDisplayLabel(
  translate: (key: string) => string,
  raw: string | undefined | null,
): string {
  const canonical = normalizeCambodiaProvince(String(raw ?? '').trim())
  if (!canonical) return '—'
  return translate(`provinces.${canonical}`)
}
