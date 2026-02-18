import { useLocation } from 'react-router-dom'

const pageTitles: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/alerts': 'Alerts',
  '/backtest': 'Backtest',
  '/health': 'System Health',
}

export function Header() {
  const location = useLocation()

  // Match the path for titles (handle /alerts/:id)
  const pathRoot = '/' + location.pathname.split('/')[1]
  const title = pageTitles[pathRoot] ?? 'Value Network Alerting'

  // Build breadcrumbs
  const segments = location.pathname.split('/').filter(Boolean)
  const breadcrumbs = segments.map((seg, i) => ({
    label: pageTitles['/' + seg] ?? seg,
    path: '/' + segments.slice(0, i + 1).join('/'),
    isLast: i === segments.length - 1,
  }))

  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">{title}</h1>
        {breadcrumbs.length > 1 && (
          <nav className="flex items-center gap-1 text-xs text-gray-500">
            {breadcrumbs.map((crumb, i) => (
              <span key={crumb.path}>
                {i > 0 && <span className="mx-1">/</span>}
                <span className={crumb.isLast ? 'text-gray-900' : ''}>
                  {crumb.label}
                </span>
              </span>
            ))}
          </nav>
        )}
      </div>
    </header>
  )
}
