import { useState } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { useRevenueStatus24h } from '../../api/client'
import { formatCurrency } from '../../lib/utils'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { CardSkeleton } from '../ui/Skeleton'

export function RevenueByChannel() {
  const [selectedDate, setSelectedDate] = useState<string | undefined>(undefined)
  const { data, isLoading, error } = useRevenueStatus24h(selectedDate)

  if (isLoading) return <CardSkeleton />
  if (error || !data) return (
    <Card>
      <CardHeader>
        <CardTitle>Revenue by Channel (24h)</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="py-8 text-center text-sm text-slate-400">No revenue data available.</p>
      </CardContent>
    </Card>
  )

  // Hourly data only covers GOOGLE_ADEX channel — show total revenue curve
  // until IT delivers multi-channel hourly data
  const chartData = data.hours.map((h) => ({
    hour: String(h.hour).padStart(2, '0'),
    revenue: h.revenue,
    baseline: h.baseline,
  }))

  const availableDates = data.available_dates ?? []

  const selectClass = 'cursor-pointer rounded-md border border-gray-200 bg-gray-50 px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm transition-colors hover:bg-gray-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500'

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CardTitle>Revenue by Channel (24h)</CardTitle>
            {availableDates.length > 1 && (
              <select
                value={selectedDate ?? data.date}
                onChange={(e) => setSelectedDate(e.target.value)}
                className={selectClass}
              >
                {availableDates.map((d) => {
                  const dt = new Date(d + 'T00:00:00')
                  const label = dt.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })
                  return <option key={d} value={d}>{label}</option>
                })}
              </select>
            )}
          </div>
        </div>
        <p className="mt-1.5 text-xs text-slate-400">
          Hourly data — GOOGLE_ADEX only. Multi-channel breakdown pending from IT.
        </p>
      </CardHeader>
      <CardContent>
        <div style={{ width: '100%', height: 320 }}>
          <ResponsiveContainer>
            <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
              <defs>
                <linearGradient id="channelGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--chart-blue, #3b82f6)" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="var(--chart-blue, #3b82f6)" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid, #f1f5f9)" />
              <XAxis
                dataKey="hour"
                tick={{ fontSize: 12, fill: 'var(--chart-tick, #64748b)' }}
                tickLine={false}
                axisLine={{ stroke: 'var(--chart-axis, #e2e8f0)' }}
              />
              <YAxis
                tick={{ fontSize: 12, fill: 'var(--chart-tick, #64748b)' }}
                tickLine={false}
                axisLine={{ stroke: 'var(--chart-axis, #e2e8f0)' }}
                tickFormatter={(v: number) =>
                  v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)
                }
              />
              <Tooltip
                content={({ active, payload, label }) => {
                  if (!active || !payload || payload.length === 0) return null
                  const rev = payload.find((p) => p.dataKey === 'revenue')
                  const base = payload.find((p) => p.dataKey === 'baseline')
                  return (
                    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-md text-xs">
                      <p className="mb-1 font-semibold text-slate-700">Hour: {label}:00</p>
                      <p className="tabular-nums text-blue-600">
                        Google AdX: {formatCurrency(Number(rev?.value ?? 0))}
                      </p>
                      <p className="tabular-nums text-slate-400">
                        Baseline 7w: {formatCurrency(Number(base?.value ?? 0))}
                      </p>
                    </div>
                  )
                }}
              />
              <Legend
                iconType="square"
                wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }}
              />
              <Area
                type="monotone"
                dataKey="baseline"
                name="Baseline 7w"
                stroke="var(--chart-gray, #94a3b8)"
                strokeWidth={1.5}
                strokeDasharray="6 3"
                fill="none"
                dot={false}
              />
              <Area
                type="monotone"
                dataKey="revenue"
                name="Google AdX (only available channel)"
                stroke="var(--chart-blue, #3b82f6)"
                strokeWidth={2}
                fill="url(#channelGradient)"
                dot={false}
                activeDot={{ r: 4, stroke: 'var(--chart-blue, #3b82f6)', strokeWidth: 2, fill: '#fff' }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
