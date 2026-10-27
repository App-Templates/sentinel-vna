import { useCallback } from 'react'
import { RefreshCw } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useAlerts, useRevenueStatus24h } from '../api/client'
import { useAlertFilters } from '../hooks/useAlertFilters'
import { useAutoRefresh } from '../hooks/useAutoRefresh'
import { DashboardStats } from '../components/dashboard/DashboardStats'
import { KpiCards } from '../components/dashboard/KpiCards'
import { RevenueStatus24h } from '../components/dashboard/RevenueStatus24h'
import { RevenueByChannel } from '../components/dashboard/RevenueByChannel'
import { AlertsFilter } from '../components/dashboard/AlertsFilter'
import { AlertsTable } from '../components/dashboard/AlertsTable'
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card'

export function DashboardPage() {
  const { filters, setFilter, clearFilters, hasActiveFilters } = useAlertFilters()
  const { data: alerts, isLoading, error } = useAlerts(filters)
  const { data: revenueData, isLoading: revenueLoading } = useRevenueStatus24h()
  const queryClient = useQueryClient()
  const handleRefresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['alerts'] })
  }, [queryClient])

  const { isActive, lastRefresh } = useAutoRefresh({
    intervalMs: 30_000,
    onRefresh: handleRefresh,
  })

  return (
    <div className="space-y-6">
      {/* Stats row */}
      <DashboardStats alerts={alerts} isLoading={isLoading} />

      {/* KPI cards: RPM, CTR, Viewability, Gross Margin */}
      <KpiCards data={revenueData} isLoading={revenueLoading} />

      {/* Revenue Status 24h chart */}
      <RevenueStatus24h />

      {/* Revenue by Channel */}
      <RevenueByChannel />

      {/* Alerts table with filters */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle>Recent Alerts</CardTitle>
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1.5 text-xs text-slate-400">
                <RefreshCw
                  size={12}
                  className={isActive ? 'animate-spin text-green-500' : ''}
                />
                {isActive
                  ? `Auto-refresh on (last: ${lastRefresh.toLocaleTimeString()})`
                  : 'Auto-refresh paused'}
              </span>
            </div>
          </div>
          <div className="mt-3">
            <AlertsFilter
              severity={filters.severity ?? ''}
              status={filters.status ?? ''}
              channelGroup={filters.channel_group ?? ''}
              fromDate={filters.from_date ?? ''}
              toDate={filters.to_date ?? ''}
              assignedTo={filters.assigned_to ?? ''}
              onSeverityChange={(v) => setFilter('severity', v)}
              onStatusChange={(v) => setFilter('status', v)}
              onChannelGroupChange={(v) => setFilter('channel_group', v)}
              onFromDateChange={(v) => setFilter('from_date', v)}
              onToDateChange={(v) => setFilter('to_date', v)}
              onAssignedToChange={(v) => setFilter('assigned_to', v)}
              onClear={clearFilters}
              hasActiveFilters={hasActiveFilters}
            />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <AlertsTable
            data={alerts}
            isLoading={isLoading}
            error={error}
          />
        </CardContent>
      </Card>
    </div>
  )
}
