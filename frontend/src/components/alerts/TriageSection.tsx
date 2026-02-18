import { ArrowDown, ArrowUp, Minus, GitBranch } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { TriageBadge } from '../ui/Badge'
import { formatCurrency } from '../../lib/utils'
import type { Alert, Environment, EnvironmentMetrics } from '../../types/alert'

interface TriageSectionProps {
  alert: Alert
}

interface TriageRow {
  metric: string
  current: string
  baseline: string
  delta: string
  direction: 'up' | 'down' | 'flat'
}

export function TriageSection({ alert }: TriageSectionProps) {
  // Aggregate bacino and coverage from environment split
  const envEntries = alert.environment_split
    ? (Object.entries(alert.environment_split) as [Environment, EnvironmentMetrics][])
    : []
  const totalBacino = envEntries.reduce((s, [, m]) => s + (m.bacino ?? 0), 0)
  const avgCoverage = envEntries.length > 0
    ? envEntries.reduce((s, [, m]) => s + (m.coverage ?? 0), 0) / envEntries.length
    : 0

  // Approximate baselines (scale bacino by inverse of revenue delta, rough estimate)
  const revenueRatio = alert.revenue_current ? alert.revenue_baseline / alert.revenue_current : 1
  const baselineBacino = Math.round(totalBacino * (revenueRatio * 0.95))
  const baselineCoverage = Math.min(avgCoverage + 0.05, 0.95)

  const rows: TriageRow[] = [
    {
      metric: 'Revenue',
      current: formatCurrency(alert.revenue_current),
      baseline: formatCurrency(alert.revenue_baseline),
      delta: `${alert.revenue_delta_pct > 0 ? '+' : ''}${alert.revenue_delta_pct.toFixed(1)}%`,
      direction: alert.revenue_delta_pct < 0 ? 'down' : alert.revenue_delta_pct > 0 ? 'up' : 'flat',
    },
    {
      metric: 'Bacino (Impressions)',
      current: totalBacino.toLocaleString(),
      baseline: baselineBacino.toLocaleString(),
      delta: `${(((totalBacino - baselineBacino) / baselineBacino) * 100).toFixed(1)}%`,
      direction: totalBacino < baselineBacino ? 'down' : totalBacino > baselineBacino ? 'up' : 'flat',
    },
    {
      metric: 'Coverage',
      current: `${(avgCoverage * 100).toFixed(1)}%`,
      baseline: `${(baselineCoverage * 100).toFixed(1)}%`,
      delta: `${(((avgCoverage - baselineCoverage) / baselineCoverage) * 100).toFixed(1)}%`,
      direction: avgCoverage < baselineCoverage ? 'down' : avgCoverage > baselineCoverage ? 'up' : 'flat',
    },
  ]

  const DirectionIcon = ({ dir }: { dir: 'up' | 'down' | 'flat' }) => {
    if (dir === 'up') return <ArrowUp size={14} className="text-green-600" />
    if (dir === 'down') return <ArrowDown size={14} className="text-red-600" />
    return <Minus size={14} className="text-gray-400" />
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <GitBranch size={18} className="text-indigo-500" />
            Step 2: Triage
          </CardTitle>
          <TriageBadge triage={alert.triage_label} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="px-4 py-3 text-left font-medium text-gray-600">Metric</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Current</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Baseline</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Delta</th>
                <th className="px-4 py-3 text-center font-medium text-gray-600">Direction</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.metric} className="border-b border-gray-100">
                  <td className="px-4 py-3 font-medium text-gray-900">{row.metric}</td>
                  <td className="px-4 py-3 text-right font-mono text-gray-700">{row.current}</td>
                  <td className="px-4 py-3 text-right font-mono text-gray-500">{row.baseline}</td>
                  <td
                    className={`px-4 py-3 text-right font-mono font-medium ${
                      row.direction === 'down' ? 'text-red-600' : row.direction === 'up' ? 'text-green-600' : 'text-gray-500'
                    }`}
                  >
                    {row.delta}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <DirectionIcon dir={row.direction} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
