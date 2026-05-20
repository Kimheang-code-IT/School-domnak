/** Prefer English name; parse `Khmer · English` combined labels from invoices. */
export function englishStudentDisplayName(
  ...candidates: Array<string | null | undefined>
): string {
  for (const raw of candidates) {
    const text = String(raw ?? '').trim()
    if (!text) continue
    if (text.includes(' · ')) {
      const parts = text
        .split(' · ')
        .map((part) => part.trim())
        .filter(Boolean)
      if (parts.length >= 2) return parts[parts.length - 1] ?? '—'
    }
    return text ?? '—'
  }
  return ''
}
