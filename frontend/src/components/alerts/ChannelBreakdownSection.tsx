import { BarChart3 } from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { formatCurrency } from '../../lib/utils'
import { CHANNEL_COLORS, CHANNEL_LABELS } from '../../lib/channels'
import type { ChannelBreakdown } from '../../types/alert'

interface ChannelBreakdownSectionProps {
  breakdown: ChannelBreakdown[]
}

const AXIS_STYLE = { fontSize: 12, fill: 'var(--chart-tick, #64748b)' }
const AXIS_LINE = { stroke: 'var(--chart-axis, #e2e8f0)' }
const GRID_STROKE = 'var(--chart-grid, #f1f5f9)'
const TOOLTIP_STYLE = {
  borderRadius: '8px',
  border: '1px solid #e2e8f0',
  fontSize: '12px',
  boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.07)',
}

export function ChannelBreakdownSection({ breakdown }: ChannelBreakdownSectionProps) {
  if (!breakdown || breakdown.length === 0) return null

  const chartData = breakdown.map((b) => ({
    channel: CHANNEL_LABELS[b.channel_group] ?? b.channel_group,
    channel_key: b.channel_group,
    revenue: b.revenue,
    baseline: b.baseline_revenue,
    delta_pct: b.delta_pct,
    share_pct: b.share_pct,
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 size={18} className="text-indigo-500" />
          Channel Breakdown
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div style={{ width: '100%', height: 280 }}>
          <ResponsiveContainer>
            <BarChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
              <XAxis
                dataKey="channel"
                tick={AXIS_STYLE}
                tickLine={false}
                axisLine={AXIS_LINE}
              />
              <YAxis
                tick={AXIS_STYLE}
                tickLine={false}
                axisLine={AXIS_LINE}
                tickFormatter={(v: number) =>
                  v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)
                }
              />
              <Tooltip
                contentStyle={TOOLTIP_STYLE}
                content={({ active, payload }) => {
                  if (!active || !payload || payload.length === 0) return null
                  const d = payload[0]?.payload
                  return (
                    <div style={TOOLTIP_STYLE} className="bg-white px-3 py-2 text-xs">
                      <p className="font-semibold text-slate-700 mb-1">{d.channel}</p>
                      <p className="tabular-nums text-blue-600">Revenue: {formatCurrency(d.revenue)}</p>
                      <p className="tabular-nums text-slate-400">Baseline: {formatCurrency(d.baseline)}</p>
                      <p className={`tabular-nums ${d.delta_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        Delta: {d.delta_pct > 0 ? '+' : ''}{d.delta_pct.toFixed(1)}%
                      </p>
                      <p className="tabular-nums text-slate-400">Share: {d.share_pct.toFixed(1)}%</p>
                    </div>
                  )
                }}
              />
              <Bar dataKey="revenue" name="Revenue" radius={[4, 4, 0, 0]}>
                {chartData.map((entry) => (
                  <Cell
                    key={entry.channel_key}
                    fill={CHANNEL_COLORS[entry.channel_key] ?? '#6b7280'}
                  />
                ))}
              </Bar>
              <Bar dataKey="baseline" name="Baseline" radius={[4, 4, 0, 0]} fillOpacity={0.3}>
                {chartData.map((entry) => (
                  <Cell
                    key={entry.channel_key}
                    fill={CHANNEL_COLORS[entry.channel_key] ?? '#6b7280'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
