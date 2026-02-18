import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { DataTable, type Column } from '../ui/DataTable'
import { SeverityBadge, StatusBadge, TriageBadge, ChannelBadge } from '../ui/Badge'
import { DeltaIndicator } from '../ui/DeltaIndicator'
import { Button } from '../ui/Button'
import { TableSkeleton } from '../ui/Skeleton'
import { formatTimestamp } from '../../lib/utils'
import type { AlertSummary } from '../../types/alert'

interface AlertsTableProps {
  data: AlertSummary[] | undefined
  isLoading: boolean
  error: Error | null
  pageSize?: number
}

export function AlertsTable({ data, isLoading, error, pageSize = 10 }: AlertsTableProps) {
  const navigate = useNavigate()
  const [page, setPage] = useState(0)

  const columns: Column<AlertSummary>[] = [
    {
      key: 'alert_id',
      header: 'Alert ID',
      render: (row) => (
        <button
          className="font-mono text-xs text-blue-600 hover:underline"
          onClick={(e) => {
            e.stopPropagation()
            navigate(`/alerts/${row.alert_id}`)
          }}
        >
          {row.alert_id.slice(0, 8)}
        </button>
      ),
    },
    {
      key: 'timestamp',
      header: 'Timestamp',
      sortable: true,
      render: (row) => (
        <span className="text-xs text-gray-500">{formatTimestamp(row.timestamp)}</span>
      ),
    },
    {
      key: 'severity',
      header: 'Severity',
      sortable: true,
      render: (row) => <SeverityBadge severity={row.severity} />,
    },
    {
      key: 'channel_group',
      header: 'Channel',
      render: (row) => <ChannelBadge channel={row.channel_group} />,
    },
    {
      key: 'triage_label',
      header: 'Triage',
      render: (row) => <TriageBadge triage={row.triage_label} />,
    },
    {
      key: 'revenue_delta_pct',
      header: 'Revenue Drop',
      sortable: true,
      render: (row) => <DeltaIndicator value={row.revenue_delta_pct} />,
    },
    {
      key: 'status',
      header: 'Status',
      sortable: true,
      render: (row) => <StatusBadge status={row.status} />,
    },
  ]

  if (isLoading) {
    return <TableSkeleton rows={pageSize} columns={7} />
  }

  if (error) {
    return (
      <div className="py-12 text-center text-red-500">
        Failed to load alerts. Please try again.
      </div>
    )
  }

  const allData = data ?? []
  const totalPages = Math.max(1, Math.ceil(allData.length / pageSize))
  const pagedData = allData.slice(page * pageSize, (page + 1) * pageSize)

  return (
    <div>
      <DataTable
        data={pagedData}
        columns={columns}
        keyExtractor={(row) => row.alert_id}
        onRowClick={(row) => navigate(`/alerts/${row.alert_id}`)}
        emptyMessage="No alerts match the current filters."
      />

      {allData.length > pageSize && (
        <div className="flex items-center justify-between border-t border-gray-200 px-4 py-3">
          <span className="text-xs text-gray-500">
            Showing {page * pageSize + 1}-{Math.min((page + 1) * pageSize, allData.length)} of{' '}
            {allData.length}
          </span>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
            >
              <ChevronLeft size={14} />
              Previous
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
            >
              Next
              <ChevronRight size={14} />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
