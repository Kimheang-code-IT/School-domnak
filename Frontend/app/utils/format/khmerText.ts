/** Khmer script block (letters, vowels, signs, digits) plus ZWNJ used in Khmer typography. */
const NON_KHMER_CHARS = /[^\u1780-\u17FF\u200C\s]/gu

/** Keep only Khmer script characters and spaces. */
export function normalizeKhmerText(raw: string): string {
  return String(raw ?? '').replace(NON_KHMER_CHARS, '')
}
