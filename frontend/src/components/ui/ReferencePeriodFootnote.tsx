import { formatTimestampUtc } from '../../lib/utils'
import { REFERENCE_PERIOD_COPY } from '../../lib/i18n-keys'

export interface ReferencePeriodFootnoteProps {
  timestamp: string
  variant?: 'card' | 'inline'
  withCurrency?: boolean
  className?: string
}

/**
 * Reference period disclosure (CORR-02 + CORR-05 / RC-(f) closure).
 *
 * card variant   → "as of 13 Jan 2026 08:57 UTC, EUR"  (block <p>, mt-2)
 * inline variant → "for 13 Jan 2026 08:57 UTC"         (inline <span>)
 *
 * The `formatTimestampUtc` helper already appends ' UTC' — so
 * REFERENCE_PERIOD_COPY.alertSuffix is the empty string '' by convention
 * (Plan 14-01 W-2 fix). The inline variant could safely concatenate
 * `{...alertPrefix}{formatted}{...alertSuffix}` with no double-UTC; we
 * elide the suffix from the JSX for minimal-noise rendering. The constant
 * stays exported as '' for forward-compat with a future non-UTC formatter
 * (flip in one place, consumers stay byte-identical).
 *
 * Anti-creep: ALL `as of ` and `for ` strings live ONLY here. UI-SPEC AC
 * #5 verifier greps `"as of` outside this file → must return ZERO.
 *
 * UI-SPEC §"CORR-02 + CORR-05" lines 261-326.
 */
export function ReferencePeriodFootnote({
  timestamp,
  variant = 'card',
  withCurrency = true,
  className,
}: ReferencePeriodFootnoteProps) {
  const formatted = formatTimestampUtc(timestamp)

  if (variant === 'inline') {
    return (
      <span className={`text-xs text-gray-500 ${className ?? ''}`.trim()}>
        {REFERENCE_PERIOD_COPY.alertPrefix}
        {formatted}
      </span>
    )
  }

  return (
    <p className={`text-xs text-gray-500 mt-2 ${className ?? ''}`.trim()}>
      {REFERENCE_PERIOD_COPY.cardPrefix}
      {formatted}
      {withCurrency ? REFERENCE_PERIOD_COPY.cardSuffix : ''}
    </p>
  )
}
