/** Turn stored paths (`/uploads/...`) into browser-loadable URLs on the current host. */
export function resolveUploadUrl(src: string | null | undefined): string {
  const raw = String(src ?? '').trim()
  if (!raw) return ''
  if (raw.startsWith('data:') || raw.startsWith('blob:')) return raw
  if (/^https?:\/\//i.test(raw)) return raw
  if (raw.startsWith('/uploads/')) {
    if (import.meta.client && typeof window !== 'undefined') {
      return `${window.location.origin}${raw}`
    }
    return raw
  }
  return raw
}
