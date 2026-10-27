import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FlaskConical, Play, Loader2 } from 'lucide-react'
import { useBacktestResults, useRunBacktest } from '../api/client'
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { DataTable, type Column } from '../components/ui/DataTable'
import { SeverityBadge, StatusBadge, TriageBadge } from '../components/ui/Badge'
import { DeltaIndicator } from '../components/ui/DeltaIndicator'
import { TableSkeleton } from '../components/ui/Skeleton'
import { formatTimestamp } from '../lib/utils'
import type { AlertSummary, BacktestResult } from '../types/alert'

function getDefaultDates() {
  // Default to the last week of available data (parquet data ends ~Jan 20, 2026)
  const end = new Date('2026-01-20')
  const start = new Date('2026-01-13')
  return {
    start: start.toISOString().split('T')[0],
    end: end.toISOString().split('T')[0],
  }
}

export function BacktestPage() {
  const navigate = useNavigate()
  const defaults = getDefaultDates()
  const [startDate, setStartDate] = useState(defaults.start)
  const [endDate, setEndDate] = useState(defaults.end)
  const [stepHours, setStepHours] = useState(2)

  const { data: backtestResults, isLoading } = useBacktestResults()
  const runMutation = useRunBacktest()

  const handleRunBacktest = () => {
    runMutation.mutate({
      start_date: startDate,
      end_date: endDate,
      step_hours: stepHours,
    })
  }

  const alertColumns: Column<AlertSummary>[] = [
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
      render: (row) => <SeverityBadge severity={row.severity} />,
    },
    {
      key: 'triage_label',
      header: 'Triage',
      render: (row) => <TriageBadge triage={row.triage_label} />,
    },
    {
      key: 'revenue_delta_pct',
      header: 'Delta',
      sortable: true,
      render: (row) => <DeltaIndicator value={row.revenue_delta_pct} />,
    },
    {
      key: 'status',
      header: 'Status',
      render: (row) => <StatusBadge status={row.status} />,
    },
  ]

  const inputClass =
    'rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500'

  return (
    <div className="space-y-6">
      {/* Backtest Form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FlaskConical size={20} />
            Run Backtest
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Start Date</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className={inputClass}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">End Date</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className={inputClass}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">
                Step (hours)
              </label>
              <select
                value={stepHours}
                onChange={(e) => setStepHours(Number(e.target.value))}
                className={inputClass}
              >
                <option value={2}>2 hours (A1+A3)</option>
                <option value={6}>6 hours (A2 drift)</option>
                <option value={1}>1 hour</option>
                <option value={12}>12 hours</option>
                <option value={24}>24 hours</option>
              </select>
            </div>
            <Button
              variant="primary"
              onClick={handleRunBacktest}
              disabled={runMutation.isPending}
            >
              {runMutation.isPending ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Play size={16} />
              )}
              {runMutation.isPending ? 'Running...' : 'Run Backtest'}
            </Button>
          </div>

          {runMutation.isPending && (
            <div className="mt-4 flex items-center gap-2 text-sm text-blue-600">
              <Loader2 size={16} className="animate-spin" />
              Backtest in progress... This may take a few minutes.
            </div>
          )}

          {runMutation.isError && (
            <div className="mt-4 text-sm text-red-500">
              Backtest failed. Using cached results.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Results */}
      <Card>
        <CardHeader>
          <CardTitle>Backtest Results</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <TableSkeleton rows={5} columns={6} />
          ) : !backtestResults || backtestResults.length === 0 ? (
            <div className="py-12 text-center text-gray-500">
              <FlaskConical size={40} className="mx-auto mb-3 text-gray-300" />
              <p>No backtest results yet. Run a backtest to see results.</p>
            </div>
          ) : (
            <div className="space-y-6 p-6">
              {backtestResults.map((bt) => (
                <BacktestResultCard
                  key={bt.backtest_id}
                  result={bt}
                  alertColumns={alertColumns}
                  onRowClick={(row) => navigate(`/alerts/${row.alert_id}`)}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function BacktestResultCard({
  result,
  alertColumns,
  onRowClick,
}: {
  result: BacktestResult
  alertColumns: Column<AlertSummary>[]
  onRowClick: (row: AlertSummary) => void
}) {
  return (
    <div className="rounded-lg border border-gray-200">
      <div className="flex flex-wrap items-center gap-4 border-b border-gray-200 bg-gray-50 px-4 py-3">
        <span className="font-mono text-xs text-gray-500">ID: {result.backtest_id}</span>
        <span className="text-sm text-gray-700">
          {formatTimestamp(result.date_range.start)} - {formatTimestamp(result.date_range.end)}
        </span>
        <span className="text-xs text-gray-500">Step: {result.date_range.step_hours}h</span>
        <span className="text-sm font-medium text-gray-900">
          {result.alerts_generated} alerts / {result.total_checks} checks
        </span>
      </div>
      {result.alerts.length > 0 ? (
        <DataTable
          data={result.alerts}
          columns={alertColumns}
          keyExtractor={(row) => row.alert_id}
          onRowClick={onRowClick}
        />
      ) : (
        <div className="py-6 text-center text-sm text-gray-400">
          No alerts generated in this backtest.
        </div>
      )}
    </div>
  )
}
