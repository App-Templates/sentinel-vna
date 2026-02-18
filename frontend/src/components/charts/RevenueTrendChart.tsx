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

interface RevenueTrendChartProps {
  data?: MetricDataPoint[]
  height?: number
}

function formatDateShort(ts: string): string {
  const d = new Date(ts)
  return d.toLocaleDateString('it-IT', { month: 'short', day: 'numeric' })
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
        <p className="text-sm text-gray-400">Dati trend revenue non disponibili per questo periodo di alert.</p>
      </div>
    )
  }

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12, fill: '#6b7280' }}
            tickLine={false}
            axisLine={{ stroke: '#e5e7eb' }}
          />
          <YAxis
            tick={{ fontSize: 12, fill: '#6b7280' }}
            tickLine={false}
            axisLine={{ stroke: '#e5e7eb' }}
            tickFormatter={(v: number) => `${(v / 1000).toFixed(0)}k`}
          />
          <Tooltip
            formatter={(value, name) => [
              formatCurrency(Number(value)),
              name === 'revenue' ? 'Revenue Corrente' : 'Baseline',
            ]}
            labelStyle={{ fontWeight: 600, marginBottom: 4 }}
            contentStyle={{
              borderRadius: '8px',
              border: '1px solid #e5e7eb',
              fontSize: '12px',
              boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
            }}
          />
          <Legend
            iconType="line"
            wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }}
          />
          <Line
            type="monotone"
            dataKey="baseline"
            name="Baseline"
            stroke="#9ca3af"
            strokeWidth={2}
            strokeDasharray="6 3"
            dot={false}
            activeDot={{ r: 4, stroke: '#9ca3af', strokeWidth: 2, fill: '#fff' }}
          />
          <Line
            type="monotone"
            dataKey="revenue"
            name="Revenue Corrente"
            stroke="#3b82f6"
            strokeWidth={2.5}
            dot={{ r: 3, fill: '#3b82f6', stroke: '#fff', strokeWidth: 2 }}
            activeDot={{ r: 5, stroke: '#3b82f6', strokeWidth: 2, fill: '#fff' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
