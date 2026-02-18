import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, Globe, Monitor, TrendingUp, History, EyeOff, AlertTriangle } from 'lucide-react'
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceArea,
} from 'recharts'
import { usePublisherWeeklyKpis, usePublisherEcpmAnalysis, usePublisherRecurringPatterns } from '../api/client'
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Skeleton, CardSkeleton } from '../components/ui/Skeleton'
import { DataTable, type Column } from '../components/ui/DataTable'
import { formatCurrency, cn } from '../lib/utils'
import type { GeoShare, EnvShare, EcpmOptimizationWindow, RecurringPattern, DriverType, HiddenPattern, DangerZone } from '../types/publisher'

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
  return d.toLocaleDateString('it-IT', { day: 'numeric', month: 'short' })
}

function getMonth(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('it-IT', { month: 'short' })
}

const SIGNAL_TOOLTIPS: Record<EcpmOptimizationWindow['signal'], string> = {
  RAISE: 'eCPM superiore alla media annua in questo periodo',
  LOWER: 'eCPM inferiore alla media annua in questo periodo',
  NEUTRAL: 'eCPM nella media annua in questo periodo',
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
          <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-semibold text-gray-600 border border-gray-200">
            &rarr; NEUTRAL
          </span>
        )
    }
  })()
  return <Tip text={SIGNAL_TOOLTIPS[signal]}>{badge}</Tip>
}

const DRIVER_CONFIG: Record<DriverType, { label: string; className: string }> = {
  DEMAND_DRIVEN: { label: 'Domanda', className: 'bg-green-100 text-green-800 border-green-200' },
  SUPPLY_SQUEEZE: { label: 'Compressione Supply', className: 'bg-orange-100 text-orange-800 border-orange-200' },
  FILL_EFFECT: { label: 'Effetto Fill', className: 'bg-orange-100 text-orange-800 border-orange-200' },
  VOLUME_DRIVEN: { label: 'Volume', className: 'bg-blue-100 text-blue-800 border-blue-200' },
  SEASONAL_DEMAND: { label: 'Stagionale', className: 'bg-purple-100 text-purple-800 border-purple-200' },
  MIXED: { label: 'Misto', className: 'bg-gray-100 text-gray-600 border-gray-200' },
}

const DRIVER_TOOLTIPS: Record<DriverType, string> = {
  DEMAND_DRIVEN: 'Il rialzo eCPM è genuino: la domanda pubblicitaria aumenta con bacino e coverage stabili',
  SUPPLY_SQUEEZE: "Attenzione: l'eCPM sale perché l'inventory (bacino) si contrae, non per vera domanda",
  FILL_EFFECT: "Attenzione: l'eCPM sale perché calano le impressions servite — solo quelle premium sopravvivono",
  VOLUME_DRIVEN: "L'eCPM scende per aumento del volume di impressions. La revenue potrebbe comunque crescere",
  SEASONAL_DEMAND: "Variazione stagionale: l'offerta di inventory supera la domanda pubblicitaria",
  MIXED: 'Nessun driver dominante identificato. Andamento influenzato da più fattori',
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
  const color = value > 5 ? 'text-green-600' : value < -5 ? 'text-red-600' : 'text-gray-500'
  const arrow = value > 0 ? '\u2191' : value < 0 ? '\u2193' : '\u2192'
  return (
    <span className={cn('font-mono text-xs', color)}>
      {arrow}{value > 0 ? '+' : ''}{value.toFixed(1)}%
    </span>
  )
}

const SEASONAL_PERIODS = [
  { label: 'Post-Capodanno', startWeek: 1, endWeek: 4, color: '#e0e7ff' },
  { label: 'San Valentino', startWeek: 6, endWeek: 7, color: '#fce7f3' },
  { label: 'Pre-Pasqua', startWeek: 10, endWeek: 12, color: '#fef9c3' },
  { label: 'Pasqua', startWeek: 13, endWeek: 16, color: '#fef3c7' },
  { label: 'Primavera', startWeek: 17, endWeek: 21, color: '#dcfce7' },
  { label: 'Pre-Estate', startWeek: 22, endWeek: 25, color: '#d1fae5' },
  { label: 'Estate', startWeek: 26, endWeek: 34, color: '#dbeafe' },
  { label: 'Rientro', startWeek: 35, endWeek: 37, color: '#f3e8ff' },
  { label: 'Autunno', startWeek: 38, endWeek: 43, color: '#fed7aa' },
  { label: 'Singles Day', startWeek: 44, endWeek: 45, color: '#fecaca' },
  { label: 'Pre-Black Friday', startWeek: 46, endWeek: 46, color: '#fbcfe8' },
  { label: 'Black Friday', startWeek: 47, endWeek: 48, color: '#fce7f3' },
  { label: 'Natale', startWeek: 49, endWeek: 52, color: '#bbf7d0' },
]

const TOGGLEABLE_SERIES = [
  { key: 'bacino', label: 'Bacino', color: '#f59e0b' },
  { key: 'coverage', label: 'Coverage', color: '#8b5cf6' },
  { key: 'impressions', label: 'Impressions', color: '#f43f5e' },
] as const

export function PublisherDetailPage() {
  const { publisherId } = useParams<{ publisherId: string }>()
  const navigate = useNavigate()
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
        <p className="text-red-500">Impossibile caricare i dettagli del publisher.</p>
        <Button variant="outline" className="mt-4" onClick={() => navigate('/publishers')}>
          Torna ai Publishers
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
      render: (row) => <span className="font-semibold text-gray-900">{row.geo_cluster}</span>,
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
      header: 'Quota',
      sortable: true,
      className: 'text-right',
      render: (row) => <span className="font-mono text-xs">{row.share_pct.toFixed(1)}%</span>,
    },
  ]

  const envColumns: Column<EnvShare>[] = [
    {
      key: 'environment',
      header: 'Ambiente',
      render: (row) => <span className="font-semibold text-gray-900">{row.environment}</span>,
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
      header: 'Quota',
      sortable: true,
      className: 'text-right',
      render: (row) => <span className="font-mono text-xs">{row.share_pct.toFixed(1)}%</span>,
    },
  ]

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1 text-sm text-gray-500">
        <Link to="/dashboard" className="hover:text-gray-900">
          Dashboard
        </Link>
        <span className="mx-1">/</span>
        <Link to="/publishers" className="hover:text-gray-900">
          Publishers
        </Link>
        <span className="mx-1">/</span>
        <span className="text-gray-900">{publisherId}</span>
      </nav>

      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/publishers')}>
            <ArrowLeft size={20} />
          </Button>
          <div>
            <h1 className="text-xl font-bold text-gray-900">{publisherId}</h1>
            <div className="mt-1 flex items-center gap-3 text-sm text-gray-500">
              <span>ID: {publisherId}</span>
              <Badge variant="default">Anno {year}</Badge>
            </div>
          </div>
        </div>
        <select
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
        >
          <option value={2025}>2025</option>
          <option value={2024}>2024</option>
        </select>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-gray-500">Revenue Totale</p>
            <p className="text-2xl font-bold text-gray-900">{formatCurrency(totalRevenue)}</p>
            {detail.yoy_summary?.total_revenue_delta_pct != null && (
              <span className={cn(
                'mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-semibold',
                detail.yoy_summary.total_revenue_delta_pct > 0
                  ? 'bg-green-50 text-green-700'
                  : detail.yoy_summary.total_revenue_delta_pct < 0
                    ? 'bg-red-50 text-red-700'
                    : 'bg-gray-50 text-gray-600'
              )}>
                {detail.yoy_summary.total_revenue_delta_pct > 0 ? '+' : ''}{detail.yoy_summary.total_revenue_delta_pct.toFixed(1)}% YoY
              </span>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-gray-500">eCPM</p>
            <p className="text-2xl font-bold text-gray-900">{weightedEcpm.toFixed(2)}&euro;</p>
            {detail.yoy_summary?.ecpm_delta_pct != null ? (
              <span className={cn(
                'mt-1 inline-block rounded-full px-2 py-0.5 text-xs font-semibold',
                detail.yoy_summary.ecpm_delta_pct > 0
                  ? 'bg-green-50 text-green-700'
                  : detail.yoy_summary.ecpm_delta_pct < 0
                    ? 'bg-red-50 text-red-700'
                    : 'bg-gray-50 text-gray-600'
              )}>
                {detail.yoy_summary.ecpm_delta_pct > 0 ? '+' : ''}{detail.yoy_summary.ecpm_delta_pct.toFixed(1)}% YoY
              </span>
            ) : (
              <p className="text-xs text-gray-400">Media ponderata</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-gray-500">Impressions</p>
            <p className="text-2xl font-bold text-gray-900">{formatCompact(totalImpressions)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-gray-500">Coverage</p>
            <p className="text-2xl font-bold text-gray-900">{(weightedCoverage * 100).toFixed(1)}%</p>
            <p className="text-xs text-gray-400">Tasso di riempimento</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Chart */}
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle>Performance Settimanale</CardTitle>
            <div className="flex items-center gap-1.5">
              {TOGGLEABLE_SERIES.map(({ key, label, color }) => (
                <button
                  key={key}
                  onClick={() => toggleSeries(key)}
                  className={cn(
                    'rounded-full border px-3 py-1 text-xs font-medium transition-colors',
                    activeSeries.includes(key)
                      ? 'border-transparent text-white'
                      : 'border-gray-300 bg-white text-gray-500 hover:bg-gray-50'
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
                      : 'border-gray-300 bg-white text-gray-500 hover:bg-gray-50'
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
                    return `Settimana ${label}`
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
              Distribuzione Geografica
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
              Distribuzione per Ambiente
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

      {/* eCPM Optimization Windows */}
      {ecpmAnalysis && (
        <Card>
          <CardHeader>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <CardTitle className="flex items-center gap-2">
                <TrendingUp size={18} className="text-emerald-500" />
                Finestre di Ottimizzazione eCPM
              </CardTitle>
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-500">eCPM Medio Annuo</span>
                <span className="text-xl font-bold text-gray-900">
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
                          : 'border-gray-100 bg-gray-50'
                      )}
                    >
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                        <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-3">
                          {signalBadge(win.signal)}
                          {driverBadge(win.driver)}
                          {win.prev_year_driver && win.driver && (
                            <Tip text={win.prev_year_driver === win.driver
                              ? "Lo stesso driver si è verificato anche l'anno precedente — andamento strutturale"
                              : "Il driver è cambiato rispetto all'anno precedente — andamento instabile, potrebbe non ripetersi"
                            }>
                              <span className={cn(
                                'inline-flex items-center rounded-full border px-1.5 py-0.5 text-[10px] font-medium',
                                win.prev_year_driver === win.driver
                                  ? 'border-green-200 bg-green-50 text-green-700'
                                  : 'border-amber-200 bg-amber-50 text-amber-700'
                              )}>
                                {win.prev_year_driver === win.driver
                                  ? `Stabile (${year - 1})`
                                  : `${year - 1}: ${DRIVER_CONFIG[win.prev_year_driver]?.label ?? win.prev_year_driver}`}
                              </span>
                            </Tip>
                          )}
                          {win.consistency_score != null && (
                            <Tip text={win.consistency_score >= 0.7
                              ? 'Andamento molto affidabile: dati interni coerenti, confermato anche nell\'anno precedente'
                              : win.consistency_score >= 0.4
                                ? 'Affidabilità media: andamento parzialmente confermato — usare con cautela'
                                : 'Bassa affidabilità: andamento debole o non confermato, dati insufficienti o incoerenti'
                            }>
                              <span className={cn(
                                'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold',
                                win.consistency_score >= 0.7
                                  ? 'bg-green-100 text-green-800 border border-green-200'
                                  : win.consistency_score >= 0.4
                                    ? 'bg-amber-100 text-amber-800 border border-amber-200'
                                    : 'bg-gray-100 text-gray-600 border border-gray-200'
                              )}>
                                {Math.round(win.consistency_score * 100)}% match
                              </span>
                            </Tip>
                          )}
                          <div>
                            <span className="font-semibold text-gray-900">{win.period_label}</span>
                            <span className="ml-2 text-sm text-gray-500">{win.date_range}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <span className="text-sm text-gray-500">
                            Media: <span className="font-mono font-medium text-gray-900">{win.avg_ecpm.toFixed(2)}&euro;</span>
                          </span>
                          <span
                            className={cn(
                              'font-mono text-sm font-semibold',
                              win.delta_pct > 0 ? 'text-green-600' : win.delta_pct < 0 ? 'text-red-600' : 'text-gray-500'
                            )}
                          >
                            {isMisleading && <AlertTriangle size={12} className="mr-1 inline text-amber-600" />}
                            {win.delta_pct > 0 ? '+' : ''}{win.delta_pct.toFixed(1)}%
                          </span>
                        </div>
                      </div>
                      {/* Multi-metric delta row */}
                      {(win.bacino_delta_pct != null || win.coverage_delta_pct != null || win.impressions_delta_pct != null || win.revenue_delta_pct != null) && (
                        <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-gray-500">
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
                      <p className="mt-2 text-sm text-gray-600">{win.rationale}</p>
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
                  Andamenti Storici eCPM
                </CardTitle>
                <p className="mt-1 text-sm text-gray-500">Andamenti ricorrenti 2024-2025</p>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <span className="text-gray-500">Media eCPM:</span>
                {recurringPatterns.yearly_avg?.ecpm_2024 != null && (
                  <span className="text-gray-700">
                    2024: <span className="font-mono font-semibold text-gray-900">{recurringPatterns.yearly_avg.ecpm_2024.toFixed(2)}&euro;</span>
                  </span>
                )}
                {recurringPatterns.yearly_avg?.ecpm_2024 != null && recurringPatterns.yearly_avg?.ecpm_2025 != null && (
                  <span className="text-gray-300">|</span>
                )}
                {recurringPatterns.yearly_avg?.ecpm_2025 != null && (
                  <span className="text-gray-700">
                    2025: <span className="font-mono font-semibold text-gray-900">{recurringPatterns.yearly_avg.ecpm_2025.toFixed(2)}&euro;</span>
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
                        <span className="font-semibold text-gray-900">{pattern.label}</span>
                        <span className="ml-2 text-sm text-gray-500">{pattern.week_range_label}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-sm text-gray-600">
                        2024: <span className="font-mono font-medium text-gray-900">{pattern.avg_ecpm_2024.toFixed(2)}&euro;</span>
                        <span className={cn(
                          'ml-1 font-mono text-xs',
                          pattern.avg_delta_pct_2024 > 0 ? 'text-green-600' : pattern.avg_delta_pct_2024 < 0 ? 'text-red-600' : 'text-gray-500'
                        )}>
                          ({pattern.avg_delta_pct_2024 > 0 ? '+' : ''}{pattern.avg_delta_pct_2024.toFixed(1)}%)
                        </span>
                      </span>
                      <span className="text-sm text-gray-600">
                        2025: <span className="font-mono font-medium text-gray-900">{pattern.avg_ecpm_2025.toFixed(2)}&euro;</span>
                        <span className={cn(
                          'ml-1 font-mono text-xs',
                          pattern.avg_delta_pct_2025 > 0 ? 'text-green-600' : pattern.avg_delta_pct_2025 < 0 ? 'text-red-600' : 'text-gray-500'
                        )}>
                          ({pattern.avg_delta_pct_2025 > 0 ? '+' : ''}{pattern.avg_delta_pct_2025.toFixed(1)}%)
                        </span>
                      </span>
                      <Tip text={pattern.consistency_score >= 0.7
                        ? 'Andamento molto affidabile: forte coerenza interna e confermato in entrambi gli anni'
                        : pattern.consistency_score >= 0.4
                          ? 'Affidabilità media: andamento parzialmente coerente — usare con cautela'
                          : 'Bassa affidabilità: alta variabilità interna o scarsa conferma cross-anno'
                      }>
                        <span className={cn(
                          'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold',
                          pattern.consistency_score >= 0.7
                            ? 'bg-green-100 text-green-800 border border-green-200'
                            : pattern.consistency_score >= 0.4
                              ? 'bg-amber-100 text-amber-800 border border-amber-200'
                              : 'bg-gray-100 text-gray-600 border border-gray-200'
                        )}>
                          {Math.round(pattern.consistency_score * 100)}% match
                        </span>
                      </Tip>
                    </div>
                  </div>
                  {/* Multi-metric context row */}
                  {pattern.driver && (
                    <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-gray-500">
                      <span>Bacino {deltaArrow(pattern.bacino_delta_pct_avg)}</span>
                      <span className="text-gray-300">|</span>
                      <span>Coverage {deltaArrow(pattern.coverage_delta_pct_avg)}</span>
                      <span className="text-gray-300">|</span>
                      <span>Impressions {deltaArrow(pattern.impressions_delta_pct_avg)}</span>
                      {pattern.revenue_delta_pct_avg != null && (
                        <>
                          <span className="text-gray-300">|</span>
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
                  <p className="mt-2 text-sm italic text-gray-500">{pattern.rationale}</p>
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
                Andamenti di Volume Nascosti
              </CardTitle>
              <p className="mt-1 text-sm text-gray-500">Andamenti revenue/impressions invisibili al monitoraggio eCPM</p>
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
                      <Tip text={hp.metric === 'revenue' ? 'Andamento rilevato sulla revenue' : hp.metric === 'impressions' ? 'Andamento rilevato sulle impressions' : 'Andamento rilevato sia su revenue che impressions'}>
                        <span className="inline-flex items-center rounded-full bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-700">
                          {hp.metric === 'revenue' ? 'Revenue' : hp.metric === 'impressions' ? 'Impressions' : 'Entrambi'}
                        </span>
                      </Tip>
                      {hp.reliability_score != null && (
                        <Tip text={hp.reliability_score >= 0.7
                          ? 'Andamento molto affidabile: confermato in entrambi gli anni con comportamento coerente'
                          : hp.reliability_score >= 0.4
                            ? 'Affidabilità media: andamento presente ma con variazioni tra gli anni'
                            : 'Bassa affidabilità: andamento debole o con alta variabilità'
                        }>
                          <span className={cn(
                            'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold',
                            hp.reliability_score >= 0.7
                              ? 'bg-green-100 text-green-800 border border-green-200'
                              : hp.reliability_score >= 0.4
                                ? 'bg-amber-100 text-amber-800 border border-amber-200'
                                : 'bg-gray-100 text-gray-600 border border-gray-200'
                          )}>
                            {Math.round(hp.reliability_score * 100)}% match
                          </span>
                        </Tip>
                      )}
                      <div>
                        <span className="font-semibold text-gray-900">{hp.label}</span>
                        <span className="ml-2 text-sm text-gray-500">{hp.week_range_label}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-sm text-gray-600">
                        2024: <span className={cn(
                          'font-mono font-medium',
                          hp.avg_delta_pct_2024 > 0 ? 'text-green-700' : hp.avg_delta_pct_2024 < 0 ? 'text-red-700' : 'text-gray-900'
                        )}>
                          {hp.avg_delta_pct_2024 > 0 ? '+' : ''}{hp.avg_delta_pct_2024.toFixed(1)}%
                        </span>
                      </span>
                      <span className="text-sm text-gray-600">
                        2025: <span className={cn(
                          'font-mono font-medium',
                          hp.avg_delta_pct_2025 > 0 ? 'text-green-700' : hp.avg_delta_pct_2025 < 0 ? 'text-red-700' : 'text-gray-900'
                        )}>
                          {hp.avg_delta_pct_2025 > 0 ? '+' : ''}{hp.avg_delta_pct_2025.toFixed(1)}%
                        </span>
                      </span>
                    </div>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-gray-500">
                    <span>eCPM nel periodo: <span className="font-semibold text-gray-700">{hp.ecpm_during_period}</span></span>
                    {hp.weekly_revenue_impact_eur != null && (
                      <>
                        <span className="text-gray-300">|</span>
                        <span className={cn(
                          'font-semibold',
                          hp.weekly_revenue_impact_eur > 0 ? 'text-green-700' : 'text-red-700'
                        )}>
                          ~{formatCurrency(Math.abs(hp.weekly_revenue_impact_eur))}/sett. impatto
                        </span>
                      </>
                    )}
                  </div>
                  <p className="mt-2 text-sm italic text-gray-600">{hp.business_impact}</p>
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
                Zone di Rischio
              </CardTitle>
              <p className="mt-1 text-sm text-gray-500">Periodi in cui coverage ed eCPM calano insieme &mdash; debolezza reale della domanda</p>
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
                        ? 'Rischio elevato: sia eCPM che coverage calano significativamente'
                        : 'Rischio moderato: calo congiunto di eCPM e coverage'
                      }>
                        <span className={cn(
                          'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold border',
                          dz.severity === 'HIGH'
                            ? 'bg-red-100 text-red-800 border-red-200'
                            : 'bg-orange-100 text-orange-800 border-orange-200'
                        )}>
                          {dz.severity === 'HIGH' ? 'ALTO' : 'MEDIO'}
                        </span>
                      </Tip>
                      {dz.reliability_score != null && (
                        <Tip text={dz.reliability_score >= 0.7
                          ? 'Zona di rischio confermata: cali significativi su più metriche, forte evidenza'
                          : dz.reliability_score >= 0.4
                            ? 'Rischio parzialmente confermato: evidenza presente ma non conclusiva'
                            : 'Evidenza debole: andamento di rischio basato su dati limitati'
                        }>
                          <span className={cn(
                            'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold',
                            dz.reliability_score >= 0.7
                              ? 'bg-red-100 text-red-800 border border-red-200'
                              : dz.reliability_score >= 0.4
                                ? 'bg-amber-100 text-amber-800 border border-amber-200'
                                : 'bg-gray-100 text-gray-600 border border-gray-200'
                          )}>
                            {Math.round(dz.reliability_score * 100)}% match
                          </span>
                        </Tip>
                      )}
                      <div>
                        <span className="font-semibold text-gray-900">{dz.label}</span>
                        <span className="ml-2 text-sm text-gray-500">{dz.week_range_label}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-xs">eCPM: {deltaArrow(dz.ecpm_delta_pct)}</span>
                      <span className="font-mono text-xs">Coverage: {deltaArrow(dz.coverage_delta_pct)}</span>
                      {dz.bacino_delta_pct != null && (
                        <span className="font-mono text-xs">Bacino: {deltaArrow(dz.bacino_delta_pct)}</span>
                      )}
                    </div>
                  </div>
                  <p className="mt-2 text-sm text-gray-600">{dz.explanation}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
