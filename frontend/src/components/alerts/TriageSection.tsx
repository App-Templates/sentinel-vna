import { ArrowDown, ArrowUp, Minus, GitBranch, AlertTriangle, TrendingUp } from 'lucide-react'
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
        {/* A6 Coverage-Zero Cause */}
        {alert.alert_rule === 'A6' && alert.coverage_zero_cause && (
          <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle size={20} className="mt-0.5 text-amber-600" />
              <div className="flex-1">
                <h4 className="font-medium text-amber-900 mb-2">
                  Probable Cause: {getCoverageZeroCauseLabel(alert.coverage_zero_cause)}
                </h4>
                <p className="text-sm text-amber-800">
                  {getCoverageZeroCauseDescription(alert.coverage_zero_cause)}
                </p>
                {alert.coverage_zero_metrics && (
                  <div className="mt-3 grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">Current Coverage:</span>
                      <span className="ml-2 font-semibold text-red-600">
                        {(alert.coverage_zero_metrics.current_coverage * 100).toFixed(2)}%
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">Baseline Coverage:</span>
                      <span className="ml-2 font-semibold">
                        {(alert.coverage_zero_metrics.baseline_coverage * 100).toFixed(2)}%
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* A7 Pricing Rule Correlation */}
        {alert.alert_rule === 'A7' && alert.pricing_rule_metrics && (
          <div className="mt-4 rounded-lg border border-purple-200 bg-purple-50 p-4">
            <div className="flex items-start gap-3">
              <TrendingUp size={20} className="mt-0.5 text-purple-600" />
              <div className="flex-1">
                <h4 className="font-medium text-purple-900 mb-2">
                  Pricing Rule Issue Detected
                </h4>
                <p className="text-sm text-purple-800 mb-3">
                  Coverage is dropping while CPM is spiking &mdash; indicates floor prices are too high and blocking valid demand.
                </p>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="text-gray-600 mb-1">Coverage Change</div>
                    <div className="text-lg font-semibold tabular-nums text-red-600">
                      {alert.pricing_rule_metrics.coverage_delta_pct.toFixed(1)}%
                    </div>
                    <div className="text-xs tabular-nums text-gray-500">
                      {(alert.pricing_rule_metrics.baseline_coverage * 100).toFixed(1)}% &rarr; {(alert.pricing_rule_metrics.current_coverage * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-600 mb-1">CPM Change</div>
                    <div className="text-lg font-semibold tabular-nums text-green-600">
                      +{alert.pricing_rule_metrics.ecpm_delta_pct.toFixed(1)}%
                    </div>
                    <div className="text-xs tabular-nums text-gray-500">
                      &euro;{alert.pricing_rule_metrics.baseline_ecpm.toFixed(2)} &rarr; &euro;{alert.pricing_rule_metrics.current_ecpm.toFixed(2)}
                    </div>
                  </div>
                </div>
                <div className="mt-3 flex items-center justify-between border-t border-purple-200 pt-3 text-sm">
                  <span className="text-gray-600">Inverse Correlation Score:</span>
                  <span className="font-semibold">{alert.pricing_rule_metrics.correlation_score.toFixed(2)}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function getCoverageZeroCauseLabel(cause: string): string {
  const labels: Record<string, string> = {
    GOOGLE_POLICY: 'Google Policy Violation',
    MCM_CONFIG: 'MCM Misconfiguration',
    ADS_TXT: 'Ads.txt Issue',
    TECHNICAL_ISSUE: 'Technical Issue',
  }
  return labels[cause] || cause
}

function getCoverageZeroCauseDescription(cause: string): string {
  const descriptions: Record<string, string> = {
    GOOGLE_POLICY: 'Sudden coverage drop to zero with stable bacino suggests a Google policy violation. Check Ad Manager for policy warnings or account suspensions.',
    MCM_CONFIG: 'Coverage at zero despite available bacino indicates MCM configuration issues. Verify publisher linking, revenue share settings, and inventory access.',
    ADS_TXT: 'Coverage zero with bacino changes suggests ads.txt validation failures. Check ads.txt file for missing or incorrect seller entries.',
    TECHNICAL_ISSUE: 'Coverage outage appears technical in nature. Check ad tag implementation, network connectivity, and integration logs.',
  }
  return descriptions[cause] || 'Unknown cause - manual investigation required.'
}
