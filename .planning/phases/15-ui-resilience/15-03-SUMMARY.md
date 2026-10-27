---
phase: 15
plan: 03
subsystem: frontend/components
tags: [ui-resilience, corr-07, corr-10, error-boundary, i18n-keys, chart-wiring, wave-2]
dependency_graph:
  requires:
    - frontend/src/lib/i18n-keys.ts (CHART_EMPTY_COPY exports — Wave 1 Plan 15-01 commit `2bbfccd`)
    - frontend/src/components/primitives/ChartErrorBoundary.tsx (Wave 1 Plan 15-02 commit `38144e6`)
    - .planning/phases/15-ui-resilience/15-UI-SPEC.md §"Empty-State Specification" lines 186-219 + §"Chart wrapping pattern" lines 174-181
  provides:
    - "RevenueTrendChart consumes CHART_EMPTY_COPY.revenueTrend in empty-state branch"
    - "EnvironmentBarChart consumes CHART_EMPTY_COPY.environmentBar in empty-state branch"
    - "GeoBreakdownPieChart consumes CHART_EMPTY_COPY.geoBreakdown in empty-state branch"
    - "RevenueStatusSection wraps RevenueTrendChart in <ChartErrorBoundary height={280}>"
    - "EnvironmentSplitSection wraps EnvironmentBarChart in <ChartErrorBoundary height={280}>"
    - "GeoBreakdownSection wraps GeoBreakdownPieChart in <ChartErrorBoundary height={260}>"
  affects:
    - .planning/phases/15-ui-resilience/15-04-PLAN.md (manual regression UAT consumer — D-15.03 prop injection now actionable)
    - ROADMAP.md Phase 15 SC #1 + #2 (closed by Wave 2; SC #3 verified in Plan 15-04)
tech-stack:
  added: []
  patterns:
    - "Named-import consumption of i18n-keys SSoT (D-15.05 — zero inline JSX strings post-phase)"
    - "Wrapper at parent composition layer (D-15.02 — boundary lives at call site, not inside chart file)"
    - "Per-chart height matching (280/280/260) so fallback box visual footprint matches chart"
    - "Anti-pattern guards verified via grep (no try/catch added inside chart render — UI-SPEC AC #14)"
    - "Single-quote, no-semicolon import style (matches existing convention in all 6 files)"
key-files:
  created: []
  modified:
    - frontend/src/components/charts/RevenueTrendChart.tsx
    - frontend/src/components/charts/EnvironmentBarChart.tsx
    - frontend/src/components/charts/GeoBreakdownPieChart.tsx
    - frontend/src/components/alerts/RevenueStatusSection.tsx
    - frontend/src/components/alerts/EnvironmentSplitSection.tsx
    - frontend/src/components/alerts/GeoBreakdownSection.tsx
decisions:
  - "D-15.02 (carried) — Wrapper at call site (parent), NOT inside chart file. Wave 2 lands the wraps in 3 alert-section files; chart components remain pure render functions."
  - "D-15.05 (carried) — i18n-keys SSoT for chart-area diagnostic copy. 3 inline strings deleted from chart files; `CHART_EMPTY_COPY.<key>` consumed instead."
  - "D-15.07 (carried) — camelCase keys (revenueTrend, environmentBar, geoBreakdown) consumed verbatim from Plan 15-01."
  - "D-15.03-IMPL — Plan 15-04 (manual regression UAT) is now actionable: a verifier can pass `data={null as any}` or `data=[{ timestamp: null, revenue: NaN }]` at any of the 3 wrapped call sites and visually confirm the boundary fallback localizes the failure."
  - "D-15-03-IMPL-01 (this plan, gotcha) — GeoBreakdownPieChart wraps at height={260} (NOT 280). Per chart prop signature line 56 (`height = 260`) and UI-SPEC line 311 + plan T2 explicit override. Two ACs verify: (a) `grep -B1 ... | grep height={260}` returns 1, (b) anti-check for `height={280}` near GeoBreakdown wrap returns 0."
  - "D-15-03-IMPL-02 (this plan, anti-creep) — No try/catch added inside chart render functions. AC #14 grep returns 0 for all 3 chart files. Boundary catches throws at React tree boundary; internal try/catch would mask the error from the boundary."
  - "D-15-03-IMPL-03 (this plan, scope discipline) — No fallbackMessage prop passed at any call site. Default `CHART_ERROR_COPY.generic` applies per Plan 15-02 contract. Per-chart custom messages deferred (out of scope for Phase 15)."
metrics:
  duration_minutes: 2
  tasks_completed: 2
  files_modified: 6
  files_created: 0
  lines_added: 18
  lines_deleted: 6
  completed_date: 2026-05-02
---

# Phase 15 Plan 03: 3-Chart Wiring + 3-Section ChartErrorBoundary Wraps Summary

**One-liner:** Closed CORR-07 (3 chart files now consume `CHART_EMPTY_COPY.{revenueTrend|environmentBar|geoBreakdown}` from the Wave 1 i18n-keys SSoT, with old inline English strings deleted) and CORR-10 (3 alert-section files import `ChartErrorBoundary` from the Wave 1 primitive and wrap each chart at its call site at the chart's default height — 280 for revenue trend + environment bar, 260 for geo pie — localizing render-throw failures so adjacent sections remain functional) atomically across 6 files in 2 R-03 atomic commits, with TS compile + Vite build clean (2460 modules, +1 vs Wave 1).

## What Shipped

### Task 1 commit `99ba861`: 3 chart files (CORR-07)

Each of the 3 chart files received exactly TWO edits:
1. New named import: `import { CHART_EMPTY_COPY } from '../../lib/i18n-keys'` (single-quote, no-semicolon — matches existing convention in each file)
2. Empty-state `<p>` inner text swap: literal English string → `{CHART_EMPTY_COPY.<camelCaseKey>}`

| File | Before (inline string) | After (i18n-keys consumer) |
|---|---|---|
| `RevenueTrendChart.tsx` | `<p ...>No revenue trend data available for this alert period.</p>` | `<p ...>{CHART_EMPTY_COPY.revenueTrend}</p>` |
| `EnvironmentBarChart.tsx` | `<p ...>No environment data available.</p>` | `<p ...>{CHART_EMPTY_COPY.environmentBar}</p>` |
| `GeoBreakdownPieChart.tsx` | `<p ...>No geographic data available.</p>` | `<p ...>{CHART_EMPTY_COPY.geoBreakdown}</p>` |

**Diff stat:** `3 files changed, 6 insertions(+), 3 deletions(-)` — exactly 1 import + 1 string swap per file, zero collateral changes.

**Locked invariants verified by AC:**
- Container `<div style={{ width: '100%', height }} className="flex items-center justify-center">` — byte-identical pre/post.
- `<p>` className `text-sm text-gray-400` — byte-identical pre/post.
- Function exports `export function RevenueTrendChart(…)` / `EnvironmentBarChart(…)` / `GeoBreakdownPieChart(…)` — preserved.
- Default heights (280, 280, 260) — preserved on each chart's prop signature.
- No try/catch added (AC #14 grep returns 0).
- No new `bg-X-Y` Tailwind class (AC #18 anti-creep grep returns 0).

### Task 2 commit `9cb0288`: 3 alert-section files (CORR-10)

Each of the 3 alert-section files received exactly TWO edits:
1. New named import: `import { ChartErrorBoundary } from '../primitives/ChartErrorBoundary'` (placed immediately after the existing chart import — co-locates boundary with wrapped component)
2. Chart JSX wrap: `<ChartErrorBoundary height={…}>…</ChartErrorBoundary>`

| File | Before (bare chart) | After (boundary-wrapped) | Height |
|---|---|---|---|
| `RevenueStatusSection.tsx` (line 141 → 142-144) | `<RevenueTrendChart data={trendData} />` | `<ChartErrorBoundary height={280}>` … `</ChartErrorBoundary>` | **280** |
| `EnvironmentSplitSection.tsx` (line 122 → 123-125) | `<EnvironmentBarChart data={environmentSplit} />` | `<ChartErrorBoundary height={280}>` … `</ChartErrorBoundary>` | **280** |
| `GeoBreakdownSection.tsx` (line 84 → 85-87) | `<GeoBreakdownPieChart data={safeGeoBreakdown} />` | `<ChartErrorBoundary height={260}>` … `</ChartErrorBoundary>` | **260** ⚠ NOT 280 |

**Diff stat:** `3 files changed, 12 insertions(+), 3 deletions(-)` — exactly 1 import + 3-line wrap (open + child + close) per file.

## Specific Gotchas (verified at execution)

### Gotcha 1: GeoBreakdownPieChart height = 260, NOT 280

The Phase 15 UI-SPEC default for `<ChartErrorBoundary>` is `height ?? 280`, but `GeoBreakdownPieChart` itself defaults to `height = 260` (verified at `frontend/src/components/charts/GeoBreakdownPieChart.tsx:56`). The wrapper `height` prop MUST match the underlying chart's default, otherwise the fallback box height differs from the chart's height — visible visual regression in UAT #2.

Two ACs verify this:
1. **Positive AC:** `grep -B1 "GeoBreakdownPieChart data={safeGeoBreakdown}" GeoBreakdownSection.tsx | grep "ChartErrorBoundary height={260}"` returns 1 ✓
2. **Anti-AC:** `grep -B1 "GeoBreakdownPieChart …" GeoBreakdownSection.tsx | grep -c "height={280}"` returns 0 ✓

### Gotcha 2: HTML entity `&lt;` vs JS literal `<` (already locked at Wave 1)

The empty-state copy uses JS literal `<` (e.g. `'Alert < 7 days old…'`), NOT the HTML entity `&lt;`. Verified at the i18n-keys.ts SSoT layer in Plan 15-01 (`grep -c "&lt;" frontend/src/lib/i18n-keys.ts` returns 0). Wave 2 chart consumers reference the SSoT by name, so this gotcha is transitively closed — JSX renders the JS literal verbatim, no entity escaping needed in `<p>{CHART_EMPTY_COPY.revenueTrend}</p>`.

### Gotcha 3: No-semicolon convention in chart files (vs typed-module semicolon convention in primitives)

All 3 chart files (`RevenueTrendChart.tsx`, `EnvironmentBarChart.tsx`, `GeoBreakdownPieChart.tsx`) use SINGLE-quote, NO-semicolon imports. Same with all 3 alert-section files. Plan locked the new imports to match per-file convention.

In contrast, `ChartErrorBoundary.tsx` (Plan 15-02) uses semicolons per D-12.01-04 typed-module convention. The asymmetry is intentional: file-level convention preserved on each side of the boundary.

## Anti-Pattern Guards Verified

| Guard | Verification | Result |
|---|---|---|
| **No try/catch in chart render** (UI-SPEC AC #14) | `grep -c "catch" frontend/src/components/charts/{Revenue,Environment,Geo}*.tsx` | All 3 → 0 ✓ |
| **No fallbackMessage prop at call sites** (scope lock) | `grep -r "fallbackMessage" frontend/src/components/alerts/` | 0 matches ✓ |
| **No new bg-X-Y in chart diffs** (UI-SPEC AC #18) | `git diff frontend/src/components/charts/ \| grep "^+" \| grep -E "bg-[a-z]+-[0-9]+"` | 0 matches ✓ |
| **Function exports preserved** (UI-SPEC AC #17) | `grep "export function {Chart}" {chart-file}` per chart | All 3 → 1 ✓ |
| **Alert-section function exports preserved** (defensive) | `grep -E "(Revenue\|Environment\|Geo)Section" frontend/src/components/alerts/*.tsx \| grep -c "export function"` | 3 ✓ |
| **GeoBreakdown wrap NOT at height=280** (gotcha 1 anti-check) | `grep -B1 "GeoBreakdownPieChart …" \| grep -c "height={280}"` | 0 ✓ |

## Verification Commands Run

| Command | Expected | Actual |
|---|---|---|
| `grep -c "CHART_EMPTY_COPY.revenueTrend" RevenueTrendChart.tsx` | ≥ 1 (UI-SPEC AC #10) | 1 ✓ |
| `grep -c "CHART_EMPTY_COPY.environmentBar" EnvironmentBarChart.tsx` | ≥ 1 (UI-SPEC AC #11) | 1 ✓ |
| `grep -c "CHART_EMPTY_COPY.geoBreakdown" GeoBreakdownPieChart.tsx` | ≥ 1 (UI-SPEC AC #12) | 1 ✓ |
| `grep -c "No revenue trend data available" RevenueTrendChart.tsx` | 0 (UI-SPEC AC #13) | 0 ✓ |
| `grep -c "No environment data available" EnvironmentBarChart.tsx` | 0 (UI-SPEC AC #13) | 0 ✓ |
| `grep -c "No geographic data available" GeoBreakdownPieChart.tsx` | 0 (UI-SPEC AC #13) | 0 ✓ |
| `grep -c "catch" {3 chart files}` | 0 each (UI-SPEC AC #14) | 0/0/0 ✓ |
| `grep "export function RevenueTrendChart" RevenueTrendChart.tsx` | 1 (UI-SPEC AC #17) | 1 ✓ |
| `grep "export function EnvironmentBarChart" EnvironmentBarChart.tsx` | 1 (UI-SPEC AC #17) | 1 ✓ |
| `grep "export function GeoBreakdownPieChart" GeoBreakdownPieChart.tsx` | 1 (UI-SPEC AC #17) | 1 ✓ |
| `grep -E "import.*CHART_EMPTY_COPY.*from.*i18n-keys" {3 chart files}` | 1 each | 1/1/1 ✓ |
| `git diff frontend/src/components/charts/ \| grep "^+" \| grep -E "bg-[a-z]+-[0-9]+"` | 0 (UI-SPEC AC #18) | 0 ✓ |
| `grep -B1 "RevenueTrendChart …" RevenueStatusSection.tsx \| grep -c "ChartErrorBoundary height={280}"` | 1 | 1 ✓ |
| `grep -B1 "EnvironmentBarChart …" EnvironmentSplitSection.tsx \| grep -c "ChartErrorBoundary height={280}"` | 1 | 1 ✓ |
| `grep -B1 "GeoBreakdownPieChart …" GeoBreakdownSection.tsx \| grep -c "ChartErrorBoundary height={260}"` | 1 (NOT 280!) | 1 ✓ |
| `grep -B1 "GeoBreakdownPieChart …" GeoBreakdownSection.tsx \| grep -c "height={280}"` | 0 (anti-check) | 0 ✓ |
| `grep -c "import { ChartErrorBoundary } …" {3 alert sections}` | 1 each | 1/1/1 ✓ |
| `grep -r "ChartErrorBoundary" frontend/src/ \| wc -l` | ≥ 7 (UI-SPEC AC #15) | 21 ✓ |
| `grep -r "fallbackMessage" frontend/src/components/alerts/` | 0 | 0 ✓ |
| `grep -E "(Revenue\|Environment\|Geo)Section" frontend/src/components/alerts/*.tsx \| grep -c "export function"` | 3 | 3 ✓ |
| `cd frontend && npx tsc --noEmit -p tsconfig.app.json` | exit 0 (UI-SPEC AC #19) | exit 0 ✓ |
| `cd frontend && npm run build` | exit 0 | exit 0, 2460 modules in 2.10s ✓ |

All 22 grep-based mechanical ACs and 2 build gates passed first-pass.

## Module Count Delta

| Phase | Modules Transformed | Notes |
|---|---|---|
| Pre-15 (Phase 14 ship) | 2459 | i18n-keys.ts ENVIRONMENT_LABELS already in Phase 14 |
| Plan 15-01 (CHART_EMPTY_COPY append) | 2459 | i18n-keys.ts unchanged module count (constants only) |
| Plan 15-02 (ChartErrorBoundary primitive create) | 2459 | New file but not yet imported anywhere in app graph |
| **Plan 15-03 (3 alert sections import primitive)** | **2460** (+1) | Primitive now consumed via 3 import statements → reachable from app graph |

The +1 module is `frontend/src/components/primitives/ChartErrorBoundary.tsx`, now reachable from `App → AlertDetailPage → {RevenueStatusSection, EnvironmentSplitSection, GeoBreakdownSection} → ChartErrorBoundary`. Wave 1 (Plan 15-02) created the file but no caller existed; Wave 2 (this plan) wires the call sites.

## Decisions Made

- **D-15.02 (carried from UI-SPEC):** Wrapper composition lives at the parent (call-site) layer. Chart components remain pure render functions. This matches the existing pattern of the global `ErrorBoundary` wrapping `<App />` in `main.tsx`. Wave 2 lands the wraps in `RevenueStatusSection`, `EnvironmentSplitSection`, `GeoBreakdownSection` — NOT inside the chart files themselves.
- **D-15.05 (carried from UI-SPEC):** `CHART_EMPTY_COPY` from `frontend/src/lib/i18n-keys.ts` is the SSoT for chart-area diagnostic copy. Wave 2 closes the contract: zero inline empty-state strings remain in chart-render functions (AC #13 grep returns 0 for all 3 old strings).
- **D-15.07 (carried from UI-SPEC):** camelCase keys (`revenueTrend`, `environmentBar`, `geoBreakdown`) consumed verbatim from the Plan 15-01 export. Object name `CHART_EMPTY_COPY` remains UPPER_SNAKE_CASE per project convention (matches `KPI_LABELS`, `REVENUE_LABELS`, `ENVIRONMENT_LABELS`).
- **D-15-03-IMPL-01 (this plan, gotcha lock):** GeoBreakdownPieChart wraps at `height={260}`. Verified twice: (a) positive AC matches `ChartErrorBoundary height={260}` immediately above the chart; (b) anti-check confirms `height={280}` does NOT appear next to that chart. UI-SPEC line 311 + plan T2 §"NOTE the 260" both flag this as the canonical override.
- **D-15-03-IMPL-02 (this plan, anti-pattern guard):** Zero try/catch added to chart render functions. AC #14 grep returns 0 for all 3 charts. The boundary at the React tree boundary catches throws cleanly; internal try/catch would have suppressed the error from the boundary, masking it (Phase 10.1 MAJOR-NEW-01 silent-failure class).
- **D-15-03-IMPL-03 (this plan, scope discipline):** No `fallbackMessage` prop passed at any call site. Default `CHART_ERROR_COPY.generic` ("Chart unavailable. Reload the page if this persists.") applies uniformly per Plan 15-02 contract. Per-chart custom messages explicitly deferred (UI-SPEC §"Out of scope": "per-chart messages are a future enhancement out of scope").

## Auth Gates

None. No credentials, no external services, no network calls modified or accessed during execution. All edits are pure-frontend JSX/TSX changes to component file scope.

## Deviations from Plan

None — plan executed exactly as written. Two-task plan, two atomic R-03 commits, all 22 mechanical ACs and 2 build gates satisfied first-pass. No Rule 1/2/3 auto-fixes triggered. No checkpoint reached. No authentication gates encountered.

## Commits

| # | Hash | Type | Subject |
|---|---|---|---|
| 1 | `99ba861` | feat | `feat(15-03): wire CHART_EMPTY_COPY into 3 chart components (CORR-07)` |
| 2 | `9cb0288` | feat | `feat(15-03): wrap 3 chart call sites in ChartErrorBoundary (CORR-10)` |

## Handoff Notes

- **Plan 15-04 (manual regression UAT — SC #3):** D-15.03 prop injection at the call site is now ACTIONABLE. A verifier can edit any of the 3 alert-section files temporarily and pass a known-bad value to the wrapped chart (e.g. `data={null as any}` or `data={[{ timestamp: null, revenue: NaN }]}`), reload the page, and visually confirm:
  - **UAT #1 (empty-state):** `data={[]}` → diagnostic copy renders inside the chart container at chart-area height (gray text, vertically centered, NOT a full-page error).
  - **UAT #2 (boundary fallback):** `data={null as any}` or malformed payload → `CHART_ERROR_COPY.generic` fallback message renders inside the chart-area container (bordered, gray background), and adjacent sections (TriageSection, ContributorsSection, header) remain operational.
  - **UAT #3 (no full-page crash — ROADMAP SC #3):** malformed payload → page does NOT blank. The boundary catches at the React tree level; `console.error('[ChartErrorBoundary]', ...)` from `componentDidCatch` is expected in devtools.

- **Phase 15 file-count gate respected:** 5 spec-locked files (i18n-keys.ts, ChartErrorBoundary.tsx, 3 chart files) + 3 call-site files (3 alert sections) = 8 total modified across the phase. UI-SPEC line 311 explicitly flags call-site files as planner-time additions ("These parent files ARE modified … NOT listed above because they depend on the grep of actual call sites").

- **ROADMAP SC closure status:** Plan 15-03 closes Phase 15 SC #1 (CORR-10 wraps live) + SC #2 (CORR-07 diagnostic copy live). SC #3 (manual regression — no full-page crash on malformed payload) is verified at runtime in Plan 15-04 via D-15.03 prop injection.

- **Block-on-high mitigation:** T-15-03-02 (high — full-page crash on malformed chart payload) is fully mitigated by this plan's 3 wraps. AC #15 grep verifies presence (≥7 references in `src/`, actual 21). Phase 15 ships the high-severity threat fully closed.

## Threat Flags

None — all surface introduced is internal to the React component tree (named imports + JSX wrapping). No new network endpoint, no new auth path, no new file-access pattern, no schema change, no new credential consumed. All `<threat_model>` STRIDE entries (T-15-03-01 through T-15-03-07) are mitigated as documented in the plan's threat register; Wave 2 execution adds no surface beyond plan scope.

## Self-Check: PASSED

- All 6 modified files contain expected changes:
  - `frontend/src/components/charts/RevenueTrendChart.tsx` — `CHART_EMPTY_COPY.revenueTrend` reference present (verified by grep above).
  - `frontend/src/components/charts/EnvironmentBarChart.tsx` — `CHART_EMPTY_COPY.environmentBar` reference present.
  - `frontend/src/components/charts/GeoBreakdownPieChart.tsx` — `CHART_EMPTY_COPY.geoBreakdown` reference present.
  - `frontend/src/components/alerts/RevenueStatusSection.tsx` — `<ChartErrorBoundary height={280}>` wraps `<RevenueTrendChart>` (lines 142-144).
  - `frontend/src/components/alerts/EnvironmentSplitSection.tsx` — `<ChartErrorBoundary height={280}>` wraps `<EnvironmentBarChart>` (lines 123-125).
  - `frontend/src/components/alerts/GeoBreakdownSection.tsx` — `<ChartErrorBoundary height={260}>` wraps `<GeoBreakdownPieChart>` (lines 85-87).
- Both task commits exist:
  - `99ba861` — `feat(15-03): wire CHART_EMPTY_COPY into 3 chart components (CORR-07)`
  - `9cb0288` — `feat(15-03): wrap 3 chart call sites in ChartErrorBoundary (CORR-10)`
- TypeScript compile (`tsc --noEmit -p tsconfig.app.json`) — exit 0.
- Vite production build (`npm run build`) — exit 0, 2460 modules transformed in 2.10s, dist clean.
- All 22 plan + UI-SPEC mechanical ACs PASS.
- GeoBreakdownPieChart height gotcha (260, NOT 280) — verified twice (positive + anti-check).
- All anti-pattern guards verified (no try/catch in 3 chart files; no fallbackMessage at 3 call sites; no new bg-X-Y in chart diffs).
