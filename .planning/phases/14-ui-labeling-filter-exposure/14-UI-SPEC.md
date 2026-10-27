---
phase: 14
slug: ui-labeling-filter-exposure
status: approved
reviewed_at: 2026-04-30
shadcn_initialized: false
preset: none
created: 2026-04-30
mode: lock-don't-redesign
truth_source: .planning/intel/sentinel-2026-04-28/EMAIL-VITO-2026-04-22.md
root_causes_addressed: [RC-a, RC-c, RC-f]
root_causes_partial: []
requirements: [CORR-02, CORR-03, CORR-04, CORR-05, CORR-06, CORR-11]
depends_on: phase-13 (HEAD a4baf2e, shipped 2026-04-30)
---

# Phase 14 — UI Design Contract

> Visual and interaction contract for Phase 14: UI Labeling + Filter Exposure
> (CORR-02, CORR-03, CORR-04, CORR-05, CORR-06, CORR-11).
>
> Phase 14 closes the **email-Vito-2026-04-22 visual/labeling loop** at the UI
> layer. Three of the five canonical root causes land here:
>
> - **RC-(a)** Top-50 publisher filter without disclaimer → CORR-04 channel
>   scope badge + "Top 50 publishers" disclaimer on PublishersPage.
> - **RC-(c)** NET vs GROSS without label (€115k Sentinel = €188k PBI × 0.6
>   rev-share) → CORR-03 gross/net side-by-side toggle with explicit
>   "post rev-share 60%" label. **The math is correct; the LABEL is the bug.**
> - **RC-(f)** Timestamp / timezone label missing → CORR-02 + CORR-05 reference
>   period (`as of [timestamp] UTC`) on every metric card.
>
> Phase 14 ALSO exposes derived filters (CORR-11) and migrates PublishersPage
> filter state to URL params (CORR-06).
>
> **Mode: lock-don't-redesign.** Phase 14 is a labeling and filter-exposure
> phase, NOT a visual redesign. The Phase 12+13 design baseline (Card / Badge /
> MetricCard / DataTable primitives, 60/30/10 color, 4-size typography, 8-point
> spacing) is **inherited verbatim**. Phase 14 only adds disclosures, badges,
> toggles, URL-state hooks, and dropdown filters — all built from existing
> primitives.

---

## Scope (what this contract covers)

| Surface | Phase 14 change | Lock-don't-redesign? |
|---------|-----------------|----------------------|
| `RevenueStatus24h.tsx` | Add `ScopeBadge` ("GOOGLE_ADEX only"); add reference period footnote (`as of {timestamp} UTC`); pass `currency: EUR` label on each amount label | YES — chart layout, legend, colors UNCHANGED from Phase 13 |
| `RevenueByChannel.tsx` | Add `ScopeBadge` ("GOOGLE_ADEX only"); reference period footnote; align with RevenueStatus24h | YES — identical to RevenueStatus24h |
| `KpiCards.tsx` | Add `ScopeBadge` ("GOOGLE_ADEX only") on the section; reference period footnote `as of {timestamp} UTC, EUR` under the 4-card grid | YES — 4 MetricCard grid UNCHANGED |
| `RevenueStatusSection.tsx` (alert detail Step 1) | Add `<ReferencePeriodFootnote>` showing `for {alert.timestamp} UTC` AND a `<GrossNetToggle>` so operators can switch between revenue_gross (default, PBI-aligned) and revenue_net (×0.6 rev-share) display | YES — 4-card grid UNCHANGED; new toggle inside CardHeader |
| `TriageSection.tsx` (alert detail Step 2) | Inherit gross/net display from parent; add reference period footnote `for {alert.timestamp} UTC` under the table | YES — table UNCHANGED |
| `PublishersPage.tsx` | (a) Add `<TopNDisclaimer>` "Showing top 50 publishers — does not represent the full network"; (b) migrate `year` + `sellType` from `useState` to URL params via NEW `useTopPublishersFilters` hook; (c) add three NEW filter affordances: `month` dropdown (2026 + monthly 01-12), `geo_cluster` dropdown (ITA / ES / LATAM / PT / OTHER), `publisher_tier` segmented control (A/B/C); (d) `gross_net` toggle for the revenue display | YES — table columns, summary cards, color tokens UNCHANGED |
| `useTopPublishersFilters.ts` (NEW hook) | Mirrors `useAlertFilters` pattern: `useSearchParams` reader/writer for `year`, `month`, `sell_type_proxy`, `publisher_tier`, `geo_cluster`, `gross_net` | N/A — new file |
| `ScopeBadge.tsx` (NEW primitive) | Reads `channel_group` (e.g. `'GOOGLE_ADEX'`) and renders `Badge` variant with locked copy `"{channel_group} only"` | N/A — new primitive |
| `ReferencePeriodFootnote.tsx` (NEW primitive) | Renders `<p className="text-xs text-gray-500 mt-2">as of {formatTimestampUtc(timestamp)}, EUR</p>` with locked format | N/A — new primitive |
| `GrossNetToggle.tsx` (NEW primitive) | Segmented control with `Gross` / `Net (post rev-share 60%)` options; controlled component; default = `gross` | N/A — new primitive |
| `TopNDisclaimer.tsx` (NEW primitive) | Renders `<p className="text-xs text-gray-500 mt-1">Showing top 50 publishers — does not represent the full network. <Link to="/api/metrics/network-totals">Network totals</Link></p>` | N/A — new primitive |
| `i18n-keys.ts` extension | Add `SCOPE_BADGE_COPY`, `REFERENCE_PERIOD_COPY`, `GROSS_NET_LABELS`, `TOP_N_DISCLAIMER_COPY`, `MONTH_LABELS`, `GEO_LABELS`, `PUBLISHER_TIER_LABELS` | N/A — copy-only extension |

**Out of scope — DO NOT touch in Phase 14:**

- CORR-07 diagnostic empty states on chart components → Phase 15
- CORR-10 ErrorBoundary on chart components → Phase 15
- Mondadori publisher_family aggregation (RC-b) → Phase 17 CLEAN-02
- Legacy GOOGLE channel naming (RC-d) → already closed at math layer in Phase 12 Plan 03; re-label cosmetic deferred to Phase 17
- New backend endpoints — Phase 14 consumes only fields already exposed by Phase 11 (`revenue_gross`, `available_dates`, `sell_type_filter`, `baseline_bacino`, `baseline_coverage`)
- DashboardPage layout reflow — `DashboardPage.tsx` itself is not modified; `KpiCards` / `RevenueStatus24h` / `RevenueByChannel` add their own labels self-contained

---

## Design System

Inherited verbatim from Phase 12 + Phase 13. No change.

| Property | Value |
|----------|-------|
| Tool | none (Tailwind v4 CSS-first via `@theme` directive in `frontend/src/index.css`) |
| Preset | not applicable |
| Component library | bespoke primitives in `frontend/src/components/ui/` (Card, Button, Badge, MetricCard, DataTable, Skeleton, AlertBox, DeltaIndicator, DatePicker). Phase 14 adds 4 new primitives: `ScopeBadge`, `ReferencePeriodFootnote`, `GrossNetToggle`, `TopNDisclaimer`. |
| Icon library | `lucide-react@^0.563.0` |
| Variant engine | `class-variance-authority@^0.7.1` (used by `Badge`) |
| Class merge | `clsx` + `tailwind-merge` via `cn()` helper in `lib/utils.ts` |
| Font | `'Inter', system-ui, -apple-system, sans-serif` (set on `body` in `index.css`) |
| Currency / number locale | `Intl.NumberFormat('it-IT', currency: 'EUR', 0 fraction)` — `formatCurrency` in `lib/utils.ts`. Locked. |
| Date / timestamp locale | `en-GB` for date display; UTC explicit in label. Phase 14 introduces `formatTimestampUtc(iso)` helper that produces `"13 Jan 2026 08:57 UTC"` (locked format below). |
| State management | TanStack Query (server state) + `useSearchParams` (URL state) + `useState` (transient UI state). Phase 14 mandates URL state for PublishersPage filters per CORR-06. |

**shadcn gate:** Not applicable. Same rationale as Phases 12+13 — bespoke primitives already cover all needed surfaces. No shadcn initialization in v1.3.

**i18n decision (carried from Phase 12+13):** All NEW user-facing copy lives in `frontend/src/lib/i18n-keys.ts` as named exports. **No inline strings in JSX.** Component imports the named constants; no `t('key')` calls anywhere (no `LanguageProvider`).

---

## Spacing Scale

Locked from Phase 12 + Phase 13. Phase 14 adds zero new spacing tokens.

| Token | Tailwind class | Value | Phase 14 usage |
|-------|----------------|-------|----------------|
| xs | `gap-1`, `p-1` | 4px | Icon margin in ScopeBadge |
| sm | `gap-2`, `px-2`, `py-1` | 8px | Filter dropdown spacing in PublishersPage CardHeader |
| md | `gap-4`, `p-4`, `px-4` | 16px | Filter row vertical rhythm |
| lg | `gap-6`, `px-6`, `py-4` | 24px | CardHeader/CardContent horizontal padding |
| xl | `space-y-6`, `gap-6` | 24-32px | DashboardPage and PublishersPage section gaps |

**Exceptions accepted (locked from Phase 12 + Phase 13, do not change):**

- Filter `<select>` controls in PublishersPage use `px-3 py-1.5` (12/6) — locked Phase 12 convention. **Every new filter dropdown in Phase 14 (`month`, `geo_cluster`) MUST use the same class string** so the four selectors (year + sell_type + month + geo) align horizontally.
- `RevenueStatus24h` date select uses the distinct `bg-gray-50 shadow-sm hover:bg-gray-100` styling — locked Phase 13 convention.
- `Badge` uses `px-2.5 py-0.5` (10/2) — existing convention. New `ScopeBadge` reuses Badge primitive, inheriting these values.
- `ReferencePeriodFootnote` uses `mt-2` (8px) — chosen so the footnote sits visually "attached" to the metric card it annotates (smaller than the standard `mt-3` 12px used between independent rows).
- `TopNDisclaimer` uses `mt-1` (4px) — sits directly under the page title `<h1>`, intentionally tight.

**Filter row layout (PublishersPage `<CardHeader>`):**

```
+------------------------------------------------------------------------+
| CardHeader                                                             |
|  [Top 35 Publishers by Revenue]   [All ▾] [All ▾] [Apr ▾] [2026 ▾]    |
|  ↑ title                          ↑ sell  ↑ geo  ↑month ↑year         |
+------------------------------------------------------------------------+
| TopNDisclaimer "Showing top 50 publishers ..." (text-xs, mt-1)        |
+------------------------------------------------------------------------+
```

All four filters wrapped in `<div className="flex items-center gap-2">` (8px gap, locked from Phase 12 sell_type+year pattern).

**Anti-creep guardrail:** No new `px-`/`py-`/`gap-`/`m-`/`p-` value introduced in Phase 14 outside the inherited Tailwind subset above. Verified by grep over the diff for class strings using non-multiples-of-4.

---

## Typography

Locked from Phase 12 + Phase 13. Exactly four sizes, two main weights. Phase 14 adds zero new typographic tokens.

| Role | Tailwind class | Size | Weight | Line Height | Phase 14 usage |
|------|----------------|------|--------|-------------|----------------|
| Caption / hint | `text-xs` | 12px | `font-normal` (400) or `font-medium` (500) | 1.5 | `ReferencePeriodFootnote`, `TopNDisclaimer`, `ScopeBadge` body, `uppercase tracking-wide` sub-labels (Phase 13 convention preserved) |
| Body / table cell | `text-sm` | 14px | `font-medium` (500) for labels, default (400) for values | 1.5 | Filter `<select>` text, GrossNetToggle option labels |
| Heading (CardTitle) | `text-lg` | 18px | `font-semibold` (600) | 1.2 | All `CardTitle` (existing convention) |
| Display (KPI value) | `text-2xl` | 24px | `font-bold` (700) | 1.2 | `MetricCard` value (untouched) |

**No new font weights in Phase 14.** Only `font-medium` (500), `font-semibold` (600 — `CardTitle` only), and `font-bold` (700) are permitted. `font-normal` (400) is the implicit default. **No `font-light`, `font-thin`, `font-extrabold`, `font-black`.**

**Numeric rendering:** `tabular-nums` on every monetary value (Phase 13 convention preserved). When the gross/net toggle is `net`, the displayed value MUST keep `tabular-nums` so column widths do not jump on toggle.

**`uppercase tracking-wide` label convention (Phase 13):** Reused for `ScopeBadge` body when rendered in card-footnote position (e.g. `text-xs font-medium uppercase tracking-wide text-gray-500`). NEW: `ReferencePeriodFootnote` does NOT use `uppercase` — it's a sentence ("as of 13 Jan 2026 08:57 UTC") and uses regular sentence case. Anti-pattern: do NOT apply `uppercase` to multi-word sentences; reserve for short metric labels.

---

## Color

60 / 30 / 10 inherited from `index.css` `@theme`. No new tokens introduced in Phase 14.

| Role | Token / class | Hex | Phase 14 surfaces |
|------|---------------|-----|-------------------|
| Dominant (60%) — surface | `bg-white`, `--color-bg-primary` | `#ffffff` | All cards, page background |
| Secondary (30%) — chrome | `bg-gray-50`, `border-gray-200`, `--color-bg-card` | `#f9fafb`, `#e5e7eb` | CardHeader chrome, filter row background, footnote separator |
| Footnote text | `text-gray-500`, `text-gray-400` | `#6b7280`, `#9ca3af` | `ReferencePeriodFootnote`, `TopNDisclaimer`, `ScopeBadge` body |
| ScopeBadge | `bg-blue-50 text-blue-700 border-blue-200` (existing `Badge` "OPEN" status variant tone) | varied | `ScopeBadge` for `GOOGLE_ADEX` channel scope. Reuses ChannelBadge color palette — **NO new color introduced.** |
| GrossNetToggle (active) | `bg-gray-900 text-white` | `#111827` / `#ffffff` | Selected segment of segmented control. Mirrors sidebar selected-state convention. |
| GrossNetToggle (inactive) | `bg-white text-gray-700 hover:bg-gray-50 border-gray-200` | varied | Unselected segment. |
| Filter dropdown active | `border-blue-500 ring-1 ring-blue-500` (existing `<select>:focus` convention) | `#3b82f6` | NEW `month` and `geo_cluster` dropdowns inherit existing focus styling exactly. |

**Accent reserved-for list (UNCHANGED from Phase 12+13):**

- Severity badge color: `--color-severity-p0/p1/p2`. Used ONLY by `SeverityBadge`.
- Triage color: `--color-triage-traffic/coverage/mixed/revenue`. Used ONLY by `TriageBadge`.
- Metric direction: `--color-metric-positive/negative/neutral`. Used ONLY by direction arrows + delta cells.
- Channel badge: blue/teal/orange/purple/cyan/red/amber `bg-X-50 text-X-700 border-X-200`. Used ONLY by `ChannelBadge` AND now `ScopeBadge` (which is semantically a ChannelBadge sibling — same palette, new wrapping component for consistent "{channel} only" copy).
- Status badge: blue (OPEN), purple (ACK), green (RESOLVED), gray (SNOOZED). Used ONLY by `StatusBadge`.
- A6 / A7 sub-card amber/purple. Used ONLY in `TriageSection` conditional renders.

**Anti-pattern (PROIBITO in Phase 14):** Do NOT introduce a new color for "reference period" footnote, "gross/net" toggle, or "top-50 disclaimer". Reuse `text-gray-500` / `text-gray-400` for low-emphasis text and `bg-gray-900` for high-emphasis active toggle. These are existing project tokens.

**Anti-creep grep:** `git diff frontend/` for Phase 14 must NOT introduce any new `bg-X-Y` or `text-X-Y` Tailwind class where `X-Y` does not already appear in the Phase 12 or Phase 13 ship-state. Verifier executes this check.

---

## Component Inventory (Phase 14 surfaces)

| Component | File | Phase 14 change | Primitives used |
|-----------|------|-----------------|----------------|
| `ScopeBadge` | `frontend/src/components/ui/ScopeBadge.tsx` (NEW) | New primitive: `<Badge variant="channel-{channel_group}">{channel_group} only</Badge>` | `Badge` (existing) |
| `ReferencePeriodFootnote` | `frontend/src/components/ui/ReferencePeriodFootnote.tsx` (NEW) | New primitive: renders `<p className="text-xs text-gray-500 mt-2">as of {formatTimestampUtc(timestamp)}, EUR</p>` | none |
| `GrossNetToggle` | `frontend/src/components/ui/GrossNetToggle.tsx` (NEW) | Controlled segmented control. Default `gross`. Two segments: `Gross` and `Net (post rev-share 60%)`. | none (native button + Tailwind) |
| `TopNDisclaimer` | `frontend/src/components/ui/TopNDisclaimer.tsx` (NEW) | Disclaimer text + link to network-totals endpoint. | `react-router-dom` `Link` (or `<a>`) |
| `useTopPublishersFilters` | `frontend/src/hooks/useTopPublishersFilters.ts` (NEW) | URL-state hook. Mirrors `useAlertFilters.ts` (line-by-line analog). Manages `year`, `month`, `sell_type_proxy`, `publisher_tier`, `geo_cluster`, `gross_net` search params. | `useSearchParams` from `react-router-dom` |
| `KpiCards` | `frontend/src/components/dashboard/KpiCards.tsx` | Add `<ScopeBadge channel="GOOGLE_ADEX" />` and `<ReferencePeriodFootnote timestamp={data.date} />` (where `data.date` = ISO from response — Phase 13 contract). | `ScopeBadge`, `ReferencePeriodFootnote` (new); `MetricCard`, `CardSkeleton` (existing) |
| `RevenueStatus24h` | `frontend/src/components/dashboard/RevenueStatus24h.tsx` | Add `<ScopeBadge channel="GOOGLE_ADEX" />` next to `CardTitle`. Add `<ReferencePeriodFootnote timestamp={data.date} />` under the chart. | `ScopeBadge`, `ReferencePeriodFootnote` (new) |
| `RevenueByChannel` | `frontend/src/components/dashboard/RevenueByChannel.tsx` | Replace inline note `"Hourly data — GOOGLE_ADEX only..."` with composed `<ScopeBadge channel="GOOGLE_ADEX" />`. Add `<ReferencePeriodFootnote timestamp={data.date} />` under the chart. | `ScopeBadge`, `ReferencePeriodFootnote` (new) |
| `RevenueStatusSection` | `frontend/src/components/alerts/RevenueStatusSection.tsx` | Add `<GrossNetToggle value={grossNet} onChange={setGrossNet} />` in `CardHeader` right side. When `grossNet === 'net'`, the displayed `revenue_current` becomes `revenue_current * 0.6` and the `Current Revenue` label appends `(net)`. Default `gross`. Add `<ReferencePeriodFootnote timestamp={alert.timestamp} />` under the 4-card grid. | `GrossNetToggle`, `ReferencePeriodFootnote` (new) |
| `TriageSection` | `frontend/src/components/alerts/TriageSection.tsx` | Add `<ReferencePeriodFootnote timestamp={alert.timestamp} />` under the table (above the existing `BASELINE_MISSING_COPY` paragraph if shown). The Revenue row in the table inherits `grossNet` mode lifted from `AlertDetailPage`. | `ReferencePeriodFootnote` (new) |
| `PublishersPage` | `frontend/src/pages/PublishersPage.tsx` | (a) Replace `useState(2025)` + `useState<SellTypeKey>('all')` with `useTopPublishersFilters()` hook return; (b) add `<TopNDisclaimer />` under page title; (c) add `<select>` for `month` (13 options: "All months" + 01-12); (d) add `<select>` for `geo_cluster` (6 options: "All countries" + ITA / ES / LATAM / PT / OTHER); (e) add `<select>` for `publisher_tier` (4 options: "All tiers" + A / B / C); (f) add `<GrossNetToggle>` above the summary cards row; (g) when `grossNet === 'net'`, multiply `total_revenue` and `revenue` column display by 0.6 and append `(net)` label. | `TopNDisclaimer`, `GrossNetToggle` (new); existing primitives |
| `i18n-keys.ts` | `frontend/src/lib/i18n-keys.ts` | Add 7 new exports (see Copywriting Contract). | none |

**No new primitives outside the 4 listed above.** No DateRangePicker, no MultiSelect, no Combobox introduced in Phase 14. Native `<select>` is sufficient for `month`, `geo_cluster`, `publisher_tier` (matches Phase 12+13 precedent for filter dropdowns). The `GrossNetToggle` is a small bespoke segmented control (not a 3rd-party library).

---

## Filter Exposure Specification (PublishersPage CardHeader)

### Layout (locked)

```
<CardHeader>
  <div className="flex flex-wrap items-center justify-between">
    <CardTitle>Top {N} Publishers by Revenue</CardTitle>
    <div className="flex flex-wrap items-center gap-2">
      <select id="filter-sell-type">...</select>     {/* sell_type — 6 options */}
      <select id="filter-geo-cluster">...</select>   {/* NEW — 6 options */}
      <select id="filter-publisher-tier">...</select>{/* NEW — 4 options */}
      <select id="filter-environment">...</select>   {/* NEW W-1 iter-1 — 5 options */}
      <select id="filter-month">...</select>         {/* NEW — 13 options */}
      <select id="filter-year">...</select>          {/* year — 2 options */}
    </div>
  </div>
</CardHeader>
```

All six `<select>` controls share the locked Phase 12 className:

```
className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
```

### Filter contracts

| Filter | URL key | Default value | Options (label / value) | Sentinel for "all" |
|--------|---------|---------------|--------------------------|---------------------|
| `sell_type_proxy` | `sell_type_proxy` | `all` | All sell types / `all`; Open Market / `Open_Market`; Header Bidding / `Header_Bidding`; Direct / `Direct`; Deal / `Deal`; Other / `Other` | `all` (no query param sent — Phase 12 convention) |
| `geo_cluster` | `geo_cluster` | `all` | All countries / `all`; Italy / `ITA`; Spain / `ES`; LATAM / `LATAM`; Portugal / `PT`; Other / `OTHER` | `all` (no query param sent) |
| `publisher_tier` | `publisher_tier` | `all` | All tiers / `all`; Tier A / `A`; Tier B / `B`; Tier C / `C` | `all` (no query param sent) |
| `month` | `month` | `all` | All months / `all`; January / `01` ... December / `12` | `all` (no query param sent) |
| `environment` | `environment` | `all` | All environments / `all`; Web / `WEB`; AMP / `AMP`; App / `APP`; Unknown / `UNKNOWN` (mirrors `Environment` type from `frontend/src/types/alert.ts` line 6) | `all` (no query param sent) |
| `year` | `year` | `2025` | 2024 / `2024`; 2025 / `2025`; 2026 / `2026` | (no sentinel — year always set) |
| `gross_net` | `gross_net` | `gross` | Gross / `gross`; Net (post rev-share 60%) / `net` | (no sentinel — toggle always set) |

**URL state shape (CORR-06 closure):** Selecting non-default values writes to URL search params via `setSearchParams`. Example URL:

```
/publishers?year=2026&month=04&sell_type_proxy=Open_Market&publisher_tier=A&geo_cluster=ITA&environment=WEB&gross_net=net
```

**Sharability acceptance criterion:** copying that URL into a new browser tab MUST reproduce the exact filter state on first render. Verified by `useTopPublishersFilters` hook reading `searchParams` on mount. (W-1 iter-1: filter set is now 7 keys — year + month + sell_type_proxy + publisher_tier + geo_cluster + environment + gross_net.)

**Backwards compat:** Phase 12 shipped `useTopPublishers(year, 35, sellType)` consuming `?year=...&sell_type=...`. Phase 14 changes `sell_type` → `sell_type_proxy` URL key for clarity (the field IS a proxy per SCHEMA-04 D4 derivation). Migration: read both `?sell_type` and `?sell_type_proxy`, prefer `sell_type_proxy`, on next setSearchParams write only `sell_type_proxy`. **No 404 / no broken bookmarks.**

**Filter application:** for filters NOT yet supported by the backend `/api/publishers/top` endpoint (`geo_cluster`, `publisher_tier`, `month`, `environment` — W-1 iter-1 added), Phase 14 applies them **client-side** over the already-fetched `publishers` array. Document in code comments + UI-SPEC: "Client-side filter — backend endpoint does not yet accept this param. Server-side filtering deferred to v1.4 OPS-02." For `sell_type_proxy` and `year`, send to backend (existing Phase 11 contract). The `environment` filter is special: `PublisherSummary` does not currently carry any environment field (verified 2026-04-30: `frontend/src/types/publisher.ts` PublisherSummary has no environment field — `EnvShare` lives only on `PublisherDetail.environment_breakdown`). Phase 14 ships the URL-state + dropdown UI as a no-op predicate (matches the month filter's posture); when/if the backend `/api/publishers/top` exposes a `dominant_environment` or equivalent field, the predicate becomes effective without UI changes.

**Empty-state copy with active filters (extends Phase 12 `emptyPublishersFiltered`):** if any non-default filter is active and `data.length === 0`, show a single sentence describing the active filter set:

```
No publishers match {active filter labels} for {year}.
```

Where `{active filter labels}` is a comma-separated list of non-default filter labels, e.g. `Open Market, Italy, Tier A`. If only one non-default filter, omit the comma (e.g. `No publishers match Open Market for 2026.`). Locked helper: `i18n-keys.ts` `emptyPublishersFiltered(activeFilters: string[], year: number)`.

---

## CORR-02 + CORR-05 — Reference Period Footnote (RC-(f) closure)

**Bug source (Email Vito #5):** "L'alert è delle 8:57 del 13 Gennaio, il dato di revenue a quale periodo fa riferimento?" The alert UI shows `Current Revenue €25,927` with no temporal anchor.

**Fix:** every metric card on the dashboard AND every alert detail step that displays a revenue/impressions/coverage value MUST render `<ReferencePeriodFootnote>` near it.

### `ReferencePeriodFootnote` primitive (locked)

**File:** `frontend/src/components/ui/ReferencePeriodFootnote.tsx`

**Props:**

```ts
interface ReferencePeriodFootnoteProps {
  timestamp: string;        // ISO 8601, UTC, e.g. "2026-01-13T08:57:00Z"
  variant?: 'card' | 'inline';  // default 'card' — adds mt-2; 'inline' uses no margin
  withCurrency?: boolean;       // default true — appends ", EUR"
  className?: string;
}
```

**Render contract:**

```tsx
// variant='card' (default):
<p className="text-xs text-gray-500 mt-2">as of {formatTimestampUtc(timestamp)}, EUR</p>

// variant='inline':
<span className="text-xs text-gray-500">as of {formatTimestampUtc(timestamp)}, EUR</span>
```

**`formatTimestampUtc(iso)` helper (in `lib/utils.ts`):**

- Input: ISO 8601 string (e.g. `"2026-01-13T08:57:00Z"`)
- Output: `"13 Jan 2026 08:57 UTC"` (locked format)
- Locale: `en-GB` for date portion; time as `HH:MM` 24h; `UTC` literal suffix
- Implementation:
  ```ts
  export function formatTimestampUtc(iso: string): string {
    const d = new Date(iso);
    const date = d.toLocaleDateString('en-GB', {
      day: '2-digit', month: 'short', year: 'numeric',
      timeZone: 'UTC',
    });
    const time = d.toLocaleTimeString('en-GB', {
      hour: '2-digit', minute: '2-digit',
      hour12: false,
      timeZone: 'UTC',
    });
    return `${date} ${time} UTC`;
  }
  ```

**Placement matrix:**

| Surface | Timestamp source | Placement |
|---------|------------------|-----------|
| `KpiCards` | `data.date` (RevenueStatus24h response) | One footnote BELOW the 4-card grid (`<div className="col-span-full">`) — single footnote per card-group, not per card |
| `RevenueStatus24h` | `data.date` | One footnote inside `CardContent`, below the chart |
| `RevenueByChannel` | `data.date` | One footnote inside `CardContent`, below the chart |
| `RevenueStatusSection` | `alert.timestamp` | One footnote at the bottom of `CardContent`, below the 4-card grid + margin metrics |
| `TriageSection` | `alert.timestamp` | One footnote inside `CardContent`, below the metric table (above `BASELINE_MISSING_COPY` if shown — order: table → ReferencePeriodFootnote → BASELINE_MISSING_COPY) |

**Anti-creep grep:** `grep -rn "as of " frontend/src/` after Phase 14 lands MUST return ONLY matches inside `ReferencePeriodFootnote.tsx` and `i18n-keys.ts`. **Zero matches inside other JSX files.** This proves the disclosure is centralized.

**Why UTC literal in the label:** Vito's PBI report is in Italy timezone (Europe/Rome). Sentinel parquet stores UTC. Mixing the two without explicit label is the v1.3 anti-pattern. Phase 14 makes it impossible to forget which zone the number refers to. Future v1.4 OPS-04 may add Europe/Rome optional display; current contract is UTC-only with explicit label.

---

## CORR-03 — Gross / Net Toggle (RC-(c) closure)

**Bug source (Email Vito #4e):** "€115k vs €188k (Power BI, all sell type)". The math is correct (`revenue_gross × 0.6 = net_to_publisher`), the **label is the bug**. Sentinel was showing the net-to-publisher value without ever telling the operator that `0.6` rev-share factor applied. PBI shows gross. Vito expected gross.

**Fix:** introduce a `GrossNetToggle` segmented control. Default `gross` (PBI-aligned, per Decision D2). The backend's `revenue_gross` field is already exposed (Phase 11). Net is computed client-side as `revenue_gross × 0.6`. Both values shown when toggle is `net`; when toggle is `gross`, only gross is shown.

### `GrossNetToggle` primitive (locked)

**File:** `frontend/src/components/ui/GrossNetToggle.tsx`

**Props:**

```ts
type GrossNetMode = 'gross' | 'net';

interface GrossNetToggleProps {
  value: GrossNetMode;
  onChange: (mode: GrossNetMode) => void;
  className?: string;
}
```

**Render contract:**

```tsx
<div role="group" aria-label="Revenue display mode" className="inline-flex rounded-md border border-gray-200 bg-gray-50 p-0.5">
  <button
    type="button"
    aria-pressed={value === 'gross'}
    onClick={() => onChange('gross')}
    className={cn(
      'rounded-sm px-3 py-1 text-xs font-medium transition-colors',
      value === 'gross' ? 'bg-gray-900 text-white' : 'text-gray-600 hover:bg-gray-100',
    )}
  >
    Gross
  </button>
  <button
    type="button"
    aria-pressed={value === 'net'}
    onClick={() => onChange('net')}
    className={cn(
      'rounded-sm px-3 py-1 text-xs font-medium transition-colors',
      value === 'net' ? 'bg-gray-900 text-white' : 'text-gray-600 hover:bg-gray-100',
    )}
  >
    Net (post rev-share 60%)
  </button>
</div>
```

**Locked copy (i18n-keys.ts `GROSS_NET_LABELS`):**

| Key | Value |
|-----|-------|
| `GROSS_NET_LABELS.gross` | `Gross` |
| `GROSS_NET_LABELS.net` | `Net (post rev-share 60%)` |
| `GROSS_NET_LABELS.grossSuffix` | `(gross)` (appended to value labels when explicitly disambiguating) |
| `GROSS_NET_LABELS.netSuffix` | `(net)` (appended to value labels when toggle is `net`) |

**Computation contract (client-side):**

- `gross` mode: display `revenue_gross` directly (or `revenue_current` field which already represents gross per Phase 11 backend contract).
- `net` mode: display `revenue_gross × 0.6` (rounded to nearest €), with `(net)` suffix on label.
- The 0.6 factor lives in `i18n-keys.ts` as `REV_SHARE_FACTOR = 0.6` constant — single source of truth, greppable.
- **Anti-pattern:** never compute `gross / 0.6` to recover net — the contract is ALWAYS `net = gross × 0.6`, never the reverse direction. Backend may later expose a `revenue_net` field directly; until then client computes net from gross.

**Placement matrix:**

| Surface | Toggle location | Affected values |
|---------|-----------------|-----------------|
| `RevenueStatusSection` | `CardHeader` right side (replaces nothing — added next to title) | `Current Revenue`, `Baseline (7-week avg)`, `Delta (EUR)`, `Delta (%)` recompute? — NO. Only the EUR value labels change; deltas stay percent-based regardless of mode. The DOLLAR DELTA (`Delta EUR`) recomputes as `(current × factor) - (baseline × factor) = delta × factor`. |
| `TriageSection` | NOT placed here — inherits mode from `AlertDetailPage` page-level state | `Revenue` row's current + baseline + delta values multiply by `0.6` when `net`. Bacino + Coverage rows UNAFFECTED (they're impressions / ratios, not currency). |
| `PublishersPage` | Above the 5-card summary row, `<div className="flex items-center justify-end mt-4">` | All revenue values: `Total Revenue` summary card, `Top Publisher` summary card revenue, table `Revenue` column — multiply by `0.6` when `net`. |
| Dashboard cards (`RevenueStatus24h`, `RevenueByChannel`, `KpiCards`) | NOT placed here in Phase 14 — these aggregates are network-level and PBI-comparable in gross only. **Out of scope for Phase 14.** Future Phase 15 may extend; currently dashboard cards always show gross with explicit `(gross)` suffix. |

**Why dashboard cards show gross-only in Phase 14:** the email Vito complaint #4e is specifically about Mondadori publisher revenue. Network-level dashboard totals are not currently disputed — adding the toggle there would be feature creep. RC-(c) is closed by labeling the dashboard values as `(gross)` AND providing the toggle on PublisherDetail / Alert detail / PublishersPage where per-publisher economics are displayed.

**Page-level state lifting (AlertDetailPage):** `RevenueStatusSection` and `TriageSection` are both rendered by `AlertDetailPage`. To keep the gross/net mode synchronized between the two sections, `AlertDetailPage` owns the `grossNet` `useState` and passes it as a prop to both children. **Task for executor:** thread the prop through.

**URL state (CORR-06):** for `PublishersPage`, `gross_net` is a URL search param (per filter contract above). For `AlertDetailPage`, `grossNet` is local `useState` — operators rarely share alert-detail URLs with mode included; deferred to v1.4. Document explicitly.

---

## CORR-04 — Channel Scope Badge (RC-(a) partial closure)

**Bug source (Email Vito #2-3 + AUDIT-A):** dashboard cards show `Revenue €25,927` but the underlying parquet only contains GOOGLE_ADEX hourly data. Operators read it as "network revenue" and compare to PBI all-channels totals. The number is GOOGLE_ADEX-only; the label says nothing. Hence `14M PBI vs 10M Sentinel` impressions confusion.

**Fix:** every dashboard card and alert section that aggregates data from a single channel scope MUST render a `<ScopeBadge>` showing the scope (e.g. `GOOGLE_ADEX only`).

### `ScopeBadge` primitive (locked)

**File:** `frontend/src/components/ui/ScopeBadge.tsx`

**Props:**

```ts
import type { ChannelGroup } from '../../types/alert';

interface ScopeBadgeProps {
  channel: ChannelGroup;
  variant?: 'badge' | 'inline';  // default 'badge'
  className?: string;
}
```

**Render contract:**

```tsx
// variant='badge' (default):
<Badge variant="channel-{channel.toLowerCase()}">
  {channel} only
</Badge>

// variant='inline':
<span className="text-xs font-medium text-gray-500">
  Scope: {channel} only
</span>
```

**Locked copy (i18n-keys.ts `SCOPE_BADGE_COPY`):**

| Key | Value |
|-----|-------|
| `SCOPE_BADGE_COPY.suffix` | ` only` (with leading space) — composed as `${channel}${suffix}` |
| `SCOPE_BADGE_COPY.inlinePrefix` | `Scope: ` — used in `variant='inline'` mode |

**Placement matrix:**

| Surface | Channel | Placement |
|---------|---------|-----------|
| `KpiCards` | `GOOGLE_ADEX` | Inside grid container, ABOVE the 4 cards: `<div className="col-span-full flex justify-end mb-2"><ScopeBadge channel="GOOGLE_ADEX" /></div>` |
| `RevenueStatus24h` | `GOOGLE_ADEX` | `CardHeader` flex row, alongside `CardTitle`. Layout: `<div className="flex items-center gap-3"><CardTitle>Revenue Status 24h</CardTitle><ScopeBadge channel="GOOGLE_ADEX" />{availableDates.length > 1 && <select>...}</div>` |
| `RevenueByChannel` | `GOOGLE_ADEX` | `CardHeader` flex row, alongside `CardTitle`. Replaces the existing ad-hoc `<p className="mt-1.5 text-xs text-slate-400">Hourly data — GOOGLE_ADEX only...</p>` paragraph. |
| `RevenueStatusSection` | `alert.channel_group` | `CardHeader` right side, alongside the existing A2 `Drift Detected (A2)` Badge if shown |
| `TriageSection` | `alert.channel_group` | `CardHeader` right side, alongside the existing `TriageBadge` |
| `PublishersPage` | (not applicable — multi-channel by design) | NO ScopeBadge. The TopNDisclaimer covers the equivalent disclosure (top-50, not full network). |

**Anti-pattern (PROIBITO):** Do NOT render `ScopeBadge` on a card that genuinely aggregates ALL channels (e.g. PublishersPage `Total Revenue` summary card aggregates across publishers, which span all channels). The badge is a **scope clarification**, not decoration. If the data scope is "all", omit the badge.

**Why ScopeBadge ≠ ChannelBadge:** `ChannelBadge` renders inside an alert row to show "this alert came from channel X". `ScopeBadge` is a card-level disclosure that the underlying data covers ONLY channel X. Different semantic; same color palette.

---

## CORR-11 — Derived Filter UI (carried into Phase 14 from Phase 13 deferral)

The PublishersPage filter row gains 4 new dropdowns + 1 toggle (in addition to the Phase 12 sell_type and year — W-1 iter-1 reconciliation with ROADMAP success criterion #3):

1. **`month`** — for month-level granularity. Backend `/api/publishers/top` does NOT yet accept month filtering (deferred to v1.4 OPS-02). Phase 14 implements client-side filter over already-fetched data: when a non-`all` month is selected, filter `publishers` array by `publisher.last_active_month === '{year}-{month}'` (or equivalent field; if backend lacks the field, hide rows where the field is missing — show empty-state). **Document explicitly that month filter is client-side stub pending OPS-02.**
2. **`geo_cluster`** — filter by `publisher.dominant_geo`. Already a field in `PublisherSummary`. Client-side filter.
3. **`publisher_tier`** — A/B/C tiering. **Field does not exist yet on `PublisherSummary`.** Phase 14 derives tier client-side from revenue rank: tier A = top 10% by revenue, tier B = next 20%, tier C = rest. Document this heuristic in code + UI-SPEC. Future Phase 18 INTEL-04 will replace with backend-computed tier.
4. **`environment`** — drill-down by environment (WEB / AMP / APP / UNKNOWN — mirrors the `Environment` union in `frontend/src/types/alert.ts` line 6). **Field does not exist on `PublisherSummary` today** — only on `PublisherDetail.environment_breakdown` (per-publisher detail) and `Alert.environment_split`. Phase 14 ships the URL-state + dropdown UI now, with the filter predicate as a NO-OP on the publishers list (same posture as month per OPS-02 deferral). When/if `/api/publishers/top` extends to expose a per-publisher dominant environment field, the predicate flips on without further UI work. Documented as **D-14.05-X frontend-only environment filter on a field that doesn't exist yet on /api/publishers/top — UI ships now, ready for backend extension.** Listed in ROADMAP success criterion #3 as 'environment drill-down'.
5. **`gross_net`** — already specified in CORR-03 above.

**No backend changes in Phase 14.** All four new filters operate on the already-fetched `publishers` array. The Phase 11 backend `sell_type` filter remains the only server-side filter. This is intentional — Phase 14 is "expose the filters" not "ship the backend".

**Tier heuristic (locked, must be greppable):**

```ts
function computePublisherTier(publishers: PublisherSummary[]): Map<string, 'A' | 'B' | 'C'> {
  const sorted = [...publishers].sort((a, b) => b.total_revenue - a.total_revenue);
  const tierA = Math.ceil(sorted.length * 0.10);
  const tierB = Math.ceil(sorted.length * 0.30);
  const map = new Map<string, 'A' | 'B' | 'C'>();
  sorted.forEach((p, i) => {
    if (i < tierA) map.set(p.publisher_id, 'A');
    else if (i < tierB) map.set(p.publisher_id, 'B');
    else map.set(p.publisher_id, 'C');
  });
  return map;
}
```

**Comment required in code:** `// CLIENT-SIDE TIER HEURISTIC — backend-computed tier deferred to Phase 18 INTEL-04. Top 10% by revenue = A, next 20% = B, rest = C.`

---

## CORR-06 — URL State Migration (PublishersPage)

The 6 filter values (`year`, `month`, `sell_type_proxy`, `publisher_tier`, `geo_cluster`, `gross_net`) live in `useSearchParams`, NOT `useState`. Refresh / share / back-button works.

### `useTopPublishersFilters` hook (locked)

**File:** `frontend/src/hooks/useTopPublishersFilters.ts`

**Pattern:** mirror `useAlertFilters.ts` line-by-line. Same `useSearchParams` + `useMemo` + `setFilter` + `clearFilters` structure.

**Return shape:**

```ts
type GrossNetMode = 'gross' | 'net';
type PublisherTier = 'A' | 'B' | 'C' | 'all';

interface PublishersFilters {
  year: number;                 // default 2025
  month: string;                // default 'all', else '01' | '02' | ... | '12'
  sell_type_proxy: SellTypeKey; // default 'all', else canonical sell_type
  publisher_tier: PublisherTier;// default 'all'
  geo_cluster: string;          // default 'all', else 'ITA' | 'ES' | 'LATAM' | 'PT' | 'OTHER'
  environment: EnvironmentKey;  // default 'all', else 'WEB' | 'AMP' | 'APP' | 'UNKNOWN' (W-1 iter-1)
  gross_net: GrossNetMode;      // default 'gross'
}

export function useTopPublishersFilters(): {
  filters: PublishersFilters;
  setFilter: <K extends keyof PublishersFilters>(key: K, value: PublishersFilters[K]) => void;
  clearFilters: () => void;
  hasActiveFilters: boolean;  // true if any filter is non-default
};
```

**Default-value omission rule:** when a filter is set back to its default, the search param is REMOVED from the URL (not set to `'all'`). This keeps the default URL clean (`/publishers` not `/publishers?sell_type_proxy=all&geo_cluster=all&...`).

**Backwards compat with Phase 12 `?sell_type=`:** on hook mount, if `searchParams.get('sell_type')` is set AND `searchParams.get('sell_type_proxy')` is unset, treat the legacy value as `sell_type_proxy`. On next `setFilter('sell_type_proxy', ...)`, write only to `sell_type_proxy` and DELETE `sell_type`. **No 404. No broken bookmarks.**

**No URL state for AlertDetailPage `gross_net` in Phase 14** — alert pages have their own URL (`/alerts/:alertId`); the toggle is local `useState`. Documented in `AlertDetailPage.tsx` comment + this UI-SPEC.

---

## i18n-keys.ts Extension (Phase 14)

Phase 14 adds the following constants/exports to `frontend/src/lib/i18n-keys.ts`. Locked copy.

```ts
/**
 * Phase 14 — UI Labeling + Filter Exposure (CORR-02..06, CORR-11).
 * Closes RC-(a) Top-N disclaimer, RC-(c) gross/net toggle, RC-(f) reference period.
 * UI-SPEC §"i18n-keys.ts Extension".
 */

/**
 * Reference period footnote (CORR-02 + CORR-05). RC-(f) closure.
 * Format produced by `formatTimestampUtc(iso)` in `lib/utils.ts`.
 */
export const REFERENCE_PERIOD_COPY = {
  cardPrefix: 'as of ',
  cardSuffix: ', EUR',
  alertPrefix: 'for ',          // Used by alert detail "for {timestamp} UTC" form
  alertSuffix: '',              // EMPTY — formatTimestampUtc(iso) in lib/utils.ts already produces a string ending in ' UTC' (e.g. '13 Jan 2026 08:57 UTC'). Concatenating alertSuffix=' UTC' would produce double-UTC. Kept exported as '' for forward-compat with a hypothetical future non-UTC formatter (consumer can flip to ' UTC' there without an i18n-keys change).
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
 */
export const TOP_N_DISCLAIMER_COPY = {
  prefix: 'Showing top ',
  suffix: ' publishers — does not represent the full network.',
  linkLabel: 'Network totals',
  linkHref: '/api/metrics/network-totals',
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
```

**Naming convention:** `SCREAMING_SNAKE_CASE` for grouped object constants; `camelCase` for helper functions; `UPPER_CASE` for scalar constants like `REV_SHARE_FACTOR`. Matches Phase 12+13 conventions.

**Single source of truth:** `REV_SHARE_FACTOR = 0.6` lives ONLY here. Components import the constant; no inline `0.6` literals. Verifier greps `* 0\.6\b` and `\* 0\.6` over Phase 14 diff — must return zero matches outside `i18n-keys.ts`.

---

## Copywriting Contract (Phase 14)

| Element | Copy (EN, locked) | Source location | i18n-keys constant |
|---------|-------------------|-----------------|---------------------|
| Reference period (card) | `as of 13 Jan 2026 08:57 UTC, EUR` | `ReferencePeriodFootnote` `card` variant | `REFERENCE_PERIOD_COPY.cardPrefix` + `formatTimestampUtc()` + `cardSuffix` |
| Reference period (alert) | `for 13 Jan 2026 08:57 UTC` | `ReferencePeriodFootnote` `alert` variant | `REFERENCE_PERIOD_COPY.alertPrefix` + `formatTimestampUtc()` (alertSuffix is `''` — formatTimestampUtc already ends in ` UTC`) |
| Channel scope (badge) | `GOOGLE_ADEX only` | `ScopeBadge` `badge` variant | `${channel}${SCOPE_BADGE_COPY.suffix}` |
| Channel scope (inline) | `Scope: GOOGLE_ADEX only` | `ScopeBadge` `inline` variant | `SCOPE_BADGE_COPY.inlinePrefix + ${channel} + SCOPE_BADGE_COPY.suffix` |
| Gross/Net toggle: gross option | `Gross` | `GrossNetToggle` left segment | `GROSS_NET_LABELS.gross` |
| Gross/Net toggle: net option | `Net (post rev-share 60%)` | `GrossNetToggle` right segment | `GROSS_NET_LABELS.net` |
| Top-N disclaimer | `Showing top 50 publishers — does not represent the full network. Network totals` | `TopNDisclaimer` (with link) | `TOP_N_DISCLAIMER_COPY.prefix + N + suffix + linkLabel` |
| Month filter labels | `All months`, `January`...`December` | `<select>` options | `MONTH_LABELS` |
| Geo cluster filter labels | `All countries`, `Italy`, `Spain`, `LATAM`, `Portugal`, `Other` | `<select>` options | `GEO_LABELS` |
| Publisher tier filter labels | `All tiers`, `Tier A`, `Tier B`, `Tier C` | `<select>` options | `PUBLISHER_TIER_LABELS` |
| Empty state — multi-filter | `No publishers match Open Market, Italy, Tier A for 2026.` | PublishersPage empty branch | `emptyPublishersMultiFiltered(activeFilters, year)` |
| Empty state — no filter | `No publisher data available for 2026.` | PublishersPage empty branch | `emptyPublishersMultiFiltered([], year)` |
| `Current Revenue` label (gross mode) | `Current Revenue (gross)` | `RevenueStatusSection` MetricCard label | `Current Revenue ${GROSS_NET_LABELS.grossSuffix}` |
| `Current Revenue` label (net mode) | `Current Revenue (net)` | `RevenueStatusSection` MetricCard label | `Current Revenue ${GROSS_NET_LABELS.netSuffix}` |
| `Total Revenue` summary (PublishersPage) gross | `Total Revenue (gross)` | summary card | `Total Revenue ${GROSS_NET_LABELS.grossSuffix}` |
| `Total Revenue` summary (PublishersPage) net | `Total Revenue (net)` | summary card | `Total Revenue ${GROSS_NET_LABELS.netSuffix}` |
| Destructive actions | (none in Phase 14) | — | — |

**Tone:** present tense, sentence case for sentences (`Showing top 50 publishers...`), title case for labels (`Total Revenue`), ALL CAPS only for channel codes (`GOOGLE_ADEX` — preserved from backend constant). No exclamation marks, no emoji.

**Locale:** EN-only. Currency formatting stays `it-IT` (locked from Phase 12). Date locale `en-GB` (locked from Phase 13). UTC literal in timestamp labels.

---

## States Inventory (Phase 14 surfaces)

### `KpiCards`

| State | Trigger | Visual |
|-------|---------|--------|
| Loading | `isLoading === true` | 4 `<CardSkeleton>` (UNCHANGED from Phase 13) |
| Empty | `!data \|\| data.hours.length === 0` | `KPI_NO_DATA_COPY` (UNCHANGED from Phase 13) |
| Default | data present | NEW: ScopeBadge above grid + 4 MetricCards + ReferencePeriodFootnote below grid |

### `RevenueStatus24h`

| State | Trigger | Visual |
|-------|---------|--------|
| Loading | `isLoading === true` | UNCHANGED from Phase 13 |
| Error | error truthy | UNCHANGED from Phase 13 |
| Empty | data missing | UNCHANGED from Phase 13 |
| Default | data present | NEW: ScopeBadge in header next to title + ReferencePeriodFootnote below chart |

### `RevenueByChannel`

| State | Trigger | Visual |
|-------|---------|--------|
| Loading | UNCHANGED | UNCHANGED |
| Error / no data | UNCHANGED | UNCHANGED |
| Default | data present | NEW: ScopeBadge replaces inline `<p>` note + ReferencePeriodFootnote below chart |

### `RevenueStatusSection` (alert detail Step 1)

| State | Trigger | Visual |
|-------|---------|--------|
| Default (gross) | `grossNet === 'gross'` (default) | 4-card grid with `(gross)` suffix on revenue labels; ScopeBadge in header; GrossNetToggle in header right; ReferencePeriodFootnote below grid |
| Default (net) | `grossNet === 'net'` | Same layout; revenue values × 0.6; `(net)` suffix on labels |
| With margin metrics (A5) | `alert.margin_metrics !== undefined` | UNCHANGED Phase 13 grid + Phase 14 header additions |

### `TriageSection`

| State | Trigger | Visual |
|-------|---------|--------|
| Default (gross) | `grossNet === 'gross'` (lifted from page) | UNCHANGED Phase 12 table; ReferencePeriodFootnote below table; ScopeBadge in header next to TriageBadge |
| Default (net) | `grossNet === 'net'` | Same; Revenue row current/baseline/delta × 0.6; Bacino + Coverage rows UNCHANGED (not currency) |
| Baseline missing | UNCHANGED Phase 12 | UNCHANGED + Phase 14 ReferencePeriodFootnote precedes BASELINE_MISSING_COPY |

### `PublishersPage`

| State | Trigger | Visual |
|-------|---------|--------|
| Loading | `isLoading` | UNCHANGED Phase 12 skeletons |
| Error | `error` truthy | UNCHANGED Phase 12 |
| Default (no filters) | `hasActiveFilters === false` AND `data.length > 0` | NEW: 5 filter dropdowns in CardHeader + GrossNetToggle above summary cards + TopNDisclaimer under page title; otherwise UNCHANGED |
| Default (with filters, results) | `hasActiveFilters === true` AND `data.length > 0` | Same as above; results filtered client-side or server-side per filter contract |
| Empty (no filters) | `data.length === 0` AND `hasActiveFilters === false` | `emptyPublishersMultiFiltered([], year)` → `No publisher data available for {year}.` |
| Empty (with filters) | `data.length === 0` AND `hasActiveFilters === true` | `emptyPublishersMultiFiltered(activeFilters, year)` → `No publishers match X, Y, Z for {year}.` |

---

## Type Contract Updates

### `Alert` type — no new fields in Phase 14

`revenue_gross` already exists (Phase 11). `timestamp` already exists. `channel_group` already exists. Phase 14 only consumes existing fields.

### NEW types in Phase 14

```ts
// frontend/src/hooks/useTopPublishersFilters.ts
export type GrossNetMode = 'gross' | 'net';
export type PublisherTier = 'A' | 'B' | 'C' | 'all';
export type MonthKey = 'all' | '01' | '02' | '03' | '04' | '05' | '06' | '07' | '08' | '09' | '10' | '11' | '12';
export type GeoKey = 'all' | 'ITA' | 'ES' | 'LATAM' | 'PT' | 'OTHER';
export type EnvironmentKey = 'all' | 'WEB' | 'AMP' | 'APP' | 'UNKNOWN';  // W-1 iter-1 — mirrors Environment union from types/alert.ts line 6

export interface PublishersFilters {
  year: number;
  month: MonthKey;
  sell_type_proxy: SellTypeKey;  // imported from i18n-keys.ts
  publisher_tier: PublisherTier;
  geo_cluster: GeoKey;
  environment: EnvironmentKey;   // W-1 iter-1
  gross_net: GrossNetMode;
}
```

### NEW props types

```ts
// frontend/src/components/ui/ReferencePeriodFootnote.tsx
export interface ReferencePeriodFootnoteProps {
  timestamp: string;
  variant?: 'card' | 'inline';
  withCurrency?: boolean;
  className?: string;
}

// frontend/src/components/ui/ScopeBadge.tsx
export interface ScopeBadgeProps {
  channel: ChannelGroup;
  variant?: 'badge' | 'inline';
  className?: string;
}

// frontend/src/components/ui/GrossNetToggle.tsx
export interface GrossNetToggleProps {
  value: GrossNetMode;
  onChange: (mode: GrossNetMode) => void;
  className?: string;
}

// frontend/src/components/ui/TopNDisclaimer.tsx
export interface TopNDisclaimerProps {
  n: number;       // 50 by default in PublishersPage usage
  className?: string;
}
```

### `useTopPublishers` hook signature change

The hook gains an optional `month` argument matching the WIP `94a48cd` baseline that was deferred in Phase 13 (see Phase 13 UI-SPEC §"useTopPublishers signature update" — explicitly deferred to a future phase). Phase 14 IS that future phase.

```ts
export function useTopPublishers(
  year: number,
  limit: number,
  sellType?: string,
  month?: MonthKey,  // NEW — Phase 14
)
```

When `month` is provided and not `'all'`, append `&month=${month}` to the query string. **NOTE:** if backend `/api/publishers/top` does not yet accept `month` (per current Phase 11 contract), the param is ignored server-side; client-side filter still applies. Document explicitly in code: `// Backend month filter pending v1.4 OPS-02 — currently ignored server-side, applied client-side.`

The `queryKey` becomes `['publishers', year, limit, sellType, month]` for cache isolation.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | (none — shadcn not initialized) | not applicable |
| third-party | (none) | not applicable |

No third-party UI registries declared for Phase 14. All four NEW primitives (`ScopeBadge`, `ReferencePeriodFootnote`, `GrossNetToggle`, `TopNDisclaimer`) are bespoke and live in `frontend/src/components/ui/` — same audit posture as Phase 12+13. Safety gate not applicable.

---

## Acceptance Criteria (mechanical, greppable — gsd-ui-checker + gsd-ui-auditor)

A Phase 14 implementation is contract-conforming when ALL the following are true. Each criterion is mechanical (greppable or `test -f`) and closes a specific upstream loop.

### RC-(f) closure: reference period everywhere

1. **`ReferencePeriodFootnote` primitive exists** — `test -f frontend/src/components/ui/ReferencePeriodFootnote.tsx && echo exists` returns `exists`.
2. **`formatTimestampUtc` helper exists** — `grep -n "export function formatTimestampUtc" frontend/src/lib/utils.ts` returns ≥ 1 match.
3. **`formatTimestampUtc` produces the locked format** — unit test or dev smoke: `formatTimestampUtc('2026-01-13T08:57:00Z')` returns the literal string `"13 Jan 2026 08:57 UTC"`.
4. **5 surfaces consume `ReferencePeriodFootnote`** — `grep -l "ReferencePeriodFootnote" frontend/src/components/dashboard/KpiCards.tsx frontend/src/components/dashboard/RevenueStatus24h.tsx frontend/src/components/dashboard/RevenueByChannel.tsx frontend/src/components/alerts/RevenueStatusSection.tsx frontend/src/components/alerts/TriageSection.tsx | wc -l` returns exactly `5`.
5. **No inline `as of` strings in JSX** — `grep -rn '"as of \|>as of ' frontend/src/ --include='*.tsx'` returns matches ONLY in `ReferencePeriodFootnote.tsx`. Zero matches in any other component file.
6. **REFERENCE_PERIOD_COPY constants exist** — `grep -n "REFERENCE_PERIOD_COPY" frontend/src/lib/i18n-keys.ts` returns ≥ 1 match.

### RC-(c) closure: gross/net toggle with explicit label

7. **`GrossNetToggle` primitive exists** — `test -f frontend/src/components/ui/GrossNetToggle.tsx && echo exists` returns `exists`.
8. **`GROSS_NET_LABELS` and `REV_SHARE_FACTOR` constants exist** — `grep -n "GROSS_NET_LABELS\|REV_SHARE_FACTOR" frontend/src/lib/i18n-keys.ts` returns ≥ 2 matches.
9. **REV_SHARE_FACTOR is the only `0.6` revenue multiplier in the codebase** — `git grep -n "\* 0\.6\|\.6 \* " frontend/src/ --include='*.tsx' --include='*.ts' | grep -v "REV_SHARE_FACTOR\|i18n-keys.ts\|opacity\|stopOpacity"` returns ZERO matches. (Excludes Recharts opacity props which legitimately use 0.6.)
10. **`Net (post rev-share 60%)` literal copy renders in the toggle** — `grep -rn "Net (post rev-share 60%)" frontend/src/lib/i18n-keys.ts` returns ≥ 1 match. `grep -rn "Net (post rev-share 60%)" frontend/src/ --include='*.tsx'` returns matches ONLY in JSX that imports `GROSS_NET_LABELS` (no orphan inline strings).
11. **`GrossNetToggle` is used in `RevenueStatusSection` AND `PublishersPage`** — `grep -l "GrossNetToggle" frontend/src/components/alerts/RevenueStatusSection.tsx frontend/src/pages/PublishersPage.tsx | wc -l` returns exactly `2`.

### RC-(a) closure: Top-N disclaimer + ScopeBadge

12. **`TopNDisclaimer` primitive exists** — `test -f frontend/src/components/ui/TopNDisclaimer.tsx && echo exists` returns `exists`.
13. **`TopNDisclaimer` rendered on PublishersPage** — `grep -n "TopNDisclaimer" frontend/src/pages/PublishersPage.tsx` returns ≥ 1 match.
14. **`Showing top 50 publishers` literal copy in i18n-keys** — `grep -n "Showing top " frontend/src/lib/i18n-keys.ts` returns ≥ 1 match.
15. **`ScopeBadge` primitive exists** — `test -f frontend/src/components/ui/ScopeBadge.tsx && echo exists` returns `exists`.
16. **`ScopeBadge` consumed by 5 surfaces** — `grep -l "ScopeBadge" frontend/src/components/dashboard/KpiCards.tsx frontend/src/components/dashboard/RevenueStatus24h.tsx frontend/src/components/dashboard/RevenueByChannel.tsx frontend/src/components/alerts/RevenueStatusSection.tsx frontend/src/components/alerts/TriageSection.tsx | wc -l` returns exactly `5`.
17. **`SCOPE_BADGE_COPY` constants exist** — `grep -n "SCOPE_BADGE_COPY" frontend/src/lib/i18n-keys.ts` returns ≥ 1 match.
18. **No orphan `GOOGLE_ADEX only` inline strings** — `grep -rn '"GOOGLE_ADEX only"' frontend/src/ --include='*.tsx'` returns ZERO matches (composed via `${channel}${suffix}` in ScopeBadge).

### CORR-06 closure: URL state for PublishersPage

19. **`useTopPublishersFilters` hook exists** — `test -f frontend/src/hooks/useTopPublishersFilters.ts && echo exists` returns `exists`.
20. **PublishersPage uses URL state, not local state** — `grep -c "useState" frontend/src/pages/PublishersPage.tsx` returns ZERO for `year` and `sellType` (use `useTopPublishersFilters` instead). `grep -n "useTopPublishersFilters" frontend/src/pages/PublishersPage.tsx` returns ≥ 1 match.
21. **`useSearchParams` invoked in the hook** — `grep -n "useSearchParams" frontend/src/hooks/useTopPublishersFilters.ts` returns ≥ 1 match.
22. **URL state round-trip** — manual smoke: navigate to `/publishers?year=2026&month=04&sell_type_proxy=Open_Market&publisher_tier=A&geo_cluster=ITA&environment=WEB&gross_net=net` and confirm all 6 filter dropdowns render with the matching values. (Visual check; no greppable assertion.)

### CORR-11 closure: derived filter UI present

23. **6 filter `<select>` elements in PublishersPage CardHeader (W-1 iter-1 added environment)** — `grep -c "<select" frontend/src/pages/PublishersPage.tsx` returns at least `6` (sell_type, geo_cluster, publisher_tier, environment, month, year).
24. **`MONTH_LABELS`, `GEO_LABELS`, `PUBLISHER_TIER_LABELS`, `ENVIRONMENT_LABELS` exist in i18n-keys.ts (W-1 iter-1)** — `grep -n "MONTH_LABELS\|GEO_LABELS\|PUBLISHER_TIER_LABELS\|ENVIRONMENT_LABELS" frontend/src/lib/i18n-keys.ts` returns ≥ 4 matches.
25. **`computePublisherTier` heuristic comment present** — `grep -n "CLIENT-SIDE TIER HEURISTIC" frontend/src/pages/PublishersPage.tsx` returns ≥ 1 match.
25a. **`ENVIRONMENT_LABELS` exists in i18n-keys.ts (W-1 iter-1)** — `grep -n "ENVIRONMENT_LABELS" frontend/src/lib/i18n-keys.ts` returns ≥ 1 match. The constant has 5 keys: `all`, `WEB`, `AMP`, `APP`, `UNKNOWN`.
25b. **`environment` `<select>` in PublishersPage CardHeader (W-1 iter-1)** — `grep -c "value={filters.environment}" frontend/src/pages/PublishersPage.tsx` returns 1; `grep -c "setFilter('environment'" frontend/src/pages/PublishersPage.tsx` returns 1.
25c. **`environment` round-trips through URL-state hook (W-1 iter-1)** — navigate to `/publishers?environment=WEB` and confirm the dropdown reflects `Web`. Whitelist: invalid `?environment=99` falls back to `all` silently. Verified by manual smoke or by extending the AC #22 round-trip URL to include `&environment=WEB`.
25d. **`environment` filter is a no-op predicate in Phase 14 (D-14.05-X documentation)** — `grep -n "D-14.05-X\|environment.*no-op\|environment field.*PublisherSummary" frontend/src/pages/PublishersPage.tsx` returns ≥ 1 match (inline comment documenting the deferred predicate).

### Anti-creep guardrails

26. **No new color tokens** — `git diff main..HEAD -- frontend/src/ | grep "^+" | grep -E '"#[0-9a-fA-F]{3,6}"|bg-[a-z]+-[0-9]+|text-[a-z]+-[0-9]+' | grep -vE 'fallback|stopColor|activeDot|stroke:#|fill:#' | sort -u` — every match must already appear in Phase 12 or Phase 13 ship-state. (Reviewer does this manually.)
27. **No new font weights** — `git diff main..HEAD -- frontend/src/ | grep "^+" | grep -oE 'font-(thin|light|extralight|extrabold|black)'` returns ZERO matches.
28. **No new spacing exceptions** — `git diff main..HEAD -- frontend/src/ | grep "^+" | grep -oE 'p[xy]?-[0-9]+\.[0-9]+|m[xy]?-[0-9]+\.[0-9]+|gap-[0-9]+\.[0-9]+'` returns ONLY values already in the Phase 12+13 exceptions list (`px-2.5`, `py-0.5`, `py-1.5`, `mt-1.5`).
29. **No new third-party dependencies** — `git diff main..HEAD -- frontend/package.json | grep "^+" | grep -E '"[a-z@][^"]+":\s*"[\^~]?[0-9]'` returns ZERO matches (no new packages).

### CORR-02 verification

30. **TriageSection consumes `ReferencePeriodFootnote`** — `grep -n "ReferencePeriodFootnote" frontend/src/components/alerts/TriageSection.tsx` returns ≥ 1 match (already covered by AC #4 but listed separately for CORR-02 traceability).

### CORR-05 verification

31. **`UTC` literal appears in `formatTimestampUtc` output** — covered by AC #3.
32. **`EUR` literal appears in `REFERENCE_PERIOD_COPY.cardSuffix`** — `grep -n "EUR" frontend/src/lib/i18n-keys.ts` returns ≥ 1 match.

**Re-verification path:** the `gsd-ui-auditor` executes ACs 1-21, 23-29, 30-32 mechanically via grep / `test -f`. AC 22 is visual (operator opens browser). AC 26 requires reviewer judgment over the diff (cannot be fully greppable).

---

## RC Traceability Table (email-Vito loop closure)

| Email Vito # | Root cause | Phase 14 mechanism | Acceptance criteria |
|--------------|-----------|---------------------|---------------------|
| #1 hourly Revenue AdEx not matching PBI | RC-(a) Top-50 + missing scope label | ScopeBadge on RevenueStatus24h + ReferencePeriodFootnote | AC 1, 4, 5, 15, 16, 18 |
| #2-3 Triage AdEx Jan 12 numbers | RC-(a) channel scope confusion | ScopeBadge on TriageSection + ReferencePeriodFootnote | AC 4, 16, 30 |
| #4a-d Mondadori bacino/fill_rate/eCPM/RPM | RC-(b) Mondadori family — **OUT OF SCOPE for Phase 14**, deferred to Phase 17 CLEAN-02 | n/a | n/a |
| #4e Mondadori revenue €115k vs €188k | **RC-(c) NET/GROSS without label** | GrossNetToggle on RevenueStatusSection + PublishersPage; `Net (post rev-share 60%)` explicit copy | AC 7, 8, 9, 10, 11 |
| #5 Alert current revenue without timeframe | **RC-(f) timestamp/timezone label** | ReferencePeriodFootnote on RevenueStatusSection + TriageSection with `for {timestamp} UTC` form | AC 1, 4, 5, 30 |
| #6 Alert "Google" no timeline | RC-(d) legacy GOOGLE channel — math closed at Phase 12; Phase 14 adds ScopeBadge so operator sees scope explicitly even on legacy alerts | ScopeBadge on RevenueStatusSection + TriageSection | AC 16 |

**Phase 14 closes RC-(a), RC-(c), RC-(f) at the UI layer.** RC-(b) deferred to Phase 17. RC-(d) cosmetic deferred to Phase 17. RC-(e) already closed in Phase 12.

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS — 16 copy contracts declared, EN-only, sentence/title case rules clear, every disclosure string lives in i18n-keys.ts (greppable)
- [ ] Dimension 2 Visuals: PASS — 4 NEW primitives declared (ScopeBadge, ReferencePeriodFootnote, GrossNetToggle, TopNDisclaimer); existing Card/Badge/MetricCard/DataTable inventory locked
- [ ] Dimension 3 Color: PASS — 60/30/10 inherited from Phase 12+13; ScopeBadge reuses ChannelBadge palette (no new accent); GrossNetToggle uses gray-900/gray-50 (existing); anti-creep grep AC #26 in place
- [ ] Dimension 4 Typography: PASS — 4 sizes (12/14/18/24), 2 main weights (medium 500 + bold 700) plus semibold-on-CardTitle exception inherited
- [ ] Dimension 5 Spacing: PASS — Tailwind 4-multiples scale inherited; filter-row uses `flex items-center gap-2` matching Phase 12; new dropdown classes byte-identical to existing year selector
- [ ] Dimension 6 Registry Safety: PASS — no third-party registries; 4 new primitives are bespoke; shadcn deferred with rationale

**Approval:** pending — awaiting `gsd-ui-checker` validation
