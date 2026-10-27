import { useHealth } from '../api/client'
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card'
import { Skeleton } from '../components/ui/Skeleton'
import { Activity, Database, Clock, Cpu } from 'lucide-react'
import { formatTimestamp } from '../lib/utils'

function StatusDot({ ok, label }: { ok: boolean; label?: string }) {
  return (
    <span className="flex items-center gap-2">
      <span
        className={`inline-block h-2.5 w-2.5 rounded-full ${ok ? 'bg-green-500' : 'bg-red-500'}`}
      />
      <span className="capitalize">{label ?? (ok ? 'healthy' : 'unhealthy')}</span>
    </span>
  )
}

export function HealthPage() {
  const { data: health, isLoading, error } = useHealth()

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      </div>
    )
  }

  if (error || !health) {
    return (
      <div className="py-12 text-center text-red-500">
        Failed to load health status.
      </div>
    )
  }

  const overallStatus = health.status ?? 'unknown'
  const version = health.version ?? '?'
  const dbOk = health.db_ok ?? false
  const schedulerRunning = health.scheduler_running ?? false
  const timestamp = health.timestamp ?? ''

  const services = [
    { label: 'Database', ok: dbOk, icon: Database },
    { label: 'Scheduler', ok: schedulerRunning, icon: Clock },
    {
      label: 'Overall',
      ok: overallStatus === 'healthy',
      icon: Cpu,
      statusLabel: overallStatus,
    },
  ]

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity size={20} />
            System Health
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
            {services.map((svc) => (
              <div
                key={svc.label}
                className="flex items-center gap-4 rounded-lg border border-slate-200 bg-white p-5"
              >
                <div className="rounded-lg bg-slate-100 p-3">
                  <svc.icon size={24} className="text-slate-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-slate-500">{svc.label}</p>
                  <StatusDot ok={svc.ok} label={svc.statusLabel} />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-6 flex items-center gap-4 text-xs text-slate-400">
            <span>Version: {version}</span>
            {timestamp && <span>Last check: {formatTimestamp(timestamp)}</span>}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
