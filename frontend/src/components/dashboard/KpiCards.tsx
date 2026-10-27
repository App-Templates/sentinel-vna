import { DollarSign, MousePointer, Eye, Percent } from 'lucide-react'
import { MetricCard } from '../ui/MetricCard'
import { CardSkeleton } from '../ui/Skeleton'
import type { RevenueStatus24hResponse } from '../../api/client'
import { KPI_LABELS, KPI_NO_DATA_COPY } from '../../lib/i18n-keys'
import { ScopeBadge } from '../ui/ScopeBadge'
import { ReferencePeriodFootnote } from '../ui/ReferencePeriodFootnote'

// KpiCards lifted-prop interface (UI-SPEC §"Component Inventory" line 163,
// AC #13). Phase 13 lifts useRevenueStatus24h() to DashboardPage and passes
// data/isLoading down so the dashboard makes ONE API call shared by all
// four cards (RPM, CTR, Viewability, Gross Margin).
export interface KpiCardsProps {
  data: RevenueStatus24hResponse | undefined
  isLoading: boolean
}

export function KpiCards({ data, isLoading }: KpiCardsProps) {
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
          {KPI_NO_DATA_COPY}
        </div>
      </div>
    )
  }

  // Compute weighted KPI aggregates from hourly data (UI-SPEC §"Component
  // Inventory" line 163: "compute RPM/CTR/viewability/gross_margin from
  // hourly data"). Backend may include extended per-hour fields (impressions,
  // bacino, ctr, viewability, gross_margin_pct) on the response — we treat
  // them as optional and fall back to 0 when absent.
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
      <div className="col-span-full flex justify-end mb-2">
        <ScopeBadge channel="GOOGLE_ADEX" />
      </div>
      <MetricCard
        label={KPI_LABELS.rpm}
        value={rpm}
        format="currency"
        icon={<DollarSign size={20} />}
      />
      <MetricCard
        label={KPI_LABELS.ctr}
        value={ctr}
        format="percent"
        icon={<MousePointer size={20} />}
      />
      <MetricCard
        label={KPI_LABELS.viewability}
        value={viewability}
        format="percent"
        icon={<Eye size={20} />}
      />
      <MetricCard
        label={KPI_LABELS.grossMargin}
        value={grossMargin}
        format="percent"
        icon={<Percent size={20} />}
      />
      <div className="col-span-full">
        <ReferencePeriodFootnote timestamp={data.date} />
      </div>
    </div>
  )
}
