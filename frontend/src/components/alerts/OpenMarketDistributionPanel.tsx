import { TrendingUp, TrendingDown, Info } from 'lucide-react'
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { formatCurrency } from '../../lib/utils'
import { CHANNEL_COLORS, CHANNEL_LABELS } from '../../lib/channels'
import { OPEN_MARKET_CHANNELS } from '../../lib/demand-layers'
import type { ChannelBreakdown, ChannelGroup } from '../../types/alert'

interface OpenMarketDistributionPanelProps {
  breakdown: ChannelBreakdown[] | undefined
}

// Phase 19 V2 — Open Market intra-channel distribution panel.
//
// Marco feedback 2026-05-19 (V2): "All'interno dell'open ci puo' essere uno
// shift di revenue tra Channel ... seguendo la logica del punto precedente
// sarebbe meglio studiare la distribuzione % della revenue nel caso di
// problemi su Open Market".
//
// Renders a side-by-side comparison of current vs baseline distribution
// across OM sub-channels so operators can quickly distinguish
// "intra-OM shift" (one OM channel gained while another lost, OM total
// roughly preserved) from "true OM revenue drop" (all OM channels lost).
export function OpenMarketDistributionPanel({
  breakdown,
}: OpenMarketDistributionPanelProps) {
  const omSet = new Set<string>(OPEN_MARKET_CHANNELS)
  const omRows = (breakdown ?? []).filter((r) => omSet.has(r.channel_group))

  // Empty state — honest disclosure when source data lacks per-OM-channel
  // hourly granularity. Affects HBM/HBP/TAM/OB historic alerts (hour_kpi.csv
  // upstream contains only GOOGLE_ADEX); resolved when Phase 21 Athena
  // hourly ingestion lands.
  if (omRows.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Info size={18} className="text-blue-500" />
            Open Market Distribution
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border border-blue-100 bg-blue-50 p-4 text-sm text-blue-900">
            <p className="font-medium mb-1">
              Per-sub-channel Open Market breakdown not available for this alert.
            </p>
            <p className="text-blue-800">
              Hourly distribution across the Open Market sub-channels
              (GOOGLE_ADEX, OPEN_BIDDING, HEADER_BIDDING_MAGNITE,
              HEADER_BIDDING_PUBMATIC, TAM) requires the Athena hourly
              ingestion. Current historic source data (hour_kpi.csv)
              covers GOOGLE_ADEX only. Athena activation lands the missing
              channels for new alerts going forward.
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const totalCurrent = omRows.reduce((sum, r) => sum + r.revenue, 0)
  const totalBaseline = omRows.reduce((sum, r) => sum + r.baseline_revenue, 0)

  const pieCurrent = omRows.map((r) => ({
    name: CHANNEL_LABELS[r.channel_group] ?? r.channel_group,
    value: r.revenue,
    channel_key: r.channel_group,
  }))
  const pieBaseline = omRows.map((r) => ({
    name: CHANNEL_LABELS[r.channel_group] ?? r.channel_group,
    value: r.baseline_revenue,
    channel_key: r.channel_group,
  }))

  // Per-channel share comparison rows (current vs baseline distribution).
  const rows = omRows.map((r) => {
    const shareCurrent = totalCurrent > 0 ? (r.revenue / totalCurrent) * 100 : 0
    const shareBaseline =
      totalBaseline > 0 ? (r.baseline_revenue / totalBaseline) * 100 : 0
    const shareDelta = shareCurrent - shareBaseline
    return {
      channel: r.channel_group as ChannelGroup,
      label: CHANNEL_LABELS[r.channel_group] ?? r.channel_group,
      revenue: r.revenue,
      baseline_revenue: r.baseline_revenue,
      delta_pct: r.delta_pct,
      shareCurrent,
      shareBaseline,
      shareDelta,
    }
  })

  const omDeltaPct =
    totalBaseline > 0 ? ((totalCurrent - totalBaseline) / totalBaseline) * 100 : 0
  // "Intra-OM shift" signal: OM total roughly preserved but individual
  // shares moved meaningfully. Threshold: ±3pp share movement, |total
  // delta| < 5%. Operator-facing heuristic — adjustable in v1.4.
  const significantShifts = rows.filter((r) => Math.abs(r.shareDelta) >= 3)
  const intraOmShift =
    Math.abs(omDeltaPct) < 5 && significantShifts.length >= 2

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp size={18} className="text-blue-500" />
          Open Market Distribution
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Headline summary */}
        <div className="mb-4 flex flex-wrap items-baseline gap-x-4 gap-y-1 text-sm">
          <span className="text-gray-700">
            OM total current:{' '}
            <span className="font-semibold text-gray-900">
              {formatCurrency(totalCurrent)}
            </span>
          </span>
          <span className="text-gray-500">
            baseline: {formatCurrency(totalBaseline)}
          </span>
          <span
            className={
              omDeltaPct >= 0
                ? 'inline-flex items-center gap-1 text-green-700'
                : 'inline-flex items-center gap-1 text-red-700'
            }
          >
            {omDeltaPct >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            {omDeltaPct > 0 ? '+' : ''}
            {omDeltaPct.toFixed(1)}%
          </span>
        </div>

        {intraOmShift && (
          <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
            <span className="font-semibold">Possible intra-OM shift:</span>{' '}
            OM total moved less than 5% while {significantShifts.length}{' '}
            sub-channel{significantShifts.length > 1 ? 's' : ''} shifted share
            by ≥3pp. A drop on one OM channel may be partially offset by a
            gain on another — verify before treating as a true revenue drop.
          </div>
        )}

        {/* Side-by-side donut: current vs baseline distribution */}
        <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <p className="mb-1 text-center text-xs font-medium uppercase tracking-wide text-gray-500">
              Current Distribution
            </p>
            <div style={{ width: '100%', height: 220 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={pieCurrent}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={45}
                    outerRadius={75}
                    paddingAngle={2}
                  >
                    {pieCurrent.map((entry) => (
                      <Cell
                        key={`cur-${entry.channel_key}`}
                        fill={CHANNEL_COLORS[entry.channel_key] ?? '#6b7280'}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(v: number, name: string) => [formatCurrency(v), name]}
                  />
                  <Legend
                    iconSize={8}
                    wrapperStyle={{ fontSize: 11 }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div>
            <p className="mb-1 text-center text-xs font-medium uppercase tracking-wide text-gray-500">
              Baseline Distribution
            </p>
            <div style={{ width: '100%', height: 220 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    data={pieBaseline}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={45}
                    outerRadius={75}
                    paddingAngle={2}
                  >
                    {pieBaseline.map((entry) => (
                      <Cell
                        key={`base-${entry.channel_key}`}
                        fill={CHANNEL_COLORS[entry.channel_key] ?? '#6b7280'}
                        fillOpacity={0.6}
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(v: number, name: string) => [formatCurrency(v), name]}
                  />
                  <Legend
                    iconSize={8}
                    wrapperStyle={{ fontSize: 11 }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Per-channel comparison table */}
        <div className="overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead>
              <tr className="border-b border-gray-200 text-left text-gray-500">
                <th className="py-2 pr-3 font-medium">Channel</th>
                <th className="py-2 pr-3 text-right font-medium">Current</th>
                <th className="py-2 pr-3 text-right font-medium">Baseline</th>
                <th className="py-2 pr-3 text-right font-medium">Δ Revenue</th>
                <th className="py-2 pr-3 text-right font-medium">Share now</th>
                <th className="py-2 pr-3 text-right font-medium">Share base</th>
                <th className="py-2 text-right font-medium">Δ Share (pp)</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={r.channel}
                  className="border-b border-gray-100 text-gray-700"
                >
                  <td className="py-2 pr-3">
                    <span
                      className="inline-block h-2 w-2 rounded-full align-middle"
                      style={{
                        backgroundColor:
                          CHANNEL_COLORS[r.channel] ?? '#6b7280',
                      }}
                    />
                    <span className="ml-2">{r.label}</span>
                  </td>
                  <td className="py-2 pr-3 text-right">{formatCurrency(r.revenue)}</td>
                  <td className="py-2 pr-3 text-right text-gray-500">
                    {formatCurrency(r.baseline_revenue)}
                  </td>
                  <td
                    className={`py-2 pr-3 text-right ${
                      r.delta_pct >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}
                  >
                    {r.delta_pct > 0 ? '+' : ''}
                    {r.delta_pct.toFixed(1)}%
                  </td>
                  <td className="py-2 pr-3 text-right">{r.shareCurrent.toFixed(1)}%</td>
                  <td className="py-2 pr-3 text-right text-gray-500">
                    {r.shareBaseline.toFixed(1)}%
                  </td>
                  <td
                    className={`py-2 text-right ${
                      Math.abs(r.shareDelta) >= 3
                        ? r.shareDelta > 0
                          ? 'text-green-700 font-semibold'
                          : 'text-red-700 font-semibold'
                        : 'text-gray-500'
                    }`}
                  >
                    {r.shareDelta > 0 ? '+' : ''}
                    {r.shareDelta.toFixed(1)}pp
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
