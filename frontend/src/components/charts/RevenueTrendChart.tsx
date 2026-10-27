import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { formatCurrency } from '../../lib/utils'
import type { MetricDataPoint } from '../../types/alert'
import { CHART_EMPTY_COPY } from '../../lib/i18n-keys'

interface RevenueTrendChartProps {
  data?: MetricDataPoint[]
  height?: number
}

function formatDateShort(ts: string): string {
  const d = new Date(ts)
  return d.toLocaleDateString('en-GB', { month: 'short', day: 'numeric' })
}

// Shared chart style constants — CSS vars from @theme in index.css
const AXIS_STYLE = { fontSize: 12, fill: 'var(--chart-tick, #64748b)' }
const AXIS_LINE = { stroke: 'var(--chart-axis, #e2e8f0)' }
const GRID_STROKE = 'var(--chart-grid, #f1f5f9)'
const TOOLTIP_STYLE = {
  borderRadius: '8px',
  border: '1px solid #e2e8f0',
  fontSize: '12px',
  boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.07)',
}

export function RevenueTrendChart({ data, height = 280 }: RevenueTrendChartProps) {
  const chartData = (data ?? []).map((p) => ({
    date: formatDateShort(p.timestamp),
    revenue: p.revenue,
    baseline: p.baseline_revenue ?? 0,
  }))

  if (chartData.length === 0) {
    return (
      <div style={{ width: '100%', height }} className="flex items-center justify-center">
        <p className="text-sm text-gray-400">{CHART_EMPTY_COPY.revenueTrend}</p>
      </div>
    )
  }

  // Tailwind color values: blue-500=#3b82f6, gray-400=#9ca3af, gray-200=#e5e7eb, gray-100=#f3f4f6, gray-500=#6b7280
  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
          <XAxis dataKey="date" tick={AXIS_STYLE} tickLine={false} axisLine={AXIS_LINE} />
          <YAxis
            tick={AXIS_STYLE}
            tickLine={false}
            axisLine={AXIS_LINE}
            tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
          />
          <Tooltip
            // Phase 17.2 HOTFIX-01 (V3 Marco 2026-05-19): the previous
            // discriminant compared the formatter's `name` arg against the
            // dataKey string, but recharts passes the `<Line name="...">`
            // prop ("Current Revenue" / "Baseline") as `name` — NOT the
            // dataKey. The comparison was always false → BOTH rows
            // rendered as "Baseline". Fix: read the dataKey off the 3rd
            // argument (`item.dataKey`) which is the actual series
            // identifier and is decoupled from any future label rename.
            formatter={(value, _name, item) => [
              formatCurrency(Number(value)),
              (item as { dataKey?: string } | undefined)?.dataKey === 'revenue'
                ? 'Current Revenue'
                : 'Baseline',
            ]}
            labelStyle={{ fontWeight: 600, marginBottom: 4 }}
            contentStyle={TOOLTIP_STYLE}
          />
          <Legend iconType="line" wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }} />
          <Line
            type="monotone"
            dataKey="baseline"
            name="Baseline"
            stroke="var(--chart-gray, #94a3b8)"
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={false}
            activeDot={{ r: 4, stroke: 'var(--chart-gray, #94a3b8)', strokeWidth: 2, fill: '#fff' }}
          />
          <Line
            type="monotone"
            dataKey="revenue"
            name="Current Revenue"
            stroke="var(--chart-blue, #3b82f6)"
            strokeWidth={2.5}
            dot={{ r: 3, fill: 'var(--chart-blue, #3b82f6)', stroke: '#fff', strokeWidth: 2 }}
            activeDot={{ r: 5, stroke: 'var(--chart-blue, #3b82f6)', strokeWidth: 2, fill: '#fff' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
