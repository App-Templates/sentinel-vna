import { useCallback } from 'react'
import { RefreshCw, Bell } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useAlerts } from '../api/client'
import { useAlertFilters } from '../hooks/useAlertFilters'
import { useAutoRefresh } from '../hooks/useAutoRefresh'
import { AlertsFilter } from '../components/dashboard/AlertsFilter'
import { AlertsTable } from '../components/dashboard/AlertsTable'
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card'

export function AlertsListPage() {
  const { filters, setFilter, clearFilters, hasActiveFilters } = useAlertFilters()
  const { data: alerts, isLoading, error } = useAlerts(filters)
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
      <div className="flex items-center justify-between">
        <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
          <Bell size={24} />
          Alerts
        </h1>
        <span className="flex items-center gap-1.5 text-xs text-gray-400">
          <RefreshCw
            size={12}
            className={isActive ? 'animate-spin text-green-500' : ''}
          />
          {isActive
            ? `Auto-refresh on (last: ${lastRefresh.toLocaleTimeString()})`
            : 'Auto-refresh paused'}
        </span>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle>
              All Alerts {alerts ? `(${alerts.length})` : ''}
            </CardTitle>
          </div>
          <div className="mt-3">
            <AlertsFilter
              severity={filters.severity ?? ''}
              status={filters.status ?? ''}
              channelGroup={filters.channel_group ?? ''}
              fromDate={filters.from_date ?? ''}
              toDate={filters.to_date ?? ''}
              onSeverityChange={(v) => setFilter('severity', v)}
              onStatusChange={(v) => setFilter('status', v)}
              onChannelGroupChange={(v) => setFilter('channel_group', v)}
              onFromDateChange={(v) => setFilter('from_date', v)}
              onToDateChange={(v) => setFilter('to_date', v)}
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
            pageSize={20}
          />
        </CardContent>
      </Card>
    </div>
  )
}
