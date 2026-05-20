import { ref } from 'vue'
import { useQueryClient } from '~/composables/data/useQueryClient'

export function useMutation() {
  const isMutating = ref(false)
  const queryClient = useQueryClient()

  async function run<T>(mutation: () => Promise<T>, invalidatePrefix?: string): Promise<T> {
    isMutating.value = true
    try {
      const result = await mutation()
      if (invalidatePrefix) queryClient.invalidate(invalidatePrefix)
      return result
    } finally {
      isMutating.value = false
    }
  }

  return {
    isMutating,
    run
  }
}
