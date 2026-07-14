/**
 * Apply saved locale after hydration so static HTML (defaultLocale) matches the first client render.
 */
export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.hook('app:mounted', () => {
    const cookie = useCookie<string | null>('i18n_redirected', { sameSite: 'lax' })
    const i18n = nuxtApp.$i18n as { locale: { value: string }, setLocale: (code: string) => Promise<void> | void }
    const saved = cookie.value
    if (!saved || saved === i18n.locale.value) return
    if (saved === 'en' || saved === 'km') {
      void i18n.setLocale(saved)
    }
  })
})
