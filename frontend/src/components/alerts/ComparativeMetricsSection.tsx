import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { DeltaIndicator } from '../ui/DeltaIndicator';
import type { YesterdayComparison, MovingAverage14d } from '../../types/alert';
import { ArrowRight } from 'lucide-react';

interface Props {
  yesterdayComparison?: YesterdayComparison;
  movingAverage14d?: MovingAverage14d;
}

export function ComparativeMetricsSection({ yesterdayComparison, movingAverage14d }: Props) {
  if (!yesterdayComparison && !movingAverage14d) {
    return null;
  }

  return (
    <div className="space-y-4">
      {yesterdayComparison && (
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <CardTitle>Yesterday Comparison</CardTitle>
              {yesterdayComparison.triggered && (
                <Badge variant={yesterdayComparison.severity === 'P0' ? 'destructive' : 'warning'}>
                  {yesterdayComparison.severity}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-6">
              <div>
                <div className="text-sm font-medium text-gray-500">Yesterday (same hour)</div>
                <div className="text-2xl font-bold mt-1">
                  €{yesterdayComparison.same_hours_revenue_yesterday.toLocaleString()}
                </div>
              </div>

              <ArrowRight className="text-gray-400" size={24} />

              <div>
                <div className="text-sm font-medium text-gray-500">Today (current hour)</div>
                <div className="text-2xl font-bold mt-1">
                  €{yesterdayComparison.current_hour_revenue.toLocaleString()}
                </div>
              </div>

              <div className="ml-auto">
                <div className="text-sm font-medium text-gray-500">Change</div>
                <div className="text-2xl font-bold flex items-center gap-2 mt-1">
                  <DeltaIndicator value={yesterdayComparison.delta_pct} size="sm" />
                  <span className={yesterdayComparison.delta_pct < 0 ? 'text-red-600' : 'text-green-600'}>
                    {yesterdayComparison.delta_pct > 0 ? '+' : ''}{yesterdayComparison.delta_pct.toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>

            {yesterdayComparison.triggered && (
              <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 rounded-md">
                <p className="text-sm text-red-800 dark:text-red-200">
                  ⚠️ Revenue is down {Math.abs(yesterdayComparison.delta_pct).toFixed(1)}% compared to yesterday's same hour.
                  This exceeds the operational threshold of -30%.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {movingAverage14d && (
        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <CardTitle>14-Day Moving Average</CardTitle>
              {movingAverage14d.triggered && (
                <Badge variant="warning">{movingAverage14d.severity}</Badge>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-6">
              <div>
                <div className="text-sm font-medium text-gray-500">14-day average (same hour)</div>
                <div className="text-2xl font-bold mt-1">
                  €{movingAverage14d.avg_revenue_14d.toLocaleString()}
                </div>
              </div>

              <ArrowRight className="text-gray-400" size={24} />

              <div>
                <div className="text-sm font-medium text-gray-500">Current hour</div>
                <div className="text-2xl font-bold mt-1">
                  €{movingAverage14d.current_revenue.toLocaleString()}
                </div>
              </div>

              <div className="ml-auto">
                <div className="text-sm font-medium text-gray-500">Divergence</div>
                <div className="text-2xl font-bold flex items-center gap-2 mt-1">
                  <DeltaIndicator value={movingAverage14d.delta_pct} size="sm" />
                  <span className={movingAverage14d.delta_pct < 0 ? 'text-red-600' : 'text-green-600'}>
                    {movingAverage14d.delta_pct > 0 ? '+' : ''}{movingAverage14d.delta_pct.toFixed(1)}%
                  </span>
                </div>
              </div>
            </div>

            {movingAverage14d.divergence_hours > 0 && (
              <div className="mt-4 flex items-center gap-2">
                <Badge variant="outline">
                  Sustained for {movingAverage14d.divergence_hours} consecutive hour{movingAverage14d.divergence_hours > 1 ? 's' : ''}
                </Badge>
              </div>
            )}

            {movingAverage14d.triggered && (
              <div className="mt-4 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-md">
                <p className="text-sm text-amber-800 dark:text-amber-200">
                  ⚠️ Revenue has diverged {Math.abs(movingAverage14d.delta_pct).toFixed(1)}% below the 14-day average
                  for {movingAverage14d.divergence_hours} consecutive hours.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
