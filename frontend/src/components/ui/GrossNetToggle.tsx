import { cn } from '../../lib/utils'
import { GROSS_NET_LABELS } from '../../lib/i18n-keys'

export type GrossNetMode = 'gross' | 'net'

export interface GrossNetToggleProps {
  value: GrossNetMode
  onChange: (mode: GrossNetMode) => void
  className?: string
}

/**
 * Gross / Net revenue display toggle (CORR-03 / RC-(c) closure).
 *
 * Segmented control with two options:
 *  - 'gross' (default, PBI-aligned per Decision D2)
 *  - 'net'   (post rev-share 60% — explicit label closes email-Vito #4e
 *            confusion: €115k Sentinel = €188k PBI × 0.6)
 *
 * Controlled component — emits onChange. The math (multiplying revenue
 * by REV_SHARE_FACTOR) is the consumer's responsibility.
 *
 * UI-SPEC §"CORR-03 — Gross / Net Toggle" lines 330-411.
 */
export function GrossNetToggle({
  value,
  onChange,
  className,
}: GrossNetToggleProps) {
  return (
    <div
      role="group"
      aria-label="Revenue display mode"
      className={cn(
        'inline-flex rounded-md border border-gray-200 bg-gray-50 p-0.5',
        className,
      )}
    >
      <button
        type="button"
        aria-pressed={value === 'gross'}
        onClick={() => onChange('gross')}
        className={cn(
          'rounded-sm px-3 py-1 text-xs font-medium transition-colors',
          value === 'gross'
            ? 'bg-gray-900 text-white'
            : 'text-gray-600 hover:bg-gray-100',
        )}
      >
        {GROSS_NET_LABELS.gross}
      </button>
      <button
        type="button"
        aria-pressed={value === 'net'}
        onClick={() => onChange('net')}
        className={cn(
          'rounded-sm px-3 py-1 text-xs font-medium transition-colors',
          value === 'net'
            ? 'bg-gray-900 text-white'
            : 'text-gray-600 hover:bg-gray-100',
        )}
      >
        {GROSS_NET_LABELS.net}
      </button>
    </div>
  )
}
