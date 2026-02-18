import { Bell, AlertTriangle, TrendingDown, CheckCircle } from 'lucide-react'
import { MetricCard } from '../ui/MetricCard'
import { CardSkeleton } from '../ui/Skeleton'
import type { AlertSummary } from '../../types/alert'

interface DashboardStatsProps {
  alerts: AlertSummary[] | undefined
  isLoading: boolean
}

export function DashboardStats({ alerts, isLoading }: DashboardStatsProps) {
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
        label="Total Alerts"
        value={totalAlerts}
        format="number"
        icon={<Bell size={20} />}
      />
      <MetricCard
        label="Open Alerts"
        value={openAlerts}
        format="number"
        icon={<AlertTriangle size={20} />}
      />
      <MetricCard
        label="P0 Active"
        value={p0Count}
        format="number"
        icon={<TrendingDown size={20} />}
      />
      <MetricCard
        label="Avg Revenue Delta"
        value={avgDelta}
        format="percent"
        icon={<CheckCircle size={20} />}
      />
    </div>
  )
}
