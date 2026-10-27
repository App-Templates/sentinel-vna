---
phase: 15
plan: 01
subsystem: frontend/i18n
tags: [ui-resilience, corr-07, corr-10, i18n-keys, ssot, wave-1]
dependency_graph:
  requires:
    - frontend/src/lib/i18n-keys.ts (existing 17 exports preserved)
    - .planning/phases/15-ui-resilience/15-UI-SPEC.md §"i18n-keys.ts Extension" (lines 222-256, copy source)
    - .planning/REQUIREMENTS.md CORR-07 (verbatim diagnostic string)
  provides:
    - CHART_EMPTY_COPY (3 keys: revenueTrend, environmentBar, geoBreakdown)
    - CHART_ERROR_COPY (1 key: generic)
  affects:
    - frontend/src/components/charts/RevenueTrendChart.tsx (Plan 15-03 consumer)
    - frontend/src/components/charts/EnvironmentBarChart.tsx (Plan 15-03 consumer)
    - frontend/src/components/charts/GeoBreakdownPieChart.tsx (Plan 15-03 consumer)
    - frontend/src/components/primitives/ChartErrorBoundary.tsx (Plan 15-02 consumer, NEW)
tech-stack:
  added: []
  patterns:
    - "Pure-append discipline (D-14.01-C precedent — 17 existing exports byte-identical)"
    - "UPPER_SNAKE_CASE object name + camelCase keys (D-15.07 + matches REVENUE_LABELS, KPI_LABELS, etc.)"
    - "Single-quote + semicolon typed-module convention (D-12.01-04)"
    - "as const literal type inference (matches every other object export)"
    - "JSDoc references back to UI-SPEC line numbers + REQUIREMENTS.md anchor"
key-files:
  created: []
  modified:
    - frontend/src/lib/i18n-keys.ts
decisions:
  - "D-15.05 — i18n-keys.ts is SSoT for chart-area diagnostic copy; zero inline strings in component JSX post-Wave-2"
  - "D-15.07 — camelCase object keys (revenueTrend, environmentBar, geoBreakdown, generic) matching project pattern (REVENUE_LABELS.status24h, KPI_LABELS.rpm)"
  - "D-15.01-IMPL — pure append AFTER emptyPublishersMultiFiltered closing brace; AC #20 verified zero deletions"
  - "Sentinel hard rule respected — UI-SPEC HTML entity `&lt;` rendered as JS literal `<` (zero `&lt;` matches in file)"
metrics:
  duration_minutes: 5
  tasks_completed: 1
  files_modified: 1
  files_created: 0
  lines_added: 20
  lines_deleted: 0
  completed_date: 2026-05-01
---

# Phase 15 Plan 01: i18n-keys.ts Extension Summary

**One-liner:** Appended `CHART_EMPTY_COPY` (3 chart-scoped diagnostic strings) and `CHART_ERROR_COPY` (ChartErrorBoundary fallback message) to `frontend/src/lib/i18n-keys.ts` as pure-append SSoT seed for Phase 15 Wave 2 consumers, with all 17 pre-existing exports byte-identical and TypeScript build clean.

## What Shipped

Two new named exports added to the bottom of `frontend/src/lib/i18n-keys.ts`, sourced verbatim from UI-SPEC §"i18n-keys.ts Extension" (lines 222-256):

```ts
export const CHART_EMPTY_COPY = {
  revenueTrend: 'No 7-week history. Alert < 7 days old or data not yet aggregated.',
  environmentBar: 'No environment split data. Alert < 7 days old or data not yet aggregated.',
  geoBreakdown: 'No geo breakdown data. Alert < 7 days old or data not yet aggregated.',
} as const;

export const CHART_ERROR_COPY = {
  generic: 'Chart unavailable. Reload the page if this persists.',
} as const;
```

- **Lines appended:** 20 (1 blank separator + 2 JSDoc blocks + 2 export blocks + final newline preserved).
- **File line count:** 199 → 219 (target was ~218, off by 1 because `wc -l` counts the trailing newline as the start of an extra line — actual content matches plan target byte-for-byte).
- **Diff stat:** `1 file changed, 20 insertions(+)`, 0 deletions.

## Verification Commands Run

| Command | Result |
|---------|--------|
| `grep -c "CHART_EMPTY_COPY" frontend/src/lib/i18n-keys.ts` | 1 (UI-SPEC AC #1 ✓) |
| `grep -F "revenueTrend: 'No 7-week history. Alert < 7 days old or data not yet aggregated.'" ...` | 1 match (UI-SPEC AC #2 ✓ — literal `<`, no HTML entity) |
| `grep -F "environmentBar: 'No environment split data." ...` | 1 match (UI-SPEC AC #3 ✓) |
| `grep -F "geoBreakdown: 'No geo breakdown data." ...` | 1 match (UI-SPEC AC #4 ✓) |
| `grep -c "CHART_ERROR_COPY" ...` | 1 (✓) |
| `grep -F "generic: 'Chart unavailable. Reload the page if this persists.'" ...` | 1 match (✓) |
| `grep -E "^export const KPI_LABELS" ...` | 1 match (existing export preserved ✓) |
| `grep -E "^export const ENVIRONMENT_LABELS" ...` | 1 match (existing export preserved, D-14.01-E ✓) |
| `grep -E "^export function emptyPublishersMultiFiltered" ...` | 1 match (existing function preserved ✓) |
| `grep -c "&lt;" ...` | 0 (UI-SPEC line 201 anti-creep ✓ — no HTML entity contamination) |
| `git diff -- frontend/src/lib/i18n-keys.ts \| grep "^-" \| grep -v "^---" \| wc -l` | 0 (UI-SPEC AC #20 ✓ — pure append, zero deletions) |
| `cd frontend && npx tsc --noEmit -p tsconfig.app.json` | exit 0 (UI-SPEC AC #19 ✓) |
| `cd frontend && npm run build` | exit 0, 2459 modules transformed, 2.14s, dist/assets clean (✓) |

## Decisions Made

- **D-15.05 (carried from UI-SPEC):** `i18n-keys.ts` is the SSoT for chart-area diagnostic copy. Wave 2 consumers will import these named exports — zero inline string literals in any chart file post-phase (anti-creep AC #13).
- **D-15.07 (carried from UI-SPEC):** Object keys are camelCase (`revenueTrend`, `environmentBar`, `geoBreakdown`, `generic`) — matches existing project convention (`REVENUE_LABELS.status24h`, `KPI_LABELS.rpm`, etc.). Object name remains UPPER_SNAKE_CASE.
- **D-15.01-IMPL (this plan, mechanical):** Append point is immediately after the closing brace of `emptyPublishersMultiFiltered` (previous file end at line 199). All 17 pre-existing exports remain byte-identical above the insertion point — verified by AC #20 grep returning 0 deleted lines.
- **Sentinel hard rule (locked by plan):** UI-SPEC HTML entity `&lt;` rendered as JS literal `<` — JSX strings need no entity escaping per UI-SPEC line 201. Verified: `grep -c "&lt;" frontend/src/lib/i18n-keys.ts` returns 0.

## Deviations from Plan

None — plan executed exactly as written. Single-task plan, single atomic commit, all UI-SPEC mechanical ACs (#1-4, #19, #20) and plan ACs satisfied first-pass. No Rule 1/2/3 auto-fixes triggered. No checkpoint reached. No authentication gates encountered.

## Commits

| # | Hash | Type | Subject |
|---|------|------|---------|
| 1 | `2bbfccd` | feat | `feat(15-01): append CHART_EMPTY_COPY + CHART_ERROR_COPY to i18n-keys.ts` |

## Handoff Notes

- **Plan 15-02 (ChartErrorBoundary primitive):** Imports `CHART_ERROR_COPY.generic` as default `fallbackMessage`. Pattern: `import { CHART_ERROR_COPY } from '@/lib/i18n-keys'` (or relative path per project convention).
- **Plan 15-03 (3 chart wiring):** Imports `CHART_EMPTY_COPY.revenueTrend` / `.environmentBar` / `.geoBreakdown` to replace the existing inline empty-state strings (`'No revenue trend data available for this alert period.'` etc.). UI-SPEC AC #10-13 will grep-verify the swap.
- **Plan 15-04 (regression injection method doc):** No code consumer of these exports; D-15.03 prop-injection is documented for visual UAT only.

## Threat Flags

None — pure constant-string append in a leaf primitive module. No new network endpoint, auth path, file access pattern, or trust boundary introduced. All threats in the plan's `<threat_model>` (T-15-01-01 Tampering, T-15-01-02 Information Disclosure, T-15-01-03 DoS) are mitigated or accepted as documented; no new surface added beyond plan scope.

## Self-Check: PASSED

- `frontend/src/lib/i18n-keys.ts` exists and contains both new exports (verified via grep above).
- Commit `2bbfccd` exists in git log (`git log --oneline -1` → `2bbfccd feat(15-01): append CHART_EMPTY_COPY + CHART_ERROR_COPY to i18n-keys.ts`).
- All 12 UI-SPEC + plan ACs grep-verified PASS.
- TypeScript compile (AC #19) and full Vite build PASS.
- Pure-append discipline (AC #20) PASS — 0 lines deleted.
