// nuxt.config.ts
// https://nuxt.com/docs/api/configuration/nuxt-config

import { DEV_API_BASE, PRODUCTION_API_BASE } from './app/utils/constants/apiBase'

export default defineNuxtConfig({
  // SPA static export for Docker/nginx — avoids prerender API errors in CI/CD
  ssr: false,

  modules: [
    '@nuxt/ui',
    '@nuxt/image',
    '@vueuse/nuxt',
    '@nuxtjs/i18n',
    '@pinia/nuxt'
  ],

  devtools: {
    enabled: process.env.NODE_ENV !== 'production'
  },

  imports: {
    dirs: [
      'utils/**',
      'utils/api/**',
      'utils/auth/**',
      'utils/constants/**',
      'utils/format/**',
      'utils/helpers/**',
      'utils/storage/**',
      'utils/validation/**'
    ]
  },

  css: ['~/assets/css/main.css'],

  i18n: {
    locales: [
      {
        code: 'en',
        name: 'English',
        file: 'en.json'
      },
      {
        code: 'km',
        name: 'ភាសាខ្មែរ',
        file: 'km.json'
      }
    ],
    defaultLocale: 'en',
    strategy: 'no_prefix',
    langDir: 'locales',
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: 'i18n_redirected',
      alwaysRedirect: true,
      redirectOn: 'root'
    }
  },

  routeRules: {
    '/api/**': {
      cors: true
    }
  },

  runtimeConfig: {
    public: {
      apiBase:
        process.env.NUXT_PUBLIC_API_BASE
        || process.env.VITE_API_BASE_URL
        || (process.env.NODE_ENV === 'production' ? PRODUCTION_API_BASE : DEV_API_BASE),
      useBackendApi: import.meta.env.NUXT_PUBLIC_USE_BACKEND_API !== 'false',
      /** Layout/design mode: auto session, no auth gates, no API calls, permissive login form */
      uiOnly: import.meta.env.NUXT_PUBLIC_UI_ONLY === 'true'
    }
  },

  compatibilityDate: '2024-07-11',

  nitro: {
    preset: 'static',
    prerender: {
      crawlLinks: false,
    },
  },

  vite: {
    build: {
      chunkSizeWarningLimit: 1000,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) return
            if (id.includes('echarts') || id.includes('vue-echarts')) return 'charts'
          }
        }
      }
    }
  }
})