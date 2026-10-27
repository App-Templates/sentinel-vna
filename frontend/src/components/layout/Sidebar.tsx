import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import type { LucideIcon } from 'lucide-react'
import {
  LayoutDashboard,
  Bell,
  BarChart3,
  FlaskConical,
  Activity,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Zap,
  Settings,
  LogOut,
  BookOpen,
  Database,
  SlidersHorizontal,
  AlertTriangle,
  Server,
} from 'lucide-react'
import { cn } from '../../lib/utils'
import { useAuthContext } from '../auth/AuthGuard'
import { useTranslation } from '../../i18n/context'
import { LanguageSwitcher } from '../ui/LanguageSwitcher'

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
}

interface NavGroup {
  prefix: string
  label: string
  icon: LucideIcon
  defaultTo: string
  children: NavItem[]
}

function useNavItems() {
  const { t } = useTranslation()
  const items: NavItem[] = [
    { to: '/dashboard', label: t('nav.dashboard'), icon: LayoutDashboard },
    { to: '/alerts', label: t('nav.alerts'), icon: Bell },
    { to: '/publishers', label: t('nav.publishers'), icon: BarChart3 },
    { to: '/backtest', label: t('nav.backtest'), icon: FlaskConical },
    { to: '/health', label: t('nav.health'), icon: Activity },
  ]
  const groups: NavGroup[] = [
    {
      prefix: '/docs',
      label: t('nav.docs'),
      icon: BookOpen,
      defaultTo: '/docs/operativo',
      children: [
        { to: '/docs/operativo', label: t('nav.docs_operative'), icon: AlertTriangle },
        { to: '/docs/tecnico', label: t('nav.docs_technical'), icon: Server },
      ],
    },
    {
      prefix: '/admin',
      label: t('nav.admin'),
      icon: Settings,
      defaultTo: '/admin/datasources',
      children: [
        { to: '/admin/datasources', label: t('nav.admin_datasources'), icon: Database },
        { to: '/admin/rules', label: t('nav.admin_rules'), icon: SlidersHorizontal },
      ],
    },
  ]
  return { navItems: items, navGroups: groups }
}

const navLinkBase =
  'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-all duration-150'

const navLinkActive = 'bg-blue-600 text-white shadow-sm'
const navLinkInactive = 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'

function NavGroupItem({
  group,
  collapsed,
  pathname,
}: {
  group: NavGroup
  collapsed: boolean
  pathname: string
}) {
  const isActive = pathname.startsWith(group.prefix)
  const [open, setOpen] = useState(isActive)

  if (collapsed) {
    return (
      <NavLink
        to={group.defaultTo}
        className={cn(navLinkBase, isActive ? navLinkActive : navLinkInactive)}
      >
        <group.icon size={18} className="shrink-0" />
      </NavLink>
    )
  }

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          navLinkBase,
          'w-full',
          isActive ? 'text-slate-100' : navLinkInactive
        )}
      >
        <group.icon size={18} className="shrink-0" />
        <span className="flex-1 text-left">{group.label}</span>
        <ChevronDown
          size={13}
          className={cn(
            'transition-transform duration-200',
            open ? 'rotate-0' : '-rotate-90'
          )}
        />
      </button>
      {open && (
        <div className="ml-5 mt-0.5 space-y-0.5 border-l border-slate-700 pl-3">
          {group.children.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive: active }) =>
                cn(
                  'flex items-center gap-2 rounded-md px-2.5 py-1.5 text-xs font-medium transition-all duration-150',
                  active
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'
                )
              }
            >
              <item.icon size={14} className="shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </div>
      )}
    </div>
  )
}

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const { user, logout } = useAuthContext()
  const location = useLocation()
  const { navItems, navGroups } = useNavItems()

  const showUser = user && user.email !== 'dev@localhost'

  return (
    <aside
      className={cn(
        'flex h-screen flex-col bg-slate-900 transition-all duration-200',
        collapsed ? 'w-[60px]' : 'w-[220px]'
      )}
    >
      {/* Logo */}
      <div
        className={cn(
          'flex h-14 items-center gap-2.5 border-b border-slate-800',
          collapsed ? 'justify-center px-3' : 'px-4'
        )}
      >
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-blue-600 shadow-sm">
          <Zap size={14} className="text-white" />
        </div>
        {!collapsed && (
          <div>
            <span className="text-sm font-bold tracking-tight text-white">Sentinel</span>
            <span className="ml-1.5 rounded bg-slate-700 px-1 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              VNA
            </span>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(navLinkBase, isActive ? navLinkActive : navLinkInactive)
            }
          >
            <item.icon size={18} className="shrink-0" />
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}

        <div className="my-2 border-t border-slate-800" />

        {navGroups.map((group) => (
          <NavGroupItem
            key={group.prefix}
            group={group}
            collapsed={collapsed}
            pathname={location.pathname}
          />
        ))}
      </nav>

      {/* User + Collapse */}
      <div className="border-t border-slate-800 p-2">
        {showUser && !collapsed && (
          <div className="mb-1.5 flex items-center gap-2 rounded-md px-2 py-1.5">
            {user.picture ? (
              <img
                src={user.picture}
                alt=""
                className="h-7 w-7 shrink-0 rounded-full"
                referrerPolicy="no-referrer"
              />
            ) : (
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-semibold text-white">
                {user.name?.[0] ?? '?'}
              </div>
            )}
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-medium text-slate-200">{user.name}</p>
              <button
                onClick={logout}
                className="flex items-center gap-1 text-[11px] text-slate-500 transition-colors duration-150 hover:text-slate-200"
              >
                <LogOut size={11} />
                Logout
              </button>
            </div>
          </div>
        )}
        <LanguageSwitcher collapsed={collapsed} />
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex w-full items-center justify-center rounded-md p-2 text-slate-500 transition-all duration-150 hover:bg-slate-800 hover:text-slate-200"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>
    </aside>
  )
}
