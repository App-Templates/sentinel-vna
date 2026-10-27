import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Cell,
  LabelList,
} from 'recharts'
import { formatCurrency } from '../../lib/utils'
import type { Environment, EnvironmentMetrics } from '../../types/alert'

const AXIS_STYLE = { fontSize: 12, fill: 'var(--chart-tick, #64748b)' }
const AXIS_LINE = { stroke: 'var(--chart-axis, #e2e8f0)' }
const GRID_STROKE = 'var(--chart-grid, #f1f5f9)'
const TOOLTIP_STYLE = {
  borderRadius: '8px',
  border: '1px solid #e2e8f0',
  fontSize: '12px',
  boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.07)',
}

interface EnvironmentBarChartProps {
  data: Record<Environment, EnvironmentMetrics>
  height?: number
}

export function EnvironmentBarChart({ data, height = 280 }: EnvironmentBarChartProps) {
  if (!data || Object.keys(data).length === 0) {
    return (
      <div style={{ width: '100%', height }} className="flex items-center justify-center">
        <p className="text-sm text-gray-400">No environment data available.</p>
      </div>
    )
  }

  const chartData = (Object.entries(data) as [Environment, EnvironmentMetrics][]).map(
    ([env, metrics]) => ({
      name: env,
      current: metrics.revenue,
      baseline: metrics.baseline_revenue,
      delta: metrics.delta_percent,
    })
  )

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <BarChart data={chartData} barGap={4} margin={{ top: 15, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={GRID_STROKE} />
          <XAxis dataKey="name" tick={AXIS_STYLE} tickLine={false} axisLine={AXIS_LINE} />
          <YAxis
            tick={AXIS_STYLE}
            tickLine={false}
            axisLine={AXIS_LINE}
            tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
          />
          <Tooltip
            formatter={(value, name) => [
              formatCurrency(Number(value)),
              name === 'baseline' ? 'Baseline' : 'Current',
            ]}
            contentStyle={TOOLTIP_STYLE}
          />
          <Legend
            iconType="rect"
            wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }}
          />
          <Bar
            dataKey="baseline"
            name="Baseline"
            fill="var(--chart-gray, #94a3b8)"
            fillOpacity={0.5}
            radius={[4, 4, 0, 0]}
            maxBarSize={60}
          />
          <Bar
            dataKey="current"
            name="Current"
            radius={[4, 4, 0, 0]}
            maxBarSize={60}
          >
            {chartData.map((entry) => (
              <Cell
                key={entry.name}
                fill={
                  entry.delta < -15
                    ? 'var(--chart-red, #ef4444)'
                    : entry.delta < -5
                      ? 'var(--chart-orange, #f97316)'
                      : 'var(--chart-blue, #3b82f6)'
                }
              />
            ))}
            <LabelList
              dataKey="delta"
              position="top"
              formatter={(v) => {
                const n = Number(v)
                return `${n > 0 ? '+' : ''}${n.toFixed(1)}%`
              }}
              style={{ fontSize: 12, fontWeight: 600, fill: 'var(--chart-tick, #64748b)' }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
