/** True only when real HTTP to `apiBase` is intended (not mock). Env strings like `"false"` must stay falsy — `Boolean("false")` is wrongly true in JS. */
export function isLiveBackendApi(config: { public: { useBackendApi?: unknown } }) {
  const v = config.public.useBackendApi
  return v !== false && v !== 'false'
}

/** Static/UI design mode — no real API, no auth enforcement, permissive forms */
export function isUiOnlyMode(config: { public: { uiOnly?: unknown } }) {
  const v = config.public.uiOnly
  return v === true || v === 'true'
}

export function useBackendMode() {
  const config = useRuntimeConfig()
  return computed(() => isLiveBackendApi(config))
}

export function useUiOnlyMode() {
  const config = useRuntimeConfig()
  return computed(() => isUiOnlyMode(config))
}
