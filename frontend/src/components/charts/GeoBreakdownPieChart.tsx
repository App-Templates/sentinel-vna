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
import { CHART_EMPTY_COPY } from '../../lib/i18n-keys'

const GEO_COLORS: Record<string, string> = {
  ITA: '#3b82f6',
  ES: '#f59e0b',
  OTHER: '#8b5cf6',
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
        <p className="text-sm text-gray-400">{CHART_EMPTY_COPY.geoBreakdown}</p>
      </div>
    )
  }

  // Phase 17.2 GAP-CLOSURE (UAT Check 5, 2026-05-20): read renamed contract
  // fields per types/alert.ts GeoBreakdown.
  const chartData = data.map((g) => ({
    name: g.cluster,
    value: g.revenue_current,
    delta: g.delta_pct,
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
                fill={GEO_COLORS[entry.name] ?? '#6b7280'}
                stroke="white"
                strokeWidth={2}
              />
            ))}
          </Pie>
          <Tooltip
            formatter={(value) => [
              formatCurrency(Number(value)),
              'Revenue',
            ]}
            contentStyle={{
              borderRadius: '8px',
              border: '1px solid #e5e7eb',
              fontSize: '12px',
              boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
            }}
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
