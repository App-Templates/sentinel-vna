---
phase: 12
slug: wip-atomic-commits-triage-server-side
status: approved
shadcn_initialized: false
preset: none
created: 2026-04-29
reviewed_at: 2026-04-29
mode: lock-don't-redesign
truth_source: .planning/intel/sentinel-2026-04-28/EMAIL-VITO-2026-04-22.md
root_causes_addressed: [RC-e]
root_causes_partial: [RC-d]
---

# Phase 12 — UI Design Contract

> Visual and interaction contract for Phase 12 (WIP atomic commits A/B/C + Triage server-side + KpiCards weighted avg + i18n keys + PublishersPage sell_type filter).
>
> Phase 12 is **wire-up + heuristic delete + filter affordance**, not new visual design. The frontend WIP working tree (uncommitted as of 2026-04-29) IS the design baseline. This spec **locks** that baseline so it does not drift through Commits A/B/C and the four CORR fixes, and so RC-(e) heuristic creep becomes grep-detectable in future phases.

---

## Scope (what this contract covers)

| Surface | What changes in Phase 12 | Lock-don't-redesign? |
|---------|--------------------------|----------------------|
| `TriageSection.tsx` | Delete client heuristic L29-32 (`revenueRatio*0.95`, `avgCoverage+0.05`, `Math.min(...,0.95)`); read `alert.baseline_bacino` and `alert.baseline_coverage` from API; add baseline-missing disclosure state | YES — table layout, columns, badges, A6/A7 sub-cards UNCHANGED |
| `KpiCards.tsx` (`frontend/src/components/dashboard/`) | i18n keys for the 4 labels (`RPM`, `CTR`, `Viewability`, `Gross Margin`); CORR-08 weighted `avgFillRate` lives in `PublishersPage`, not here | YES — 4-card grid, MetricCard primitive, icon set UNCHANGED |
| `PublishersPage.tsx` | (a) Replace `avgFillRate = simple_average` (line 57) with weighted-by-impressions; (b) add `sell_type` dropdown next to year selector; (c) wire `sell_type` into `useTopPublishers` queryKey + URL | YES — table columns, summary card grid, color tokens UNCHANGED |
| `Alert` type (`types/alert.ts`) | Add `baseline_bacino?: number` and `baseline_coverage?: number` (optional — backend may return null when env_split missing) | N/A — type-only |
| Commit A files (design+i18n infra: `index.css`, `Card`/`Button`/`Badge`/`Skeleton`, `Sidebar`, `main.tsx`, `lib/utils`, `.gitignore`) | Already in working tree from WIP. Phase 12 lands them as one atomic commit | YES — content already final, no edits during phase |
| Commit B files (IT→EN translation: `DocsPage`, `PublisherDetailPage`, layout labels, ~10 files) | Already in working tree. Phase 12 lands them as one atomic commit | YES — content already final |
| Commit C files (`backend/api/routes.py` YoY 7w + complete-day + available_dates; `publisher_routes.py` bacino dedup) | Backend, not UI. Listed for completeness only | N/A — backend |

**Out of scope (deferred to later phases — DO NOT touch):**
- CORR-02 reference-period label on alert metric cards → Phase 14
- CORR-03 gross/net side-by-side toggle → Phase 13
- CORR-04 channel scope badge ("GOOGLE_ADEX only") on dashboard cards → Phase 14
- CORR-05 timestamp/timezone label on every metric card → Phase 14
- CORR-06 PublishersPage filter state in URL (full migration to `useSearchParams`) → Phase 14
- CORR-07 diagnostic empty states on chart components → Phase 15
- CORR-10 ErrorBoundary on chart components → Phase 15
- CORR-11 derived filter UI (geo, environment, publisher tier, gross/net) → Phase 14
- Mondadori publisher_family aggregation (RC-b) → Phase 13
- WIP Commit D (dashboard date navigation) → Phase 13
- WIP Commit E (Vercel static export) → Phase 16

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none (Tailwind v4 CSS-first via `@theme` directive in `frontend/src/index.css`) |
| Preset | not applicable |
| Component library | bespoke primitives in `frontend/src/components/ui/` (Card, Button, Badge, MetricCard, DataTable, Skeleton, AlertBox, DeltaIndicator) |
| Icon library | `lucide-react@^0.563.0` |
| Variant engine | `class-variance-authority@^0.7.1` (used by `Badge`) |
| Class merge | `clsx` + `tailwind-merge` via `cn()` helper in `lib/utils.ts` |
| Font | `'Inter', system-ui, -apple-system, sans-serif` (set on `body` in `index.css`) |
| Currency / number locale | `Intl.NumberFormat('it-IT', currency: 'EUR', 0 fraction)` — see `formatCurrency` in `lib/utils.ts`. Locked. Phase 12 does NOT change number formatting. |

**shadcn gate decision:** No shadcn initialization in Phase 12. The project ships its own primitives that are already used across 9 pages. Introducing shadcn now would (a) violate lock-don't-redesign, (b) bloat a phase whose explicit purpose is heuristic deletion + WIP commit landing, (c) duplicate primitives that already work. Re-evaluate at Phase 16 (Vercel decision) or v1.4 milestone planning.

**i18n decision (WIP-03 IT→EN):** The WIP working tree is doing IT→EN as **plain string replacement** (no library). Phase 12 inherits that approach for Commit B. CORR-09 ("i18n keys for KpiCards") is interpreted in this phase as: introduce a single `frontend/src/lib/i18n-keys.ts` constant module exporting the EN strings (`KPI_LABELS.RPM = 'RPM'`, etc.) so future Phase 14 work can swap the constant module for a real i18n library (`react-intl`, `react-i18next`, `next-intl`) without touching component JSX. **Rationale:** the planner needs the KpiCards labels readable from one canonical place to enforce CORR-09; introducing a full i18n runtime in this phase would explode scope.

---

## Spacing Scale

Inherited from Tailwind v4 default scale (multiples of 4px). Locked to the subset already used by the codebase:

| Token | Tailwind class | Value | Usage in Phase 12 surfaces |
|-------|----------------|-------|---------------------------|
| xs | `gap-1`, `p-1` | 4px | Icon margin (DirectionIcon in TriageSection) |
| sm | `gap-2`, `px-2`, `py-1` | 8px | Badge padding (Badge.tsx px-2.5 py-0.5 = 10/2 — accept existing exception) |
| md | `gap-4`, `p-4`, `px-4` | 16px | Default card padding inner; CardContent `px-6 py-4` (24/16, accept) |
| lg | `gap-6`, `px-6`, `py-4` | 24px | CardHeader/CardContent horizontal padding |
| xl | `space-y-6`, `gap-6` | 24-32px | PublishersPage section gap; Triage card vertical rhythm |
| 2xl | `mt-8` | 32px | (not used in Phase 12 surfaces) |

**Exceptions accepted (do not "fix" in Phase 12):**
- `Badge` uses `px-2.5 py-0.5` (10/2) — existing convention across 8 badge variants. Out of scope.
- `CardHeader` uses `px-6 py-4` (24/16) and `CardContent` uses `px-6 py-4`. Asymmetry intentional (24 horizontal pulls eye in, 16 vertical packs density). Locked.
- Top selector in `PublishersPage` uses `px-3 py-1.5` for the year `<select>` (12/6). Locked. The new `sell_type` `<select>` MUST use the same `px-3 py-1.5` so the two filters align horizontally.

---

## Typography

Locked subset of Tailwind defaults — declared exactly four sizes and two weights:

| Role | Tailwind class | Size | Weight | Line Height | Used by |
|------|----------------|------|--------|-------------|---------|
| Body / table cell | `text-sm` | 14px | `font-medium` (500) for labels, default (400) for values | 1.5 (Tailwind default) | TriageSection table cells, KpiCards labels via `MetricCard label="..."` |
| Caption / hint | `text-xs` | 12px | `font-normal` (400) | 1.5 | PublishersPage trend column, sub-labels ("Top X publishers"), DirectionIcon adjacent text |
| Heading (CardTitle) | `text-lg` | 18px | `font-semibold` (600) | 1.2 (Tailwind default for `lg` headings ~ 1.4, accept) | `CardTitle` ("Step 2: Triage") |
| Display (KPI value, page title, summary card value) | `text-2xl` | 24px | `font-bold` (700) | 1.2 | `MetricCard` value, PublishersPage summary cards `text-2xl font-bold`, page title `<h1 className="text-xl font-bold">` (accept `text-xl` 20px as page-title; KPI value 24px) |

**Two weights total:** `font-medium` (500) for column headers + small labels, and `font-bold` (700) for big numbers. `font-semibold` (600) is permitted ONLY on `CardTitle` (existing convention). `font-normal` is the implicit default (400) for body values. **No new weights introduced in Phase 12.**

**Number formatting in cells:** `font-mono` Tailwind class on numeric table cells (existing convention in TriageSection + PublishersPage). Phase 12 MUST keep `font-mono` on:
- TriageSection `Current` / `Baseline` / `Delta` columns (existing).
- PublishersPage Revenue / Bacino / Share % / eCPM / RPM / Coverage / Fill Rate / Trend 4w cells (existing).
- The new `baseline_bacino` value when shown — so it visually matches the `Bacino (Impressions)` current value.

---

## Color

60 / 30 / 10 inherited from `index.css` `@theme` block + Tailwind palette. Locked.

| Role | Token / class | Hex | Usage in Phase 12 surfaces |
|------|---------------|-----|---------------------------|
| Dominant (60%) — surface | `--color-bg-primary` / `bg-white` | `#ffffff` | Page background, Card surfaces, table rows |
| Secondary (30%) — cards / chrome | `--color-bg-card` / `bg-gray-50`, `border-gray-200` | `#f9fafb`, `#e5e7eb` | TriageSection thead row (`bg-gray-50`), Card border, table row dividers `border-gray-100` |
| Sidebar (separate plane, also 30% bucket) | `--color-bg-sidebar` / `bg-gray-900` | `#111827` | Sidebar (`Sidebar.tsx`) — NOT touched in Phase 12 |
| Accent (10%) — semantic only | (see below — no single accent) | (varied) | Severity, Triage, Channel badges; delta direction colors |
| Destructive | `text-red-600` / `bg-red-100 text-red-800` | `#dc2626` / `#fee2e2` / `#991b1b` | Delta column when `direction === 'down'`; SeverityBadge `P0`; coverage-zero "Current Coverage" emphasis |

**Accent reserved-for list (explicit; never repurpose):**
- Severity badge color: `--color-severity-p0` `#ef4444` (P0 red), `--color-severity-p1` `#f97316` (P1 orange), `--color-severity-p2` `#eab308` (P2 yellow). Used ONLY by `SeverityBadge`.
- Triage color: `--color-triage-traffic` `#6366f1` (indigo, also `text-indigo-500` on `GitBranch` icon in TriageSection title), `--color-triage-coverage` `#f59e0b` (amber), `--color-triage-mixed` `#f43f5e` (rose), `--color-triage-revenue` `#64748b` (slate). Used ONLY by `TriageBadge` and the icon next to "Step 2: Triage".
- Metric direction: `--color-metric-positive` `#22c55e` (green-600 in cells), `--color-metric-negative` `#ef4444` (red-600 in cells), `--color-metric-neutral` `#6b7280` (gray-400 for `flat` direction). Used ONLY by direction arrows + delta cells in TriageSection (and existing PublishersPage trend column).
- Channel badge: blue/teal/orange/purple/cyan/red/amber `bg-X-50 text-X-700 border-X-200` — used ONLY by `ChannelBadge`.
- Status badge: blue (OPEN), purple (ACK), green (RESOLVED), gray (SNOOZED) — used ONLY by `StatusBadge`.
- A6 cause sub-card: amber-200/50/600/800/900 — used ONLY in `TriageSection.tsx` A6 conditional render. Locked, do not generalize.
- A7 pricing-rule sub-card: purple-200/50/600/800/900 — used ONLY in `TriageSection.tsx` A7 conditional render. Locked.

**Anti-pattern (PROIBITO in Phase 12):** Do NOT introduce new accent colors when wiring `baseline_bacino`/`baseline_coverage`. The new values render in the existing baseline column with the existing `text-gray-500 font-mono` styling. The values themselves change; the visual treatment does not.

**Baseline-missing disclosure state (NEW behaviour, locked styling):**
When `alert.baseline_bacino == null` OR `alert.baseline_coverage == null` (backend returned null because `environment_split_json` missing or unparseable — see `backend/api/routes.py` `_compute_baseline_from_env_split` returns `(None, None)` on every failure path):
- Bacino baseline cell renders the literal string `"—"` (em-dash, U+2014), `text-gray-400 font-mono` (one shade lighter than normal `text-gray-500`).
- Coverage baseline cell renders `"—"`, `text-gray-400 font-mono`.
- Delta cell renders `"—"`, `text-gray-400 font-mono` (no color, since direction is undefined).
- Direction column renders `<Minus size={14} className="text-gray-400" />` (the existing `flat` icon, NOT a new icon).
- A small caption row appears UNDER the table (inside the same `CardContent`, NOT inside a new card), styled `text-xs text-gray-500 mt-3`, copy: `Baseline unavailable for this alert (no environment split data).`

**Anti-heuristic-creep guardrail:** TriageSection MUST NOT compute baseline values from any other field. The grep `revenueRatio\s*\*\s*0\.95\|avgCoverage\s*\+\s*0\.05\|Math\.min.*0\.95` MUST return zero matches in `frontend/src/components/alerts/TriageSection.tsx` after Phase 12 lands. This is an explicit acceptance criterion for the phase verifier (RC-e closure at UI layer).

---

## Component Inventory (Phase 12 surfaces)

| Component | File | Phase 12 change | Primitive used |
|-----------|------|-----------------|----------------|
| `TriageSection` | `frontend/src/components/alerts/TriageSection.tsx` | Delete L29-32 heuristic; read `alert.baseline_bacino` + `alert.baseline_coverage`; add baseline-missing disclosure caption | `Card`, `CardHeader`, `CardTitle`, `CardContent`, `TriageBadge`, `lucide:GitBranch/ArrowUp/ArrowDown/Minus/AlertTriangle/TrendingUp` |
| `KpiCards` | `frontend/src/components/dashboard/KpiCards.tsx` | Replace 4 hardcoded EN strings with imports from new `lib/i18n-keys.ts` (CORR-09 prep) | `MetricCard`, `CardSkeleton`, `lucide:DollarSign/MousePointer/Eye/Percent` |
| `PublishersPage` | `frontend/src/pages/PublishersPage.tsx` | Replace L57 `avgCoverage = data.reduce / data.length` with weighted-by-impressions (CORR-08); add `sell_type` `<select>` next to year `<select>`; wire to `useTopPublishers` | `Card`, `CardHeader`, `CardTitle`, `CardContent`, `DataTable`, `Skeleton`/`CardSkeleton`/`TableSkeleton`, `lucide:BarChart3` |
| `i18n-keys.ts` | `frontend/src/lib/i18n-keys.ts` (NEW file, ~30 lines) | New module exporting EN-only constants for KPI labels, sell_type filter labels, baseline-missing copy | none |
| `Alert` type | `frontend/src/types/alert.ts` | Add `baseline_bacino?: number` and `baseline_coverage?: number` (optional, server may return null) | none |
| `useTopPublishers` | `frontend/src/api/client.ts` (L231) | Add `sellType?: string` arg → propagate to query string `&sell_type=Open_Market` ; include in `queryKey` for cache isolation | `useQuery` |

**No new primitives.** Phase 12 must NOT add a Select/Dropdown primitive. The existing `<select>` element from `PublishersPage.tsx` L240-245 (year selector) is the locked pattern; the `sell_type` selector copies that styling byte-for-byte.

---

## Sell Type Filter UI (PublishersPage — NEW affordance)

**Decision: dropdown, not badge, not URL-state-only.** Rationale (driven by RC-a + email Vito #4a/4e):

- A badge would be passive (display-only) and would not invoke the Phase 11 server-side filter.
- A URL-state-only filter (deferred to Phase 14 CORR-06) would not surface the filter to operators who land on the page with no URL params — the most common discovery flow today.
- A dropdown that defaults to "All sell types" and offers `Open_Market` / `Header_Bidding` / `Direct` / `Deal` / `Other` matches PBI's "all sell type vs Open Market" toggle that Vito explicitly references in the email (`€188k all sell type vs €90k Open Market`).

**Visual specification (locked):**

Place the new `<select>` to the LEFT of the existing year `<select>`, inside the same `<div className="flex items-center justify-between">` in `<CardHeader>`. Both selects sit on the right side; the title `"Top {N} Publishers by Revenue"` stays on the left.

```
+----------------------------------------------------------+
| CardHeader                                               |
|  [Top 35 Publishers by Revenue]   [All sell types ▾] [2025 ▾]
+----------------------------------------------------------+
```

Both selects MUST share the exact existing classes:
```
className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
```

Spacing between the two selects: `gap-2` (8px) — wrap them in `<div className="flex items-center gap-2">`.

**Default value:** `"all"` (rendered label `"All sell types"`). Maps to `sellType=undefined` in the hook → no `sell_type=` query param sent → existing 200 backwards-compat path (verified by Phase 11 Plan 03 D-11.03-03).

**Option list (locked, copy verbatim from `lib/i18n-keys.ts`):**
| Value | Label |
|-------|-------|
| `all` | `All sell types` |
| `Open_Market` | `Open Market` |
| `Header_Bidding` | `Header Bidding` |
| `Direct` | `Direct` |
| `Deal` | `Deal` |
| `Other` | `Other` |

**Interaction:**
- Selecting an option triggers `useTopPublishers(year, 35, sellType)`. `react-query` re-fetches due to `queryKey: ['publishers', year, limit, sellType]`.
- During fetch, the existing `Skeleton` loading state is reused.
- On success, the table re-renders with filtered rows.
- On `503` (column guard from Phase 11 Plan 03), the existing `error` branch (L43-49) renders `Failed to load publisher data.` — for Phase 12, do NOT differentiate 503 vs 5xx; that's deferred to Phase 14.
- On `400` (whitelist violation, only possible if a developer sends a non-canonical value via URL hack — not via the dropdown), same `error` branch.
- The `summary cards row` (L195-231) recomputes from the filtered `data` automatically — no extra wiring needed.

**No URL state in Phase 12.** Selecting a sell_type does NOT update `window.location` or `?sell_type=...`. This is intentional — full URL-state migration is CORR-06 / Phase 14 scope. Phase 12 only adds the affordance + hook wiring.

---

## Copywriting Contract

| Element | Copy (EN, locked) | Source location |
|---------|-------------------|-----------------|
| Primary CTA — TriageSection | (no CTA — Step 2 of a 7-step alert detail view, read-only) | n/a |
| Primary CTA — PublishersPage | (no CTA — list view, click-row to navigate) | n/a |
| Empty state — PublishersPage | `No publisher data available for {year}.` | `PublishersPage.tsx` L249-251 (existing — keep as-is, do NOT add sell_type to the message) |
| Empty state — PublishersPage with sell_type filter | `No publishers match {sellType label} for {year}.` (NEW — render only when `data.length === 0 && sellType !== 'all'`) | NEW — derive from `i18n-keys.ts` |
| Error state — PublishersPage | `Failed to load publisher data.` | L46 (existing — keep) |
| Loading state — PublishersPage | (skeleton — no copy) | L22-40 (existing) |
| Error state — TriageSection | (none — section renders inside `AlertDetailPage` which owns alert-load errors) | n/a |
| Baseline-missing — TriageSection | `Baseline unavailable for this alert (no environment split data).` (NEW caption row) | NEW — derive from `i18n-keys.ts` |
| KpiCards labels (CORR-09) | `RPM`, `CTR`, `Viewability`, `Gross Margin` | NEW: `i18n-keys.ts` `KPI_LABELS` |
| sell_type filter labels | (see Option list table above) | NEW: `i18n-keys.ts` `SELL_TYPE_LABELS` |
| Destructive actions | (none in Phase 12 — Triage section is read-only; PublishersPage is list-only) | n/a |

**Tone:** present tense, sentence case for body copy ("Baseline unavailable for this alert..."), title case for short labels ("All sell types", "Top 35 Publishers"). Match existing Sentinel copy register — no exclamation marks, no emoji except the existing country flags in PublishersPage `country` column (L82, locked).

**Locale rule:** All Phase 12 NEW copy is EN-only (Commit B is the IT→EN migration commit). Currency formatting stays `it-IT` locale (`formatCurrency` in `lib/utils.ts`) — that's a number-formatting choice, not copy. Do not change `formatCurrency` in Phase 12.

---

## States Inventory (per surface)

### TriageSection (`AlertDetailPage` → "Step 2")

| State | Trigger | Visual |
|-------|---------|--------|
| Default | `alert.baseline_bacino` and `alert.baseline_coverage` both populated | 3 rows (Revenue, Bacino, Coverage) with current/baseline/delta/direction. A6 sub-card shown if `alert_rule==='A6'`. A7 sub-card shown if `alert_rule==='A7'`. |
| Baseline missing | Either `baseline_bacino` OR `baseline_coverage` is `null`/`undefined` | Bacino + Coverage rows show `"—"` in baseline + delta cells, direction `Minus` icon `text-gray-400`. Caption row appears under the table: `Baseline unavailable for this alert (no environment split data).` |
| Loading | (parent `AlertDetailPage` owns loading; TriageSection only renders when `alert` is defined) | n/a — no skeleton inside TriageSection |
| Error | (parent owns) | n/a |

### KpiCards (`DashboardPage`)

| State | Trigger | Visual |
|-------|---------|--------|
| Default | `useRevenueStatus24h` returns data | 4 MetricCards in `grid grid-cols-2 lg:grid-cols-4` |
| Loading | `isLoading === true` | 4 `CardSkeleton` in same grid |
| Missing extended fields | `data.rpm` etc. undefined | Render `0` (existing fallback `?? 0`). Phase 12 does NOT introduce empty-state copy here — that's Phase 14 CORR-05 |

### PublishersPage

| State | Trigger | Visual |
|-------|---------|--------|
| Default | `data.length > 0` and `error === undefined` | Page title + 5-card summary row + DataTable. Year + sell_type selectors in CardHeader. |
| Loading | `isLoading === true` | Skeleton rows: title skeleton + 5 CardSkeleton + Card with TableSkeleton (existing) |
| Error | `error` truthy | `Failed to load publisher data.` centered, `text-red-500` (existing) |
| Empty (no sell_type filter) | `data.length === 0` AND `sellType === 'all'` | Existing copy: `No publisher data available for {year}.` (centered, `text-gray-500`) |
| Empty (with sell_type filter) | `data.length === 0` AND `sellType !== 'all'` | NEW copy: `No publishers match {sellType label} for {year}.` (same centering + color as existing empty state) |

---

## Type Contract Updates (lock)

`frontend/src/types/alert.ts` `Alert` interface gains:

```ts
export interface Alert {
  // ... existing fields ...

  // Phase 11 API-03 server-side baselines (Phase 12 wires consumer)
  baseline_bacino?: number;       // null when environment_split_json missing/unparseable
  baseline_coverage?: number;     // null when environment_split_json missing/unparseable
}
```

Both fields are **optional** to match backend's `(None, None)` failure-path return contract (verified by Phase 11 Plan 02 D-11.02-02). TriageSection MUST handle the `undefined` case via the baseline-missing disclosure state above.

`useTopPublishers` signature gains:

```ts
export function useTopPublishers(
  year = 2025,
  limit = 35,
  sellType?: string,  // 'Open_Market' | 'Header_Bidding' | 'Direct' | 'Deal' | 'Other' | undefined (= all)
)
```

`queryKey` becomes `['publishers', year, limit, sellType]`. Query string construction: append `&sell_type=${sellType}` only when `sellType !== undefined && sellType !== 'all'`.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | (none — shadcn not initialized) | not applicable |
| third-party | (none) | not applicable |

No third-party UI registries declared for Phase 12. All UI primitives are bespoke and live in `frontend/src/components/ui/` — already audited via the existing codebase.

---

## Acceptance Criteria (gsd-ui-checker + gsd-ui-auditor)

A Phase 12 implementation is contract-conforming when ALL the following are true:

1. **RC-(e) closed at UI layer** — `git grep` of `revenueRatio\s*\*\|avgCoverage\s*\+\s*0\.05\|Math\.min.*0\.95` in `frontend/src/components/alerts/TriageSection.tsx` returns ZERO matches.
2. **TriageSection reads server fields** — `alert.baseline_bacino` and `alert.baseline_coverage` appear in the Bacino + Coverage baseline cell render path. Verified by static `grep -n "alert.baseline_bacino\|alert.baseline_coverage" frontend/src/components/alerts/TriageSection.tsx` returning ≥ 2 lines.
3. **Baseline-missing state renders** — for an alert payload where either `baseline_bacino` or `baseline_coverage` is `null`, the Bacino + Coverage baseline cells show `"—"` and the caption `Baseline unavailable for this alert (no environment split data).` appears.
4. **Type contract** — `frontend/src/types/alert.ts` `Alert` interface contains `baseline_bacino?: number` and `baseline_coverage?: number`.
5. **CORR-08 weighted avgFillRate** — `PublishersPage.tsx` `avgCoverage` (or its renamed weighted equivalent) is computed as `sum(p.avg_coverage * p.total_impressions) / sum(p.total_impressions)`, NOT as a simple mean. Manual verification: against the 35 Mondadori-feb fixture, the weighted value differs from the simple mean by ≥ 1 ppt.
6. **CORR-09 i18n keys** — `frontend/src/lib/i18n-keys.ts` exists. `KpiCards.tsx` imports `KPI_LABELS` (or equivalent) from this module instead of hardcoding `"RPM"`/`"CTR"`/`"Viewability"`/`"Gross Margin"` in JSX.
7. **PublishersPage sell_type dropdown** — A `<select>` with 6 options (`all` + 5 canonical sell_types) appears in `<CardHeader>` to the LEFT of the year selector, sharing the exact `className` of the existing year selector. Selecting a non-`all` value triggers a re-fetch with `?sell_type=...` query param. Empty result with non-`all` selection shows `No publishers match {label} for {year}.`
8. **No new accent colors** — `git diff` of Phase 12's three component files shows no introduction of color tokens outside the locked palette in `index.css` `@theme`. Verified by checker grep of new `bg-` / `text-` classes.
9. **No new font weights** — only `font-medium` (500), `font-semibold` (600), `font-bold` (700), and the implicit `font-normal` (400) appear in Phase 12 diffs. No `font-light`, `font-thin`, `font-extrabold`, `font-black`.
10. **Spacing locked** — selector classes match `px-3 py-1.5`; both PublishersPage selectors aligned via `flex items-center gap-2`.
11. **Two atomic commits land Commit A and Commit B** — `git log` after Phase 12 shows exactly one commit titled along the lines of `feat(ui): land design system + i18n infrastructure (WIP-02 Commit A)` and one `feat(ui): translate UI content from IT to EN (WIP-03 Commit B)`. Commit C is backend-only (no UI surface diff). The four CORR fixes (CORR-01/08/09 + sell_type wire) MAY land as separate atomic commits OR folded into Commit A — planner decides; this UI contract is silent.
12. **Heuristic-creep grep passes** — `git grep -n "\* 0\.95\|+ 0\.05\|+ 0\.04" frontend/src/` returns ZERO matches inside any Triage* or Kpi* component (catches future regressions of the same shape).

**Re-verification path:** the `gsd-ui-auditor` (run after execute) executes greps 1, 2, 8, 9, 12 mechanically. The remaining checks are visual (auditor uses the running app on `localhost:5173` after `pnpm dev` / `npm run dev`).

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS — 8 copy strings declared, EN-only, sentence/title case rules clear
- [ ] Dimension 2 Visuals: PASS — no new primitives; existing Card/Badge/MetricCard/DataTable inventory locked
- [ ] Dimension 3 Color: PASS — 60/30/10 locked from `@theme`, accent reserved-for list explicit, anti-creep guardrail in place
- [ ] Dimension 4 Typography: PASS — 4 sizes (12/14/18/24), 2 main weights (medium 500 + bold 700) plus semibold-on-CardTitle exception
- [ ] Dimension 5 Spacing: PASS — Tailwind 4-multiples scale, exceptions documented, selector alignment locked
- [ ] Dimension 6 Registry Safety: PASS — no third-party registries declared; shadcn deferred with rationale

**Approval:** pending — awaiting `gsd-ui-checker` validation
