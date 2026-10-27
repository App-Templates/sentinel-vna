import { cn, formatCurrency } from '../../lib/utils'
import { Card } from './Card'
import { DeltaIndicator } from './DeltaIndicator'

interface MetricCardProps {
  label: string
  value: number
  delta?: number
  format?: 'currency' | 'currency_decimal' | 'number' | 'percent'
  subtitle?: string
  className?: string
  icon?: React.ReactNode
  iconBg?: string
  iconColor?: string
  accentColor?: string
}

export function MetricCard({
  label,
  value,
  delta,
  format = 'currency',
  subtitle,
  className,
  icon,
  iconBg = 'bg-slate-50',
  iconColor = 'text-slate-400',
  accentColor,
}: MetricCardProps) {
  const formattedValue =
    format === 'currency'
      ? formatCurrency(value)
      : format === 'currency_decimal'
        ? new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'EUR',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          }).format(value)
        : format === 'percent'
          ? `${value.toFixed(1)}%`
          : value.toLocaleString()

  return (
    <Card className={cn('relative overflow-hidden transition-shadow duration-200 hover:shadow-md', className)}>
      {accentColor && (
        <div className={cn('absolute left-0 top-0 h-full w-1 rounded-l-lg', accentColor)} />
      )}
      <div className={cn('flex items-start justify-between py-4', accentColor ? 'pl-6 pr-5' : 'px-5')}>
        <div className="min-w-0 space-y-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{label}</p>
          <p className="text-2xl font-bold tabular-nums text-slate-900">{formattedValue}</p>
          {subtitle && (
            <p className="text-xs text-slate-400">{subtitle}</p>
          )}
          {delta !== undefined && (
            <DeltaIndicator value={delta} size="sm" />
          )}
        </div>
        {icon && (
          <div className={cn('flex-shrink-0 rounded-lg p-2.5', iconBg, iconColor)}>
            {icon}
          </div>
        )}
      </div>
    </Card>
  )
}
