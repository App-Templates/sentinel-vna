import { DollarSign, MousePointer, Eye, Percent } from 'lucide-react'
import { MetricCard } from '../ui/MetricCard'
import { CardSkeleton } from '../ui/Skeleton'
import type { RevenueStatus24hResponse } from '../../api/client'
import { useTranslation } from '../../i18n/context'

interface KpiCardsProps {
  data: RevenueStatus24hResponse | undefined
  isLoading: boolean
}

export function KpiCards({ data, isLoading }: KpiCardsProps) {
  const { t } = useTranslation()
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <CardSkeleton key={i} />
        ))}
      </div>
    )
  }

  if (!data || data.hours.length === 0) {
    return (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <div className="col-span-full rounded-lg border border-gray-200 bg-white px-6 py-8 text-center text-sm text-gray-400">
          {t('kpi.no_data')}
        </div>
      </div>
    )
  }

  const dateLabel = `${data.date} — ${data.day_of_week}`

  const hours = data.hours as Array<{
    hour: number
    revenue: number
    impressions?: number
    bacino?: number
    ctr?: number
    viewability?: number
    gross_margin_pct?: number
  }>

  const totalRevenue = hours.reduce((s, h) => s + (h.revenue ?? 0), 0)
  const totalImpressions = hours.reduce((s, h) => s + (h.impressions ?? 0), 0)
  const totalBacino = hours.reduce((s, h) => s + (h.bacino ?? 0), 0)

  let wCtr = 0
  let wView = 0
  let wMargin = 0
  for (const h of hours) {
    const imp = h.impressions ?? 0
    const rev = h.revenue ?? 0
    if (imp > 0) {
      wCtr += (h.ctr ?? 0) * imp
      wView += (h.viewability ?? 0) * imp
    }
    if (rev > 0) {
      wMargin += (h.gross_margin_pct ?? 0) * rev
    }
  }

  const rpm = totalBacino > 0 ? (totalRevenue / totalBacino) * 1000 : 0
  const ctr = totalImpressions > 0 ? (wCtr / totalImpressions) * 100 : 0
  const viewability = totalImpressions > 0 ? (wView / totalImpressions) * 100 : 0
  const grossMargin = totalRevenue > 0 ? wMargin / totalRevenue : 0

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
      <MetricCard
        label={t('kpi.rpm')}
        value={rpm}
        format="currency_decimal"
        subtitle={dateLabel}
        icon={<DollarSign size={18} />}
        iconBg="bg-indigo-50"
        iconColor="text-indigo-500"
        accentColor="bg-indigo-500"
      />
      <MetricCard
        label={t('kpi.ctr')}
        value={ctr}
        format="percent"
        subtitle={dateLabel}
        icon={<MousePointer size={18} />}
        iconBg="bg-cyan-50"
        iconColor="text-cyan-500"
        accentColor="bg-cyan-500"
      />
      <MetricCard
        label={t('kpi.viewability')}
        value={viewability}
        format="percent"
        subtitle={dateLabel}
        icon={<Eye size={18} />}
        iconBg="bg-violet-50"
        iconColor="text-violet-500"
        accentColor="bg-violet-500"
      />
      <MetricCard
        label={t('kpi.gross_margin')}
        value={grossMargin}
        format="percent"
        subtitle={dateLabel}
        icon={<Percent size={18} />}
        iconBg="bg-teal-50"
        iconColor="text-teal-500"
        accentColor="bg-teal-500"
      />
    </div>
  )
}
