import { cn } from '../../lib/utils'

interface PageContainerProps {
  children: React.ReactNode
  className?: string
}

export function PageContainer({ children, className }: PageContainerProps) {
  return (
    <main className={cn('flex-1 overflow-y-auto p-6', className)}>
      <div className="mx-auto max-w-[1600px]">
        {children}
      </div>
    </main>
  )
}
