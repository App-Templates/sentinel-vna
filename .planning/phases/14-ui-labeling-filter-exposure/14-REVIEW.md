---
phase: 14-ui-labeling-filter-exposure
reviewed: 2026-04-30T21:34:46Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - frontend/src/api/client.ts
  - frontend/src/components/alerts/RevenueStatusSection.tsx
  - frontend/src/components/alerts/TriageSection.tsx
  - frontend/src/components/dashboard/KpiCards.tsx
  - frontend/src/components/dashboard/RevenueByChannel.tsx
  - frontend/src/components/dashboard/RevenueStatus24h.tsx
  - frontend/src/components/ui/GrossNetToggle.tsx
  - frontend/src/components/ui/ReferencePeriodFootnote.tsx
  - frontend/src/components/ui/ScopeBadge.tsx
  - frontend/src/components/ui/TopNDisclaimer.tsx
  - frontend/src/hooks/useTopPublishersFilters.ts
  - frontend/src/lib/i18n-keys.ts
  - frontend/src/lib/utils.ts
  - frontend/src/pages/AlertDetailPage.tsx
  - frontend/src/pages/PublishersPage.tsx
findings:
  critical: 1
  warning: 2
  info: 8
  total: 11
status: issues_found
---

# Phase 14: Code Review Report

**Reviewed:** 2026-04-30T21:34:46Z
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Phase 14 ships UI labeling primitives (`ScopeBadge`, `ReferencePeriodFootnote`, `GrossNetToggle`, `TopNDisclaimer`) plus URL-state filter expansion on PublishersPage, closing RC-(a)/(c)/(f) from Email Vito 2026-04-22. Anti-creep contracts are clean: `REV_SHARE_FACTOR=0.6` is the SOLE live `0.6` literal in the frontend (every other hit is mock data, an unrelated threshold, a docstring, or documentation). The `as of `/`for ` strings are confined to `ReferencePeriodFootnote` + the `i18n-keys` SSoT. Component decomposition, prop threading (B-1 `grossNetMode` lifted to `AlertDetailPage`), and whitelist-validated URL params are correctly implemented.

**One Critical bug** must block merge: `PublishersPage` calls `useMemo` AFTER conditional early-returns, violating React's Rules of Hooks. The two `eslint-disable-next-line react-hooks/rules-of-hooks` comments on lines 89 and 99 are masking — not silencing — a real defect that will surface as a runtime hooks-order error the moment `isLoading` or `error` toggles between renders.

Two Warnings address division-by-zero in `TriageSection` baseline math, plus the silent error path in `api/client.ts` that calls `window.location.reload()` on every 401 (loop risk if auth is broken).

Info findings cover code-quality smells (`TEAM_EMAILS` defined inside component body, `weightedEcpm` undoes-the-multiply gymnastics, magic-number tier thresholds, rank-after-filter UX subtlety, `gross_margin_pct` unit ambiguity).

## Critical Issues

### CR-01: Rules of Hooks violation in PublishersPage — `useMemo` called after conditional early returns

**File:** `frontend/src/pages/PublishersPage.tsx:89-108`
**Issue:** Two `useMemo` calls are placed AFTER the `if (isLoading) return ...` (line 55) and `if (error) return ...` (line 76) early-returns. React requires hooks to be called in the same order on every render. When `isLoading` is `true`, only `useTopPublishersFilters`, `useNavigate`, and `useTopPublishers` execute. When `isLoading` flips to `false` on the next render, two additional `useMemo` calls execute — React detects "Rendered more hooks than during the previous render" and throws. The two `// eslint-disable-next-line react-hooks/rules-of-hooks` comments suppress the lint warning but do NOT fix the underlying bug; they only conceal it. This will manifest the moment a query refetches, network reconnects, or a user lands on the page with a cold cache. R-13 architectural quality forbids known-incorrect code paths.

**Fix:** Move the two `useMemo` calls ABOVE the early-returns, then keep the early-returns where they are. Hooks first, conditional rendering after.

```tsx
export function PublishersPage() {
  const { filters, setFilter } = useTopPublishersFilters()
  const navigate = useNavigate()
  const { data: publishers, isLoading, error } = useTopPublishers(
    filters.year,
    35,
    filters.sell_type_proxy,
    filters.month,
  )

  // ALL hooks BEFORE any early return
  const rawData = publishers ?? []
  const tierMap = useMemo(() => computePublisherTier(rawData), [rawData])
  const data = useMemo(() => rawData.filter((p) => {
    if (filters.geo_cluster !== 'all' && p.dominant_geo !== filters.geo_cluster) return false
    if (filters.publisher_tier !== 'all' && tierMap.get(p.publisher_id) !== filters.publisher_tier) return false
    return true
  }), [rawData, tierMap, filters.geo_cluster, filters.publisher_tier])

  // Conditional rendering AFTER all hooks have been called
  if (isLoading) {
    return (/* skeleton */)
  }
  if (error) {
    return (/* error UI */)
  }

  // ... rest of render
}
```

Also DELETE the two `eslint-disable-next-line react-hooks/rules-of-hooks` comments — they were silencing a true positive.

## Warnings

### WR-01: Division-by-zero in TriageSection baseline delta math (NaN/Infinity propagation)

**File:** `frontend/src/components/alerts/TriageSection.tsx:73-90`
**Issue:** The `baselineMissing` guard checks `baselineBacino == null || baselineCoverage == null` (line 51), which catches `null`/`undefined` but NOT zero. When the server returns `baseline_bacino: 0` or `baseline_coverage: 0` (legitimate edge case for a freshly onboarded publisher or a coverage-zero alert A6), lines 76 and 87 compute `(totalBacino - 0) / 0` → `Infinity`, then `.toFixed(1)` returns the string `"Infinity"` rendered raw in the table cell. Same for direction-icon dispatch (`totalBacino > 0` is true, so direction is `up` even though the comparison is logically meaningless). Note A6 alerts (coverage zero) are explicitly handled in the section below — ironic that the metric row above would render `Infinity%`.

**Fix:** Either (a) treat zero as missing for delta math, or (b) compute delta only when divisor is non-zero. Recommended (a) because zero baseline is itself a "no usable baseline" signal:

```tsx
// Replace line 51:
const baselineMissing =
  baselineBacino == null || baselineCoverage == null ||
  baselineBacino === 0 || baselineCoverage === 0
```

If you want to preserve "0 is a valid baseline" semantics, instead guard each delta computation:

```tsx
delta: baselineMissing || (baselineBacino as number) === 0
  ? '—'
  : `${(((totalBacino - (baselineBacino as number)) / (baselineBacino as number)) * 100).toFixed(1)}%`,
```

### WR-02: Silent reload-on-401 in fetchJSON can produce a reload loop

**File:** `frontend/src/api/client.ts:14-17`
**Issue:** Every 401 response triggers `window.location.reload()` synchronously inside the fetch helper, with no debounce or counter. If the auth cookie is genuinely invalid (expired refresh token, server-side session cleared, IDP misconfiguration), the page reloads → `useAuth` fires → backend returns 401 → page reloads again. In a TanStack Query app with `refetchInterval: 30_000` on `useAlerts` and `60_000` on `useHealth`, multiple in-flight requests can simultaneously trigger reload, producing a stuck-loading UX. The `throw new Error('Session expired')` after the reload is unreachable in practice — `window.location.reload()` is async and the throw runs in the same tick, but the reload tears down the JS context immediately after.

**Fix:** Redirect to the auth entrypoint instead of reloading the current URL, or gate reload behind a sessionStorage flag to break loops:

```ts
if (res.status === 401) {
  // Avoid reload-loop: only reload once per session boot
  const reloaded = sessionStorage.getItem('auth_reload_attempted')
  if (!reloaded) {
    sessionStorage.setItem('auth_reload_attempted', '1')
    window.location.href = '/auth/login'
  }
  throw new Error('Session expired')
}
```

(Clear the flag on successful `/auth/me` in `useAuth`.)

## Info

### IN-01: `TEAM_EMAILS` array re-allocated on every AlertDetailPage render

**File:** `frontend/src/pages/AlertDetailPage.tsx:87-92`
**Issue:** `TEAM_EMAILS` is declared inside the component body. A new array reference is created on every render — harmless for the `<select>` mapping (no memoized child), but it's a code-quality smell that signals reviewer "this should be a module-level constant".

**Fix:** Move outside the component:

```tsx
const TEAM_EMAILS = [
  'vito.sena@adkaora.com',
  'ops1@adkaora.com',
  'ops2@adkaora.com',
  'dev-user@adkaora.com',
] as const

export function AlertDetailPage() { /* ... */ }
```

### IN-02: `weightedEcpm` divides-out the just-applied `revenueMultiplier` (fragile coupling)

**File:** `frontend/src/pages/PublishersPage.tsx:117,123`
**Issue:** Line 117 multiplies revenue by `revenueMultiplier`; line 123 divides it back out. The chain `(totalRevenue / revenueMultiplier / totalImpressions) * 1000` is correct only because someone remembered the upstream multiplication. If a future change moves the multiply into a sub-aggregation or skips it, eCPM silently breaks. Better to keep gross and net as separate locals.

**Fix:**

```tsx
const grossTotalRevenue = data.reduce((sum, p) => sum + p.total_revenue, 0)
const totalRevenue = grossTotalRevenue * revenueMultiplier
// ...
const weightedEcpm = totalImpressions > 0
  ? (grossTotalRevenue / totalImpressions) * 1000  // mode-invariant
  : 0
```

### IN-03: Tier thresholds 0.10 / 0.30 are magic numbers

**File:** `frontend/src/pages/PublishersPage.tsx:28-29`
**Issue:** `Math.ceil(sorted.length * 0.10)` and `Math.ceil(sorted.length * 0.30)` are inline. The comment explains "Top 10% = A, next 20% = B" but the constants aren't named. Phase 18 INTEL-04 will replace this with backend tiers; leaving named constants makes the deletion safer.

**Fix:**

```tsx
const TIER_A_THRESHOLD = 0.10  // top 10%
const TIER_B_THRESHOLD = 0.30  // top 30% (next 20%)
const tierA = Math.ceil(sorted.length * TIER_A_THRESHOLD)
const tierB = Math.ceil(sorted.length * TIER_B_THRESHOLD)
```

### IN-04: Rank computed AFTER filtering can confuse operators

**File:** `frontend/src/pages/PublishersPage.tsx:254`
**Issue:** `rankedData = data.map((p, i) => ({ ...p, rank: i + 1 }))` numbers rows starting from 1 in the FILTERED set. A publisher who is overall #25 will appear as "#1" when the user filters to tier C. The disclaimer says "Top N publishers" but the rank suggests "rank within visible result set". Operators reading this with a backend report will mis-correlate. Consider preserving the unfiltered rank, or relabeling the column header from `#` to `Filter Rank` / removing it under filters.

**Fix:** Compute rank from `rawData` then filter:

```tsx
const ranked = rawData.map((p, i) => ({ ...p, rank: i + 1 }))
const rankedData = ranked.filter((p) => /* same predicate */)
```

(Then ranks reflect global revenue order; gaps are visible when filters are active, which is the honest disclosure.)

### IN-05: `gross_margin_pct` unit is undocumented — display may be off by 100x

**File:** `frontend/src/components/dashboard/KpiCards.tsx:69,76,103`
**Issue:** `wMargin += (h.gross_margin_pct ?? 0) * rev` then `grossMargin = wMargin / totalRevenue`. The output is rendered with `format="percent"` (which `MetricCard` presumably formats by appending `%` or by `formatPercent` which adds sign + `%`). If backend returns `gross_margin_pct` as a percentage (e.g., `35` for 35%), the displayed string will be "35.0%" (correct). If backend returns a decimal (`0.35`), the displayed string will be "0.4%" (wrong, off by 100). The hourly type declaration on lines 44-52 doesn't pin the unit. Backend contract should be documented in a comment or asserted.

**Fix:** Add inline comment + a runtime sanity log when in dev, OR multiply by 100 if the contract is decimal:

```tsx
// Backend contract: gross_margin_pct is a percentage (0-100), not a decimal.
// See backend/api/routes.py _compute_revenue_status_24h.
const grossMargin = totalRevenue > 0 ? wMargin / totalRevenue : 0
```

If actually a decimal, change line 76 to `wMargin / totalRevenue * 100`.

### IN-06: YoY hour alignment by index assumes both arrays are 24-long

**File:** `frontend/src/components/dashboard/RevenueStatus24h.tsx:62`
**Issue:** `yoy: yoyHours[i] ?? null` aligns prev-year by array INDEX, not by `hour` field. If `prev_year.hours` has 23 entries (DST?) or comes shifted (timezone bug in backend), the yoy line on the chart will be off by one hour. Cheap fix: align by hour key.

**Fix:**

```tsx
const yoyByHour = new Map(prevYear?.hours?.map((v, i) => [data.hours[i]?.hour ?? i, v]))
// then in chartData:
yoy: yoyByHour.get(h.hour) ?? null,
```

(Or document that backend guarantees 24-length parallel arrays and assert `data.hours.length === yoyHours.length`.)

### IN-07: `hasActiveFilters` returns true when only `?year=2025` (the default) is in URL

**File:** `frontend/src/hooks/useTopPublishersFilters.ts:165-173`
**Issue:** `hasActiveFilters` returns `searchParams.has('year') || ...`. The hook elsewhere applies "default-omission" — `setFilter` deletes the param when it equals the default (line 142). But if a user manually crafts `/publishers?year=2025`, `hasActiveFilters` reports `true` even though no FILTER differs from defaults. Minor: the value is consumed for "show clear filters" affordance — operator sees a button suggesting active filters when there are none.

**Fix:** Compute `hasActiveFilters` from filter VALUES, not URL keys:

```tsx
const hasActiveFilters =
  filters.year !== DEFAULTS.year ||
  filters.month !== DEFAULTS.month ||
  filters.sell_type_proxy !== DEFAULTS.sell_type_proxy ||
  filters.publisher_tier !== DEFAULTS.publisher_tier ||
  filters.geo_cluster !== DEFAULTS.geo_cluster ||
  filters.environment !== DEFAULTS.environment ||
  filters.gross_net !== DEFAULTS.gross_net
```

### IN-08: Mutating react-query response object in `usePublisherRecurringPatterns`

**File:** `frontend/src/api/client.ts:280-285`
**Issue:** The hook mutates `resp` (the parsed response) in-place to back-fill missing keys (`resp.ecpm_patterns = raw.patterns`). React Query caches the returned object by reference; downstream consumers see the mutated shape, but if a future caller relies on `Object.freeze`-style immutability or a structuralSharing comparator, this will surprise. Cleaner to return a new object.

**Fix:**

```tsx
return {
  ...resp,
  ecpm_patterns: resp.ecpm_patterns ?? (raw.patterns as RecurringPatternsResponse['ecpm_patterns']) ?? [],
  hidden_patterns: resp.hidden_patterns ?? [],
  danger_zones: resp.danger_zones ?? [],
}
```

---

## Anti-creep verification (PASS)

Two grep contracts from UI-SPEC AC #5 / #9 were verified during review:

- `grep -rn "0\.6" frontend/src/` returns only: `i18n-keys.ts:113` (the SSoT), comments/docstrings in `RevenueStatusSection.tsx`, `PublishersPage.tsx`, `GrossNetToggle.tsx`; unrelated thresholds in `ContributorsSection.tsx` (`concentrationIndex > 0.6`); mock data in `mockData.ts`; documentation in `DocsPage.tsx`. No live duplication of `REV_SHARE_FACTOR`. **PASS**.
- `grep -rn "as of " frontend/src/` returns only `ReferencePeriodFootnote.tsx` (docstring) and `i18n-keys.ts` (the SSoT). **PASS**.

---

_Reviewed: 2026-04-30T21:34:46Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
