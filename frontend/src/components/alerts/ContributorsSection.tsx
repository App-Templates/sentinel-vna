import { Users } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { DataTable, type Column } from '../ui/DataTable'
import { DeltaIndicator } from '../ui/DeltaIndicator'
import { formatCurrency } from '../../lib/utils'
import type { Contributor } from '../../types/alert'

interface ContributorsSectionProps {
  contributors: Contributor[]
}

export function ContributorsSection({ contributors }: ContributorsSectionProps) {
  const safeContributors = contributors ?? []

  // Phase 17.2 GAP-CLOSURE (UAT Check 5, 2026-05-20):
  // Renamed reads to match payload contract — display_name (was publisher_name),
  // revenue_current (was current_revenue), revenue_baseline (was baseline_revenue),
  // delta_eur (was delta_absolute), delta_pct (was delta_percent). Same contract
  // drift class as TriageSection HOTFIX-05; see 17.2-05-DIAGNOSIS.md.
  const top3Ids = new Set(
    [...safeContributors]
      .sort((a, b) => Math.abs(b.delta_eur) - Math.abs(a.delta_eur))
      .slice(0, 3)
      .map((c) => c.publisher_id)
  )

  const concentrationIndex =
    safeContributors.length > 0
      ? [...safeContributors]
          .sort((a, b) => Math.abs(b.quota_of_drop) - Math.abs(a.quota_of_drop))
          .slice(0, 3)
          .reduce((sum, c) => sum + c.quota_of_drop, 0)
      : 0

  const columns: Column<Contributor>[] = [
    {
      key: 'display_name',
      header: 'Publisher',
      sortable: true,
      render: (row) => (
        <span className={top3Ids.has(row.publisher_id) ? 'font-semibold text-gray-900' : ''}>
          {row.display_name}
        </span>
      ),
    },
    {
      key: 'revenue_current',
      header: 'Current (EUR)',
      sortable: true,
      className: 'text-right',
      render: (row) => (
        <span className="font-mono">{formatCurrency(row.revenue_current)}</span>
      ),
    },
    {
      key: 'revenue_baseline',
      header: 'Baseline (EUR)',
      sortable: true,
      className: 'text-right',
      render: (row) => (
        <span className="font-mono text-gray-500">{formatCurrency(row.revenue_baseline)}</span>
      ),
    },
    {
      key: 'delta_eur',
      header: 'Delta (EUR)',
      sortable: true,
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
      sortable: true,
      className: 'text-right',
      render: (row) => <DeltaIndicator value={row.delta_pct} />,
    },
    {
      key: 'quota_of_drop',
      header: 'Quota Drop',
      sortable: true,
      className: 'text-right',
      // Payload emits quota_of_drop as a percentage (e.g. 10.57 = 10.57%),
      // not a 0..1 fraction. Verified against live snapshot 2026-05-20.
      render: (row) => (
        <div className="flex items-center justify-end gap-2">
          <div className="h-1.5 w-16 overflow-hidden rounded-full bg-gray-200">
            <div
              className="h-full rounded-full bg-red-400"
              style={{ width: `${Math.min(row.quota_of_drop, 100)}%` }}
            />
          </div>
          <span className="w-12 text-right font-mono text-xs">
            {row.quota_of_drop.toFixed(1)}%
          </span>
        </div>
      ),
    },
  ]

  // Phase 17.2 HOTFIX-04 (B1 Marco 2026-05-19): explicit empty-state card
  // so Tab 3 always renders clean visible content even with an empty
  // contributors array. Mirrors EnvironmentSplitSection.tsx lines 22-37
  // pattern. Avoids the prior half-bait layout (Concentration 0.0% + a
  // DataTable empty fallback) which looked like a real measurement.
  // See .planning/phases/17.2-marco-feedback-hotfix/17.2-04-DIAGNOSIS.md.
  if (safeContributors.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users size={18} className="text-blue-500" />
            Step 3: Top Contributors
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="py-4 text-center text-sm text-gray-400">No contributor data available.</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Users size={18} className="text-blue-500" />
            Step 3: Top Contributors
          </CardTitle>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-500">Concentration (Top 3):</span>
            <span
              // concentrationIndex is a sum of percentages (each
              // quota_of_drop is already 0..100). Threshold check uses
              // 60% to match Marco's "concentrated drop" rule of thumb.
              className={`font-semibold ${concentrationIndex > 60 ? 'text-red-600' : 'text-amber-600'}`}
            >
              {concentrationIndex.toFixed(1)}%
            </span>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <DataTable
          data={safeContributors}
          columns={columns}
          keyExtractor={(row) => row.publisher_id}
        />
      </CardContent>
    </Card>
  )
}
