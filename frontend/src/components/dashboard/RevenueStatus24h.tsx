import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from 'recharts'
import { useRevenueStatus24h } from '../../api/client'
import { formatCurrency, formatPercent } from '../../lib/utils'
import { Card, CardHeader, CardContent } from '../ui/Card'
import { CardSkeleton } from '../ui/Skeleton'

export function RevenueStatus24h() {
  const { data, isLoading, error } = useRevenueStatus24h()

  if (isLoading) {
    return (
      <div className="h-[420px]">
        <CardSkeleton />
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent>
          <p className="text-sm text-red-500">
            Errore nel caricamento dei dati revenue 24h: {(error as Error).message}
          </p>
        </CardContent>
      </Card>
    )
  }

  if (!data || data.hours.length === 0) {
    return (
      <Card>
        <CardContent>
          <p className="text-sm text-gray-400">Nessun dato revenue 24h disponibile.</p>
        </CardContent>
      </Card>
    )
  }

  const chartData = data.hours.map((h) => ({
    hour: String(h.hour).padStart(2, '0'),
    revenue: h.revenue,
    baseline: h.baseline,
    delta_pct: h.delta_pct,
  }))

  const deltaColor =
    data.total_delta_pct !== null && data.total_delta_pct >= 0
      ? 'text-green-500'
      : 'text-red-500'

  const prevYear = data.prev_year
  const pyDeltaColor =
    prevYear && prevYear.delta_pct >= 0 ? 'text-green-500' : 'text-red-500'

  return (
    <Card>
      <CardHeader className="border-b border-gray-200">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Revenue Status 24h</h3>
            <p className="text-sm text-gray-500">
              {data.date} &mdash; {data.day_of_week}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-1 text-sm">
            <div>
              <span className="text-gray-500">Revenue: </span>
              <span className="font-semibold text-gray-900">
                {formatCurrency(data.total_revenue)}
              </span>
            </div>
            <div>
              <span className="text-gray-500">Baseline 7w: </span>
              <span className="font-semibold text-gray-900">
                {formatCurrency(data.total_baseline)}
              </span>
            </div>
            {data.total_delta_pct !== null && (
              <div>
                <span className="text-gray-500">vs 7w: </span>
                <span className={`font-semibold ${deltaColor}`}>
                  {formatPercent(data.total_delta_pct)}
                </span>
              </div>
            )}
            {prevYear && (
              <>
                <div>
                  <span className="text-gray-500">YoY ({prevYear.date.slice(0, 4)}): </span>
                  <span className="font-semibold text-gray-900">
                    {formatCurrency(prevYear.total_revenue)}
                  </span>
                </div>
                <div>
                  <span className="text-gray-500">vs YoY: </span>
                  <span className={`font-semibold ${pyDeltaColor}`}>
                    {formatPercent(prevYear.delta_pct)}
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div style={{ width: '100%', height: 300 }}>
          <ResponsiveContainer>
            <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
              <defs>
                <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.15} />
                  <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="hour"
                tick={{ fontSize: 12, fill: '#6b7280' }}
                tickLine={false}
                axisLine={{ stroke: '#e5e7eb' }}
              />
              <YAxis
                tick={{ fontSize: 12, fill: '#6b7280' }}
                tickLine={false}
                axisLine={{ stroke: '#e5e7eb' }}
                tickFormatter={(v: number) =>
                  v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)
                }
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (!active || !payload || payload.length === 0) return null
                  const rev = payload.find((p) => p.dataKey === 'revenue')
                  const base = payload.find((p) => p.dataKey === 'baseline')
                  const point = chartData.find((d) => d.hour === label)
                  return (
                    <div className="rounded-lg border border-gray-200 bg-white px-3 py-2 shadow-md text-xs">
                      <p className="font-semibold text-gray-700 mb-1">Ora: {label}:00</p>
                      <p className="text-blue-600">
                        Revenue: {formatCurrency(Number(rev?.value ?? 0))}
                      </p>
                      <p className="text-gray-500">
                        Baseline 7w: {formatCurrency(Number(base?.value ?? 0))}
                      </p>
                      {point?.delta_pct !== null && point?.delta_pct !== undefined && (
                        <p className={point.delta_pct >= 0 ? 'text-green-600' : 'text-red-600'}>
                          Delta vs 7w: {formatPercent(point.delta_pct)}
                        </p>
                      )}
                      {prevYear && (
                        <p className="text-amber-600 mt-1 border-t border-gray-100 pt-1">
                          YoY media/h: {formatCurrency(prevYear.hourly_avg)}
                        </p>
                      )}
                    </div>
                  )
                }}
              />
              <Legend
                iconType="line"
                wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }}
              />
              {prevYear && (
                <ReferenceLine
                  y={prevYear.hourly_avg}
                  stroke="#f59e0b"
                  strokeDasharray="8 4"
                  strokeWidth={1.5}
                  label={{
                    value: `YoY ${prevYear.date.slice(0, 4)}`,
                    position: 'right',
                    fill: '#f59e0b',
                    fontSize: 11,
                  }}
                />
              )}
              <Area
                type="monotone"
                dataKey="baseline"
                name="Baseline 7w"
                stroke="#9ca3af"
                strokeWidth={2}
                strokeDasharray="6 3"
                fill="none"
                dot={false}
                activeDot={{ r: 4, stroke: '#9ca3af', strokeWidth: 2, fill: '#fff' }}
              />
              <Area
                type="monotone"
                dataKey="revenue"
                name="Revenue"
                stroke="#3b82f6"
                strokeWidth={2.5}
                fill="url(#revenueGradient)"
                dot={{ r: 3, fill: '#3b82f6', stroke: '#fff', strokeWidth: 2 }}
                activeDot={{ r: 5, stroke: '#3b82f6', strokeWidth: 2, fill: '#fff' }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
