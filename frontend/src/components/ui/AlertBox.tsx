import { AlertTriangle, Info, CheckCircle, XCircle } from 'lucide-react'
import { cn } from '../../lib/utils'

const variants = {
  warning: {
    container: 'bg-amber-50 border-amber-200 text-amber-800',
    icon: AlertTriangle,
  },
  info: {
    container: 'bg-blue-50 border-blue-200 text-blue-800',
    icon: Info,
  },
  success: {
    container: 'bg-green-50 border-green-200 text-green-800',
    icon: CheckCircle,
  },
  error: {
    container: 'bg-red-50 border-red-200 text-red-800',
    icon: XCircle,
  },
}

interface AlertBoxProps {
  variant?: keyof typeof variants
  title?: string
  children: React.ReactNode
  className?: string
}

export function AlertBox({
  variant = 'info',
  title,
  children,
  className,
}: AlertBoxProps) {
  const { container, icon: Icon } = variants[variant]

  return (
    <div className={cn('flex gap-3 rounded-lg border p-4', container, className)}>
      <Icon size={20} className="mt-0.5 shrink-0" />
      <div className="min-w-0">
        {title && <p className="mb-1 font-semibold">{title}</p>}
        <div className="text-sm">{children}</div>
      </div>
    </div>
  )
}
