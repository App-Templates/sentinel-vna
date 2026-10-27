import { TrendingDown } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { DeltaIndicator } from '../ui/DeltaIndicator'
import { Badge } from '../ui/Badge'
import { RevenueTrendChart } from '../charts/RevenueTrendChart'
import { ChartErrorBoundary } from '../primitives/ChartErrorBoundary'
import { formatCurrency, cn } from '../../lib/utils'
import { ScopeBadge } from '../ui/ScopeBadge'
import { ReferencePeriodFootnote } from '../ui/ReferencePeriodFootnote'
import { GrossNetToggle, type GrossNetMode } from '../ui/GrossNetToggle'
import { GROSS_NET_LABELS, REV_SHARE_FACTOR } from '../../lib/i18n-keys'
import type { Alert, MetricDataPoint } from '../../types/alert'

interface RevenueStatusSectionProps {
  alert: Alert
  trendData?: MetricDataPoint[]
  // B-1 iter-1: page-level mode state lifted to AlertDetailPage.
  // UI-SPEC §CORR-03 line 408 mandate.
  mode: GrossNetMode
  onModeChange: (mode: GrossNetMode) => void
}

export function RevenueStatusSection({ alert, trendData, mode, onModeChange }: RevenueStatusSectionProps) {
  // CORR-03 / RC-(c) closure (B-1 iter-1): mode is OWNED by AlertDetailPage
  // via page-level state (GrossNetMode, default 'gross') and threaded as a
  // prop. UI-SPEC §CORR-03 line 408 'AlertDetailPage owns the grossNet
  // state and passes it as a prop to both children'. The GrossNetToggle
  // below renders value={mode} and emits onChange={onModeChange} —
  // page-level updates propagate to TriageSection's Revenue row via the
  // same prop chain.

  // Gross source: prefer alert.revenue_gross (Phase 11 D-11.02-02 optional
  // field); fall back to alert.revenue_current (which represents gross per
  // Phase 11 backend contract — see types/alert.ts line 62 + 65 comments).
  const grossCurrent = alert.revenue_gross ?? alert.revenue_current
  const grossBaseline = alert.revenue_baseline

  // Net = gross × REV_SHARE_FACTOR (single source of truth in i18n-keys.ts).
  // UI-SPEC §CORR-03 line 394 'never compute gross / 0.6 to recover net —
  // contract is ALWAYS net = gross × factor, never the reverse'.
  const displayedCurrent = mode === 'net' ? grossCurrent * REV_SHARE_FACTOR : grossCurrent
  const displayedBaseline = mode === 'net' ? grossBaseline * REV_SHARE_FACTOR : grossBaseline
  const deltaEur = displayedCurrent - displayedBaseline

  // Label suffix for MetricCard (UI-SPEC §Copywriting Contract lines 683-684).
  const suffix = mode === 'net' ? GROSS_NET_LABELS.netSuffix : GROSS_NET_LABELS.grossSuffix

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <TrendingDown size={18} className="text-red-500" />
            Step 1: Revenue Status
          </CardTitle>
          <div className="flex items-center gap-3">
            <ScopeBadge channel={alert.channel_group} />
            <GrossNetToggle value={mode} onChange={onModeChange} />
            {alert.alert_rule === 'A2' && (
              <Badge variant="P1">Drift Detected (A2)</Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <MetricCard
            label={`Current Revenue ${suffix}`}
            value={displayedCurrent}
            format="currency"
          />
          <MetricCard
            label={`Baseline (7-week avg) ${suffix}`}
            value={displayedBaseline}
            format="currency"
          />
          <Card>
            <CardContent className="py-4">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Delta (EUR)</p>
              <p className={`text-2xl font-bold tabular-nums mt-1 ${deltaEur < 0 ? 'text-red-600' : 'text-green-600'}`}>
                {formatCurrency(deltaEur)}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="py-4">
              <p className="text-xs font-medium uppercase tracking-wide text-gray-500">Delta (%)</p>
              <div className="mt-1">
                <DeltaIndicator value={alert.revenue_delta_pct} size="lg" />
              </div>
            </CardContent>
          </Card>
        </div>

        {alert.margin_metrics && (
          <div className="border-t border-gray-200 pt-4">
            <h4 className="mb-3 text-sm font-semibold text-gray-700">
              eCPM Analysis (Margin Alert A5)
            </h4>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <Card>
                <CardContent className="py-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-1">Current eCPM</p>
                  <p className="text-2xl font-semibold tabular-nums">
                    &euro;{alert.margin_metrics.current_ecpm.toFixed(2)}
                  </p>
                  <p className="text-xs text-gray-500 mt-1 tabular-nums">
                    {alert.margin_metrics.current_impressions.toLocaleString()} impressions
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="py-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-1">Baseline eCPM</p>
                  <p className="text-2xl font-semibold tabular-nums">
                    &euro;{alert.margin_metrics.baseline_ecpm.toFixed(2)}
                  </p>
                  <p className="text-xs text-gray-500 mt-1 tabular-nums">
                    {alert.margin_metrics.baseline_impressions.toLocaleString()} impressions
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="py-4">
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-1">eCPM Change</p>
                  <p className={cn(
                    "text-2xl font-semibold tabular-nums",
                    alert.margin_metrics.ecpm_delta_pct < 0 ? "text-red-600" : "text-green-600"
                  )}>
                    {alert.margin_metrics.ecpm_delta_pct > 0 ? '+' : ''}{alert.margin_metrics.ecpm_delta_pct.toFixed(1)}%
                  </p>
                  <p className="text-xs text-gray-500 mt-1">Margin compression detected</p>
                </CardContent>
              </Card>
            </div>
          </div>
        )}

        <div>
          {/* Phase 17.2 HOTFIX-02 (V4 Marco 2026-05-19): heading was "(7 Weeks)"
              but useAlertTrend(alertId) returns 7 daily points (not 7 weekly).
              Path A (label fix) chosen per CONTEXT.md operator decision; Path B
              (reshape data to 7-week rolling) deferred to backlog. */}
          <h4 className="mb-3 text-sm font-semibold text-gray-700">Revenue Trend (Last 7 Days)</h4>
          <ChartErrorBoundary height={280}>
            <RevenueTrendChart data={trendData} />
          </ChartErrorBoundary>
        </div>

        <ReferencePeriodFootnote variant="card" timestamp={alert.timestamp} />
      </CardContent>
    </Card>
  )
}
