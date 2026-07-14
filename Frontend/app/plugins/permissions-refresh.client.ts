/**
 * Refresh user permissions when the tab becomes visible again,
 * so role changes apply without a full re-login.
 */
export default defineNuxtPlugin(() => {
  if (!import.meta.client) return

  const auth = useAuthStore()
  let lastSync = 0

  async function refreshIfStale() {
    if (!auth.isLoggedIn) return
    const now = Date.now()
    if (now - lastSync < 30_000) return
    lastSync = now
    try {
      await auth.fetchMe()
    } catch {
      // Ignore; route middleware will re-check on next navigation.
    }
  }

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') void refreshIfStale()
  })
})
