/** Max local digits (with optional leading 0), e.g. 0123456789 */
export const CAMBODIA_PHONE_MAX_LENGTH = 10

/** Keep digits only; strip +855 prefix; cap length for Cambodia mobile numbers. */
export function normalizeCambodiaPhone(raw: string): string {
  let digits = String(raw ?? '').replace(/\D/g, '')
  if (digits.startsWith('855') && digits.length > 9) {
    digits = digits.slice(3)
  }
  if (digits.startsWith('0')) {
    return digits.slice(0, CAMBODIA_PHONE_MAX_LENGTH + 1)
  }
  return digits.slice(0, CAMBODIA_PHONE_MAX_LENGTH)
}
