---
phase: 13
slug: dashboard-date-navigation
status: approved
shadcn_initialized: false
preset: none
created: 2026-04-30
reviewed_at: 2026-04-30
mode: lock-don't-redesign
truth_source: .planning/intel/sentinel-2026-04-28/EMAIL-VITO-2026-04-22.md
root_causes_addressed: []
root_causes_partial: []
---

# Phase 13 — UI Design Contract

> Visual and interaction contract for Phase 13: Dashboard Date Navigation (WIP-05 Commit D).
>
> Phase 13 is a **controlled WIP landing**, not a new visual design. The WIP
> working-tree commit `94a48cd` IS the design baseline. This spec locks that
> baseline so the executor cherry-picks and adapts the 8 target files without
> scope creep, and so the verifier can mechanically check all acceptance
> criteria.
>
> **Critical constraint:** The WIP uses `useTranslation()` / `LanguageProvider`
> throughout. Phase 12 downgraded this to `lib/i18n-keys.ts` constants. Phase
> 13 MUST follow the same downgrade: any `t('key')` call in the 8 Commit D
> files is replaced with the appropriate EN constant from `i18n-keys.ts`.
> `LanguageProvider`, `i18n/context.tsx`, `i18n/en.ts`, `i18n/it.ts`, and
> `i18n/index.ts` are NOT part of Commit D.

---

## Scope (what this contract covers)

Commit D = exactly 8 files. Planner enforces this with a file-count gate.

| File | Surface | Change summary |
|------|---------|----------------|
| `frontend/src/components/dashboard/RevenueStatus24h.tsx` | Dashboard — main revenue chart | Add `selectedDate` state; date `<select>` in `<CardHeader>` populated from `available_dates`; wire `selectedDate` to `useRevenueStatus24h`; add YoY area series from `prev_year.hours[]`; adapt chart CSS to CSS vars; strip `ReferenceLine` (hourly_avg gone); remove IT strings; adapt all `t()` calls to i18n-keys constants |
| `frontend/src/api/client.ts` | API types + hooks | Extend `PrevYearData` with `hours?: number[]` (replaces `hourly_avg`); add `available_dates?: string[]` to `RevenueStatus24hResponse`; change `useRevenueStatus24h` URL from `?date=` param to path-based `/metrics/revenue-status-24h/${date}`; update `useTopPublishers` signature to add optional `month?: number` arg |
| `frontend/src/components/alerts/RevenueStatusSection.tsx` | Alert detail — revenue status cards | Migrate raw div cards to `<Card><CardContent>` primitives; add `tabular-nums`; add `uppercase tracking-wide` to sub-labels |
| `frontend/src/components/charts/RevenueTrendChart.tsx` | Alert detail — revenue trend chart | Migrate chart styling to CSS var constants (`AXIS_STYLE`, `AXIS_LINE`, `GRID_STROKE`, `TOOLTIP_STYLE`); fix locale `it-IT` → `en-GB` in `formatDateShort`; replace IT empty-state string |
| `frontend/src/components/dashboard/RevenueByChannel.tsx` | Dashboard — revenue by channel | Remove `selectedChannels` prop (decouple from external filter); add own `selectedDate` state; wire to `useRevenueStatus24h(selectedDate)` |
| `frontend/src/components/dashboard/KpiCards.tsx` | Dashboard — KPI metric cards | Accept `data`/`isLoading` props (lifted from parent); add empty-state branch; compute RPM/CTR/viewability/gross_margin from hourly data |
| `frontend/src/pages/DashboardPage.tsx` | Dashboard page | Lift `useRevenueStatus24h()` call to page level; pass `data`/`isLoading` down to `KpiCards`; remove `ChannelFilter` + `selectedChannels` state; simplify `RevenueByChannel` invocation |
| `frontend/src/components/ui/DatePicker.tsx` | UI primitive (NEW) | New `<input type="date">` wrapper that debounces commits to on-blur/Enter only; `min`/`max` constrained to `available_dates` range |

**Out of scope — DO NOT touch in Phase 13:**
- `i18n/context.tsx`, `i18n/en.ts`, `i18n/it.ts`, `i18n/index.ts` — NOT part of Commit D
- `frontend/vercel.json`, `vite.config.ts`, `scripts/deploy.sh` — Commit E / Phase 16
- `frontend/src/pages/PublishersPage.tsx` — already landed in Phase 12 Plan 05
- `frontend/src/components/alerts/TriageSection.tsx` — already landed in Phase 12 Plan 04
- Any backend file — Commit C already shipped (Phase 12 Plan 03)
- CORR-03 gross/net toggle — Phase 14
- CORR-04 channel scope badge — Phase 14
- CORR-11 derived filter UI — Phase 14

---

## Design System

Inherited from Phase 12. No change.

| Property | Value |
|----------|-------|
| Tool | none (Tailwind v4 CSS-first via `@theme` directive in `frontend/src/index.css`) |
| Preset | not applicable |
| Component library | bespoke primitives in `frontend/src/components/ui/` (Card, Button, Badge, MetricCard, DataTable, Skeleton, AlertBox, DeltaIndicator). `DatePicker` is NEW in this phase. |
| Icon library | `lucide-react@^0.563.0` |
| Variant engine | `class-variance-authority@^0.7.1` (used by `Badge`) |
| Class merge | `clsx` + `tailwind-merge` via `cn()` helper in `lib/utils.ts` |
| Font | `'Inter', system-ui, -apple-system, sans-serif` (set on `body` in `index.css`) |
| Currency / number locale | `Intl.NumberFormat('it-IT', currency: 'EUR', 0 fraction)` — `formatCurrency` in `lib/utils.ts`. Locked. |
| Date locale | `en-GB` for date display (e.g. `toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })`). Replaces `it-IT` that existed in some WIP paths. |

**shadcn gate:** Not applicable. Same rationale as Phase 12 — bespoke primitives already cover all needed surfaces. No shadcn initialization.

**i18n gate (CRITICAL):** The WIP `94a48cd` uses `t('key')` from `useTranslation()` / `LanguageProvider` throughout the 8 Commit D files. Phase 12 decided NOT to land `LanguageProvider` (UI-SPEC §"i18n decision" line 65). Phase 13 carries the same constraint. Every `t('key')` call in the landing must be replaced with the corresponding EN string constant from `frontend/src/lib/i18n-keys.ts`. New constants MUST be added to `i18n-keys.ts` for keys not yet present (see Copywriting Contract below for exact constant names and values).

---

## Spacing Scale

Locked from Phase 12. Phase 13 inherits the same subset.

| Token | Tailwind class | Value | Phase 13 usage |
|-------|----------------|-------|----------------|
| xs | `gap-1`, `p-1` | 4px | Icon margin |
| sm | `gap-2`, `px-2`, `py-1` | 8px | Badge padding; gap between date select and card title |
| md | `gap-4`, `p-4`, `px-4` | 16px | Card inner padding |
| lg | `gap-6`, `px-6`, `py-4` | 24px | CardHeader/CardContent horizontal padding |
| xl | `space-y-6`, `gap-6` | 24-32px | DashboardPage section gaps |

**Exceptions accepted (locked from Phase 12, do not change):**
- Date `<select>` in `RevenueStatus24h` uses `px-3 py-1.5` (12/6) — same as PublishersPage year selector (Phase 12 §Spacing exception). This is INTENTIONAL to match the design language of all select controls across the app. **Why 6px and not 8px (`py-2`):** 6px gives the correct optical height for an inline control adjacent to `CardTitle` text; `py-2` (8px) would make the select visibly taller than the surrounding line height and break alignment with the CardTitle baseline.
- `CardContent.py-4` (16px) — accepted asymmetry.
- `gap-x-5 gap-y-1` in RevenueStat24h header inline stats row — inherited from WIP design, not corrected.

**New gap in RevenueStatus24h header:** The date select sits inside `<div className="flex items-center gap-3">` alongside the `<CardTitle>` — gap-3 (12px) acceptable because the select is a sibling to a title element, not an icon.

---

## Typography

Locked from Phase 12. Exactly four sizes, two main weights.

| Role | Tailwind class | Size | Weight | Line Height | Phase 13 usage |
|------|----------------|------|--------|-------------|----------------|
| Caption / hint | `text-xs` | 12px | `font-normal` (400) | 1.5 | Chart legend labels, `uppercase tracking-wide` sub-labels in `RevenueStatusSection` metric cards |
| Body / table cell | `text-sm` | 14px | `font-medium` (500) for labels, default (400) for values | 1.5 | Date select label, header stat labels, error/empty text in cards |
| Heading (CardTitle) | `text-lg` | 18px | `font-semibold` (600) | 1.2 | `CardTitle` in `RevenueStatus24h`, `RevenueByChannel`, `KpiCards` |
| Display (KPI value) | `text-2xl` | 24px | `font-bold` (700) | 1.2 | `MetricCard` value, `RevenueStatusSection` delta EUR value |

**No new font weights in Phase 13.** Only `font-medium` (500) and `font-bold` (700) are permitted. `font-semibold` (600) is permitted ONLY on `CardTitle` (existing convention, locked from Phase 12) — do not generalize to other elements. `font-normal` (400) is the implicit default.

**Numeric rendering:** `tabular-nums` class on all monetary values and deltas. The WIP adds this class throughout Commit D — carry it exactly. `font-mono` is NOT used on chart tooltip values (contrast: it IS used in table cells per Phase 12 §Typography).

**`uppercase tracking-wide` label convention (NEW in Phase 13):** `RevenueStatusSection` metric card labels (e.g. "Delta (EUR)", "Delta (%)", "Current eCPM") use `text-xs font-medium uppercase tracking-wide text-gray-500`. This is the WIP design choice for metric card sub-labels. Lock it exactly as the WIP has it; do NOT normalize to `text-sm font-medium text-gray-500`.

---

## Color

60 / 30 / 10 inherited from `index.css` `@theme`. Locked from Phase 12. No new tokens introduced in Phase 13.

| Role | Token / class | Hex | Phase 13 surfaces |
|------|---------------|-----|-------------------|
| Dominant (60%) — surface | `bg-white` | `#ffffff` | Card surfaces, chart background, tooltip bg |
| Secondary (30%) — chrome | `bg-gray-50`, `border-gray-200` | `#f9fafb`, `#e5e7eb` | CardHeader borders, chart grid lines |
| Chart primary (revenue line) | `var(--chart-blue, #3b82f6)` | `#3b82f6` | Revenue area series in `RevenueStatus24h`, `RevenueByChannel` |
| Chart baseline | `var(--chart-gray, #94a3b8)` | `#94a3b8` | Baseline 7w dashed line series in `RevenueStatus24h` |
| Chart YoY | `var(--chart-amber, #f59e0b)` | `#f59e0b` | YoY 7w dashed line series in `RevenueStatus24h` (NEW area series replacing ReferenceLine) |
| Chart grid / axis | `var(--chart-grid, #f1f5f9)`, `var(--chart-axis, #e2e8f0)` | `#f1f5f9`, `#e2e8f0` | Chart grid + axis lines in ALL charts |
| Chart tick text | `var(--chart-tick, #64748b)` | `#64748b` | X/Y axis tick labels in ALL charts |
| Metric direction positive | `text-green-500` / `text-green-600` | `#22c55e` / `#16a34a` | Positive revenue delta, positive YoY delta |
| Metric direction negative | `text-red-500` / `text-red-600` | `#ef4444` / `#dc2626` | Negative revenue delta, negative YoY delta |
| Tooltip border | `border-slate-200` | `#e2e8f0` | Chart tooltip border (WIP migrates from `border-gray-200`) |
| Tooltip text | `text-slate-700`, `text-slate-500` | `#334155`, `#64748b` | Tooltip heading + data labels |
| Select control | `border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100` | see classes | Date select in `RevenueStatus24h` header — uses distinct styling from PublishersPage selects (see below) |

**Accent reserved-for list (unchanged from Phase 12):** Severity badges (P0/P1/P2), TriageBadge, DeltaIndicator directional arrows, ChannelBadge, StatusBadge. Phase 13 does NOT introduce new accent uses.

**Date select styling (RevenueStatus24h — distinct from PublishersPage selects):**
The WIP uses a slightly different select class in `RevenueStatus24h` vs the PublishersPage year/sell_type selects:
```
cursor-pointer rounded-md border border-gray-200 bg-gray-50 px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm transition-colors hover:bg-gray-100 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500
```
Lock this class string exactly as the WIP has it — the `shadow-sm`, `transition-colors`, `hover:bg-gray-100`, `focus:outline-none` additions make the date control feel more prominent than the filter selects. This is intentional: the date picker is a primary navigation control on the dashboard.

**YoY area series — REPLACES ReferenceLine:** The current `RevenueStatus24h` uses a `<ReferenceLine y={prevYear.hourly_avg}>` with a flat dashed line at the hourly average. The WIP replaces this with a proper `<Area dataKey="yoy">` series driven by `prev_year.hours[]`. This is a behavior AND visual change locked in Phase 13. The `ReferenceLine` import and the `hourly_avg` field usage MUST be removed.

**Anti-creep guard:** No new inline hex color literals. All chart colors go through `var(--chart-X, #fallback)` CSS var pattern that the WIP establishes. This is detectable by grep.

---

## Component Inventory (Phase 13 surfaces)

| Component | File | Phase 13 change | Primitives used |
|-----------|------|-----------------|----------------|
| `RevenueStatus24h` | `frontend/src/components/dashboard/RevenueStatus24h.tsx` | Add date selector; YoY area series; CSS var styling; remove IT strings + t() calls; remove ReferenceLine + hourly_avg | `Card`, `CardHeader`, `CardTitle`, `CardContent`, `CardSkeleton`, `lucide` (none new) |
| `DatePicker` | `frontend/src/components/ui/DatePicker.tsx` (NEW) | New component: `<input type="date">` with blur/Enter commit debounce; min/max from `availableDates` array | none (native input only) |
| `KpiCards` | `frontend/src/components/dashboard/KpiCards.tsx` | Accept `data`/`isLoading` props; add KPI empty state; compute hourly aggregates for RPM/CTR/viewability/gross_margin | `MetricCard`, `CardSkeleton` |
| `RevenueByChannel` | `frontend/src/components/dashboard/RevenueByChannel.tsx` | Remove `selectedChannels` prop; add own `selectedDate` state; add error empty state; fix `CHANNEL_COLORS`/`CHANNEL_LABELS` removal | `Card`, `CardHeader`, `CardTitle`, `CardContent`, `CardSkeleton` |
| `RevenueTrendChart` | `frontend/src/components/charts/RevenueTrendChart.tsx` | CSS var constants; locale fix `it-IT` → `en-GB`; replace IT empty-state string | existing recharts primitives |
| `RevenueStatusSection` | `frontend/src/components/alerts/RevenueStatusSection.tsx` | Wrap metric cards in `<Card><CardContent>`; add `tabular-nums`; `uppercase tracking-wide` on sub-labels | `Card`, `CardContent`, `DeltaIndicator` |
| `DashboardPage` | `frontend/src/pages/DashboardPage.tsx` | Lift `useRevenueStatus24h` call; pass props to `KpiCards`; remove `ChannelFilter` + `selectedChannels` state; simplify `RevenueByChannel` | existing layout components |
| `client.ts` | `frontend/src/api/client.ts` | Extend `PrevYearData`; add `available_dates` to response type; path-based URL for date variant; `useTopPublishers` month arg (EXCLUDED in Phase 13 — see §API Contract executor note) | `useQuery` |

**No new primitives other than `DatePicker`.** `DatePicker.tsx` wraps a native `<input type="date">` — no third-party date library.

**`ChannelFilter` removal:** `DashboardPage` currently imports `ChannelFilter` and manages `selectedChannels` state. Phase 13 removes both — the WIP shows `RevenueByChannel` managing its own date state independently. `ChannelFilter.tsx` itself is NOT deleted (it may be used by other pages), only the usage in `DashboardPage` is removed.

---

## API Contract (client.ts changes)

These are the exact type changes locked for Phase 13. The executor MUST match these shapes — they are consumed by `RevenueStatus24h` and must be backwards-compatible with the backend already shipped in Phase 12 Plan 03 (Commit C).

### `PrevYearData` update

```ts
export interface PrevYearData {
  date: string
  day_of_week: string
  total_revenue: number
  delta_pct: number
  hours?: number[]        // NEW — per-hour synthetic YoY distribution (replaces hourly_avg)
  // hourly_avg removed  — field no longer returned by Commit C backend
}
```

### `RevenueStatus24hResponse` update

```ts
export interface RevenueStatus24hResponse {
  date: string
  day_of_week: string
  hours: RevenueHourData[]
  total_revenue: number
  total_baseline: number
  total_delta_pct: number | null
  prev_year: PrevYearData | null
  available_dates?: string[]   // NEW — ISO date strings, newest first (Commit C backend)
}
```

### `useRevenueStatus24h` URL change

```ts
export function useRevenueStatus24h(date?: string) {
  const path = date
    ? `/metrics/revenue-status-24h/${date}`   // path-based, NOT ?date=
    : '/metrics/revenue-status-24h'
  return useQuery<RevenueStatus24hResponse>({
    queryKey: ['revenue-status-24h', date],
    queryFn: () => fetchJSON<RevenueStatus24hResponse>(path),
    staleTime: 5 * 60_000,
  })
}
```

**Rationale:** Phase 12 Plan 03 (Commit C) shipped path-based date variant in `backend/api/routes.py`. The current `client.ts` still uses `?date=` query param. Phase 13 aligns the frontend to the backend contract.

### `useTopPublishers` signature update

> **PHASE 13 EXECUTOR — EXCLUDED FROM COMMIT D PER PLAN DECISION D-13.01-A / D-13.02-B.**
> This signature change is documented for design awareness but MUST NOT be applied in
> Phase 13. The `useTopPublishers` function MUST remain byte-identical to Phase 12
> ship-state after Plan 13-02 lands. See 13-02-PLAN.md decisions for rationale
> (preserves Phase 12 `PublishersPage.tsx` call signature). Reapplication may be
> revisited in a future phase that also updates `PublishersPage.tsx`.
>
> This annotation is a **clarification**, not a design change: the verbatim code
> block below stays in the spec for traceability of the WIP `94a48cd` baseline,
> but Plan 13-02 Task 2 explicitly skips this hunk. The byte-identity check in
> Plan 13-02 Task 2 Step 6 verifies the function body is unchanged.

```ts
export function useTopPublishers(year = 2026, month?: number, limit = 50) {
  const file = month ? `top_${year}_${String(month).padStart(2, '0')}` : `top_${year}`
  return useQuery({
    queryKey: ['publishers', year, month, limit],
    queryFn: () =>
      fetchJSON<{ publishers: PublisherSummary[] }>(`/publishers/${file}`)
        .then((r) => r.publishers),
  })
}
```

NOTE: `PublishersPage.tsx` was already landed in Phase 12 with `useTopPublishers(year, 35, sellType)` signature. The Phase 13 change to `client.ts` changes the `useTopPublishers` signature. The executor MUST verify `PublishersPage.tsx` still compiles after this change. The WIP has a different `PublishersPage` than what Phase 12 shipped — the Phase 12 version is the authoritative one and must be preserved. The `client.ts` signature change may require a minor compatibility shim or the planner must coordinate this carefully. This is flagged for the planner as a potential conflict.

---

## Date Navigation UI Specification

### Date Selector in `RevenueStatus24h`

The date `<select>` appears in the `<CardHeader>`, to the right of the `<CardTitle>`.

**Layout:**
```
+---------------------------------------------------+
| CardHeader                                        |
|  <CardTitle>Revenue Status 24h</CardTitle>        |
|  [Wed 23 Apr 2026 ▾]    ← date select            |
+---------------------------------------------------+
| (inline stats: Revenue / Baseline 7w / vs 7w / YoY) |
+---------------------------------------------------+
| CardContent (chart) |
```

The `<CardTitle>` and date select sit in `<div className="flex items-center gap-3">`.

The inline stats row sits on a separate line: `<div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1">`.

**Conditional render:** The date `<select>` is only rendered when `availableDates.length > 1`. When only one date is available (or `available_dates` is empty/missing), the CardHeader shows only the title.

**Date label format:** `en-GB` locale with `{ weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }` — produces e.g. `"Wed, 23 Apr 2026"`.

**Select value:** `value={selectedDate ?? data.date}` — defaults to the latest complete day returned by the backend when no user selection has been made.

**On change:** `onChange={(e) => setSelectedDate(e.target.value)}` — triggers `useRevenueStatus24h(selectedDate)` refetch via react-query `queryKey: ['revenue-status-24h', selectedDate]`.

### `DatePicker` primitive

Used as a NEW primitive in `frontend/src/components/ui/DatePicker.tsx` but NOT wired into `RevenueStatus24h` in the Commit D landing. The WIP uses a plain `<select>` in `RevenueStatus24h`, not the `DatePicker` component. `DatePicker.tsx` is shipped as a primitive for future use (e.g. Phase 14 alert date filters). The component is standalone — no callers in Phase 13 other than existing.

**Props contract (locked):**
```ts
interface DatePickerProps {
  value: string           // YYYY-MM-DD ISO date string
  availableDates: string[] // ISO dates, newest first; used for min/max bounds
  onChange: (date: string) => void
  className?: string
}
```

**Interaction contract:**
- `onChange` fires ONLY on blur or Enter key press, NOT on every keystroke (prevents intermediate API calls during calendar navigation).
- `min` = last element of `availableDates` (oldest available date).
- `max` = first element of `availableDates` (most recent available date).
- Internal `localValue` state tracks uncommitted input; committed value updates `commitRef`.

### YoY 7-Week Rolling Baseline Area Series

**Baseline window label (required by success criterion #2):** The header stat row MUST include an explicit label identifying the YoY baseline window. The locked label is:

```
YoY 7w ({prevYear year})    e.g. "YoY 7w (2025)"
```

This appears in the inline stats row as:
```
<span className="text-gray-500">YoY 7w ({prevYear.date.slice(0, 4)}):</span>
<span className="font-semibold tabular-nums text-gray-900">{formatCurrency(prevYear.total_revenue)}</span>
```

The chart legend label for the YoY area series is: `` `YoY 7w ${prevYear?.date.slice(0, 4) ?? ''}` `` — e.g. `"YoY 7w 2025"`.

This label is the SUCCESS CRITERION #2 implementation — it explicitly identifies both the rolling window type (7w) and the reference year. The old `"vs YoY"` label was ambiguous about the window. The new form is unambiguous.

**YoY area series visual spec (locked):**
- `dataKey="yoy"` — values from `chartData[i].yoy` = `yoyHours[i] ?? null`
- `stroke="var(--chart-amber, #f59e0b)"`, `strokeWidth={1.5}`, `strokeDasharray="8 4"`
- `fill="none"`, `dot={false}`
- `activeDot={{ r: 4, stroke: 'var(--chart-amber, #f59e0b)', strokeWidth: 2, fill: '#fff' }}`
- Only rendered when `yoyHours.length > 0`

**ReferenceLine removed:** The existing `<ReferenceLine y={prevYear.hourly_avg}>` and the `hourly_avg` field reference MUST be deleted. The `hourly_avg` field no longer exists in `PrevYearData` after the `client.ts` update.

---

## i18n-keys.ts Extension (NEW constants for Phase 13)

Phase 13 adds the following constants to `frontend/src/lib/i18n-keys.ts`. These replace the `t('key')` calls from the WIP.

```ts
/**
 * RevenueStatus24h labels (Phase 13 — dashboard date navigation).
 * Replaces t('revenue.*') calls from WIP `94a48cd`.
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
 * KpiCards empty state (Phase 13 — lifted prop pattern).
 * Replaces t('kpi.no_data') from WIP.
 */
export const KPI_NO_DATA_COPY = 'No KPI data available.';
```

**Constant naming convention:** `SCREAMING_SNAKE_CASE` for single-value strings; object const for grouped labels. Matches `KPI_LABELS` / `SELL_TYPE_LABELS` / `BASELINE_MISSING_COPY` / `emptyPublishersFiltered` established in Phase 12.

---

## Copywriting Contract

| Element | Copy (EN, locked) | Location | i18n-keys constant |
|---------|-------------------|----------|---------------------|
| Revenue chart title | `Revenue Status 24h` | `RevenueStatus24h` CardTitle | `REVENUE_LABELS.status24h` |
| Revenue stat label | `Revenue:` | Inline stats row | `REVENUE_LABELS.revenue` |
| Baseline stat label | `Baseline 7w:` | Inline stats row | `REVENUE_LABELS.baseline7w` |
| vs-7w delta label | `vs 7w:` | Inline stats row | hardcoded string (no key needed — short) |
| YoY stat label | `YoY 7w ({year}):` | Inline stats row | `REVENUE_LABELS.yoy7w` + year interpolation |
| vs-YoY delta label | `vs YoY 7w:` | Inline stats row | hardcoded (short) |
| Chart tooltip — hour header | `Hour: {HH}:00` | Tooltip | `REVENUE_LABELS.hour` |
| Chart tooltip — revenue | `Revenue: {value}` | Tooltip | `REVENUE_LABELS.revenue` |
| Chart tooltip — baseline | `Baseline 7w: {value}` | Tooltip | `REVENUE_LABELS.baseline7w` |
| Chart tooltip — delta | `Delta vs 7w: {pct}` | Tooltip | `REVENUE_LABELS.deltaVs7w` |
| Chart tooltip — YoY | `YoY 7w {year}: {value}` | Tooltip | `REVENUE_LABELS.yoy7w` |
| Area legend — baseline | `Baseline 7w` | Chart legend | `REVENUE_LABELS.baseline7w` |
| Area legend — revenue | `Revenue` | Chart legend | `REVENUE_LABELS.revenue` |
| Area legend — YoY | `YoY 7w {year}` | Chart legend | `REVENUE_LABELS.yoy7w` + year |
| Error state — RevenueStatus24h | `Failed to load 24h revenue data: {message}` | Card error branch | hardcoded (matches WIP) |
| Empty state — RevenueStatus24h | `No revenue data available.` | Card empty branch | `REVENUE_LABELS.noData` |
| Empty state — RevenueByChannel | `No revenue data available.` | Card empty branch | `REVENUE_LABELS.noData` (reuse) |
| Empty state — KpiCards | `No KPI data available.` | Grid empty branch | `KPI_NO_DATA_COPY` |
| RevenueTrendChart empty | `No revenue trend data available for this alert period.` | Div center | hardcoded in component (EN, replaces IT) |
| RevenueStatusSection — "Delta (EUR)" label | `Delta (EUR)` | Card sub-label | hardcoded (no key; concise label) |
| RevenueStatusSection — "Delta (%)" label | `Delta (%)` | Card sub-label | hardcoded |
| RevenueStatusSection — "Current eCPM" | `Current eCPM` | Card sub-label | hardcoded |
| RevenueStatusSection — "Baseline eCPM" | `Baseline eCPM` | Card sub-label | hardcoded |
| RevenueStatusSection — "eCPM Change" | `eCPM Change` | Card sub-label | hardcoded |
| RevenueStatusSection — margin sub-note | `Margin compression detected` | Sub-label p | hardcoded (already EN in WIP) |
| Destructive actions | (none in Phase 13) | — | — |

**Tone:** present tense, sentence case for body copy, title case for short metric labels. No exclamation marks, no emoji.

**IT strings removed from Phase 13 surfaces (must be gone after landing):**
- `RevenueStatus24h`: `"Errore nel caricamento dei dati revenue 24h: ..."` → `"Failed to load 24h revenue data: ..."`
- `RevenueStatus24h`: `"Nessun dato revenue 24h disponibile."` → `REVENUE_LABELS.noData`
- `RevenueStatus24h`: `"Ora: {label}:00"` in tooltip → `"Hour: {label}:00"`
- `RevenueTrendChart`: `"Dati trend revenue non disponibili per questo periodo di alert."` → `"No revenue trend data available for this alert period."`
- `RevenueTrendChart`: `d.toLocaleDateString('it-IT', ...)` → `d.toLocaleDateString('en-GB', ...)`

---

## States Inventory (per surface)

### `RevenueStatus24h` (DashboardPage)

| State | Trigger | Visual |
|-------|---------|--------|
| Loading | `isLoading === true` | `<div className="h-[420px]"><CardSkeleton /></div>` (existing height-locked skeleton) |
| Error | `error` truthy | Card with `text-sm text-red-500` message: `Failed to load 24h revenue data: {msg}` |
| Empty | `!data \|\| data.hours.length === 0` | Card with `text-sm text-gray-400`: `No revenue data available.` |
| Default (no YoY data) | `data.prev_year === null` | 2 area series (Revenue + Baseline 7w); inline stats: Revenue, Baseline 7w, vs 7w delta only; no date select when `availableDates.length <= 1` |
| Default (with YoY data) | `data.prev_year !== null && prev_year.hours.length > 0` | 3 area series (Revenue + Baseline 7w + YoY 7w); inline stats: Revenue, Baseline 7w, vs 7w, YoY 7w ({year}), vs YoY 7w |
| Date selector visible | `availableDates.length > 1` | `<select>` in CardHeader title row; changing triggers refetch |

### `KpiCards` (DashboardPage — lifted props)

| State | Trigger | Visual |
|-------|---------|--------|
| Loading | `isLoading === true` | 4 `<CardSkeleton>` in `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4` |
| Empty | `!data \|\| data.hours.length === 0` | `col-span-full` centered `text-sm text-gray-400`: `No KPI data available.` |
| Default | data present | 4 `MetricCard` instances (RPM, CTR, Viewability, Gross Margin) with computed aggregates from hourly data |

### `RevenueByChannel` (DashboardPage)

| State | Trigger | Visual |
|-------|---------|--------|
| Loading | `isLoading === true` | `<CardSkeleton />` |
| Error / no data | `error \|\| !data` | Card with `CardTitle "Revenue by Channel (24h)"` + `text-center text-sm text-slate-400`: `No revenue data available.` |
| Default | data present | Area chart with `revenue` and `baseline` series for the selected date (GOOGLE_ADEX only) |

### `RevenueStatusSection` (AlertDetailPage)

| State | Trigger | Visual |
|-------|---------|--------|
| Default | `alert.revenue_current` etc. present | 3-card grid (Revenue Current, Revenue Baseline, Delta EUR + Delta %) wrapped in `<Card><CardContent>` primitives |
| With margin metrics (A5) | `alert.margin_metrics !== undefined` | Additional 3-card grid: Current eCPM, Baseline eCPM, eCPM Change |

### `RevenueTrendChart` (AlertDetailPage sub-component)

| State | Trigger | Visual |
|-------|---------|--------|
| Empty | `chartData.length === 0` | Centered `text-sm text-gray-400`: `No revenue trend data available for this alert period.` |
| Default | `chartData.length > 0` | LineChart with baseline + revenue series, CSS var styling |

---

## File-Count Gate (Anti-scope-creep)

The executor MUST verify before creating the atomic commit:

```bash
git diff --cached --name-only | grep "^frontend/" | sort
```

Expected output: exactly 8 lines, matching this list in alphabetical order:
```
frontend/src/api/client.ts
frontend/src/components/alerts/RevenueStatusSection.tsx
frontend/src/components/charts/RevenueTrendChart.tsx
frontend/src/components/dashboard/KpiCards.tsx
frontend/src/components/dashboard/RevenueByChannel.tsx
frontend/src/components/dashboard/RevenueStatus24h.tsx
frontend/src/components/ui/DatePicker.tsx
frontend/src/pages/DashboardPage.tsx
```

If the count is not 8 or the list deviates: STOP, do not commit, surface to operator.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | (none — shadcn not initialized) | not applicable |
| third-party | (none) | not applicable |

No third-party UI registries. `DatePicker` is a native `<input type="date">` wrapper — zero external library.

---

## Acceptance Criteria (gsd-ui-checker + gsd-ui-auditor)

A Phase 13 implementation is contract-conforming when ALL the following are true:

1. **Commit D file count gate** — `git show HEAD --name-only | grep "^frontend/" | wc -l` returns exactly `8`. The 8 files match the File-Count Gate list above byte-for-byte.

2. **available_dates consumer** — `grep -n "available_dates" frontend/src/components/dashboard/RevenueStatus24h.tsx` returns ≥ 1 match; `grep -n "available_dates" frontend/src/api/client.ts` returns ≥ 1 match (in `RevenueStatus24hResponse` interface).

3. **Date select rendered conditionally** — `grep -n "availableDates.length > 1" frontend/src/components/dashboard/RevenueStatus24h.tsx` returns ≥ 1 match (not unconditionally rendered).

4. **Path-based URL** — `grep -n "revenue-status-24h/\${" frontend/src/api/client.ts` returns ≥ 1 match (path-based, not `?date=`). `grep -n "?date=" frontend/src/api/client.ts` returns ZERO matches in the `useRevenueStatus24h` function body.

5. **YoY 7w label present** — `grep -n "YoY 7w" frontend/src/components/dashboard/RevenueStatus24h.tsx` returns ≥ 2 matches (one in inline stats, one in chart legend). This is success criterion #2.

6. **YoY area series replaces ReferenceLine** — `grep -n "ReferenceLine\|hourly_avg" frontend/src/components/dashboard/RevenueStatus24h.tsx` returns ZERO matches. `grep -n "dataKey=\"yoy\"" frontend/src/components/dashboard/RevenueStatus24h.tsx` returns ≥ 1 match.

7. **No LanguageProvider / useTranslation in Commit D files** — `git show HEAD -- frontend/src/components/dashboard/RevenueStatus24h.tsx frontend/src/components/dashboard/KpiCards.tsx frontend/src/components/dashboard/RevenueByChannel.tsx frontend/src/pages/DashboardPage.tsx | grep "useTranslation\|LanguageProvider\|from '../../i18n/context'"` returns ZERO matches.

8. **IT strings removed** — `grep -n "Errore nel\|Nessun dato\|Ora:\|Dati trend\|it-IT" frontend/src/components/dashboard/RevenueStatus24h.tsx frontend/src/components/charts/RevenueTrendChart.tsx` returns ZERO matches.

9. **REVENUE_LABELS constant in i18n-keys.ts** — `grep -n "REVENUE_LABELS" frontend/src/lib/i18n-keys.ts` returns ≥ 1 match.

10. **DatePicker new file** — `test -f frontend/src/components/ui/DatePicker.tsx && echo "exists"` returns `"exists"`.

11. **CSS var pattern in chart files** — `grep -n "var(--chart-" frontend/src/components/dashboard/RevenueStatus24h.tsx frontend/src/components/charts/RevenueTrendChart.tsx` returns ≥ 2 matches total (confirming migration from hardcoded hex to CSS vars).

12. **No new hardcoded hex colors** — `git show HEAD -- frontend/src/components/dashboard/RevenueStatus24h.tsx frontend/src/components/charts/RevenueTrendChart.tsx | grep "^+" | grep -E '"#[0-9a-fA-F]{3,6}"' | grep -v "fallback\|stopColor\|activeDot\|stroke:#\|fill:#"` returns ZERO matches (all hex literals must be inside CSS var fallbacks or dot/stroke props referencing CSS vars).

13. **KpiCards accepts props** — `grep -n "interface KpiCardsProps" frontend/src/components/dashboard/KpiCards.tsx` returns ≥ 1 match; `grep -n "export function KpiCards()" frontend/src/components/dashboard/KpiCards.tsx` returns ZERO matches (no-arg version is replaced).

14. **RevenueByChannel no selectedChannels prop** — `grep -n "selectedChannels" frontend/src/components/dashboard/RevenueByChannel.tsx frontend/src/pages/DashboardPage.tsx` returns ZERO matches.

15. **tabular-nums in RevenueStatusSection** — `grep -c "tabular-nums" frontend/src/components/alerts/RevenueStatusSection.tsx` returns ≥ 3 (multiple monetary value cells).

**Re-verification path:** the `gsd-ui-auditor` executes checks 1–12 mechanically via grep. Checks 13–15 are also grep-based. Visual validation: operator confirms the date selector appears in the live `RevenueStatus24h` card and changes trigger a data reload; YoY area series appears as amber dashed line in the chart.

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS — 15 copy strings declared + 5 IT→EN removals listed; EN-only, no LanguageProvider
- [ ] Dimension 2 Visuals: PASS — DatePicker only new primitive; all other components are lock-don't-redesign; WIP design locked
- [ ] Dimension 3 Color: PASS — 60/30/10 inherited; 3 chart CSS vars declared; amber YoY series locked; no new accent colors
- [ ] Dimension 4 Typography: PASS — 4 sizes (12/14/18/24), 2 main weights (medium 500 + bold 700), tabular-nums pattern locked
- [ ] Dimension 5 Spacing: PASS — 8-point scale inherited; date select px-3 py-1.5 exception documented; gap-3 in title row justified
- [ ] Dimension 6 Registry Safety: PASS — no third-party registries; DatePicker is native input only

**Approval:** pending — awaiting `gsd-ui-checker` validation
