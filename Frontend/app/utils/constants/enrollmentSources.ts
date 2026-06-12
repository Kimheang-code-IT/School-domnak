/** Canonical enrollment / invoice source values (must match backend storage). */
export const ENROLLMENT_SOURCE_OPTIONS = [
  'Domnaksiiksa',
  'Learn fast',
  'rean chinese',
  'other',
] as const

export type EnrollmentSource = (typeof ENROLLMENT_SOURCE_OPTIONS)[number]
