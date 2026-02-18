import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarChart3 } from 'lucide-react'
import { useTopPublishers } from '../api/client'
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card'
import { DataTable, type Column } from '../components/ui/DataTable'
import { Skeleton, CardSkeleton, TableSkeleton } from '../components/ui/Skeleton'
import { formatCurrency } from '../lib/utils'
import type { PublisherSummary } from '../types/publisher'

function formatBacino(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`
  return String(value)
}

export function PublishersPage() {
  const [year, setYear] = useState(2025)
  const navigate = useNavigate()
  const { data: publishers, isLoading, error } = useTopPublishers(year)

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

  const data = publishers ?? []

  const totalRevenue = data.reduce((sum, p) => sum + p.total_revenue, 0)
  const totalBacino = data.reduce((sum, p) => sum + p.total_bacino, 0)
  const totalImpressions = data.reduce((sum, p) => sum + p.total_impressions, 0)
  const weightedEcpm = totalImpressions > 0 ? (totalRevenue / totalImpressions) * 1000 : 0
  const avgCoverage = data.length > 0 ? data.reduce((sum, p) => sum + p.avg_coverage, 0) / data.length : 0

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
        <span className="font-mono">{formatCurrency(row.total_revenue)}</span>
      ),
    },
    {
      key: 'total_bacino',
      header: 'Bacino',
      sortable: true,
      className: 'text-right',
      headerTitle: 'Totale ad requests (bacino pubblicitario)',
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
      headerTitle: 'Revenue Per Mille: ricavo per 1000 ad requests (bacino)',
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
      headerTitle: 'Impressions / Bacino: quota di ad requests effettivamente riempite',
      render: (row) => (
        <span className="font-mono text-xs">{(row.fill_rate * 100).toFixed(1)}%</span>
      ),
    },
    {
      key: 'google_pct',
      header: 'Google %',
      sortable: true,
      className: 'text-right',
      headerTitle: '% revenue dal canale Google (vs Open Bidding)',
      render: (row) => (
        <span className="font-mono text-xs">{row.google_pct.toFixed(1)}%</span>
      ),
    },
    {
      key: 'trend_4w',
      header: 'Trend 4w',
      sortable: true,
      className: 'text-right',
      headerTitle: 'Variazione revenue ultime 4 settimane vs 4 settimane precedenti',
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

      {/* Stats Row */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-5">
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-gray-500">Total Revenue</p>
            <p className="text-2xl font-bold text-gray-900">{formatCurrency(totalRevenue)}</p>
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
            <p className="text-xs text-gray-400">{data[0] ? formatCurrency(data[0].total_revenue) : ''}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <p className="text-sm text-gray-500">Avg Coverage</p>
            <p className="text-2xl font-bold text-gray-900">{(avgCoverage * 100).toFixed(1)}%</p>
            <p className="text-xs text-gray-400">Fill rate</p>
          </CardContent>
        </Card>
      </div>

      {/* Publishers Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Top {data.length} Publishers by Revenue</CardTitle>
            <select
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            >
              <option value={2025}>2025</option>
              <option value={2024}>2024</option>
            </select>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {data.length === 0 ? (
            <div className="py-12 text-center text-gray-500">
              No publisher data available for {year}.
            </div>
          ) : (
            <DataTable
              data={rankedData}
              columns={columns}
              keyExtractor={(row) => row.publisher_id}
              onRowClick={(row) => navigate(`/publishers/${row.publisher_id}`)}
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
