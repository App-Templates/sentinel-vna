import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarChart3 } from 'lucide-react'
import { useTopPublishers } from '../api/client'
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card'
import { DataTable, type Column } from '../components/ui/DataTable'
import { Skeleton, CardSkeleton, TableSkeleton } from '../components/ui/Skeleton'
import { TopNDisclaimer } from '../components/ui/TopNDisclaimer'
import { GrossNetToggle } from '../components/ui/GrossNetToggle'
import { formatCurrency } from '../lib/utils'
import {
  SELL_TYPE_LABELS,
  type SellTypeKey,
  MONTH_LABELS,
  GEO_LABELS,
  PUBLISHER_TIER_LABELS,
  ENVIRONMENT_LABELS,
  GROSS_NET_LABELS,
  REV_SHARE_FACTOR,
  emptyPublishersMultiFiltered,
} from '../lib/i18n-keys'
import { useTopPublishersFilters, type MonthKey, type GeoKey, type PublisherTier, type EnvironmentKey } from '../hooks/useTopPublishersFilters'
import type { PublisherSummary } from '../types/publisher'

// CLIENT-SIDE TIER HEURISTIC — backend-computed tier deferred to Phase 18 INTEL-04. Top 10% by revenue = A, next 20% = B, rest = C.
function computePublisherTier(publishers: PublisherSummary[]): Map<string, 'A' | 'B' | 'C'> {
  const sorted = [...publishers].sort((a, b) => b.total_revenue - a.total_revenue)
  const tierA = Math.ceil(sorted.length * 0.10)
  const tierB = Math.ceil(sorted.length * 0.30)
  const map = new Map<string, 'A' | 'B' | 'C'>()
  sorted.forEach((p, i) => {
    if (i < tierA) map.set(p.publisher_id, 'A')
    else if (i < tierB) map.set(p.publisher_id, 'B')
    else map.set(p.publisher_id, 'C')
  })
  return map
}

function formatBacino(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`
  return String(value)
}

export function PublishersPage() {
  const { filters, setFilter } = useTopPublishersFilters()
  const navigate = useNavigate()
  const { data: publishers, isLoading, error } = useTopPublishers(
    filters.year,
    35,
    filters.sell_type_proxy,
    filters.month,
  )

  // Phase 14 CR-01 fix: ALL hooks must be called BEFORE any conditional early
  // return per React's Rules of Hooks. Previously these `useMemo` calls sat
  // below the `if (isLoading)` / `if (error)` guards with eslint-disable
  // comments masking a real defect — when `isLoading` flipped between renders,
  // React detected hook count mismatch and threw. Now hooks first, conditional
  // rendering after.
  const rawData = publishers ?? []

  // Phase 14 CORR-11: tier classification on the UNFILTERED data so that
  // tier ranks are stable regardless of geo/tier filter selection. Memoized
  // because tier computation is O(n log n).
  const tierMap = useMemo(() => computePublisherTier(rawData), [rawData])

  // Phase 14 CORR-11: client-side filter pipeline. Geo + tier + month are
  // applied here (backend extension deferred to Phase 18 INTEL-04 for tier;
  // deferred for geo + month per UI-SPEC §CORR-11 lines 478-483).
  // D-14.05-X: PublisherSummary does not expose an environment field today;
  // the environment filter ships as a no-op predicate per the same posture
  // as the month filter — when backend extends with dominant_environment or
  // similar, add the predicate here with zero UI changes.
  const data = useMemo(() => rawData.filter((p) => {
    if (filters.geo_cluster !== 'all' && p.dominant_geo !== filters.geo_cluster) return false
    if (filters.publisher_tier !== 'all' && tierMap.get(p.publisher_id) !== filters.publisher_tier) return false
    // Month filter: PublisherSummary does not currently carry a month-of-activity
    // field. When/if a `last_active_month` field lands, add the predicate here.
    // For Phase 14 the month filter is a no-op on the client (already passed to
    // useTopPublishers; backend ignores it per OPS-02 deferral).
    return true
  }), [rawData, tierMap, filters.geo_cluster, filters.publisher_tier])

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-64" />
          </CardHeader>
          <CardContent className="p-0">
            <TableSkeleton rows={10} columns={7} />
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="py-12 text-center">
        <p className="text-red-500">Failed to load publisher data.</p>
      </div>
    )
  }

  // Phase 14 CORR-03: gross/net mode multiplier for revenue display.
  // REV_SHARE_FACTOR is the SSoT (Plan 14-01); never inline 0.6.
  const revenueMultiplier = filters.gross_net === 'net' ? REV_SHARE_FACTOR : 1
  const grossNetSuffix = filters.gross_net === 'net'
    ? GROSS_NET_LABELS.netSuffix
    : GROSS_NET_LABELS.grossSuffix

  const totalRevenue = data.reduce((sum, p) => sum + p.total_revenue, 0) * revenueMultiplier
  const totalBacino = data.reduce((sum, p) => sum + p.total_bacino, 0)
  const totalImpressions = data.reduce((sum, p) => sum + p.total_impressions, 0)
  // CORR-08 weighted eCPM: per-impression CPM is mode-INVARIANT (impressions are
  // not subject to rev-share). UI-SPEC §CORR-03 line 401 limits the toggle to
  // publisher revenue display, not derived per-impression metrics.
  const weightedEcpm = totalImpressions > 0 ? (totalRevenue / revenueMultiplier / totalImpressions) * 1000 : 0
  // CORR-08: weighted by total_impressions (UI-SPEC AC #5).
  // Simple mean overweights small publishers. Weighted matches PBI 35.2% target.
  const totalCoverageWeight = data.reduce((sum, p) => sum + (p.avg_coverage * p.total_impressions), 0)
  const avgFillRate = totalImpressions > 0 ? totalCoverageWeight / totalImpressions : 0

  const columns: Column<PublisherSummary & { rank: number }>[] = [
    {
      key: 'rank',
      header: '#',
      className: 'w-12 text-center',
      render: (row) => (
        <span className="font-mono text-xs text-gray-400">{row.rank}</span>
      ),
    },
    {
      key: 'publisher_id',
      header: 'Publisher',
      sortable: true,
      render: (row) => (
        <span className="font-semibold text-gray-900">{row.publisher_id}</span>
      ),
    },
    {
      key: 'country',
      header: 'Country',
      sortable: true,
      render: (row) => {
        const flag = row.dominant_geo === 'ITA' ? '🇮🇹' : row.dominant_geo === 'ES' ? '🇪🇸' : '🌎'
        return (
          <span className="text-sm">
            <span className="mr-1.5">{flag}</span>
            {row.country}
          </span>
        )
      },
    },
    {
      key: 'total_revenue',
      header: 'Revenue',
      sortable: true,
      className: 'text-right',
      render: (row) => (
        <span className="font-mono tabular-nums">{formatCurrency(row.total_revenue * revenueMultiplier)}</span>
      ),
    },
    {
      key: 'total_bacino',
      header: 'Bacino',
      sortable: true,
      className: 'text-right',
      headerTitle: 'Total ad requests (ad pool): number of ad requests generated by the site/app',
      render: (row) => (
        <span className="font-mono text-xs">{formatBacino(row.total_bacino)}</span>
      ),
    },
    {
      key: 'revenue_share_pct',
      header: 'Share %',
      sortable: true,
      className: 'text-right',
      render: (row) => (
        <span className="font-mono text-xs">{row.revenue_share_pct.toFixed(1)}%</span>
      ),
    },
    {
      key: 'ecpm',
      header: 'eCPM',
      sortable: true,
      className: 'text-right',
      render: (row) => (
        <span className="font-mono">{row.ecpm.toFixed(2)}&euro;</span>
      ),
    },
    {
      key: 'avg_marginality',
      header: 'RPM',
      sortable: true,
      className: 'text-right',
      headerTitle: 'Revenue Per Mille: net revenue per 1000 ad requests (supply). Measures overall traffic monetization',
      render: (row) => (
        <span className="font-mono">{row.avg_marginality.toFixed(2)}&euro;</span>
      ),
    },
    {
      key: 'avg_coverage',
      header: 'Coverage',
      sortable: true,
      className: 'text-right',
      render: (row) => (
        <span className="font-mono text-xs">{(row.avg_coverage * 100).toFixed(1)}%</span>
      ),
    },
    {
      key: 'fill_rate',
      header: 'Fill Rate',
      sortable: true,
      className: 'text-right',
      headerTitle: 'Impressions / Ad Requests: percentage of ad requests actually filled with an ad. Typical values: 40-70%',
      render: (row) => (
        <span className="font-mono text-xs">{(row.fill_rate * 100).toFixed(1)}%</span>
      ),
    },
    {
      key: 'google_pct',
      header: 'Google %',
      sortable: true,
      className: 'text-right',
      headerTitle: 'Percentage of revenue from the Google AdExchange channel. High values (>60%) indicate dependency on a single channel',
      render: (row) => (
        <span className="font-mono text-xs">{row.google_pct.toFixed(1)}%</span>
      ),
    },
    {
      key: 'trend_4w',
      header: 'Trend 4w',
      sortable: true,
      className: 'text-right',
      headerTitle: 'Revenue change over the last 4 weeks vs the previous 4 weeks. Indicates publisher momentum',
      render: (row) => {
        if (row.trend_4w === null) return <span className="text-gray-400">-</span>
        const color = row.trend_4w > 0 ? 'text-green-600' : row.trend_4w < -5 ? 'text-red-600' : 'text-gray-600'
        return (
          <span className={`font-mono text-xs ${color}`}>
            {row.trend_4w > 0 ? '+' : ''}{row.trend_4w.toFixed(1)}%
          </span>
        )
      },
    },
  ]

  const rankedData = data.map((p, i) => ({ ...p, rank: i + 1 }))

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div className="flex items-center gap-3">
        <BarChart3 size={24} className="text-blue-500" />
        <h1 className="text-xl font-bold text-gray-900">Top Publishers</h1>
      </div>

      {/* Phase 14 CORR-04 / RC-(a) closure: Top-N disclaimer */}
      {/* Phase 17.2 HOTFIX-06 (D1 Marco 2026-05-19): forward active filter
         state so the Network totals link reflects current page context.
         Destructured explicitly (not spread) to surface compile-time errors
         if any filter key is renamed in a future phase, and to keep the
         contract between PublishersPage and TopNDisclaimer auditable from
         this file alone. */}
      <TopNDisclaimer
        n={data.length}
        filters={{
          year: filters.year,
          month: filters.month,
          sell_type_proxy: filters.sell_type_proxy,
          geo_cluster: filters.geo_cluster,
          publisher_tier: filters.publisher_tier,
          environment: filters.environment,
        }}
      />

      {/* Phase 14 CORR-03 / RC-(c) closure: gross/net display mode toggle */}
      <div className="flex items-center justify-end mt-4">
        <GrossNetToggle
          value={filters.gross_net}
          onChange={(mode) => setFilter('gross_net', mode)}
        />
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-5">
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-gray-500">{`Total Revenue ${grossNetSuffix}`}</p>
            <p className="text-2xl font-bold text-gray-900 tabular-nums">{formatCurrency(totalRevenue)}</p>
            <p className="text-xs text-gray-400">Top {data.length} publishers</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-gray-500">Total Bacino</p>
            <p className="text-2xl font-bold text-gray-900">{formatBacino(totalBacino)}</p>
            <p className="text-xs text-gray-400">Ad requests totali</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-gray-500">Avg eCPM</p>
            <p className="text-2xl font-bold text-gray-900">{weightedEcpm.toFixed(2)}&euro;</p>
            <p className="text-xs text-gray-400">Weighted average</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-gray-500">Top Publisher</p>
            <p className="text-2xl font-bold text-gray-900">{data[0]?.publisher_id ?? '-'}</p>
            <p className="text-xs text-gray-400 tabular-nums">{data[0] ? formatCurrency(data[0].total_revenue * revenueMultiplier) : ''}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-gray-500">Avg Fill Rate</p>
            <p className="text-2xl font-bold text-gray-900">{(avgFillRate * 100).toFixed(1)}%</p>
            <p className="text-xs text-gray-400">Weighted by impressions</p>
          </CardContent>
        </Card>
      </div>

      {/* Publishers Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Top {data.length} Publishers by Revenue</CardTitle>
            <div className="flex flex-wrap items-center gap-2">
              <select
                value={filters.sell_type_proxy}
                onChange={(e) => setFilter('sell_type_proxy', e.target.value as SellTypeKey)}
                className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                aria-label="Filter publishers by sell type"
              >
                {(Object.keys(SELL_TYPE_LABELS) as SellTypeKey[]).map((key) => (
                  <option key={key} value={key}>{SELL_TYPE_LABELS[key]}</option>
                ))}
              </select>
              <select
                value={filters.geo_cluster}
                onChange={(e) => setFilter('geo_cluster', e.target.value as GeoKey)}
                className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                aria-label="Filter publishers by geo cluster"
              >
                {(Object.keys(GEO_LABELS) as GeoKey[]).map((key) => (
                  <option key={key} value={key}>{GEO_LABELS[key]}</option>
                ))}
              </select>
              <select
                value={filters.publisher_tier}
                onChange={(e) => setFilter('publisher_tier', e.target.value as PublisherTier)}
                className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                aria-label="Filter publishers by tier"
              >
                {(Object.keys(PUBLISHER_TIER_LABELS) as PublisherTier[]).map((key) => (
                  <option key={key} value={key}>{PUBLISHER_TIER_LABELS[key]}</option>
                ))}
              </select>
              <select
                value={filters.environment}
                onChange={(e) => setFilter('environment', e.target.value as EnvironmentKey)}
                className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                aria-label="Filter publishers by environment"
              >
                {(Object.keys(ENVIRONMENT_LABELS) as EnvironmentKey[]).map((key) => (
                  <option key={key} value={key}>{ENVIRONMENT_LABELS[key]}</option>
                ))}
              </select>
              <select
                value={filters.month}
                onChange={(e) => setFilter('month', e.target.value as MonthKey)}
                className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                aria-label="Filter publishers by month"
              >
                {(Object.keys(MONTH_LABELS) as MonthKey[]).map((key) => (
                  <option key={key} value={key}>{MONTH_LABELS[key]}</option>
                ))}
              </select>
              <select
                value={filters.year}
                onChange={(e) => setFilter('year', Number(e.target.value))}
                className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                aria-label="Filter publishers by year"
              >
                <option value={2025}>2025</option>
                <option value={2024}>2024</option>
              </select>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {data.length === 0 ? (
            <div className="py-12 text-center text-gray-500">
              {emptyPublishersMultiFiltered(
                [
                  filters.sell_type_proxy !== 'all' ? SELL_TYPE_LABELS[filters.sell_type_proxy] : null,
                  filters.geo_cluster !== 'all' ? GEO_LABELS[filters.geo_cluster] : null,
                  filters.publisher_tier !== 'all' ? PUBLISHER_TIER_LABELS[filters.publisher_tier] : null,
                  filters.month !== 'all' ? MONTH_LABELS[filters.month] : null,
                ].filter(Boolean) as string[],
                filters.year,
              )}
            </div>
          ) : (
            <DataTable
              data={rankedData}
              columns={columns}
              keyExtractor={(row) => row.publisher_id}
              onRowClick={(row) =>
                // Phase 17.1 MAP-07: removed _family early-return guard. Backend
                // (publisher_routes.py MAP-03/05) no longer produces "Mondadori_family"
                // synthetic rows; all publisher_ids are clean PBI-style names that
                // the backend resolves via reverse-mapping (MAP-08). Names with
                // spaces/accents (e.g. "Prensa Ibérica") get URL-encoded by
                // encodeURIComponent so route matching works.
                navigate(`/publishers/${encodeURIComponent(row.publisher_id)}`)
              }
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
