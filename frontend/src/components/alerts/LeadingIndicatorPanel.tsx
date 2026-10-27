import { AlertTriangle, TrendingDown } from 'lucide-react'
import { Card, CardContent } from '../ui/Card'
import type { LeadingIndicator } from '../../types/alert'

interface LeadingIndicatorPanelProps {
  indicator: LeadingIndicator
}

export function LeadingIndicatorPanel({ indicator }: LeadingIndicatorPanelProps) {
  const metricLabel = indicator.type === 'CTR_DROP' ? 'CTR' : 'Viewability'

  return (
    <Card className="border-amber-300 bg-amber-50">
      <CardContent className="py-4">
        <div className="flex items-start gap-3">
          <div className="rounded-full bg-amber-100 p-2">
            <AlertTriangle size={20} className="text-amber-600" />
          </div>
          <div className="flex-1">
            <h4 className="font-semibold text-amber-900">Early Signal Detected</h4>
            <p className="mt-1 text-sm text-amber-800">
              A {metricLabel} drop was detected{' '}
              <span className="font-semibold">{indicator.detected_hours_before}h before</span>{' '}
              the revenue alert fired.
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-4 text-sm">
              <div className="flex items-center gap-1.5">
                <TrendingDown size={14} className="text-amber-600" />
                <span className="text-amber-800">
                  {metricLabel}: {indicator.metric_current.toFixed(2)}%
                  <span className="text-amber-600 ml-1">
                    (was {indicator.metric_baseline.toFixed(2)}%, delta {indicator.delta_pct > 0 ? '+' : ''}{indicator.delta_pct.toFixed(1)}%)
                  </span>
                </span>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

interface CrossChannelAnnotationProps {
  annotation: string
}

export function CrossChannelAnnotation({ annotation }: CrossChannelAnnotationProps) {
  return (
    <Card className="border-blue-300 bg-blue-50">
      <CardContent className="py-4">
        <div className="flex items-start gap-3">
          <div className="rounded-full bg-blue-100 p-2">
            <AlertTriangle size={20} className="text-blue-600" />
          </div>
          <div>
            <h4 className="font-semibold text-blue-900">Probable Direct Campaign</h4>
            <p className="mt-1 text-sm text-blue-800">
              {annotation || 'Cross-channel detection indicates a likely direct campaign — verify DIRECT channel.'}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
