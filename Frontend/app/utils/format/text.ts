export function truncateText(text: string | undefined | null, max = 120): string {
  const s = String(text ?? '')
  if (s.length <= max) return s
  return `${s.slice(0, max)}…`
}
