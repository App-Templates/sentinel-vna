---
phase: 13-dashboard-date-navigation
reviewed: 2026-04-30T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - frontend/src/api/client.ts
  - frontend/src/components/alerts/RevenueStatusSection.tsx
  - frontend/src/components/charts/RevenueTrendChart.tsx
  - frontend/src/components/dashboard/KpiCards.tsx
  - frontend/src/components/dashboard/RevenueByChannel.tsx
  - frontend/src/components/dashboard/RevenueStatus24h.tsx
  - frontend/src/components/ui/DatePicker.tsx
  - frontend/src/lib/i18n-keys.ts
  - frontend/src/pages/DashboardPage.tsx
findings:
  critical: 0
  warning: 6
  info: 6
  total: 12
status: issues_found
---

# Phase 13: Code Review Report

**Reviewed:** 2026-04-30
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Phase 13 lands the WIP-05 Commit D cherry-pick onto `main` with two surgical
adaptations: (a) i18n downgrade to EN constants in `lib/i18n-keys.ts`, and
(b) `useTopPublishers` signature kept Phase-12-compatible. Both adaptations
verify clean — no `t('...')` residues, `useTopPublishers` still accepts
`(year, limit, sellType)`.

The diff itself is well-scoped and the new code is readable. However, the
phase intent — "lift date navigation to dashboard so all panels share one
date" — is **only partially realized**. `KpiCards` was correctly lifted to
consume `data` via props from `DashboardPage`, but `RevenueStatus24h` and
`RevenueByChannel` each still keep their own `useState<string|undefined>(undefined)`
date and call `useRevenueStatus24h()` independently. Result: each panel
navigates dates in isolation, KpiCards is stuck on the un-dated default
forever, and the dashboard fires three near-identical queries instead of
one. This is the most consequential issue in the diff (WR-01 below).

A second class of issues centers on **silent-fail patterns** in KpiCards
(WR-02) — backend field renames will silently degrade KPIs to zero with no
type error and no log — and on the new `DatePicker` (WR-03, WR-04, WR-05)
which has unsorted-input fragility, no membership validation, and zero
consumers in the diff. The remaining items are quality-tier polish (info).

## Warnings

### WR-01: Date navigation lift is incomplete — three independent dates, three queries

**File:** `frontend/src/pages/DashboardPage.tsx:18`, `frontend/src/components/dashboard/RevenueStatus24h.tsx:19-20`, `frontend/src/components/dashboard/RevenueByChannel.tsx:19-20`

**Issue:** `DashboardPage` calls `useRevenueStatus24h()` (no date) and passes
`data` into `<KpiCards />`. But `<RevenueStatus24h />` and `<RevenueByChannel />`
each *internally* declare `const [selectedDate, setSelectedDate] = useState(undefined)`
and call `useRevenueStatus24h(selectedDate)`. Consequences:

1. The dashboard fires three queries on mount (all with `date=undefined`,
   so React Query dedupes via shared queryKey `['revenue-status-24h', undefined]`
   — but only by coincidence). The KpiCards comment at lines 8-10 ("dashboard
   makes ONE API call shared by all four cards") is misleading: the lift only
   covers KpiCards, and only because the other two panels happen to default
   to the same key.
2. As soon as the user changes the date dropdown inside `RevenueStatus24h`,
   that panel updates but KpiCards and RevenueByChannel do NOT — they remain
   on the original (no-date) data. Users see misaligned dates across panels.
3. `selectedDate` is duplicated state across two components for the same
   logical concern — a textbook lifted-state-up violation.

**Fix:** Lift `selectedDate` to `DashboardPage`, pass it (and `setSelectedDate`,
or a `onDateChange` callback) down to all three consumers. Have all three
components consume the same `data`/`isLoading` from the parent's single
`useRevenueStatus24h(selectedDate)` call. Example:

```tsx
// DashboardPage.tsx
const [selectedDate, setSelectedDate] = useState<string | undefined>(undefined)
const { data: revenueData, isLoading: revenueLoading } = useRevenueStatus24h(selectedDate)

return (
  <>
    <KpiCards data={revenueData} isLoading={revenueLoading} />
    <RevenueStatus24h
      data={revenueData}
      isLoading={revenueLoading}
      selectedDate={selectedDate}
      onDateChange={setSelectedDate}
    />
    <RevenueByChannel
      data={revenueData}
      isLoading={revenueLoading}
      selectedDate={selectedDate}
      onDateChange={setSelectedDate}
    />
  </>
)
```

Then strip `useState` and `useRevenueStatus24h` calls from
`RevenueStatus24h.tsx` and `RevenueByChannel.tsx`. This matches the comment
in `KpiCards.tsx:8-10` and the phase title "dashboard-date-navigation".

---

### WR-02: KpiCards silently swallows backend field renames (silent-fail anti-pattern)

**File:** `frontend/src/components/dashboard/KpiCards.tsx:42-74`

**Issue:** The component casts `data.hours` to a wider local type than the
exported `RevenueHourData` (which only declares `hour | revenue | baseline | delta_pct`):

```ts
const hours = data.hours as Array<{
  hour: number
  revenue: number
  impressions?: number
  bacino?: number
  ctr?: number
  viewability?: number
  gross_margin_pct?: number
}>
```

All extended fields are optional (`?:`) and every read uses `?? 0`. If the
backend renames any of these (e.g., `bacino` → `pool`, or `gross_margin_pct`
→ `margin_pct`), the cast still compiles, every `?? 0` returns 0, and the
KPIs silently render as `€0.00 RPM`, `0.00% CTR`, `0.00% Margin` with no
error state, no log, and no test failure. This is precisely the silent-fail
class that R-17 (capability-sdk `assertCreds` / fail-fast) was authored to
prevent in another part of the platform — the same principle applies here.

**Fix:** Either (a) extend `RevenueHourData` in `client.ts` to include the
extended fields with explicit `number | undefined`, then drop the cast;
or (b) add a runtime check that warns when a non-zero share of hours have
all extended fields missing:

```ts
const hasAnyExtended = hours.some(
  (h) => h.impressions != null || h.bacino != null || h.ctr != null,
)
if (!hasAnyExtended && totalRevenue > 0) {
  console.warn('[KpiCards] backend response missing extended fields; KPIs will be 0')
  // optionally render a "fields missing" banner instead of zero values
}
```

Option (a) is preferred — codify the contract.

---

### WR-03: DatePicker assumes `availableDates` is sorted descending — silently breaks if order changes

**File:** `frontend/src/components/ui/DatePicker.tsx:35-36`

**Issue:** `min={availableDates[availableDates.length - 1]}` and
`max={availableDates[0]}` only produce a valid `min ≤ max` interval if the
array is sorted **descending**. If the backend ever returns ascending
order — or if a future caller sorts ascending before passing in — the input
becomes `min > max`, and most browsers will silently reject every typed
date (HTML5 `<input type="date">` clamps but won't fire `onChange` for
out-of-range typed values in some browsers). The component has no defensive
sort and no JSDoc warning that descending order is required.

**Fix:** Sort defensively inside the component (cheap — date strings are
ISO so lexicographic compare works):

```ts
const sorted = [...availableDates].sort() // ascending
const minDate = sorted[0]
const maxDate = sorted[sorted.length - 1]
// ...
min={minDate}
max={maxDate}
```

Or document the precondition in JSDoc and in the prop type if you'd rather
not pay the sort cost.

---

### WR-04: DatePicker accepts dates not in `availableDates` — leads to 404 on commit

**File:** `frontend/src/components/ui/DatePicker.tsx:24-29`

**Issue:** `commit(date)` only checks `date && date !== commitRef.current`.
The user can type any date inside the `min..max` range — including dates
that are NOT in `availableDates` (e.g., gaps when ETL skipped a day) —
and `onChange(date)` will fire, triggering an API call that the backend
will 404. The component name "DatePicker that only commits the selected date
on blur or Enter" suggests the constraint check is the parent's job, but
no parent is wiring it (see WR-05).

**Fix:** Validate membership before commit:

```ts
function commit(date: string) {
  if (!date || date === commitRef.current) return
  if (availableDates.length > 0 && !availableDates.includes(date)) {
    // reset to last committed value, or surface a UI hint
    setLocalValue(commitRef.current)
    return
  }
  commitRef.current = date
  onChange(date)
}
```

For an O(1) lookup at scale, use a `Set` memoized via `useMemo` over
`availableDates`.

---

### WR-05: DatePicker has zero consumers in this diff — unused new component

**File:** `frontend/src/components/ui/DatePicker.tsx` (entire file)

**Issue:** The phase title is "dashboard-date-navigation" and the file
introduces `DatePicker.tsx`, but neither `RevenueStatus24h.tsx`,
`RevenueByChannel.tsx`, nor `DashboardPage.tsx` imports it. Both panels
still use a plain native `<select>` (RevenueStatus24h.tsx:82-93,
RevenueByChannel.tsx:53-64) listing `availableDates`. So the component
ships as **dead code** in this commit — added to the bundle but never
mounted.

Either it should be wired into the dashboard (and the WR-01 lift), or it
should not have shipped in this commit.

**Fix:** Wire `DatePicker` into the lifted state from WR-01, replacing the
two duplicated `<select>` blocks. If the intent was to land the component
ahead of a follow-up wiring commit, document that with a `TODO(phase-13.x)`
or split into a separate prep commit explicitly noted as preparatory.

---

### WR-06: RevenueByChannel does not handle empty `hours` array

**File:** `frontend/src/components/dashboard/RevenueByChannel.tsx:23-32`

**Issue:** Early return is `if (error || !data)`. If `data` is defined but
`data.hours` is an empty array (a valid backend response on a no-traffic
day), the chart renders an empty `AreaChart` with axes but no data — no
`noData` message. Compare with the sibling `RevenueStatus24h.tsx:42`
which correctly checks `!data || data.hours.length === 0`.

**Fix:** Mirror the sibling component's check:

```tsx
if (error || !data || data.hours.length === 0) return (
  <Card>
    <CardHeader><CardTitle>Revenue by Channel (24h)</CardTitle></CardHeader>
    <CardContent>
      <p className="py-8 text-center text-sm text-slate-400">{REVENUE_LABELS.noData}</p>
    </CardContent>
  </Card>
)
```

## Info

### IN-01: YoY index alignment assumes equal hours-array length, no assertion

**File:** `frontend/src/components/dashboard/RevenueStatus24h.tsx:53,60`

**Issue:** `yoy: yoyHours[i] ?? null` pairs hour `i` of the current day with
index `i` of `prev_year.hours`. If the backend ever returns `prev_year.hours`
with a length other than 24 (or differently-aligned to a partial-day current
response), the YoY line drifts silently. There's no length-parity check or
warning.

**Fix:** Add a one-line check + warn, or align by hour-of-day if the
backend supplies a parallel hour array. Minimum:

```ts
if (yoyHours.length > 0 && yoyHours.length !== data.hours.length) {
  console.warn('[RevenueStatus24h] yoy hours length mismatch', {
    cur: data.hours.length, prev: yoyHours.length,
  })
}
```

---

### IN-02: Hardcoded `#3b82f6` activeDot stroke breaks CSS-var pattern

**File:** `frontend/src/components/dashboard/RevenueStatus24h.tsx:222`

**Issue:** Lines 218 and 221 correctly use `var(--chart-blue, #3b82f6)`,
but line 222's `activeDot` props read `stroke: '#3b82f6'` literal —
inconsistent with the theming convention adopted throughout this file and
in `RevenueTrendChart.tsx`. Theming overrides won't apply to this single dot.

**Fix:**

```tsx
activeDot={{ r: 5, stroke: 'var(--chart-blue, #3b82f6)', strokeWidth: 2, fill: '#fff' }}
```

---

### IN-03: Duplicated `selectClass` literal across two dashboard panels

**File:** `frontend/src/components/dashboard/RevenueStatus24h.tsx:73`, `frontend/src/components/dashboard/RevenueByChannel.tsx:44`

**Issue:** The 13-utility-class string is duplicated verbatim in both
panels. If the design system updates focus rings or hover bg, both must
change in lockstep — a future drift point.

**Fix:** After WR-01/WR-05 wire `DatePicker`, both `<select>` blocks
disappear. If they survive in the short term, hoist the literal to a
shared module or to the new `DatePicker` component as default classes.

---

### IN-04: Magic numbers for chart heights (280, 300, 320, 420) duplicated across files

**File:** `frontend/src/components/charts/RevenueTrendChart.tsx:35`, `frontend/src/components/dashboard/RevenueStatus24h.tsx:24,134`, `frontend/src/components/dashboard/RevenueByChannel.tsx:72`

**Issue:** Chart heights `280`/`300`/`320`/`420` are scattered as inline
literals. Mostly harmless, but a constants module (e.g.,
`lib/chart-constants.ts`) would centralize the design-token-equivalent
values.

**Fix:** Optional. Extract when next chart is added:

```ts
export const CHART_HEIGHT = { trend: 280, status24h: 300, byChannel: 320 } as const
```

---

### IN-05: KpiCards `gross_margin_pct` unit ambiguity (fraction vs percent)

**File:** `frontend/src/components/dashboard/KpiCards.tsx:74,99`

**Issue:** `wMargin / totalRevenue` produces a revenue-weighted average of
`h.gross_margin_pct`. The result is then passed to `<MetricCard format="percent" />`.
Whether that renders correctly depends on whether the backend returns
percent (e.g., `35` for 35%) or fraction (`0.35`). The same unit choice
governs `ctr` (multiplied by 100 on line 72 — implies fraction input) and
`viewability` (also `*100` on line 73). But `gross_margin` (line 74) is
NOT multiplied by 100. So the convention is inconsistent: CTR/Viewability
treat the source as fraction, GrossMargin treats it as already-percent.
At minimum, document the assumption; ideally, enforce it in the type.

**Fix:** Add a comment + add explicit narrowing in client.ts type or
runtime, e.g.:

```ts
// CTR/viewability are fractions in [0,1]; gross_margin_pct is already a
// percent in [0,100]. Confirm with backend `/metrics/revenue-status-24h`
// schema before changing.
```

If the convention turns out to be wrong, GrossMargin will display 100x
too small.

---

### IN-06: `RevenueByChannel` date dropdown lacks i18n key for footer note

**File:** `frontend/src/components/dashboard/RevenueByChannel.tsx:51,67-69,103,108`

**Issue:** Phase-13 i18n downgrade replaces `t('revenue.*')` with
`REVENUE_LABELS.*` constants. Most call sites use the constants, but
several literal English strings remain in this file:

- `'Revenue by Channel (24h)'` (line 51)
- `'Hourly data — GOOGLE_ADEX only. Multi-channel breakdown pending from IT.'` (line 68)
- `'Hour: '` and `'Google AdX:'`/`'Baseline 7w:'` in the tooltip (lines 103-108)

These live outside `i18n-keys.ts`, breaking the "single source of truth for
copy strings" promise documented at `i18n-keys.ts:1-4`. Phase 14 swap to
`react-i18next` will miss them.

**Fix:** Extend `REVENUE_LABELS` (or add a `CHANNEL_LABELS` block):

```ts
export const CHANNEL_LABELS = {
  byChannel24h: 'Revenue by Channel (24h)',
  channelDataDisclaimer: 'Hourly data — GOOGLE_ADEX only. Multi-channel breakdown pending from IT.',
  googleAdx: 'Google AdX',
  googleAdxLegend: 'Google AdX (only available channel)',
} as const;
```

Same applies to `RevenueStatus24h.tsx:24` (`Step 1: Revenue Status` is in
`RevenueStatusSection.tsx`, not in scope here, but consider it a follow-up).

---

_Reviewed: 2026-04-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
