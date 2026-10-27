import { TOP_N_DISCLAIMER_COPY } from '../../lib/i18n-keys'

/**
 * Phase 17.2 HOTFIX-06 (D1 Marco 2026-05-19): filters prop is forwarded
 * into the Network totals link as URLSearchParams. When absent, the link
 * falls back to the bare linkBase (backward compatible with non-Publishers
 * callers, e.g. dashboard widgets that may render this disclaimer with no
 * filter context).
 *
 * Backend /api/metrics/network-totals today accepts only `date` + `channel`
 * (backend/api/routes.py:981); un-recognized query params are ignored
 * server-side (FastAPI default). When backend extends to accept year /
 * month / sell_type / etc., this component requires zero changes.
 */
export interface TopNDisclaimerFilters {
  year?: number | string
  month?: string
  sell_type_proxy?: string
  geo_cluster?: string
  publisher_tier?: string
  environment?: string
}

export interface TopNDisclaimerProps {
  n: number
  className?: string
  filters?: TopNDisclaimerFilters
}

/**
 * Compose the runtime href for the Network totals link from the active
 * PublishersPage filter state. URLSearchParams handles RFC-3986 percent
 * encoding automatically (T-17.2-03-01 mitigation).
 *
 * Skips the 'all' sentinel and undefined/empty values so the URL reflects
 * only filters the operator actively narrowed. When no filters are
 * provided or all are 'all', returns the bare base URL.
 */
function composeNetworkTotalsHref(
  base: string,
  filters?: TopNDisclaimerFilters,
): string {
  if (!filters) return base
  const qs = new URLSearchParams()
  // 'all' is the sentinel used by SELL_TYPE_LABELS / GEO_LABELS /
  // PUBLISHER_TIER_LABELS / ENVIRONMENT_LABELS / MONTH_LABELS for "no filter"
  // (see frontend/src/lib/i18n-keys.ts + useTopPublishersFilters.ts DEFAULTS).
  if (filters.year !== undefined && filters.year !== '') qs.set('year', String(filters.year))
  if (filters.month && filters.month !== 'all') qs.set('month', filters.month)
  if (filters.sell_type_proxy && filters.sell_type_proxy !== 'all') qs.set('sell_type', filters.sell_type_proxy)
  if (filters.geo_cluster && filters.geo_cluster !== 'all') qs.set('country', filters.geo_cluster)
  if (filters.publisher_tier && filters.publisher_tier !== 'all') qs.set('tier', filters.publisher_tier)
  if (filters.environment && filters.environment !== 'all') qs.set('environment', filters.environment)
  const q = qs.toString()
  return q ? `${base}?${q}` : base
}

/**
 * Top-N publishers disclaimer (CORR-04 / RC-(a) full closure).
 *
 * Renders the locked disclaimer composed from TOP_N_DISCLAIMER_COPY:
 *   {prefix}{N}{suffix} + link to {linkBase}?{filter-qs} labeled {linkLabel}
 * (Phase 11 /api/metrics/network-totals endpoint)
 *
 * Closes email-Vito #1, #2, #3 (Mondadori bacino 366M PBI vs 133M
 * Sentinel — operators conflated top-50 subset with all-publishers
 * total). The disclaimer makes the scope explicit AND surfaces the
 * network-totals API as the source of truth for full-network numbers.
 *
 * Phase 17.2 HOTFIX-03 (V5 Marco 2026-05-19): elevated from a
 * near-invisible light-gray footnote to a body-weight, left-bordered
 * amber callout. Operators scanning the page now see the scope note
 * immediately — Marco's screenshot showed the disclaimer being missed
 * entirely (confused Top 35 vs Top 50 across two emails).
 *
 * Phase 17.2 HOTFIX-06 (D1 Marco 2026-05-19): the "Network totals" link
 * now honors the active PublishersPage filter context — clicking with
 * (year=2026, month=03, sell_type=Direct) on the page produces a href
 * of /api/metrics/network-totals?year=2026&month=03&sell_type=Direct
 * instead of the bare endpoint that always returned the same default row.
 *
 * UI-SPEC §"Component Inventory" line 189; Copywriting line 677; AC #12-14.
 */
export function TopNDisclaimer({ n, className, filters }: TopNDisclaimerProps) {
  const href = composeNetworkTotalsHref(TOP_N_DISCLAIMER_COPY.linkBase, filters)
  return (
    <div
      className={`mt-2 mb-3 rounded-md border-l-4 border-amber-400 bg-amber-50 px-3 py-2 text-sm text-gray-800 ${className ?? ''}`.trim()}
      role="note"
    >
      <span className="font-semibold">{TOP_N_DISCLAIMER_COPY.prefix}{n}</span>
      {TOP_N_DISCLAIMER_COPY.suffix}
      {' '}
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-blue-700 underline hover:text-blue-900"
      >
        {TOP_N_DISCLAIMER_COPY.linkLabel}
      </a>
    </div>
  )
}
