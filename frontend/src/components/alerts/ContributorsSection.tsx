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

  const top3Ids = new Set(
    [...safeContributors]
      .sort((a, b) => Math.abs(b.delta_absolute) - Math.abs(a.delta_absolute))
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
      key: 'publisher_name',
      header: 'Publisher',
      sortable: true,
      render: (row) => (
        <span className={top3Ids.has(row.publisher_id) ? 'font-semibold text-slate-900' : ''}>
          {row.publisher_name}
        </span>
      ),
    },
    {
      key: 'current_revenue',
      header: 'Current (EUR)',
      sortable: true,
      className: 'text-right',
      render: (row) => (
        <span className="tabular-nums">{formatCurrency(row.current_revenue)}</span>
      ),
    },
    {
      key: 'baseline_revenue',
      header: 'Baseline (EUR)',
      sortable: true,
      className: 'text-right',
      render: (row) => (
        <span className="tabular-nums text-slate-400">{formatCurrency(row.baseline_revenue)}</span>
      ),
    },
    {
      key: 'delta_absolute',
      header: 'Delta (EUR)',
      sortable: true,
      className: 'text-right',
      render: (row) => (
        <span
          className={`tabular-nums font-medium ${row.delta_absolute < 0 ? 'text-red-600' : 'text-green-600'}`}
        >
          {formatCurrency(row.delta_absolute)}
        </span>
      ),
    },
    {
      key: 'delta_percent',
      header: 'Delta %',
      sortable: true,
      className: 'text-right',
      render: (row) => <DeltaIndicator value={row.delta_percent} />,
    },
    {
      key: 'quota_of_drop',
      header: 'Quota Drop',
      sortable: true,
      className: 'text-right',
      render: (row) => (
        <div className="flex items-center justify-end gap-2">
          <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full rounded-full bg-red-400"
              style={{ width: `${Math.min(row.quota_of_drop * 100, 100)}%` }}
            />
          </div>
          <span className="w-12 text-right tabular-nums text-xs">
            {(row.quota_of_drop * 100).toFixed(1)}%
          </span>
        </div>
      ),
    },
  ]

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Users size={18} className="text-blue-500" />
            Step 3: Top Contributors
          </CardTitle>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-500">Concentration (Top 3):</span>
            <span
              className={`font-semibold ${concentrationIndex > 0.6 ? 'text-red-600' : 'text-amber-600'}`}
            >
              {(concentrationIndex * 100).toFixed(1)}%
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
