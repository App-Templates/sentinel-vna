import { AlertBox } from '../ui/AlertBox'

interface CacheWarningSectionProps {
  warning: string
}

export function CacheWarningSection({ warning }: CacheWarningSectionProps) {
  if (!warning) return null

  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold text-gray-700">Step 7: Data Quality</h3>
      <AlertBox variant="warning" title="Cache / Memory Effects">
        {warning}
      </AlertBox>
    </div>
  )
}
