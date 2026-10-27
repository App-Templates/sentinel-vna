import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useTranslation } from '../i18n/context'
import { ArrowLeft, Globe, Monitor, TrendingUp, History, EyeOff, AlertTriangle, MousePointer, Eye, DollarSign, Percent } from 'lucide-react'
import {
  ComposedChart,
  AreaChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceArea,
  ReferenceLine,
} from 'recharts'
import { usePublisherWeeklyKpis, usePublisherEcpmAnalysis, usePublisherRecurringPatterns } from '../api/client'
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card'
import { MetricCard } from '../components/ui/MetricCard'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Skeleton, CardSkeleton } from '../components/ui/Skeleton'
import { DataTable, type Column } from '../components/ui/DataTable'
import { formatCurrency, cn } from '../lib/utils'
import { CHANNEL_COLORS, CHANNEL_LABELS, ALL_CHANNELS } from '../lib/channels'
import type { GeoShare, EnvShare, EcpmOptimizationWindow, RecurringPattern, DriverType, HiddenPattern, DangerZone, WeeklyKpi } from '../types/publisher'

function Tip({ children, text }: { children: React.ReactNode; text: string }) {
  return (
    <span className="group relative inline-flex">
      {children}
      <span className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 hidden w-max max-w-[250px] -translate-x-1/2 rounded-lg bg-gray-900 px-3 py-2 text-xs font-normal text-white shadow-lg group-hover:block">
        {text}
      </span>
    </span>
  )
}

function formatCompact(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`
  return value.toLocaleString()
}

function formatShortDate(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', { day: 'numeric', month: 'short' })
}

function getMonth(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short' })
}

const SIGNAL_TOOLTIPS: Record<EcpmOptimizationWindow['signal'], string> = {
  RAISE: 'eCPM above annual average in this period',
  LOWER: 'eCPM below annual average in this period',
  NEUTRAL: 'eCPM within annual average in this period',
}

function signalBadge(signal: EcpmOptimizationWindow['signal']) {
  const badge = (() => {
    switch (signal) {
      case 'RAISE':
        return (
          <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-semibold text-green-800 border border-green-200">
            &uarr; RAISE
          </span>
        )
      case 'LOWER':
        return (
          <span className="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-800 border border-red-200">
            &darr; LOWER
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-600 border border-slate-200">
            &rarr; NEUTRAL
          </span>
        )
    }
  })()
  return <Tip text={SIGNAL_TOOLTIPS[signal]}>{badge}</Tip>
}

const DRIVER_CONFIG: Record<DriverType, { label: string; className: string }> = {
  DEMAND_DRIVEN: { label: 'Demand', className: 'bg-green-100 text-green-800 border-green-200' },
  SUPPLY_SQUEEZE: { label: 'Supply Squeeze', className: 'bg-orange-100 text-orange-800 border-orange-200' },
  FILL_EFFECT: { label: 'Fill Effect', className: 'bg-orange-100 text-orange-800 border-orange-200' },
  VOLUME_DRIVEN: { label: 'Volume', className: 'bg-blue-100 text-blue-800 border-blue-200' },
  SEASONAL_DEMAND: { label: 'Seasonal', className: 'bg-purple-100 text-purple-800 border-purple-200' },
  MIXED: { label: 'Mixed', className: 'bg-slate-100 text-slate-600 border-slate-200' },
}

const DRIVER_TOOLTIPS: Record<DriverType, string> = {
  DEMAND_DRIVEN: 'eCPM increase is genuine: ad demand grows with stable supply and coverage',
  SUPPLY_SQUEEZE: 'Warning: eCPM rising because inventory (supply) is contracting, not due to real demand',
  FILL_EFFECT: 'Warning: eCPM rising because served impressions are decreasing — only premium ones survive',
  VOLUME_DRIVEN: 'eCPM dropping due to higher impression volume. Revenue may still grow',
  SEASONAL_DEMAND: 'Seasonal variation: inventory supply exceeds ad demand',
  MIXED: 'No dominant driver identified. Trend influenced by multiple factors',
}

function driverBadge(driver: DriverType | undefined) {
  if (!driver) return null
  const cfg = DRIVER_CONFIG[driver]
  if (!cfg) return null
  const isMisleading = driver === 'SUPPLY_SQUEEZE' || driver === 'FILL_EFFECT'
  return (
    <Tip text={DRIVER_TOOLTIPS[driver]}>
      <span className={cn('inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold', cfg.className)}>
        {isMisleading && <AlertTriangle size={11} className="text-amber-600" />}
        {cfg.label}
      </span>
    </Tip>
  )
}

function deltaArrow(value: number | undefined) {
  if (value == null) return null
  const color = value > 5 ? 'text-green-600' : value < -5 ? 'text-red-600' : 'text-slate-500'
  const arrow = value > 0 ? '\u2191' : value < 0 ? '\u2193' : '\u2192'
  return (
    <span className={cn('tabular-nums text-xs', color)}>
      {arrow}{value > 0 ? '+' : ''}{value.toFixed(1)}%
    </span>
  )
}

const SEASONAL_PERIODS = [
  { label: 'Post-New Year', startWeek: 1, endWeek: 4, color: '#e0e7ff' },
  { label: "Valentine's Day", startWeek: 6, endWeek: 7, color: '#fce7f3' },
  { label: 'Pre-Easter', startWeek: 10, endWeek: 12, color: '#fef9c3' },
  { label: 'Easter', startWeek: 13, endWeek: 16, color: '#fef3c7' },
  { label: 'Spring', startWeek: 17, endWeek: 21, color: '#dcfce7' },
  { label: 'Pre-Summer', startWeek: 22, endWeek: 25, color: '#d1fae5' },
  { label: 'Summer', startWeek: 26, endWeek: 34, color: '#dbeafe' },
  { label: 'Back to School', startWeek: 35, endWeek: 37, color: '#f3e8ff' },
  { label: 'Autumn', startWeek: 38, endWeek: 43, color: '#fed7aa' },
  { label: 'Singles Day', startWeek: 44, endWeek: 45, color: '#fecaca' },
  { label: 'Pre-Black Friday', startWeek: 46, endWeek: 46, color: '#fbcfe8' },
  { label: 'Black Friday', startWeek: 47, endWeek: 48, color: '#fce7f3' },
  { label: 'Christmas', startWeek: 49, endWeek: 52, color: '#bbf7d0' },
]

const TOGGLEABLE_SERIES = [
  { key: 'bacino', label: 'Bacino', color: '#f59e0b' },
  { key: 'coverage', label: 'Coverage', color: '#8b5cf6' },
  { key: 'impressions', label: 'Impressions', color: '#f43f5e' },
] as const

export function PublisherDetailPage() {
  const { publisherId } = useParams<{ publisherId: string }>()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [year, setYear] = useState(2025)
  const [activeSeries, setActiveSeries] = useState<string[]>([])
  const [showPrevYear, setShowPrevYear] = useState(false)

  // Always request YoY data — the backend returns prev_* fields only for top-35 publishers
  // and silently ignores the param for others, so there's no overhead.
  const { data: detail, isLoading, error } = usePublisherWeeklyKpis(publisherId, year, true)
  const { data: ecpmAnalysis } = usePublisherEcpmAnalysis(publisherId, year)
  const { data: recurringPatterns } = usePublisherRecurringPatterns(publisherId)

  const toggleSeries = (key: string) => {
    setActiveSeries((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-6 w-48" />
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10 rounded-md" />
          <div>
            <Skeleton className="mb-2 h-7 w-64" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
        <Skeleton className="h-[460px] rounded-lg" />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Skeleton className="h-48 rounded-lg" />
          <Skeleton className="h-48 rounded-lg" />
        </div>
      </div>
    )
  }

  if (error || !detail) {
    return (
      <div className="py-12 text-center">
        <p className="text-red-500">Unable to load publisher details.</p>
        <Button variant="outline" className="mt-4" onClick={() => navigate('/publishers')}>
          Back to Publishers
        </Button>
      </div>
    )
  }

  const weeklyKpis = detail.weekly_kpis
  const totalRevenue = weeklyKpis.reduce((s, w) => s + w.revenue, 0)
  const totalImpressions = weeklyKpis.reduce((s, w) => s + w.impressions, 0)
  const totalBacino = weeklyKpis.reduce((s, w) => s + w.bacino, 0)
  const weightedEcpm = totalImpressions > 0 ? (totalRevenue / totalImpressions) * 1000 : 0
  const weightedCoverage = totalBacino > 0 ? totalImpressions / totalBacino : 0

  const chartData = weeklyKpis.map((w) => ({
    week_label: `W${w.week}`,
    week_start: w.week_start,
    week_end: w.week_end,
    seasonal_period: w.seasonal_period,
    revenue: w.revenue,
    ecpm: w.ecpm,
    bacino: w.bacino,
    coverage: w.coverage,
    impressions: w.impressions,
    prev_revenue: w.prev_revenue,
    prev_ecpm: w.prev_ecpm,
    delta_revenue_pct: w.delta_revenue_pct,
    delta_ecpm_pct: w.delta_ecpm_pct,
  }))

  const geoColumns: Column<GeoShare>[] = [
    {
      key: 'geo_cluster',
      header: 'Geo',
      render: (row) => <span className="font-semibold text-slate-900">{row.geo_cluster}</span>,
    },
    {
      key: 'revenue',
      header: 'Revenue',
      sortable: true,
      className: 'text-right',
      render: (row) => <span className="font-mono">{formatCurrency(row.revenue)}</span>,
    },
    {
      key: 'share_pct',
      header: 'Share',
      sortable: true,
      className: 'text-right',
      render: (row) => <span className="tabular-nums text-xs">{row.share_pct.toFixed(1)}%</span>,
    },
  ]

  const envColumns: Column<EnvShare>[] = [
    {
      key: 'environment',
      header: 'Environment',
      render: (row) => <span className="font-semibold text-slate-900">{row.environment}</span>,
    },
    {
      key: 'revenue',
      header: 'Revenue',
      sortable: true,
      className: 'text-right',
      render: (row) => <span className="font-mono">{formatCurrency(row.revenue)}</span>,
    },
    {
      key: 'share_pct',
      header: 'Share',
      sortable: true,
      className: 'text-right',
      render: (row) => <span className="tabular-nums text-xs">{row.share_pct.toFixed(1)}%</span>,
    },
  ]

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1 text-sm text-slate-500">
        <Link to="/dashboard" className="hover:text-slate-900">
          Dashboard
        </Link>
        <span className="mx-1">/</span>
        <Link to="/publishers" className="hover:text-slate-900">
          Publishers
        </Link>
        <span className="mx-1">/</span>
        <span className="text-slate-900">{publisherId}</span>
      </nav>

      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/publishers')}>
            <ArrowLeft size={20} />
          </Button>
          <div>
            <h1 className="text-xl font-bold text-slate-900">{publisherId}</h1>
            <div className="mt-1 flex items-center gap-3 text-sm text-slate-500">
              <span>ID: {publisherId}</span>
              <Badge variant="default">Year {year}</Badge>
            </div>
          </div>
        </div>
        <select
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          className="cursor-pointer rounded-md border border-slate-200 bg-slate-50 px-3 py-1.5 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value={2025}>2025</option>
          <option value={2024}>2024</option>
        </select>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label={t('publishers.total_revenue')}
          value={totalRevenue}
          format="currency"
          delta={detail.yoy_summary?.total_revenue_delta_pct ?? undefined}
          subtitle="YoY comparison"
          icon={<DollarSign size={18} />}
          iconBg="bg-emerald-50"
          iconColor="text-emerald-500"
          accentColor="bg-emerald-500"
        />
        <MetricCard
          label={t('publishers.avg_ecpm')}
          value={weightedEcpm}
          format="currency_decimal"
          delta={detail.yoy_summary?.ecpm_delta_pct ?? undefined}
          subtitle={t('publishers.weighted_average')}
          icon={<TrendingUp size={18} />}
          iconBg="bg-violet-50"
          iconColor="text-violet-500"
          accentColor="bg-violet-500"
        />
        <MetricCard
          label="Impressions"
          value={totalImpressions}
          format="number"
          subtitle={`${formatCompact(totalImpressions)} served`}
          icon={<Eye size={18} />}
          iconBg="bg-blue-50"
          iconColor="text-blue-500"
          accentColor="bg-blue-500"
        />
        <MetricCard
          label="Coverage"
          value={weightedCoverage * 100}
          format="percent"
          subtitle="Fill rate"
          icon={<Percent size={18} />}
          iconBg="bg-cyan-50"
          iconColor="text-cyan-500"
          accentColor="bg-cyan-500"
        />
      </div>

      {/* Main Chart */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle>Weekly Performance</CardTitle>
            <div className="flex items-center gap-1.5">
              {TOGGLEABLE_SERIES.map(({ key, label, color }) => (
                <button
                  key={key}
                  onClick={() => toggleSeries(key)}
                  className={cn(
                    'rounded-full border px-3 py-1 text-xs font-medium transition-colors',
                    activeSeries.includes(key)
                      ? 'border-transparent text-white'
                      : 'border-slate-200 bg-white text-slate-500 hover:bg-slate-50'
                  )}
                  style={
                    activeSeries.includes(key) ? { backgroundColor: color } : undefined
                  }
                >
                  {label}
                </button>
              ))}
              {detail?.yoy_summary && (
                <button
                  onClick={() => setShowPrevYear((v) => !v)}
                  className={cn(
                    'rounded-full border px-3 py-1 text-xs font-medium transition-colors',
                    showPrevYear
                      ? 'border-transparent bg-gray-700 text-white'
                      : 'border-slate-200 bg-white text-slate-500 hover:bg-slate-50'
                  )}
                >
                  {year - 1}
                </button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div style={{ width: '100%', height: 400 }}>
            <ResponsiveContainer>
              <ComposedChart
                data={chartData}
                margin={{ top: 10, right: 60, left: 10, bottom: 30 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />

                {SEASONAL_PERIODS.map((period) => (
                  <ReferenceArea
                    key={period.label}
                    x1={`W${period.startWeek}`}
                    x2={`W${period.endWeek}`}
                    fill={period.color}
                    fillOpacity={0.5}
                    label={{
                      value: period.label,
                      position: 'insideTop',
                      style: { fontSize: 10, fill: '#6b7280', fontWeight: 500 },
                    }}
                    ifOverflow="extendDomain"
                  />
                ))}

                <XAxis
                  dataKey="week_label"
                  tick={(props: any) => {
                    const { x, y, payload } = props
                    const idx = payload.index
                    const entry = chartData[idx]
                    if (!entry?.week_start) {
                      return (
                        <text x={x} y={y + 14} textAnchor="middle" fontSize={11} fill="#6b7280">
                          {payload.value}
                        </text>
                      )
                    }
                    const month = getMonth(entry.week_start)
                    const prevEntry = idx > 0 ? chartData[idx - 1] : null
                    const prevMonth = prevEntry?.week_start ? getMonth(prevEntry.week_start) : null
                    const showMonth = month !== prevMonth
                    return (
                      <g>
                        <text x={x} y={y + 14} textAnchor="middle" fontSize={10} fill="#9ca3af">
                          {payload.value}
                        </text>
                        {showMonth && (
                          <text x={x} y={y + 28} textAnchor="middle" fontSize={11} fontWeight={600} fill="#374151">
                            {month}
                          </text>
                        )}
                      </g>
                    )
                  }}
                  tickLine={false}
                  axisLine={{ stroke: '#e5e7eb' }}
                  interval={3}
                />
                <YAxis
                  yAxisId="revenue"
                  orientation="left"
                  tick={{ fontSize: 12, fill: '#6b7280' }}
                  tickLine={false}
                  axisLine={{ stroke: '#e5e7eb' }}
                  tickFormatter={(v: number) =>
                    v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v.toString()
                  }
                  label={{
                    value: 'Revenue (EUR)',
                    angle: -90,
                    position: 'insideLeft',
                    style: { fontSize: 11, fill: '#9ca3af' },
                  }}
                />
                <YAxis
                  yAxisId="ecpm"
                  orientation="right"
                  tick={{ fontSize: 12, fill: '#6b7280' }}
                  tickLine={false}
                  axisLine={{ stroke: '#e5e7eb' }}
                  tickFormatter={(v: number) => `${v.toFixed(1)}`}
                  label={{
                    value: 'eCPM (EUR)',
                    angle: 90,
                    position: 'insideRight',
                    style: { fontSize: 11, fill: '#9ca3af' },
                  }}
                />

                <Tooltip
                  formatter={(value, name, props) => {
                    const v = Number(value ?? 0)
                    const entry = props?.payload
                    const formatDelta = (d: number | null | undefined) => {
                      if (d == null) return ''
                      const sign = d > 0 ? '+' : ''
                      return ` (${sign}${d.toFixed(1)}% YoY)`
                    }
                    switch (name) {
                      case 'Revenue':
                        return [
                          `${formatCurrency(v)}${showPrevYear ? formatDelta(entry?.delta_revenue_pct) : ''}`,
                          name,
                        ]
                      case 'eCPM':
                        return [
                          `${v.toFixed(2)}\u20AC${showPrevYear ? formatDelta(entry?.delta_ecpm_pct) : ''}`,
                          name,
                        ]
                      case `Revenue ${year - 1}`:
                        return [formatCurrency(v), name]
                      case `eCPM ${year - 1}`:
                        return [`${v.toFixed(2)}\u20AC`, name]
                      case 'Bacino':
                        return [formatCompact(v), name]
                      case 'Coverage':
                        return [`${(v * 100).toFixed(1)}%`, name]
                      case 'Impressions':
                        return [formatCompact(v), name]
                      default:
                        return [String(v), name]
                    }
                  }}
                  labelFormatter={(label, payload) => {
                    const entry = payload?.[0]?.payload
                    if (entry?.week_start && entry?.week_end) {
                      const range = `${label}: ${formatShortDate(entry.week_start)} - ${formatShortDate(entry.week_end)}`
                      return entry.seasonal_period ? `${range} (${entry.seasonal_period})` : range
                    }
                    return `Week ${label}`
                  }}
                  contentStyle={{
                    borderRadius: '8px',
                    border: '1px solid #e5e7eb',
                    fontSize: '12px',
                    boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                  }}
                  labelStyle={{ fontWeight: 600, marginBottom: 4 }}
                />
                <Legend
                  iconType="line"
                  wrapperStyle={{ fontSize: '12px', paddingTop: '12px' }}
                />

                {/* Revenue Area - always visible */}
                <Area
                  yAxisId="revenue"
                  type="monotone"
                  dataKey="revenue"
                  name="Revenue"
                  stroke="#3b82f6"
                  strokeWidth={2.5}
                  fill="#3b82f6"
                  fillOpacity={0.08}
                  dot={false}
                  activeDot={{ r: 5, stroke: '#3b82f6', strokeWidth: 2, fill: '#fff' }}
                />

                {/* eCPM Line - always visible */}
                <Line
                  yAxisId="ecpm"
                  type="monotone"
                  dataKey="ecpm"
                  name="eCPM"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4, stroke: '#10b981', strokeWidth: 2, fill: '#fff' }}
                />

                {/* YoY: Previous year revenue */}
                {showPrevYear && (
                  <Line
                    yAxisId="revenue"
                    type="monotone"
                    dataKey="prev_revenue"
                    name={`Revenue ${year - 1}`}
                    stroke="#94a3b8"
                    strokeWidth={1.5}
                    strokeDasharray="6 3"
                    opacity={0.7}
                    dot={false}
                    activeDot={{ r: 3, stroke: '#94a3b8', strokeWidth: 2, fill: '#fff' }}
                  />
                )}

                {/* YoY: Previous year eCPM */}
                {showPrevYear && (
                  <Line
                    yAxisId="ecpm"
                    type="monotone"
                    dataKey="prev_ecpm"
                    name={`eCPM ${year - 1}`}
                    stroke="#64748b"
                    strokeWidth={1.5}
                    strokeDasharray="6 3"
                    opacity={0.7}
                    dot={false}
                    activeDot={{ r: 3, stroke: '#64748b', strokeWidth: 2, fill: '#fff' }}
                  />
                )}

                {/* Toggleable: Bacino */}
                {activeSeries.includes('bacino') && (
                  <Line
                    yAxisId="revenue"
                    type="monotone"
                    dataKey="bacino"
                    name="Bacino"
                    stroke="#f59e0b"
                    strokeWidth={1.5}
                    strokeDasharray="4 2"
                    dot={false}
                    activeDot={{ r: 4, stroke: '#f59e0b', strokeWidth: 2, fill: '#fff' }}
                  />
                )}

                {/* Toggleable: Coverage */}
                {activeSeries.includes('coverage') && (
                  <Line
                    yAxisId="ecpm"
                    type="monotone"
                    dataKey="coverage"
                    name="Coverage"
                    stroke="#8b5cf6"
                    strokeWidth={1.5}
                    strokeDasharray="4 2"
                    dot={false}
                    activeDot={{ r: 4, stroke: '#8b5cf6', strokeWidth: 2, fill: '#fff' }}
                  />
                )}

                {/* Toggleable: Impressions */}
                {activeSeries.includes('impressions') && (
                  <Line
                    yAxisId="revenue"
                    type="monotone"
                    dataKey="impressions"
                    name="Impressions"
                    stroke="#f43f5e"
                    strokeWidth={1.5}
                    strokeDasharray="4 2"
                    dot={false}
                    activeDot={{ r: 4, stroke: '#f43f5e', strokeWidth: 2, fill: '#fff' }}
                  />
                )}
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Geo + Environment Breakdown */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Geo Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe size={18} className="text-amber-500" />
              Geographic Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <DataTable
              data={detail.geo_breakdown}
              columns={geoColumns}
              keyExtractor={(row) => row.geo_cluster}
            />
          </CardContent>
        </Card>

        {/* Environment Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Monitor size={18} className="text-purple-500" />
              Environment Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <DataTable
              data={detail.environment_breakdown}
              columns={envColumns}
              keyExtractor={(row) => row.environment}
            />
          </CardContent>
        </Card>
      </div>

      {/* Revenue by Channel (stacked area) */}
      {weeklyKpis.some((w) => w.revenue_by_channel) && (
        <Card>
          <CardHeader>
            <CardTitle>Revenue by Channel</CardTitle>
          </CardHeader>
          <CardContent>
            <div style={{ width: '100%', height: 350 }}>
              <ResponsiveContainer>
                <AreaChart
                  data={weeklyKpis.map((w) => {
                    const point: Record<string, string | number> = {
                      week_label: `W${w.week}`,
                    }
                    if (w.revenue_by_channel) {
                      for (const ch of ALL_CHANNELS) {
                        point[ch] = w.revenue_by_channel[ch] ?? 0
                      }
                    }
                    return point
                  })}
                  margin={{ top: 10, right: 20, left: 10, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="week_label" tick={{ fontSize: 11, fill: '#6b7280' }} tickLine={false} interval={3} />
                  <YAxis tick={{ fontSize: 12, fill: '#6b7280' }} tickLine={false} tickFormatter={(v: number) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)} />
                  <Tooltip
                    formatter={((value: number, name: string) => [formatCurrency(value), CHANNEL_LABELS[name] ?? name]) as any}
                    contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '12px' }}
                  />
                  <Legend iconType="square" wrapperStyle={{ fontSize: '11px' }} formatter={(v: string) => CHANNEL_LABELS[v] ?? v} />
                  {ALL_CHANNELS.map((ch) => (
                    <Area key={ch} type="monotone" dataKey={ch} name={ch} stackId="ch" stroke={CHANNEL_COLORS[ch]} fill={CHANNEL_COLORS[ch]} fillOpacity={0.7} />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* CTR & Viewability Trends */}
      {weeklyKpis.some((w) => w.ctr != null || w.viewability != null) && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* CTR Trend */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MousePointer size={18} className="text-blue-500" />
                CTR Trend
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div style={{ width: '100%', height: 250 }}>
                <ResponsiveContainer>
                  <ComposedChart
                    data={weeklyKpis.map((w) => ({ week_label: `W${w.week}`, ctr: w.ctr ?? 0 }))}
                    margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="week_label" tick={{ fontSize: 11, fill: '#6b7280' }} tickLine={false} interval={3} />
                    <YAxis tick={{ fontSize: 12, fill: '#6b7280' }} tickLine={false} tickFormatter={(v: number) => `${v.toFixed(2)}%`} />
                    <Tooltip formatter={(v: number | undefined) => [`${(v ?? 0).toFixed(3)}%`, 'CTR']} contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '12px' }} />
                    <Line type="monotone" dataKey="ctr" stroke="#3b82f6" strokeWidth={2} dot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Viewability Trend */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Eye size={18} className="text-green-500" />
                Viewability Trend
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div style={{ width: '100%', height: 250 }}>
                <ResponsiveContainer>
                  <ComposedChart
                    data={weeklyKpis.map((w) => ({ week_label: `W${w.week}`, viewability: w.viewability ?? 0 }))}
                    margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="week_label" tick={{ fontSize: 11, fill: '#6b7280' }} tickLine={false} interval={3} />
                    <YAxis tick={{ fontSize: 12, fill: '#6b7280' }} tickLine={false} tickFormatter={(v: number) => `${v.toFixed(0)}%`} />
                    <Tooltip formatter={(v: number | undefined) => [`${(v ?? 0).toFixed(1)}%`, 'Viewability']} contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '12px' }} />
                    <Line type="monotone" dataKey="viewability" stroke="#10b981" strokeWidth={2} dot={false} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* RPM Trend */}
      {weeklyKpis.some((w) => w.rpm != null) && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign size={18} className="text-emerald-500" />
              RPM Trend
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div style={{ width: '100%', height: 280 }}>
              <ResponsiveContainer>
                <ComposedChart
                  data={weeklyKpis.map((w) => ({ week_label: `W${w.week}`, rpm: w.rpm ?? 0 }))}
                  margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="week_label" tick={{ fontSize: 11, fill: '#6b7280' }} tickLine={false} interval={3} />
                  <YAxis tick={{ fontSize: 12, fill: '#6b7280' }} tickLine={false} tickFormatter={(v: number) => `${v.toFixed(2)}\u20AC`} />
                  <Tooltip formatter={(v: number | undefined) => [`${(v ?? 0).toFixed(2)}\u20AC`, 'RPM']} contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '12px' }} />
                  <Area type="monotone" dataKey="rpm" stroke="#10b981" strokeWidth={2} fill="#10b981" fillOpacity={0.08} dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Gross Margin Trend */}
      {weeklyKpis.some((w) => w.gross_margin_pct != null) && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Percent size={18} className="text-red-500" />
              Gross Margin Trend
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div style={{ width: '100%', height: 280 }}>
              <ResponsiveContainer>
                <ComposedChart
                  data={weeklyKpis.map((w) => ({ week_label: `W${w.week}`, gross_margin_pct: w.gross_margin_pct ?? 0 }))}
                  margin={{ top: 5, right: 20, left: 10, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="week_label" tick={{ fontSize: 11, fill: '#6b7280' }} tickLine={false} interval={3} />
                  <YAxis tick={{ fontSize: 12, fill: '#6b7280' }} tickLine={false} tickFormatter={(v: number) => `${v.toFixed(0)}%`} />
                  <Tooltip formatter={(v: number | undefined) => [`${(v ?? 0).toFixed(1)}%`, 'Gross Margin']} contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '12px' }} />
                  <ReferenceLine y={30} stroke="#ef4444" strokeDasharray="6 3" strokeWidth={1.5} label={{ value: 'Threshold 30%', position: 'right', fill: '#ef4444', fontSize: 11 }} />
                  <Area type="monotone" dataKey="gross_margin_pct" stroke="#ef4444" strokeWidth={2} fill="#ef4444" fillOpacity={0.06} dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Enriched Weekly KPI Table */}
      {weeklyKpis.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Weekly KPI Summary</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto p-0">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="px-3 py-2 text-left font-medium text-slate-500">Week</th>
                  <th className="px-3 py-2 text-right font-medium text-slate-500">Revenue</th>
                  <th className="px-3 py-2 text-right font-medium text-slate-500">eCPM</th>
                  <th className="px-3 py-2 text-right font-medium text-slate-500">Impressions</th>
                  <th className="px-3 py-2 text-right font-medium text-slate-500">Coverage</th>
                  <th className="px-3 py-2 text-right font-medium text-slate-500">RPM</th>
                  <th className="px-3 py-2 text-right font-medium text-slate-500">CTR</th>
                  <th className="px-3 py-2 text-right font-medium text-slate-500">Viewability</th>
                  <th className="px-3 py-2 text-right font-medium text-slate-500">Gross Margin</th>
                </tr>
              </thead>
              <tbody>
                {weeklyKpis.map((w: WeeklyKpi) => (
                  <tr key={w.week} className="border-b border-slate-100 hover:bg-slate-50">
                    <td className="px-3 py-2 font-medium text-slate-900">W{w.week}</td>
                    <td className="px-3 py-2 text-right font-mono">{formatCurrency(w.revenue)}</td>
                    <td className="px-3 py-2 text-right font-mono">{w.ecpm.toFixed(2)}&euro;</td>
                    <td className="px-3 py-2 text-right font-mono">{formatCompact(w.impressions)}</td>
                    <td className="px-3 py-2 text-right font-mono">{(w.coverage * 100).toFixed(1)}%</td>
                    <td className="px-3 py-2 text-right font-mono">{w.rpm != null ? `${w.rpm.toFixed(2)}\u20AC` : '-'}</td>
                    <td className="px-3 py-2 text-right font-mono">{w.ctr != null ? `${w.ctr.toFixed(3)}%` : '-'}</td>
                    <td className="px-3 py-2 text-right font-mono">{w.viewability != null ? `${w.viewability.toFixed(1)}%` : '-'}</td>
                    <td className="px-3 py-2 text-right font-mono">{w.gross_margin_pct != null ? `${w.gross_margin_pct.toFixed(1)}%` : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {/* eCPM Optimization Windows */}
      {ecpmAnalysis && (
        <Card>
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <CardTitle className="flex items-center gap-2">
                <TrendingUp size={18} className="text-emerald-500" />
                eCPM Optimization Windows
              </CardTitle>
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-500">Annual Avg eCPM</span>
                <span className="text-xl font-bold text-slate-900">
                  {ecpmAnalysis.yearly_avg_ecpm.toFixed(2)}&euro;
                </span>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[...ecpmAnalysis.optimization_windows]
                .sort((a, b) => (a.weeks[0] ?? 0) - (b.weeks[0] ?? 0))
                .map((win) => {
                  const isMisleading = win.driver === 'SUPPLY_SQUEEZE' || win.driver === 'FILL_EFFECT'
                  return (
                    <div
                      key={win.period_id}
                      className={cn(
                        'rounded-lg border p-4',
                        isMisleading
                          ? 'border-amber-200 bg-amber-50'
                          : 'border-slate-100 bg-slate-50'
                      )}
                    >
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                        <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-3">
                          {signalBadge(win.signal)}
                          {driverBadge(win.driver)}
                          {win.prev_year_driver && win.driver && (
                            <Tip text={win.prev_year_driver === win.driver
                              ? "Same driver occurred in the previous year — structural trend"
                              : "Driver changed vs previous year — unstable trend, may not repeat"
                            }>
                              <span className={cn(
                                'inline-flex items-center rounded-full border px-1.5 py-0.5 text-[10px] font-medium',
                                win.prev_year_driver === win.driver
                                  ? 'border-green-200 bg-green-50 text-green-700'
                                  : 'border-amber-200 bg-amber-50 text-amber-700'
                              )}>
                                {win.prev_year_driver === win.driver
                                  ? `Stable (${year - 1})`
                                  : `${year - 1}: ${DRIVER_CONFIG[win.prev_year_driver]?.label ?? win.prev_year_driver}`}
                              </span>
                            </Tip>
                          )}
                          {win.consistency_score != null && (
                            <Tip text={win.consistency_score >= 0.7
                              ? 'Very reliable trend: internally consistent data, also confirmed in the previous year'
                              : win.consistency_score >= 0.4
                                ? 'Medium reliability: trend partially confirmed — use with caution'
                                : 'Low reliability: weak or unconfirmed trend, insufficient or inconsistent data'
                            }>
                              <span className={cn(
                                'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold',
                                win.consistency_score >= 0.7
                                  ? 'bg-green-100 text-green-800 border border-green-200'
                                  : win.consistency_score >= 0.4
                                    ? 'bg-amber-100 text-amber-800 border border-amber-200'
                                    : 'bg-slate-100 text-slate-600 border border-slate-200'
                              )}>
                                {Math.round(win.consistency_score * 100)}% match
                              </span>
                            </Tip>
                          )}
                          <div>
                            <span className="font-semibold text-slate-900">{win.period_label}</span>
                            <span className="ml-2 text-sm text-slate-500">{win.date_range}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <span className="text-sm text-slate-500">
                            Avg: <span className="font-mono font-medium text-slate-900">{win.avg_ecpm.toFixed(2)}&euro;</span>
                          </span>
                          <span
                            className={cn(
                              'tabular-nums text-sm font-semibold',
                              win.delta_pct > 0 ? 'text-green-600' : win.delta_pct < 0 ? 'text-red-600' : 'text-slate-500'
                            )}
                          >
                            {isMisleading && <AlertTriangle size={12} className="mr-1 inline text-amber-600" />}
                            {win.delta_pct > 0 ? '+' : ''}{win.delta_pct.toFixed(1)}%
                          </span>
                        </div>
                      </div>
                      {/* Multi-metric delta row */}
                      {(win.bacino_delta_pct != null || win.coverage_delta_pct != null || win.impressions_delta_pct != null || win.revenue_delta_pct != null) && (
                        <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-slate-500">
                          {win.bacino_delta_pct != null && (
                            <span className="font-mono">Bacino: {deltaArrow(win.bacino_delta_pct)}</span>
                          )}
                          {win.coverage_delta_pct != null && (
                            <span className="font-mono">Coverage: {deltaArrow(win.coverage_delta_pct)}</span>
                          )}
                          {win.impressions_delta_pct != null && (
                            <span className="font-mono">Impressions: {deltaArrow(win.impressions_delta_pct)}</span>
                          )}
                          {win.revenue_delta_pct != null && (
                            <span className="font-mono">Revenue: {deltaArrow(win.revenue_delta_pct)}</span>
                          )}
                        </div>
                      )}
                      {/* Warning for misleading drivers */}
                      {isMisleading && win.driver_explanation && (
                        <div className="mt-2 flex items-start gap-1.5 rounded-md bg-amber-100/60 px-2.5 py-1.5 text-xs text-amber-800">
                          <AlertTriangle size={13} className="mt-0.5 shrink-0 text-amber-600" />
                          <span>{win.driver_explanation}</span>
                        </div>
                      )}
                      <p className="mt-2 text-sm text-slate-600">{win.rationale}</p>
                    </div>
                  )
                })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Historical eCPM Patterns */}
      {recurringPatterns && recurringPatterns.ecpm_patterns.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <History size={18} className="text-amber-500" />
                  Historical eCPM Trends
                </CardTitle>
                <p className="mt-1 text-sm text-slate-500">Recurring trends 2024-2025</p>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <span className="text-slate-500">Media eCPM:</span>
                {recurringPatterns.yearly_avg?.ecpm_2024 != null && (
                  <span className="text-slate-700">
                    2024: <span className="font-mono font-semibold text-slate-900">{recurringPatterns.yearly_avg.ecpm_2024.toFixed(2)}&euro;</span>
                  </span>
                )}
                {recurringPatterns.yearly_avg?.ecpm_2024 != null && recurringPatterns.yearly_avg?.ecpm_2025 != null && (
                  <span className="text-slate-300">|</span>
                )}
                {recurringPatterns.yearly_avg?.ecpm_2025 != null && (
                  <span className="text-slate-700">
                    2025: <span className="font-mono font-semibold text-slate-900">{recurringPatterns.yearly_avg.ecpm_2025.toFixed(2)}&euro;</span>
                  </span>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recurringPatterns.ecpm_patterns.map((pattern: RecurringPattern) => (
                <div
                  key={pattern.id}
                  className="rounded-lg border border-amber-200 bg-amber-50 p-4"
                >
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-3">
                      {signalBadge(pattern.signal)}
                      {driverBadge(pattern.driver)}
                      <div>
                        <span className="font-semibold text-slate-900">{pattern.label}</span>
                        <span className="ml-2 text-sm text-slate-500">{pattern.week_range_label}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-sm text-slate-600">
                        2024: <span className="font-mono font-medium text-slate-900">{pattern.avg_ecpm_2024.toFixed(2)}&euro;</span>
                        <span className={cn(
                          'ml-1 tabular-nums text-xs',
                          pattern.avg_delta_pct_2024 > 0 ? 'text-green-600' : pattern.avg_delta_pct_2024 < 0 ? 'text-red-600' : 'text-slate-500'
                        )}>
                          ({pattern.avg_delta_pct_2024 > 0 ? '+' : ''}{pattern.avg_delta_pct_2024.toFixed(1)}%)
                        </span>
                      </span>
                      <span className="text-sm text-slate-600">
                        2025: <span className="font-mono font-medium text-slate-900">{pattern.avg_ecpm_2025.toFixed(2)}&euro;</span>
                        <span className={cn(
                          'ml-1 tabular-nums text-xs',
                          pattern.avg_delta_pct_2025 > 0 ? 'text-green-600' : pattern.avg_delta_pct_2025 < 0 ? 'text-red-600' : 'text-slate-500'
                        )}>
                          ({pattern.avg_delta_pct_2025 > 0 ? '+' : ''}{pattern.avg_delta_pct_2025.toFixed(1)}%)
                        </span>
                      </span>
                      <Tip text={pattern.consistency_score >= 0.7
                        ? 'Very reliable trend: strong internal consistency, confirmed in both years'
                        : pattern.consistency_score >= 0.4
                          ? 'Medium reliability: trend partially consistent — use with caution'
                          : 'Low reliability: high internal variability or poor cross-year confirmation'
                      }>
                        <span className={cn(
                          'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold',
                          pattern.consistency_score >= 0.7
                            ? 'bg-green-100 text-green-800 border border-green-200'
                            : pattern.consistency_score >= 0.4
                              ? 'bg-amber-100 text-amber-800 border border-amber-200'
                              : 'bg-slate-100 text-slate-600 border border-slate-200'
                        )}>
                          {Math.round(pattern.consistency_score * 100)}% match
                        </span>
                      </Tip>
                    </div>
                  </div>
                  {/* Multi-metric context row */}
                  {pattern.driver && (
                    <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-slate-500">
                      <span>Bacino {deltaArrow(pattern.bacino_delta_pct_avg)}</span>
                      <span className="text-slate-300">|</span>
                      <span>Coverage {deltaArrow(pattern.coverage_delta_pct_avg)}</span>
                      <span className="text-slate-300">|</span>
                      <span>Impressions {deltaArrow(pattern.impressions_delta_pct_avg)}</span>
                      {pattern.revenue_delta_pct_avg != null && (
                        <>
                          <span className="text-slate-300">|</span>
                          <span>Revenue {deltaArrow(pattern.revenue_delta_pct_avg)}</span>
                        </>
                      )}
                    </div>
                  )}
                  {/* Warning tooltip for misleading drivers */}
                  {pattern.driver && (pattern.driver === 'SUPPLY_SQUEEZE' || pattern.driver === 'FILL_EFFECT') && pattern.driver_explanation && (
                    <div className="mt-2 flex items-start gap-1.5 rounded-md bg-amber-100/60 px-2.5 py-1.5 text-xs text-amber-800">
                      <AlertTriangle size={13} className="mt-0.5 shrink-0 text-amber-600" />
                      <span>{pattern.driver_explanation}</span>
                    </div>
                  )}
                  <p className="mt-2 text-sm italic text-slate-500">{pattern.rationale}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Hidden Volume Patterns */}
      {recurringPatterns && recurringPatterns.hidden_patterns.length > 0 && (
        <Card>
          <CardHeader>
            <div>
              <CardTitle className="flex items-center gap-2">
                <EyeOff size={18} className="text-slate-500" />
                Hidden Volume Trends
              </CardTitle>
              <p className="mt-1 text-sm text-slate-500">Revenue/impressions trends invisible to eCPM monitoring</p>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recurringPatterns.hidden_patterns.map((hp: HiddenPattern) => (
                <div
                  key={hp.id}
                  className="rounded-lg border border-slate-200 bg-slate-50 p-4"
                >
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-3">
                      <span className={cn(
                        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border',
                        hp.signal === 'UP'
                          ? 'bg-green-100 text-green-800 border-green-200'
                          : 'bg-red-100 text-red-800 border-red-200'
                      )}>
                        {hp.signal === 'UP' ? '\u2191' : '\u2193'} {hp.signal}
                      </span>
                      <Tip text={hp.metric === 'revenue' ? 'Trend detected on revenue' : hp.metric === 'impressions' ? 'Trend detected on impressions' : 'Trend detected on both revenue and impressions'}>
                        <span className="inline-flex items-center rounded-full bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-700">
                          {hp.metric === 'revenue' ? 'Revenue' : hp.metric === 'impressions' ? 'Impressions' : 'Both'}
                        </span>
                      </Tip>
                      {hp.reliability_score != null && (
                        <Tip text={hp.reliability_score >= 0.7
                          ? 'Very reliable trend: confirmed in both years with consistent behavior'
                          : hp.reliability_score >= 0.4
                            ? 'Medium reliability: trend present but with variations between years'
                            : 'Low reliability: weak trend or high variability'
                        }>
                          <span className={cn(
                            'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold',
                            hp.reliability_score >= 0.7
                              ? 'bg-green-100 text-green-800 border border-green-200'
                              : hp.reliability_score >= 0.4
                                ? 'bg-amber-100 text-amber-800 border border-amber-200'
                                : 'bg-slate-100 text-slate-600 border border-slate-200'
                          )}>
                            {Math.round(hp.reliability_score * 100)}% match
                          </span>
                        </Tip>
                      )}
                      <div>
                        <span className="font-semibold text-slate-900">{hp.label}</span>
                        <span className="ml-2 text-sm text-slate-500">{hp.week_range_label}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-sm text-slate-600">
                        2024: <span className={cn(
                          'font-mono font-medium',
                          hp.avg_delta_pct_2024 > 0 ? 'text-green-700' : hp.avg_delta_pct_2024 < 0 ? 'text-red-700' : 'text-slate-900'
                        )}>
                          {hp.avg_delta_pct_2024 > 0 ? '+' : ''}{hp.avg_delta_pct_2024.toFixed(1)}%
                        </span>
                      </span>
                      <span className="text-sm text-slate-600">
                        2025: <span className={cn(
                          'font-mono font-medium',
                          hp.avg_delta_pct_2025 > 0 ? 'text-green-700' : hp.avg_delta_pct_2025 < 0 ? 'text-red-700' : 'text-slate-900'
                        )}>
                          {hp.avg_delta_pct_2025 > 0 ? '+' : ''}{hp.avg_delta_pct_2025.toFixed(1)}%
                        </span>
                      </span>
                    </div>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-slate-500">
                    <span>eCPM during period: <span className="font-semibold text-slate-700">{hp.ecpm_during_period}</span></span>
                    {hp.weekly_revenue_impact_eur != null && (
                      <>
                        <span className="text-slate-300">|</span>
                        <span className={cn(
                          'font-semibold',
                          hp.weekly_revenue_impact_eur > 0 ? 'text-green-700' : 'text-red-700'
                        )}>
                          ~{formatCurrency(Math.abs(hp.weekly_revenue_impact_eur))}/week impact
                        </span>
                      </>
                    )}
                  </div>
                  <p className="mt-2 text-sm italic text-slate-600">{hp.business_impact}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Danger Zones */}
      {recurringPatterns && recurringPatterns.danger_zones.length > 0 && (
        <Card>
          <CardHeader>
            <div>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle size={18} className="text-rose-500" />
                Risk Zones
              </CardTitle>
              <p className="mt-1 text-sm text-slate-500">Periods where coverage and eCPM drop together &mdash; real demand weakness</p>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recurringPatterns.danger_zones.map((dz: DangerZone) => (
                <div
                  key={dz.id}
                  className="rounded-lg border border-rose-200 bg-rose-50 p-4"
                >
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-3">
                      <Tip text={dz.severity === 'HIGH'
                        ? 'High risk: both eCPM and coverage declining significantly'
                        : 'Moderate risk: joint decline in eCPM and coverage'
                      }>
                        <span className={cn(
                          'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border',
                          dz.severity === 'HIGH'
                            ? 'bg-red-100 text-red-800 border-red-200'
                            : 'bg-orange-100 text-orange-800 border-orange-200'
                        )}>
                          {dz.severity === 'HIGH' ? 'HIGH' : 'MEDIUM'}
                        </span>
                      </Tip>
                      {dz.reliability_score != null && (
                        <Tip text={dz.reliability_score >= 0.7
                          ? 'Confirmed risk zone: significant declines across multiple metrics, strong evidence'
                          : dz.reliability_score >= 0.4
                            ? 'Partially confirmed risk: evidence present but not conclusive'
                            : 'Weak evidence: risk trend based on limited data'
                        }>
                          <span className={cn(
                            'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold',
                            dz.reliability_score >= 0.7
                              ? 'bg-red-100 text-red-800 border border-red-200'
                              : dz.reliability_score >= 0.4
                                ? 'bg-amber-100 text-amber-800 border border-amber-200'
                                : 'bg-slate-100 text-slate-600 border border-slate-200'
                          )}>
                            {Math.round(dz.reliability_score * 100)}% match
                          </span>
                        </Tip>
                      )}
                      <div>
                        <span className="font-semibold text-slate-900">{dz.label}</span>
                        <span className="ml-2 text-sm text-slate-500">{dz.week_range_label}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="tabular-nums text-xs">eCPM: {deltaArrow(dz.ecpm_delta_pct)}</span>
                      <span className="tabular-nums text-xs">Coverage: {deltaArrow(dz.coverage_delta_pct)}</span>
                      {dz.bacino_delta_pct != null && (
                        <span className="tabular-nums text-xs">Bacino: {deltaArrow(dz.bacino_delta_pct)}</span>
                      )}
                    </div>
                  </div>
                  <p className="mt-2 text-sm text-slate-600">{dz.explanation}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
