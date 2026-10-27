import { Globe } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { DataTable, type Column } from '../ui/DataTable'
import { DeltaIndicator } from '../ui/DeltaIndicator'
import { GeoBreakdownPieChart } from '../charts/GeoBreakdownPieChart'
import { ChartErrorBoundary } from '../primitives/ChartErrorBoundary'
import { formatCurrency } from '../../lib/utils'
import type { GeoBreakdown } from '../../types/alert'

interface GeoBreakdownSectionProps {
  geoBreakdown: GeoBreakdown[]
}

export function GeoBreakdownSection({ geoBreakdown }: GeoBreakdownSectionProps) {
  const safeGeoBreakdown = geoBreakdown ?? []

  // Phase 17.2 GAP-CLOSURE (UAT Check 5, 2026-05-20):
  // Renamed reads to match payload contract — cluster + cluster_name
  // (was geo_cluster), revenue_current (was current_revenue),
  // revenue_baseline (was baseline_revenue), delta_eur (was delta_absolute),
  // delta_pct (was delta_percent), quota_of_drop (was contribution).
  // Display column shows cluster_name (e.g. "Italy") with cluster code
  // (e.g. "ITA") as muted subtext for compact recognition. Same contract
  // drift class as TriageSection HOTFIX-05; see 17.2-05-DIAGNOSIS.md.
  const columns: Column<GeoBreakdown>[] = [
    {
      key: 'cluster_name',
      header: 'Geo',
      render: (row) => (
        <span className="font-semibold text-gray-900">
          {row.cluster_name}
          <span className="ml-1 font-mono text-xs text-gray-400">{row.cluster}</span>
        </span>
      ),
    },
    {
      key: 'revenue_current',
      header: 'Current',
      className: 'text-right',
      render: (row) => <span className="font-mono">{formatCurrency(row.revenue_current)}</span>,
    },
    {
      key: 'revenue_baseline',
      header: 'Baseline',
      className: 'text-right',
      render: (row) => (
        <span className="font-mono text-gray-500">{formatCurrency(row.revenue_baseline)}</span>
      ),
    },
    {
      key: 'delta_eur',
      header: 'Delta',
      className: 'text-right',
      render: (row) => (
        <span
          className={`font-mono font-medium ${row.delta_eur < 0 ? 'text-red-600' : 'text-green-600'}`}
        >
          {formatCurrency(row.delta_eur)}
        </span>
      ),
    },
    {
      key: 'delta_pct',
      header: 'Delta %',
      className: 'text-right',
      render: (row) => <DeltaIndicator value={row.delta_pct} />,
    },
    {
      key: 'quota_of_drop',
      header: 'Quota Drop',
      className: 'text-right',
      // Payload emits quota_of_drop as a percentage (e.g. 44.87 = 44.87%),
      // not a 0..1 fraction. Verified against live snapshot 2026-05-20.
      render: (row) => (
        <span className="font-mono text-xs">{row.quota_of_drop.toFixed(0)}%</span>
      ),
    },
  ]

  // Phase 17.2 HOTFIX-04 (B1 Marco 2026-05-19): explicit empty-state card
  // so Tab 4 always renders clean visible content even with an empty
  // geoBreakdown array. Mirrors EnvironmentSplitSection.tsx lines 22-37
  // pattern. Avoids the prior half-empty-table / half-empty-pie layout.
  // See .planning/phases/17.2-marco-feedback-hotfix/17.2-04-DIAGNOSIS.md.
  if (safeGeoBreakdown.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe size={18} className="text-amber-500" />
            Step 4: Geographic Breakdown
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="py-4 text-center text-sm text-gray-400">No geo data available.</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Globe size={18} className="text-amber-500" />
          Step 4: Geographic Breakdown
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div>
            <DataTable
              data={safeGeoBreakdown}
              columns={columns}
              keyExtractor={(row) => row.cluster}
            />
          </div>
          <div className="flex items-center justify-center">
            <ChartErrorBoundary height={260}>
              <GeoBreakdownPieChart data={safeGeoBreakdown} />
            </ChartErrorBoundary>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
