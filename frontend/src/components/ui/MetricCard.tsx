import { cn, formatCurrency } from '../../lib/utils'
import { Card } from './Card'
import { DeltaIndicator } from './DeltaIndicator'

interface MetricCardProps {
  label: string
  value: number
  delta?: number
  format?: 'currency' | 'number' | 'percent'
  className?: string
  icon?: React.ReactNode
}

export function MetricCard({
  label,
  value,
  delta,
  format = 'currency',
  className,
  icon,
}: MetricCardProps) {
  const formattedValue =
    format === 'currency'
      ? formatCurrency(value)
      : format === 'percent'
        ? `${value.toFixed(1)}%`
        : value.toLocaleString()

  return (
    <Card className={cn('p-5', className)}>
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <p className="text-sm font-medium text-gray-500">{label}</p>
          <p className="text-2xl font-bold text-gray-900">{formattedValue}</p>
          {delta !== undefined && (
            <DeltaIndicator value={delta} size="sm" />
          )}
        </div>
        {icon && (
          <div className="rounded-lg bg-gray-100 p-2 text-gray-600">
            {icon}
          </div>
        )}
      </div>
    </Card>
  )
}
