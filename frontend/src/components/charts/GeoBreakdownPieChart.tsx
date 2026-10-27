import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Legend,
  Tooltip,
  type PieLabelRenderProps,
} from 'recharts'
import { formatCurrency } from '../../lib/utils'
import type { GeoBreakdown } from '../../types/alert'

// Using chart design tokens from @theme
const GEO_COLORS: Record<string, string> = {
  ITA: 'var(--chart-blue, #3b82f6)',
  ES: 'var(--chart-amber, #f59e0b)',
  OTHER: 'var(--chart-violet, #8b5cf6)',
}

const TOOLTIP_STYLE = {
  borderRadius: '8px',
  border: '1px solid #e2e8f0',
  fontSize: '12px',
  boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.07)',
}

interface GeoBreakdownPieChartProps {
  data: GeoBreakdown[]
  height?: number
}

const RADIAN = Math.PI / 180

function renderLabel(props: PieLabelRenderProps) {
  const cx = Number(props.cx ?? 0)
  const cy = Number(props.cy ?? 0)
  const midAngle = Number(props.midAngle ?? 0)
  const innerRadius = Number(props.innerRadius ?? 0)
  const outerRadius = Number(props.outerRadius ?? 0)
  const percent = Number(props.percent ?? 0)
  const name = String(props.name ?? '')

  const radius = innerRadius + (outerRadius - innerRadius) * 0.5
  const x = cx + radius * Math.cos(-midAngle * RADIAN)
  const y = cy + radius * Math.sin(-midAngle * RADIAN)

  if (percent < 0.05) return null

  return (
    <text
      x={x}
      y={y}
      fill="white"
      textAnchor="middle"
      dominantBaseline="central"
      fontSize={12}
      fontWeight={600}
    >
      {name} {(percent * 100).toFixed(0)}%
    </text>
  )
}

export function GeoBreakdownPieChart({ data, height = 260 }: GeoBreakdownPieChartProps) {
  if (!data || data.length === 0) {
    return (
      <div style={{ width: '100%', height }} className="flex items-center justify-center">
        <p className="text-sm text-gray-400">No geographic data available.</p>
      </div>
    )
  }

  const chartData = data.map((g) => ({
    name: g.geo_cluster,
    value: g.current_revenue,
    delta: g.delta_percent,
  }))

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={90}
            paddingAngle={2}
            dataKey="value"
            label={renderLabel}
            labelLine={false}
          >
            {chartData.map((entry) => (
              <Cell
                key={entry.name}
                fill={GEO_COLORS[entry.name] ?? 'var(--chart-gray, #94a3b8)'}
                stroke="white"
                strokeWidth={2}
              />
            ))}
          </Pie>
          <Tooltip
            formatter={(value) => [formatCurrency(Number(value)), 'Revenue']}
            contentStyle={TOOLTIP_STYLE}
          />
          <Legend
            iconType="circle"
            wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }}
            formatter={(value: string) => (
              <span className="text-gray-700">{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
