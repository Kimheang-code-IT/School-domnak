/** Production site — HTTPS only (no mixed content). */
export const PRODUCTION_SITE_URL = 'https://school.72-62-250-194.sslip.io' as const

export const PRODUCTION_API_BASE = `${PRODUCTION_SITE_URL}/api/v1` as const

const PRODUCTION_HOSTS = ['school.72-62-250-194.sslip.io', '72.62.250.194'] as const

/** Dev-only fallback when NUXT_PUBLIC_API_BASE is unset. */
export const DEV_API_BASE = 'http://localhost:8000/api/v1' as const

function upgradeInsecureProductionUrl(url: string): string {
  for (const host of PRODUCTION_HOSTS) {
    if (url.startsWith(`http://${host}`)) {
      return url.replace(/^http:/, 'https:')
    }
  }
  return url
}

/** Resolve API base from runtime config; production never falls back to HTTP localhost. */
export function resolveApiBase(configured?: string): string {
  const value = configured?.trim()
  if (value) {
    return upgradeInsecureProductionUrl(value)
  }
  if (import.meta.dev) {
    return DEV_API_BASE
  }
  return PRODUCTION_API_BASE
}
