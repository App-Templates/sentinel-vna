import { useLocation } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { useTranslation } from '../../i18n/context'

export function Header() {
  const location = useLocation()
  const { t } = useTranslation()

  const pageTitles: Record<string, string> = {
    '/dashboard': t('page.dashboard'),
    '/alerts': t('page.alerts'),
    '/publishers': t('page.publishers'),
    '/backtest': t('page.backtest'),
    '/health': t('page.health'),
    '/docs': t('page.docs'),
    '/admin': t('page.admin'),
  }

  const pathRoot = '/' + location.pathname.split('/')[1]
  const title = pageTitles[pathRoot] ?? 'Value Network Alerting'

  const segments = location.pathname.split('/').filter(Boolean)
  const breadcrumbs = segments.map((seg, i) => ({
    label: pageTitles['/' + seg] ?? seg,
    path: '/' + segments.slice(0, i + 1).join('/'),
    isLast: i === segments.length - 1,
  }))

  return (
    <header className="flex h-14 items-center border-b border-slate-200 bg-white px-6">
      <div>
        <h1 className="text-base font-semibold text-slate-900">{title}</h1>
        {breadcrumbs.length > 1 && (
          <nav className="flex items-center gap-1 text-xs text-slate-400" aria-label="Breadcrumb">
            {breadcrumbs.map((crumb, i) => (
              <span key={crumb.path} className="flex items-center gap-1">
                {i > 0 && <ChevronRight size={11} className="text-slate-300" />}
                <span className={crumb.isLast ? 'font-medium text-slate-600' : ''}>
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
