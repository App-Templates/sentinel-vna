import { TrendingDown } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { MetricCard } from '../ui/MetricCard'
import { DeltaIndicator } from '../ui/DeltaIndicator'
import { Badge } from '../ui/Badge'
import { RevenueTrendChart } from '../charts/RevenueTrendChart'
import { formatCurrency } from '../../lib/utils'
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
          <div className="rounded-lg border border-gray-200 bg-white p-5">
            <p className="text-sm font-medium text-gray-500">Delta (EUR)</p>
            <p className={`text-2xl font-bold ${deltaEur < 0 ? 'text-red-600' : 'text-green-600'}`}>
              {formatCurrency(deltaEur)}
            </p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-5">
            <p className="text-sm font-medium text-gray-500">Delta (%)</p>
            <DeltaIndicator value={alert.revenue_delta_pct} size="lg" />
          </div>
        </div>

        <div>
          <h4 className="mb-3 text-sm font-semibold text-gray-700">Revenue Trend (7 Weeks)</h4>
          <RevenueTrendChart data={trendData} />
        </div>
      </CardContent>
    </Card>
  )
}
