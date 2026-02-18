import { Globe } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { DataTable, type Column } from '../ui/DataTable'
import { DeltaIndicator } from '../ui/DeltaIndicator'
import { GeoBreakdownPieChart } from '../charts/GeoBreakdownPieChart'
import { formatCurrency } from '../../lib/utils'
import type { GeoBreakdown } from '../../types/alert'

interface GeoBreakdownSectionProps {
  geoBreakdown: GeoBreakdown[]
}

export function GeoBreakdownSection({ geoBreakdown }: GeoBreakdownSectionProps) {
  const safeGeoBreakdown = geoBreakdown ?? []

  const columns: Column<GeoBreakdown>[] = [
    {
      key: 'geo_cluster',
      header: 'Geo',
      render: (row) => (
        <span className="font-semibold text-gray-900">{row.geo_cluster}</span>
      ),
    },
    {
      key: 'current_revenue',
      header: 'Current',
      className: 'text-right',
      render: (row) => <span className="font-mono">{formatCurrency(row.current_revenue)}</span>,
    },
    {
      key: 'baseline_revenue',
      header: 'Baseline',
      className: 'text-right',
      render: (row) => (
        <span className="font-mono text-gray-500">{formatCurrency(row.baseline_revenue)}</span>
      ),
    },
    {
      key: 'delta_absolute',
      header: 'Delta',
      className: 'text-right',
      render: (row) => (
        <span
          className={`font-mono font-medium ${row.delta_absolute < 0 ? 'text-red-600' : 'text-green-600'}`}
        >
          {formatCurrency(row.delta_absolute)}
        </span>
      ),
    },
    {
      key: 'delta_percent',
      header: 'Delta %',
      className: 'text-right',
      render: (row) => <DeltaIndicator value={row.delta_percent} />,
    },
    {
      key: 'contribution',
      header: 'Contribution',
      className: 'text-right',
      render: (row) => (
        <span className="font-mono text-xs">{(row.contribution * 100).toFixed(0)}%</span>
      ),
    },
  ]

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
              keyExtractor={(row) => row.geo_cluster}
            />
          </div>
          <div className="flex items-center justify-center">
            <GeoBreakdownPieChart data={safeGeoBreakdown} />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
