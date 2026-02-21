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

const navItems: NavItem[] = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/alerts', label: 'Alerts', icon: Bell },
  { to: '/publishers', label: 'Top Publishers', icon: BarChart3 },
  { to: '/backtest', label: 'Backtest', icon: FlaskConical },
  { to: '/health', label: 'Health', icon: Activity },
]

const navGroups: NavGroup[] = [
  {
    prefix: '/docs',
    label: 'Docs & FAQ',
    icon: BookOpen,
    defaultTo: '/docs/operativo',
    children: [
      { to: '/docs/operativo', label: 'Operativo', icon: AlertTriangle },
      { to: '/docs/tecnico', label: 'Tecnico', icon: Server },
    ],
  },
  {
    prefix: '/admin',
    label: 'Admin',
    icon: Settings,
    defaultTo: '/admin/datasources',
    children: [
      { to: '/admin/datasources', label: 'Data Sources', icon: Database },
      { to: '/admin/rules', label: 'Alerting Rules', icon: SlidersHorizontal },
    ],
  },
]

function NavGroupItem({ group, collapsed, pathname }: { group: NavGroup; collapsed: boolean; pathname: string }) {
  const isActive = pathname.startsWith(group.prefix)
  const [open, setOpen] = useState(isActive)

  if (collapsed) {
    return (
      <NavLink
        to={group.defaultTo}
        className={cn(
          'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
          isActive ? 'bg-gray-800 text-white' : 'text-gray-400 hover:bg-gray-800 hover:text-white'
        )}
      >
        <group.icon size={20} className="shrink-0" />
      </NavLink>
    )
  }

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          'flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
          isActive ? 'text-white' : 'text-gray-400 hover:bg-gray-800 hover:text-white'
        )}
      >
        <group.icon size={20} className="shrink-0" />
        <span className="flex-1 text-left">{group.label}</span>
        <ChevronDown size={14} className={cn('transition-transform', open ? 'rotate-0' : '-rotate-90')} />
      </button>
      {open && (
        <div className="ml-5 space-y-0.5 border-l border-gray-700 pl-3">
          {group.children.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive: active }) =>
                cn(
                  'flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm transition-colors',
                  active ? 'bg-gray-800 text-white font-medium' : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                )
              }
            >
              <item.icon size={16} className="shrink-0" />
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

  const showUser = user && user.email !== 'dev@localhost'

  return (
    <aside
      className={cn(
        'flex h-screen flex-col bg-gray-900 text-gray-300 transition-all duration-200',
        collapsed ? 'w-16' : 'w-60'
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center gap-2 border-b border-gray-800 px-4">
        <Zap size={24} className="shrink-0 text-blue-400" />
        {!collapsed && (
          <span className="text-lg font-bold text-white">Sentinel</span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-2 py-4">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-gray-800 text-white'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              )
            }
          >
            <item.icon size={20} className="shrink-0" />
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}

        {navGroups.map((group) => (
          <NavGroupItem key={group.prefix} group={group} collapsed={collapsed} pathname={location.pathname} />
        ))}
      </nav>

      {/* User info + Collapse toggle */}
      <div className="border-t border-gray-800 p-2">
        {showUser && (
          <div className="mb-2 flex items-center gap-2 rounded-md px-2 py-2">
            {user.picture ? (
              <img
                src={user.picture}
                alt=""
                className="h-8 w-8 shrink-0 rounded-full"
                referrerPolicy="no-referrer"
              />
            ) : (
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-sm font-medium text-white">
                {user.name?.[0] ?? '?'}
              </div>
            )}
            {!collapsed && (
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-white">{user.name}</p>
                <button
                  onClick={logout}
                  className="flex items-center gap-1 text-xs text-gray-400 hover:text-white"
                >
                  <LogOut size={12} />
                  Logout
                </button>
              </div>
            )}
          </div>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex w-full items-center justify-center rounded-md p-2 text-gray-400 hover:bg-gray-800 hover:text-white"
        >
          {collapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
        </button>
      </div>
    </aside>
  )
}
