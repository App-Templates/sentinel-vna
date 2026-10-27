import { Badge } from './Badge'
import { SCOPE_BADGE_COPY } from '../../lib/i18n-keys'
import type { ChannelGroup } from '../../types/alert'

export interface ScopeBadgeProps {
  channel: ChannelGroup
  variant?: 'badge' | 'inline'
  className?: string
}

/**
 * Channel scope disclosure (CORR-04 / RC-(a) closure).
 *
 * Renders `<channel> only` to disclose that the
 * surrounding card/section's data is single-channel-scoped. Closes the
 * email-Vito #2-3 confusion where dashboard cards aggregating GOOGLE_ADEX
 * data were compared to PBI all-channels totals.
 *
 * Composition: `${channel}${SCOPE_BADGE_COPY.suffix}` — never inline.
 *
 * Variant 'badge' (default): renders via existing Badge primitive with
 * channel-specific palette (Badge.tsx variants line 26-33).
 * Variant 'inline': renders a low-emphasis `<span>` for inline placement.
 *
 * Anti-pattern: do NOT render ScopeBadge on multi-channel aggregates
 * (e.g. PublishersPage Total Revenue card). Use TopNDisclaimer there.
 *
 * UI-SPEC §"CORR-04 — Channel Scope Badge" lines 414-470.
 */
export function ScopeBadge({
  channel,
  variant = 'badge',
  className,
}: ScopeBadgeProps) {
  if (variant === 'inline') {
    return (
      <span className={`text-xs font-medium text-gray-500 ${className ?? ''}`.trim()}>
        {SCOPE_BADGE_COPY.inlinePrefix}
        {channel}
        {SCOPE_BADGE_COPY.suffix}
      </span>
    )
  }
  return (
    <Badge variant={channel} className={className}>
      {channel}
      {SCOPE_BADGE_COPY.suffix}
    </Badge>
  )
}
