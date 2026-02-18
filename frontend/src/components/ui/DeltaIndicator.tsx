import { ArrowDown, ArrowUp, Minus } from 'lucide-react'
import { cn, formatPercent } from '../../lib/utils'

interface DeltaIndicatorProps {
  value: number
  showIcon?: boolean
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

export function DeltaIndicator({
  value,
  showIcon = true,
  className,
  size = 'md',
}: DeltaIndicatorProps) {
  const isPositive = value > 0
  const isNegative = value < 0

  const colorClass = isNegative
    ? 'text-red-600'
    : isPositive
      ? 'text-green-600'
      : 'text-gray-500'

  const sizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  }

  const iconSize = {
    sm: 12,
    md: 14,
    lg: 16,
  }

  const Icon = isPositive ? ArrowUp : isNegative ? ArrowDown : Minus

  return (
    <span
      className={cn(
        'inline-flex items-center gap-0.5 font-medium',
        colorClass,
        sizeClasses[size],
        className
      )}
    >
      {showIcon && <Icon size={iconSize[size]} />}
      {formatPercent(value)}
    </span>
  )
}
