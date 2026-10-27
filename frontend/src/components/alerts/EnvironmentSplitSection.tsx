import { Monitor, Smartphone, Tablet, AlertTriangle } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { DeltaIndicator } from '../ui/DeltaIndicator'
import { Badge } from '../ui/Badge'
import { EnvironmentBarChart } from '../charts/EnvironmentBarChart'
import { ChartErrorBoundary } from '../primitives/ChartErrorBoundary'
import { formatCurrency } from '../../lib/utils'
import type { Environment, EnvironmentMetrics } from '../../types/alert'

interface EnvironmentSplitSectionProps {
  environmentSplit: Record<Environment, EnvironmentMetrics>
}

const envIcons: Record<Environment, React.ReactNode> = {
  WEB: <Monitor size={20} className="text-blue-500" />,
  AMP: <Tablet size={20} className="text-orange-500" />,
  APP: <Smartphone size={20} className="text-green-500" />,
  UNKNOWN: <Monitor size={20} className="text-gray-400" />,
}

export function EnvironmentSplitSection({ environmentSplit }: EnvironmentSplitSectionProps) {
  if (!environmentSplit || Object.keys(environmentSplit).length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Monitor size={18} className="text-purple-500" />
            Step 5: Environment Split
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="py-4 text-center text-sm text-gray-400">No environment data available.</p>
        </CardContent>
      </Card>
    )
  }

  // Phase 17.2 GAP-CLOSURE (UAT Check 5+6, 2026-05-20):
  // The payload's `environment_split` carries sibling scalar keys like
  // `amp_drift_detected: true` alongside the per-env dicts (WEB/AMP/APP).
  // Iterating with a naive Object.entries treats those scalars as if they
  // were EnvironmentMetrics — every property read returns undefined,
  // throws on `.toFixed(...)` in the JSX, AlertDetailPage's error boundary
  // catches it, all tabs go blank. Mirror the predicate Wave 1 (HOTFIX-05)
  // applied in TriageSection.tsx and read the new payload field names.
  const entries = (Object.entries(environmentSplit) as [Environment, unknown][])
    .filter(
      (entry): entry is [Environment, EnvironmentMetrics] =>
        typeof entry[1] === 'object' &&
        entry[1] !== null &&
        'revenue_current' in (entry[1] as object),
    )

  // Detect AMP drift: significant AMP decline relative to others
  const ampMetrics = entries.find(([e]) => e === 'AMP')?.[1]
  const webMetrics = entries.find(([e]) => e === 'WEB')?.[1]
  const appMetrics = entries.find(([e]) => e === 'APP')?.[1]
  const otherAvgDelta =
    webMetrics && appMetrics
      ? (webMetrics.delta_pct + appMetrics.delta_pct) / 2
      : 0
  const ampDrift =
    !!ampMetrics && Math.abs(ampMetrics.delta_pct) > Math.abs(otherAvgDelta) * 1.5

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Monitor size={18} className="text-purple-500" />
            Step 5: Environment Split
          </CardTitle>
          {ampDrift && (
            <div className="flex items-center gap-1.5">
              <AlertTriangle size={14} className="text-orange-500" />
              <Badge variant="P1">AMP Drift Detected</Badge>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {entries.map(([env, metrics]) => (
            <div
              key={env}
              className={`rounded-lg border p-4 ${
                env === 'AMP' && ampDrift
                  ? 'border-orange-300 bg-orange-50'
                  : 'border-gray-200 bg-gray-50'
              }`}
            >
              <div className="mb-3 flex items-center gap-2">
                {envIcons[env]}
                <h4 className="font-semibold text-gray-900">{env}</h4>
                {env === 'AMP' && ampDrift && (
                  <AlertTriangle size={14} className="text-orange-500" />
                )}
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Revenue</span>
                  <span className="font-medium font-mono">{formatCurrency(metrics.revenue_current)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Baseline</span>
                  <span className="font-mono text-gray-500">
                    {formatCurrency(metrics.revenue_baseline)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Delta</span>
                  <DeltaIndicator value={metrics.delta_pct} size="sm" />
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Bacino</span>
                  <span className="font-medium font-mono">{metrics.bacino_current.toLocaleString()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Coverage</span>
                  <span
                    className={`font-medium font-mono ${
                      metrics.coverage_current < 0.75 ? 'text-red-600' : ''
                    }`}
                  >
                    {(metrics.coverage_current * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div>
          <h4 className="mb-3 text-sm font-semibold text-gray-700">
            Current vs Baseline by Environment
          </h4>
          <ChartErrorBoundary height={280}>
            <EnvironmentBarChart data={environmentSplit} />
          </ChartErrorBoundary>
        </div>
      </CardContent>
    </Card>
  )
}
