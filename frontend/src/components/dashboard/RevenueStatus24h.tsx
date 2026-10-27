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
import { cn, formatCurrency, formatPercent } from '../../lib/utils'
import { REVENUE_LABELS } from '../../lib/i18n-keys'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { CardSkeleton } from '../ui/Skeleton'
import { ScopeBadge } from '../ui/ScopeBadge'
import { ReferencePeriodFootnote } from '../ui/ReferencePeriodFootnote'

export function RevenueStatus24h() {
  const [selectedDate, setSelectedDate] = useState<string | undefined>(undefined)
  const { data, isLoading, error } = useRevenueStatus24h(selectedDate)

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
            Failed to load 24h revenue data: {(error as Error).message}
          </p>
        </CardContent>
      </Card>
    )
  }

  if (!data || data.hours.length === 0) {
    return (
      <Card>
        <CardContent>
          <p className="text-sm text-gray-400">{REVENUE_LABELS.noData}</p>
        </CardContent>
      </Card>
    )
  }

  const prevYear = data.prev_year
  const yoyHours = prevYear?.hours ?? []

  const chartData = data.hours.map((h, i) => ({
    hour: String(h.hour).padStart(2, '0'),
    revenue: h.revenue,
    baseline: h.baseline,
    delta_pct: h.delta_pct,
    yoy: yoyHours[i] ?? null,
  }))

  const deltaColor =
    data.total_delta_pct !== null && data.total_delta_pct >= 0
      ? 'text-green-500'
      : 'text-red-500'

  const pyDeltaColor =
    prevYear && prevYear.delta_pct >= 0 ? 'text-green-500' : 'text-red-500'

  const availableDates = data.available_dates ?? []

  const selectClass = 'cursor-pointer rounded-md border border-gray-200 bg-gray-50 px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm transition-colors hover:bg-gray-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500'

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CardTitle>{REVENUE_LABELS.status24h}</CardTitle>
            <ScopeBadge channel="GOOGLE_ADEX" />
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
        <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1">
          <div className="flex items-center gap-1.5 text-sm">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-blue-500" />
            <span className="text-gray-500">{REVENUE_LABELS.revenue}:</span>
            <span className="font-semibold tabular-nums text-gray-900">{formatCurrency(data.total_revenue)}</span>
          </div>
          <div className="flex items-center gap-1.5 text-sm">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-gray-400" />
            <span className="text-gray-500">{REVENUE_LABELS.baseline7w}:</span>
            <span className="font-semibold tabular-nums text-gray-900">{formatCurrency(data.total_baseline)}</span>
          </div>
          {data.total_delta_pct !== null && (
            <div className="text-sm">
              <span className="text-gray-500">vs 7w: </span>
              <span className={`font-semibold tabular-nums ${deltaColor}`}>
                {formatPercent(data.total_delta_pct)}
              </span>
            </div>
          )}
          {prevYear ? (
            <>
              {/* YoY 7w inline-stats label (UI-SPEC §"YoY 7-Week Rolling Baseline" line 313, AC #5) */}
              <div className="flex items-center gap-1.5 text-sm">
                <span className="inline-block h-2.5 w-2.5 rounded-full bg-amber-500" />
                <span className="text-gray-500">{REVENUE_LABELS.yoy7w} ({prevYear.date.slice(0, 4)}):</span>
                <span className="font-semibold tabular-nums text-gray-900">{formatCurrency(prevYear.total_revenue)}</span>
              </div>
              <div className="text-sm">
                <span className="text-gray-500">vs {REVENUE_LABELS.yoy7w}: </span>
                <span className={`font-semibold tabular-nums ${pyDeltaColor}`}>
                  {formatPercent(prevYear.delta_pct)}
                </span>
              </div>
            </>
          ) : (
            <div className="text-sm text-gray-400" title="Il dataset 2025 inizia il 24 Feb 2025; le date precedenti non hanno comparativo YoY 7w">
              {REVENUE_LABELS.yoy7w}: <span className="italic">non disponibile per questa data</span>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div style={{ width: '100%', height: 300 }}>
          <ResponsiveContainer>
            <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 5 }}>
              <defs>
                <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--chart-blue, #3b82f6)" stopOpacity={0.18} />
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
                  const yoy = payload.find((p) => p.dataKey === 'yoy')
                  const point = chartData.find((d) => d.hour === label)
                  return (
                    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-md text-xs">
                      <p className="mb-1 font-semibold text-slate-700">{REVENUE_LABELS.hour}: {label}:00</p>
                      <p className="tabular-nums text-blue-600">
                        {REVENUE_LABELS.revenue}: {formatCurrency(Number(rev?.value ?? 0))}
                      </p>
                      <p className="tabular-nums text-slate-500">
                        {REVENUE_LABELS.baseline7w}: {formatCurrency(Number(base?.value ?? 0))}
                      </p>
                      {point?.delta_pct !== null && point?.delta_pct !== undefined && (
                        <p className={cn('tabular-nums', point.delta_pct >= 0 ? 'text-green-600' : 'text-red-600')}>
                          {REVENUE_LABELS.deltaVs7w}: {formatPercent(point.delta_pct)}
                        </p>
                      )}
                      {yoy?.value != null && (
                        <p className="mt-1 border-t border-slate-100 pt-1 tabular-nums text-amber-600">
                          {REVENUE_LABELS.yoy7w} {prevYear?.date.slice(0, 4)}: {formatCurrency(Number(yoy.value))}
                        </p>
                      )}
                    </div>
                  )
                }}
              />
              <Legend iconType="line" wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }} />
              <Area
                type="monotone"
                dataKey="baseline"
                name={REVENUE_LABELS.baseline7w}
                stroke="var(--chart-gray, #94a3b8)"
                strokeWidth={2}
                strokeDasharray="6 3"
                fill="none"
                dot={false}
                activeDot={{ r: 4, stroke: 'var(--chart-gray, #94a3b8)', strokeWidth: 2, fill: '#fff' }}
              />
              {/* YoY 7w chart-legend label (UI-SPEC §"YoY 7-Week Rolling Baseline" line 319, AC #5) */}
              {yoyHours.length > 0 && (
                <Area
                  type="monotone"
                  dataKey="yoy"
                  name={`${REVENUE_LABELS.yoy7w} ${prevYear?.date.slice(0, 4) ?? ''}`}
                  stroke="var(--chart-amber, #f59e0b)"
                  strokeWidth={1.5}
                  strokeDasharray="8 4"
                  fill="none"
                  dot={false}
                  activeDot={{ r: 4, stroke: 'var(--chart-amber, #f59e0b)', strokeWidth: 2, fill: '#fff' }}
                />
              )}
              <Area
                type="monotone"
                dataKey="revenue"
                name={REVENUE_LABELS.revenue}
                stroke="var(--chart-blue, #3b82f6)"
                strokeWidth={2.5}
                fill="url(#revenueGradient)"
                dot={{ r: 3, fill: 'var(--chart-blue, #3b82f6)', stroke: '#fff', strokeWidth: 2 }}
                activeDot={{ r: 5, stroke: '#3b82f6', strokeWidth: 2, fill: '#fff' }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <ReferencePeriodFootnote timestamp={data.date} />
      </CardContent>
    </Card>
  )
}
