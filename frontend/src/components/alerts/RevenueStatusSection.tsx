import { TrendingDown } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { DeltaIndicator } from '../ui/DeltaIndicator'
import { Badge } from '../ui/Badge'
import { RevenueTrendChart } from '../charts/RevenueTrendChart'
import { formatCurrency, cn } from '../../lib/utils'
import type { Alert, MetricDataPoint } from '../../types/alert'

interface RevenueStatusSectionProps {
  alert: Alert
  trendData?: MetricDataPoint[]
}

export function RevenueStatusSection({ alert, trendData }: RevenueStatusSectionProps) {
  const deltaEur = alert.revenue_current - alert.revenue_baseline

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <TrendingDown size={18} className="text-red-500" />
            Step 1: Revenue Status
          </CardTitle>
          {alert.alert_rule === 'A2' && (
            <Badge variant="P1">Drift Detected (A2)</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <MetricCard
            label="Current Revenue"
            value={alert.revenue_current}
            format="currency"
          />
          <MetricCard
            label="Baseline (7-week avg)"
            value={alert.revenue_baseline}
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
          <h4 className="mb-3 text-sm font-semibold text-gray-700">Revenue Trend (7 Weeks)</h4>
          <RevenueTrendChart data={trendData} />
        </div>
      </CardContent>
    </Card>
  )
}
