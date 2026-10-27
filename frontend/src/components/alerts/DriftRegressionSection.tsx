import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card';
import { DeltaIndicator } from '../ui/DeltaIndicator';
import type { DriftRegression } from '../../types/alert';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface Props {
  drift: DriftRegression;
}

export function DriftRegressionSection({ drift }: Props) {
  // Generate synthetic trend data points for visualization
  // Backend provides slope and days, we reconstruct the line
  const trendData = Array.from({ length: drift.days_analyzed }, (_, i) => {
    // Approximate revenue trend: assume 100 as base, apply slope
    const dayValue = 100 + (drift.slope_pct_per_day * i);
    return {
      day: i + 1,
      revenue: Math.max(0, dayValue),
    };
  });

  // Add projection point 7 days out
  const projectionPoint = {
    day: drift.days_analyzed + 7,
    revenue: Math.max(0, 100 + (drift.slope_pct_per_day * (drift.days_analyzed + 7))),
    projected: true,
  };
  trendData.push(projectionPoint);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Drift Regression Analysis</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="py-4">
              <div className="text-xs font-medium uppercase tracking-wide text-gray-500">Slope (per day)</div>
              <div className="text-2xl font-bold tabular-nums flex items-center gap-2 mt-1">
                <DeltaIndicator value={drift.slope_pct_per_day} size="sm" />
                <span className={drift.slope_pct_per_day < 0 ? 'text-red-600' : 'text-green-600'}>
                  {drift.slope_pct_per_day.toFixed(2)}%
                </span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="py-4">
              <div className="text-xs font-medium uppercase tracking-wide text-gray-500">Cumulative Drop</div>
              <div className="text-2xl font-bold tabular-nums flex items-center gap-2 mt-1">
                <DeltaIndicator value={drift.cumulative_drop_pct} size="sm" />
                <span className={drift.cumulative_drop_pct < 0 ? 'text-red-600' : 'text-green-600'}>
                  {drift.cumulative_drop_pct.toFixed(1)}%
                </span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="py-4">
              <div className="text-xs font-medium uppercase tracking-wide text-gray-500">R² (fit quality)</div>
              <div className="text-2xl font-bold tabular-nums mt-1">{drift.r_squared.toFixed(3)}</div>
              <div className="text-xs text-gray-500 mt-1">
                {drift.r_squared >= 0.8 ? 'Excellent' : drift.r_squared >= 0.5 ? 'Good' : 'Moderate'}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="py-4">
              <div className="text-xs font-medium uppercase tracking-wide text-gray-500">7d Projection</div>
              <div className="text-2xl font-bold tabular-nums flex items-center gap-2 mt-1">
                <DeltaIndicator value={drift.projection_7d_pct} size="sm" />
                <span className={drift.projection_7d_pct < 0 ? 'text-red-600' : 'text-green-600'}>
                  {drift.projection_7d_pct.toFixed(1)}%
                </span>
              </div>
            </CardContent>
          </Card>
        </div>

        <div>
          <h4 className="mb-3 text-sm font-semibold text-slate-600">Trend over {drift.days_analyzed} days</h4>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid, #f1f5f9)" />
              <XAxis
                dataKey="day"
                tick={{ fontSize: 12, fill: 'var(--chart-tick, #64748b)' }}
                tickLine={false}
                axisLine={{ stroke: 'var(--chart-axis, #e2e8f0)' }}
                label={{ value: 'Days analyzed', position: 'insideBottom', offset: -5, fontSize: 12, fill: '#64748b' }}
              />
              <YAxis
                tick={{ fontSize: 12, fill: 'var(--chart-tick, #64748b)' }}
                tickLine={false}
                axisLine={{ stroke: 'var(--chart-axis, #e2e8f0)' }}
                label={{ value: 'Revenue (indexed)', angle: -90, position: 'insideLeft', fontSize: 12, fill: '#64748b' }}
              />
              <Tooltip
                contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '12px', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.07)' }}
                formatter={(value: number | undefined) => {
                  if (value === undefined) return ['N/A', 'Revenue'];
                  return [value.toFixed(1), 'Revenue'];
                }}
              />
              <Line
                type="monotone"
                dataKey="revenue"
                stroke="var(--chart-red, #ef4444)"
                strokeWidth={2}
                dot={(props: any) => {
                  if (props.payload.projected) {
                    return <circle cx={props.cx} cy={props.cy} r={4} fill="var(--chart-amber, #f59e0b)" stroke="var(--chart-red, #ef4444)" strokeWidth={2} />;
                  }
                  return <circle cx={props.cx} cy={props.cy} r={3} fill="var(--chart-red, #ef4444)" />;
                }}
              />
            </LineChart>
          </ResponsiveContainer>
          <p className="text-xs text-gray-500 mt-2">
            ⚠️ Yellow point indicates 7-day projection based on current trend
          </p>
        </div>

        <div className="p-4 bg-amber-50 dark:bg-amber-900/20 rounded-md">
          <p className="text-sm text-amber-800 dark:text-amber-200">
            <strong>Gradual decline detected:</strong> Revenue has been dropping at an average rate of{' '}
            {Math.abs(drift.slope_pct_per_day).toFixed(2)}% per day over the past {drift.days_analyzed} days.
            If this trend continues, expect an additional {Math.abs(drift.projection_7d_pct).toFixed(1)}% drop over the next 7 days.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
