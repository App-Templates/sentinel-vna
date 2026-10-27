// Phase 12 — EN-only constants module (UI-SPEC §"i18n decision" line 65-66).
// Single source of truth for copy strings. Intentionally NOT a full i18n
// provider — Phase 14 (CORR-06) may swap this module for `react-i18next` /
// `next-intl` without touching component JSX.

/**
 * KpiCards labels (CORR-09). Imported by
 * frontend/src/components/dashboard/KpiCards.tsx.
 */
export const KPI_LABELS = {
  rpm: 'RPM',
  ctr: 'CTR',
  viewability: 'Viewability',
  grossMargin: 'Gross Margin',
} as const;

/**
 * Sell-type dropdown labels for PublishersPage filter
 * (UI-SPEC §"Sell Type Filter UI" line 188-194). The 5 canonical sell_types
 * mirror backend/api/publisher_routes.py VALID_SELL_TYPES tuple verbatim.
 * Key 'all' maps to `sellType=undefined` in the hook (no query param sent).
 */
export const SELL_TYPE_LABELS = {
  all: 'All sell types',
  Open_Market: 'Open Market',
  Header_Bidding: 'Header Bidding',
  Direct: 'Direct',
  Deal: 'Deal',
  Other: 'Other',
} as const;

export type SellTypeKey = keyof typeof SELL_TYPE_LABELS;

/**
 * TriageSection baseline-missing disclosure (UI-SPEC §"Color" line 138 +
 * §"Copywriting Contract" line 220).
 */
export const BASELINE_MISSING_COPY =
  'Baseline unavailable for this alert (no environment split data).';

/**
 * PublishersPage empty-with-filter copy (UI-SPEC §"Copywriting Contract" line
 * 216, §"States Inventory" line 258). Caller substitutes {label} and {year}
 * with the active sell_type label and the active year.
 */
export function emptyPublishersFiltered(label: string, year: number): string {
  return `No publishers match ${label} for ${year}.`;
}

/**
 * RevenueStatus24h + RevenueByChannel + RevenueTrendChart labels (Phase 13
 * — dashboard date navigation, WIP-05 Commit D). Replaces t('revenue.*')
 * calls from WIP `94a48cd`. Imported by
 * frontend/src/components/dashboard/RevenueStatus24h.tsx,
 * frontend/src/components/dashboard/RevenueByChannel.tsx,
 * frontend/src/components/charts/RevenueTrendChart.tsx.
 * UI-SPEC §"i18n-keys.ts Extension" lines 331-339.
 */
export const REVENUE_LABELS = {
  status24h: 'Revenue Status 24h',
  revenue: 'Revenue',
  baseline7w: 'Baseline 7w',
  yoy7w: 'YoY 7w',
  deltaVs7w: 'Delta vs 7w',
  hour: 'Hour',
  noData: 'No revenue data available.',
} as const;

/**
 * KpiCards empty state copy (Phase 13 — lifted-prop pattern per UI-SPEC
 * §"Component Inventory" line 163, §"States Inventory" line 412).
 * Imported by frontend/src/components/dashboard/KpiCards.tsx.
 */
export const KPI_NO_DATA_COPY = 'No KPI data available.';

/**
 * Phase 14 — UI Labeling + Filter Exposure (CORR-02..06, CORR-11).
 * Closes RC-(a) Top-N disclaimer, RC-(c) gross/net toggle, RC-(f) reference period.
 * UI-SPEC §"i18n-keys.ts Extension" lines 547-664.
 */

/**
 * Reference period footnote (CORR-02 + CORR-05). RC-(f) closure.
 * Format produced by `formatTimestampUtc(iso)` in `lib/utils.ts`.
 */
export const REFERENCE_PERIOD_COPY = {
  cardPrefix: 'as of ',
  cardSuffix: ', EUR',
  alertPrefix: 'for ',
  alertSuffix: '',
} as const;

/**
 * Channel scope badge (CORR-04). RC-(a) partial closure.
 * Composed as `${channel}${suffix}` → "GOOGLE_ADEX only".
 */
export const SCOPE_BADGE_COPY = {
  suffix: ' only',
  inlinePrefix: 'Scope: ',
} as const;

/**
 * Gross / Net revenue display toggle (CORR-03). RC-(c) closure.
 * `factor` is the rev-share constant — single source of truth.
 */
export const GROSS_NET_LABELS = {
  gross: 'Gross',
  net: 'Net (post rev-share 60%)',
  grossSuffix: '(gross)',
  netSuffix: '(net)',
} as const;

export const REV_SHARE_FACTOR = 0.6;

/**
 * Top-N publishers disclaimer (CORR-04). RC-(a) full closure.
 * Rendered on PublishersPage under the page title.
 *
 * Phase 17.2 HOTFIX-03 + HOTFIX-06 (V5 + D1 Marco 2026-05-19): linkHref
 * renamed to linkBase to communicate that the runtime href is composed
 * from `linkBase` + the active PublishersPage filter URLSearchParams.
 * Backend endpoint contract is unchanged; un-recognized query params
 * are ignored server-side (FastAPI default).
 */
export const TOP_N_DISCLAIMER_COPY = {
  prefix: 'Showing top ',
  suffix: ' publishers — does not represent the full network.',
  linkLabel: 'Network totals',
  linkBase: '/api/metrics/network-totals',
} as const;

/**
 * Month filter labels (CORR-11). 'all' is the default sentinel.
 */
export const MONTH_LABELS = {
  all: 'All months',
  '01': 'January',
  '02': 'February',
  '03': 'March',
  '04': 'April',
  '05': 'May',
  '06': 'June',
  '07': 'July',
  '08': 'August',
  '09': 'September',
  '10': 'October',
  '11': 'November',
  '12': 'December',
} as const;

/**
 * Geo cluster filter labels (CORR-11). Mirrors backend GeoCluster type
 * from frontend/src/types/alert.ts.
 */
export const GEO_LABELS = {
  all: 'All countries',
  ITA: 'Italy',
  ES: 'Spain',
  LATAM: 'LATAM',
  PT: 'Portugal',
  OTHER: 'Other',
} as const;

/**
 * Publisher tier filter labels (CORR-11).
 * Tier derivation is CLIENT-SIDE for Phase 14; backend compute deferred to v1.4
 * Phase 18 INTEL-04. See PublishersPage.tsx `computePublisherTier`.
 */
export const PUBLISHER_TIER_LABELS = {
  all: 'All tiers',
  A: 'Tier A',
  B: 'Tier B',
  C: 'Tier C',
} as const;

/**
 * Environment filter labels (CORR-11, W-1 iter-1).
 * Mirrors the Environment union from frontend/src/types/alert.ts line 6:
 *   export type Environment = 'WEB' | 'AMP' | 'APP' | 'UNKNOWN'
 * The /api/publishers/top endpoint does NOT currently expose an environment
 * field on PublisherSummary; this filter ships as a no-op predicate per the
 * same posture as the month filter (D-14.05-G + D-14.05-X). When the backend
 * extends, the predicate becomes effective with zero UI changes.
 */
export const ENVIRONMENT_LABELS = {
  all: 'All environments',
  WEB: 'Web',
  AMP: 'AMP',
  APP: 'App',
  UNKNOWN: 'Unknown',
} as const;

/**
 * Multi-filter empty-state copy (extends Phase 12 emptyPublishersFiltered).
 * Caller passes the array of active filter labels (e.g. ['Open Market', 'Italy']).
 */
export function emptyPublishersMultiFiltered(
  activeFilters: string[],
  year: number,
): string {
  if (activeFilters.length === 0) {
    return `No publisher data available for ${year}.`;
  }
  return `No publishers match ${activeFilters.join(', ')} for ${year}.`;
}

/**
 * Phase 15 — UI Resilience (CORR-07 diagnostic empty states + CORR-10 error boundary).
 * Chart-area empty-state copy. Sourced from REQUIREMENTS.md CORR-07 verbatim.
 * Parallel structure: "No [data]. Alert < 7 days old or data not yet aggregated."
 */
export const CHART_EMPTY_COPY = {
  revenueTrend: 'No 7-week history. Alert < 7 days old or data not yet aggregated.',
  environmentBar: 'No environment split data. Alert < 7 days old or data not yet aggregated.',
  geoBreakdown: 'No geo breakdown data. Alert < 7 days old or data not yet aggregated.',
} as const;

/**
 * Phase 15 — ChartErrorBoundary fallback message (CORR-10).
 * Used when a chart component throws during render.
 * Distinct from empty-state (empty = no data; error = render failure).
 */
export const CHART_ERROR_COPY = {
  generic: 'Chart unavailable. Reload the page if this persists.',
} as const;
