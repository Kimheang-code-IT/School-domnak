import type { DropdownMenuItem } from '~/types/nuxt-ui'

export function useUserMenu() {
  const auth = useAuthStore()
  const colorMode = useColorMode()
  const i18n = useI18n()
  const { t } = i18n

  const defaultPrimaryColor = 'blue'
  const defaultNeutralColor = 'zinc'
  const colors = [
    'slate',
    'gray',
    'zinc',
    'neutral',
    'stone',
    'red',
    'orange',
    'amber',
    'yellow',
    'lime',
    'green',
    'emerald',
    'teal',
    'cyan',
    'sky',
    'blue',
    'indigo',
    'violet',
    'purple',
    'fuchsia',
    'pink',
    'rose',
  ]
  const neutrals = ['slate', 'gray', 'zinc', 'neutral']

  const primaryColor = useCookie<string>('ui-primary-color', {
    default: () => defaultPrimaryColor,
    sameSite: 'lax'
  })
  const neutralColor = useCookie<string>('ui-neutral-color', {
    default: () => defaultNeutralColor,
    sameSite: 'lax'
  })

  const currentPrimary = computed(() =>
    colors.includes(primaryColor.value || '') ? (primaryColor.value as string) : defaultPrimaryColor
  )
  const currentNeutral = computed(() =>
    neutrals.includes(neutralColor.value || '') ? (neutralColor.value as string) : defaultNeutralColor
  )

  const applyThemeColors = (primary: string, neutral: string) => {
    updateAppConfig({
      ui: {
        colors: {
          primary,
          neutral
        }
      }
    })
  }

  if (primaryColor.value !== currentPrimary.value) {
    primaryColor.value = currentPrimary.value
  }
  if (neutralColor.value !== currentNeutral.value) {
    neutralColor.value = currentNeutral.value
  }

  applyThemeColors(currentPrimary.value, currentNeutral.value)

  const user = computed(() => {
    const name = auth.user?.name || auth.user?.email || 'User'

    return {
      name,
      avatar: {
        src: `https://ui-avatars.com/api/?name=${encodeURIComponent(name)}&background=random`,
        alt: name,
      },
    }
  })

  const router = useRouter()
  const session = useAuthSessionManager()

  async function handleLogout(e?: Event) {
    e?.preventDefault()
    await auth.logout()
    session.clearSession()

    if (import.meta.client) {
      window.location.replace('/login')
      return
    }

    await router.replace('/login')
  }

  const items = computed<DropdownMenuItem[][]>(() => [
    [
      {
        type: 'label',
        label: user.value.name,
        avatar: user.value.avatar,
      },
    ],
    [
      {
        label: t('settings.history'),
        icon: 'i-lucide-clock',
        onSelect(e: Event) {
          e.preventDefault()
          router.push('/history')
        },
      },
    ],
    [
      {
        label: t('settings.language'),
        icon: 'i-lucide-languages',
        children: (i18n.locales.value || []).map((loc: any) => ({
          label: loc.name,
          icon: loc.icon,
          type: 'checkbox',
          checked: i18n.locale.value === loc.code,
          onSelect: (e: Event) => {
            e.preventDefault()
            i18n.setLocale(loc.code)
          }
        }))
      },
      {
        label: t('settings.theme'),
        icon: 'i-lucide-palette',
        children: [
          {
            label: t('settings.primary'),
            slot: 'chip',
            chip: currentPrimary.value,
            content: {
              align: 'center',
              collisionPadding: 16,
            },
            children: colors.map((color) => ({
              label: color,
              chip: color,
              slot: 'chip',
              checked: currentPrimary.value === color,
              type: 'checkbox',
              onSelect: (e: Event) => {
                e.preventDefault()
                primaryColor.value = color
                applyThemeColors(color, currentNeutral.value)
              },
            })),
          },
          {
            label: t('settings.neutral'),
            slot: 'chip',
            chip:
              currentNeutral.value === 'neutral'
                ? 'old-neutral'
                : currentNeutral.value,
            content: {
              align: 'end',
              collisionPadding: 16,
            },
            children: neutrals.map((color) => ({
              label: color,
              chip: color === 'neutral' ? 'old-neutral' : color,
              slot: 'chip',
              type: 'checkbox',
              checked: currentNeutral.value === color,
              onSelect: (e: Event) => {
                e.preventDefault()
                neutralColor.value = color
                applyThemeColors(currentPrimary.value, color)
              },
            })),
          },
        ],
      },
      {
        label: t('settings.appearance'),
        icon: 'i-lucide-sun-moon',
        children: [
          {
            label: t('settings.light'),
            icon: 'i-lucide-sun',
            type: 'checkbox',
            checked: colorMode.value === 'light',
            onSelect(e: Event) {
              e.preventDefault()
              colorMode.preference = 'light'
            },
          },
          {
            label: t('settings.dark'),
            icon: 'i-lucide-moon',
            type: 'checkbox',
            checked: colorMode.value === 'dark',
            onUpdateChecked(checked: boolean) {
              if (checked) {
                colorMode.preference = 'dark'
              }
            },
            onSelect(e: Event) {
              e.preventDefault()
            },
          },
        ],
      },
    ],
    [
      {
        label: t('settings.logout'),
        icon: 'i-lucide-log-out',
        color: 'error',
        onSelect: handleLogout,
      },
    ],
  ])

  return {
    user,
    items,
    handleLogout,
  }
}
