import { Button } from '../ui/Button'
import { X } from 'lucide-react'
import type { Severity, AlertStatus, ChannelGroup } from '../../types/alert'
import { CHANNEL_LABELS } from '../../lib/channels'

interface AlertsFilterProps {
  severity: string
  status: string
  channelGroup: string
  fromDate: string
  toDate: string
  assignedTo: string
  onSeverityChange: (value: string) => void
  onStatusChange: (value: string) => void
  onChannelGroupChange: (value: string) => void
  onFromDateChange: (value: string) => void
  onToDateChange: (value: string) => void
  onAssignedToChange: (value: string) => void
  onClear: () => void
  hasActiveFilters: boolean
}

// Unified form element class — used across all filters and forms
export const formInputClass =
  'cursor-pointer rounded-md border border-gray-200 bg-gray-50 px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm transition-colors hover:bg-gray-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500'

const severities: Severity[] = ['P0', 'P1', 'P2']
const statuses: AlertStatus[] = ['OPEN', 'ACK', 'RESOLVED', 'SNOOZED']
const channels: ChannelGroup[] = [
  'GOOGLE',
  'OPEN_BIDDING',
  'GOOGLE_ADEX',
  'HEADER_BIDDING_MAGNITE',
  'HEADER_BIDDING_PUBMATIC',
  'TAM',
  'DIRECT',
  'DEAL',
]

const TEAM_EMAILS = [
  'vito.sena@adkaora.com',
  'ops1@adkaora.com',
  'ops2@adkaora.com',
  'dev-user@adkaora.com',
]

export function AlertsFilter({
  severity,
  status,
  channelGroup,
  fromDate,
  toDate,
  assignedTo,
  onSeverityChange,
  onStatusChange,
  onChannelGroupChange,
  onFromDateChange,
  onToDateChange,
  onAssignedToChange,
  onClear,
  hasActiveFilters,
}: AlertsFilterProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <select
        value={severity}
        onChange={(e) => onSeverityChange(e.target.value)}
        className={formInputClass}
      >
        <option value="">All Severities</option>
        {severities.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>

      <select
        value={status}
        onChange={(e) => onStatusChange(e.target.value)}
        className={formInputClass}
      >
        <option value="">All Statuses</option>
        {statuses.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>

      <select
        value={channelGroup}
        onChange={(e) => onChannelGroupChange(e.target.value)}
        className={formInputClass}
      >
        <option value="">All Channels</option>
        {channels.map((c) => (
          <option key={c} value={c}>
            {CHANNEL_LABELS[c] ?? c}
          </option>
        ))}
      </select>

      <select
        value={assignedTo}
        onChange={(e) => onAssignedToChange(e.target.value)}
        className={formInputClass}
      >
        <option value="">All Assignments</option>
        <option value="ME">Assigned to Me</option>
        <option value="UNASSIGNED">Unassigned</option>
        {TEAM_EMAILS.map((email) => (
          <option key={email} value={email}>
            {email}
          </option>
        ))}
      </select>

      <div className="flex items-center gap-1.5">
        <label className="text-xs text-slate-500">From:</label>
        <input
          type="date"
          value={fromDate}
          onChange={(e) => onFromDateChange(e.target.value)}
          className={formInputClass}
        />
      </div>

      <div className="flex items-center gap-1.5">
        <label className="text-xs text-slate-500">To:</label>
        <input
          type="date"
          value={toDate}
          onChange={(e) => onToDateChange(e.target.value)}
          className={formInputClass}
        />
      </div>

      {hasActiveFilters && (
        <Button variant="ghost" size="sm" onClick={onClear}>
          <X size={13} />
          Clear filters
        </Button>
      )}
    </div>
  )
}
