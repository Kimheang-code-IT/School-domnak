import { defineConfig } from 'vitest/config'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const root = dirname(fileURLToPath(import.meta.url))

/** Match Nuxt `~` → application source (`app/`) so Vitest resolves the same imports as dev. */
export default defineConfig({
  test: {
    environment: 'node'
  },
  resolve: {
    alias: {
      '~': resolve(root, 'app'),
      '@': resolve(root, 'app'),
      '~~': root,
      '@@': root
    }
  }
})
