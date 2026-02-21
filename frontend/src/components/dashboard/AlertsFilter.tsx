import { Button } from '../ui/Button'
import { X } from 'lucide-react'
import type { Severity, AlertStatus, ChannelGroup } from '../../types/alert'

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

const selectClass =
  'rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500'

const dateInputClass =
  'rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500'

const severities: Severity[] = ['P0', 'P1', 'P2']
const statuses: AlertStatus[] = ['OPEN', 'ACK', 'RESOLVED', 'SNOOZED']
const channels: ChannelGroup[] = ['GOOGLE', 'OPEN_BIDDING']

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
    <div className="flex flex-wrap items-center gap-3">
      <select
        value={severity}
        onChange={(e) => onSeverityChange(e.target.value)}
        className={selectClass}
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
        className={selectClass}
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
        className={selectClass}
      >
        <option value="">All Channels</option>
        {channels.map((c) => (
          <option key={c} value={c}>
            {c === 'OPEN_BIDDING' ? 'Open Bidding' : 'Google'}
          </option>
        ))}
      </select>

      <select
        value={assignedTo}
        onChange={(e) => onAssignedToChange(e.target.value)}
        className={selectClass}
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
        <label className="text-xs text-gray-500">From:</label>
        <input
          type="date"
          value={fromDate}
          onChange={(e) => onFromDateChange(e.target.value)}
          className={dateInputClass}
        />
      </div>

      <div className="flex items-center gap-1.5">
        <label className="text-xs text-gray-500">To:</label>
        <input
          type="date"
          value={toDate}
          onChange={(e) => onToDateChange(e.target.value)}
          className={dateInputClass}
        />
      </div>

      {hasActiveFilters && (
        <Button variant="ghost" size="sm" onClick={onClear}>
          <X size={14} />
          Clear
        </Button>
      )}
    </div>
  )
}
