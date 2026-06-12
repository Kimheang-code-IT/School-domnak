// nuxt.config.ts
// https://nuxt.com/docs/api/configuration/nuxt-config

export default defineNuxtConfig({
  modules: [
    '@nuxt/ui',
    '@nuxt/image',
    '@vueuse/nuxt',
    '@nuxtjs/i18n',
    '@nuxt/fonts',
    '@pinia/nuxt'
  ],

  devtools: {
    enabled: true
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
        import.meta.env.NUXT_PUBLIC_API_BASE
        || import.meta.env.VITE_API_BASE_URL
        || 'http://localhost:8000/api/v1',
      useBackendApi: import.meta.env.NUXT_PUBLIC_USE_BACKEND_API !== 'false',
      /** Layout/design mode: auto session, no auth gates, no API calls, permissive login form */
      uiOnly: import.meta.env.NUXT_PUBLIC_UI_ONLY === 'true'
    }
  },

  compatibilityDate: '2024-07-11',

  nitro: {
    preset: 'static',
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