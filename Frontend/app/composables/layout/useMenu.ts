import type { NavigationMenuItem } from '~/types/nuxt-ui'
import { PERMISSIONS, type Permission } from '~/utils/auth/permissions'

type MenuLink = NavigationMenuItem & {
  permission?: Permission
  children?: MenuLink[]
}

export const useMenu = () => {
  const open = ref(false)
  const { t } = useI18n()
  const auth = useAuthStore()

  const rawLinks = computed(() => [[
    {
      label: t('navigation.dashboard'),
      icon: 'i-lucide-grid-2x2',
      to: '/',
      permission: PERMISSIONS.dashboardView,
      class: 'text-md gap-2',
      onSelect: () => { open.value = false },
    },
    {
      label: t('pages.category.title'),
      icon: 'i-lucide-swatch-book',
      to: '/category',
      permission: PERMISSIONS.categoryView,
      class: 'my-2 text-md gap-2',
      onSelect: () => { open.value = false },
    },
    {
      label: t('pages.courses.title'),
      icon: 'i-lucide-book-open',
      to: '/courses',
      permission: PERMISSIONS.coursesView,
      class: 'my-2 text-md gap-2',
      onSelect: () => { open.value = false },
    },
    {
      label: t('pages.levels.title'),
      icon: 'i-lucide-layers',
      to: '/levels',
      permission: PERMISSIONS.levelsView,
      class: 'my-2 text-md gap-2',
      onSelect: () => { open.value = false },
    },
    {
      label: t('pages.allclass.title'),
      icon: 'i-lucide-house',
      to: '/allclass',
      permission: PERMISSIONS.allClassView,
      class: 'my-2 text-md gap-2',
      onSelect: () => { open.value = false },
    },
    {
      label: t('pages.allstudent.title'),
      icon: 'i-lucide-square-user-round',
      to: '/allstudent',
      permission: PERMISSIONS.allStudentView,
      class: 'my-2 text-md gap-2',
      onSelect: () => { open.value = false },
    },
    {
      label: t('pages.report.title'),
      icon: 'i-lucide-file-bar-chart',
      to: '/report',
      permission: PERMISSIONS.reportView,
      class: 'my-2 text-md gap-2',
      onSelect: () => { open.value = false },
    },
    {
      label: t('pages.comission.title'),
      icon: 'i-lucide-badge-percent',
      to: '/comission',
      permission: PERMISSIONS.comissionView,
      class: 'my-2 text-md gap-2',
      onSelect: () => { open.value = false },
    },
    {
      label: t('pages.finance.title'),
      icon: 'i-lucide-landmark',
      to: '/finance',
      permission: PERMISSIONS.financeView,
      class: 'my-2 text-md gap-2',
      onSelect: () => { open.value = false },
    },
    {
      label: t('navigation.settings'),
      icon: 'i-lucide-settings',
      type: 'trigger',
      class: 'my-2 text-md gap-2',
      children: [
        {
          label: t('pages.userManagement.title'),
          to: '/settings/user-management',
          permission: PERMISSIONS.settingsUserView,
          class: 'text-md gap-2',
          onSelect: () => { open.value = false },
        },
        {
          label: t('pages.roleManagement.title'),
          to: '/settings/role-management',
          permission: PERMISSIONS.settingsRoleView,
          class: 'my-2 text-md gap-2',
          onSelect: () => { open.value = false },
        },
      ],
    },
  ], []] as MenuLink[][])

  function canSeeMenuItem(item: MenuLink): boolean {
    if (item.children?.length) {
      const visibleChildren = item.children.filter(
        (child) => !child.permission || auth.hasPermission(child.permission),
      )
      return visibleChildren.length > 0
    }
    if (!item.permission) return true
    return auth.hasPermission(item.permission)
  }

  function filterMenuItem(item: MenuLink): MenuLink | null {
    if (!canSeeMenuItem(item)) return null
    if (item.children?.length) {
      const children = item.children
        .filter((child) => !child.permission || auth.hasPermission(child.permission))
        .map((child) => ({ ...child }))
      if (!children.length) return null
      const firstChild = children[0]
      return {
        ...item,
        to: firstChild?.to,
        children,
      }
    }
    return { ...item }
  }

  const links = computed(() =>
    rawLinks.value.map((group) =>
      group
        .map((item) => filterMenuItem(item))
        .filter((item): item is MenuLink => item != null),
    ),
  )

  return {
    open,
    links,
  }
}
