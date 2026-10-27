import { Bell, AlertTriangle, TrendingDown, CheckCircle } from 'lucide-react'
import { MetricCard } from '../ui/MetricCard'
import { CardSkeleton } from '../ui/Skeleton'
import type { AlertSummary } from '../../types/alert'
import { useTranslation } from '../../i18n/context'

interface DashboardStatsProps {
  alerts: AlertSummary[] | undefined
  isLoading: boolean
}

export function DashboardStats({ alerts, isLoading }: DashboardStatsProps) {
  const { t } = useTranslation()
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <CardSkeleton key={i} />
        ))}
      </div>
    )
  }

  const totalAlerts = alerts?.length ?? 0
  const openAlerts = alerts?.filter((a) => a.status === 'OPEN').length ?? 0
  const p0Count = alerts?.filter((a) => a.severity === 'P0' && a.status !== 'RESOLVED').length ?? 0
  const avgDelta = totalAlerts
    ? alerts!.reduce((sum, a) => sum + a.revenue_delta_pct, 0) / totalAlerts
    : 0

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
      <MetricCard
        label={t('dashboard.total_alerts')}
        value={totalAlerts}
        format="number"
        subtitle={t('dashboard.all_severities')}
        icon={<Bell size={18} />}
        iconBg="bg-blue-50"
        iconColor="text-blue-500"
        accentColor="bg-blue-500"
      />
      <MetricCard
        label={t('dashboard.open_alerts')}
        value={openAlerts}
        format="number"
        subtitle={t('dashboard.pending_action')}
        icon={<AlertTriangle size={18} />}
        iconBg="bg-amber-50"
        iconColor="text-amber-500"
        accentColor="bg-amber-500"
      />
      <MetricCard
        label={t('dashboard.p0_active')}
        value={p0Count}
        format="number"
        subtitle={t('dashboard.critical_severity')}
        icon={<TrendingDown size={18} />}
        iconBg="bg-red-50"
        iconColor="text-red-500"
        accentColor="bg-red-500"
      />
      <MetricCard
        label={t('dashboard.avg_revenue_delta')}
        value={avgDelta}
        format="percent"
        subtitle={t('dashboard.across_all_alerts')}
        icon={<CheckCircle size={18} />}
        iconBg="bg-emerald-50"
        iconColor="text-emerald-500"
        accentColor="bg-emerald-500"
      />
    </div>
  )
}
