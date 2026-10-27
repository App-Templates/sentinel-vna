---
phase: 15
plan: 02
subsystem: frontend/components/primitives
tags: [ui-resilience, corr-10, error-boundary, class-component, wave-1, primitive]
dependency_graph:
  requires:
    - frontend/src/lib/i18n-keys.ts (CHART_ERROR_COPY.generic — Wave 1 sibling Plan 15-01 commit `2bbfccd`)
    - frontend/src/components/ErrorBoundary.tsx (existing project class-component pattern, mirrored — NOT modified)
    - .planning/phases/15-ui-resilience/15-UI-SPEC.md §"ChartErrorBoundary primitive specification" (lines 124-172, props + fallback locked)
  provides:
    - "class ChartErrorBoundary (named export) — per-chart-area React ErrorBoundary"
    - "ChartErrorBoundaryProps interface (children, height?, fallbackMessage?)"
    - "frontend/src/components/primitives/ subdirectory (NEW — first primitive)"
  affects:
    - frontend/src/components/alerts/RevenueStatusSection.tsx (Wave 2 Plan 15-03 consumer)
    - frontend/src/components/alerts/EnvironmentSplitSection.tsx (Wave 2 Plan 15-03 consumer)
    - frontend/src/components/alerts/GeoBreakdownSection.tsx (Wave 2 Plan 15-03 consumer)
tech-stack:
  added: []
  patterns:
    - "Class-component ErrorBoundary (D-15.01 — DIY, NOT react-error-boundary library; mirrors existing ErrorBoundary.tsx)"
    - "Static getDerivedStateFromError + instance componentDidCatch (React canonical error-boundary contract)"
    - "Chart-area scoped fallback via inline style={{ width: '100%', height }} (D-15.02/D-15.06 — distinct from full-viewport ErrorBoundary)"
    - "console.error with [ChartErrorBoundary] diagnostic prefix (UAT #2 anchor)"
    - "Single-quote + semicolon typed-module convention (D-12.01-04 — Phase 12 typed-module discipline)"
    - "Named export (NOT default) — Wave 2 consumers import via { ChartErrorBoundary }"
    - "i18n-keys SSoT consumption (D-15.05 — CHART_ERROR_COPY.generic, no inline string)"
key-files:
  created:
    - frontend/src/components/primitives/ChartErrorBoundary.tsx
  modified: []
decisions:
  - "D-15.01 — DIY class-component (no react-error-boundary dep added). Mirrors existing project pattern in ErrorBoundary.tsx."
  - "D-15.02 — Chart-area scoped fallback (caller wraps at parent composition layer in Wave 2). Boundary itself is height/width sized; NOT full-viewport."
  - "D-15.04 — NO auto-reload button. Anti-pattern locked — auto-reload masks repeat failures (Phase 14 WR-02 401 reload-loop incident precedent)."
  - "D-15.05 — i18n-keys SSoT for fallback copy. Default fallbackMessage sourced from CHART_ERROR_COPY.generic (Plan 15-01 export)."
  - "D-15.06 — Placement in NEW components/primitives/ subdirectory (distinguishes error-boundary infrastructure from UI primitives in components/ui/)."
  - "D-15.02-IMPL — Diagnostic logging is additive: componentDidCatch logs error + ErrorInfo to console.error; render path consumes ONLY CHART_ERROR_COPY.generic or trusted fallbackMessage prop (T-15-02-02 + T-15-02-03 mitigations)."
metrics:
  duration_minutes: 2
  tasks_completed: 1
  files_modified: 0
  files_created: 1
  lines_added: 69
  lines_deleted: 0
  completed_date: 2026-05-02
---

# Phase 15 Plan 02: ChartErrorBoundary Primitive Summary

**One-liner:** Created `frontend/src/components/primitives/ChartErrorBoundary.tsx` (69 lines, new `primitives/` subdirectory) — a per-chart-area React class-component ErrorBoundary that catches render errors via `static getDerivedStateFromError` + `componentDidCatch`, renders a same-sized fallback with `CHART_ERROR_COPY.generic` from the Wave 1 i18n-keys SSoT, omits the anti-pattern auto-reload mechanism (D-15.04), and logs diagnostics to `console.error` with the `[ChartErrorBoundary]` prefix for devtools surfacing — closing CORR-10 at the primitive layer for Wave 2 consumers.

## What Shipped

One new file at the exact path locked by the plan:

- **`frontend/src/components/primitives/ChartErrorBoundary.tsx`** (69 lines, 0 deletions)
- Implicitly creates the **`frontend/src/components/primitives/`** subdirectory (first occupant; no `index.ts` barrel — Phase 15 has only this one primitive per UI-SPEC §File-Count Gate).

### File contract delivered

```tsx
import { Component, type ErrorInfo, type ReactNode } from 'react';
import { CHART_ERROR_COPY } from '../../lib/i18n-keys';

interface ChartErrorBoundaryProps {
  children: ReactNode;
  height?: number;
  fallbackMessage?: string;
}

interface ChartErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ChartErrorBoundary extends Component<
  ChartErrorBoundaryProps,
  ChartErrorBoundaryState
> {
  // constructor — initial { hasError: false, error: null }
  // static getDerivedStateFromError(error) — returns { hasError: true, error }
  // componentDidCatch(error, info) — console.error('[ChartErrorBoundary]', error, info)
  // render() — fallback (chart-area sized div) OR children
}
```

## Mirror Points vs Existing `ErrorBoundary.tsx`

| Aspect | Global `ErrorBoundary` (existing) | `ChartErrorBoundary` (this plan) |
|---|---|---|
| Class-component pattern | ✓ extends Component | ✓ extends Component (mirrored) |
| `static getDerivedStateFromError` | ✓ | ✓ (mirrored) |
| `componentDidCatch` | ✗ absent | ✓ NEW — with `[ChartErrorBoundary]` console.error prefix |
| Sizing | `min-h-screen` (full viewport) | `style={{ width: '100%', height }}` chart-area (D-15.06 divergence) |
| Reload button | ✓ `onClick={() => window.location.reload()}` | ✗ ABSENT (D-15.04 anti-pattern lock) |
| Fallback copy source | inline `error?.message` literal + heading literal | `CHART_ERROR_COPY.generic` from i18n-keys SSoT (D-15.05) |
| Quote/semicolon convention | no semicolons, single-quote | semicolons + single-quote (D-12.01-04 typed-module) |
| Background palette | `bg-gray-50 p-8` heading | `bg-gray-50 border border-gray-200 rounded-md` (Phase 14 ship-state palette only — no semantic-error color introduced) |

## Verification Commands Run

| Command | Expected | Actual |
|---|---|---|
| `test -f frontend/src/components/primitives/ChartErrorBoundary.tsx` | exit 0 | exit 0 ✓ (UI-SPEC AC #5) |
| `grep -c 'getDerivedStateFromError' …` | ≥ 1 | 1 ✓ (UI-SPEC AC #6) |
| `grep -c 'componentDidCatch' …` | ≥ 1 | 2 ✓ (UI-SPEC AC #7) |
| `grep -c 'console.error' …` | ≥ 1 | 2 ✓ (UI-SPEC AC #8) |
| `grep -cF '[ChartErrorBoundary]' …` | ≥ 1 | 2 ✓ (diagnostic anchor for UAT #2) |
| `grep -c 'window.location.reload' …` | 0 | 0 ✓ (UI-SPEC AC #9 / D-15.04) |
| `grep -c 'min-h-screen' …` | 0 | 0 ✓ (UI-SPEC AC #16 — chart-scoped only) |
| `grep -c 'dangerouslySetInnerHTML' …` | 0 | 0 ✓ (T-15-02-02 XSS surface absent) |
| `grep -c 'export class ChartErrorBoundary' …` | 1 | 1 ✓ (named export) |
| `grep -c 'import { CHART_ERROR_COPY }' …` | 1 | 1 ✓ (D-15.05 i18n-keys SSoT) |
| `grep -cE 'bg-(red\|orange\|yellow\|green)-' …` | 0 | 0 ✓ (no new color tokens — UI-SPEC §"ErrorBoundary fallback color") |
| `grep -cE 'as any\b' …` | 0 | 0 ✓ (R-13 type safety) |
| `wc -l …` | ≥ 35 | 69 ✓ (must_haves.artifacts.min_lines) |
| `cd frontend && npx tsc --noEmit -p tsconfig.app.json` | exit 0 | exit 0 ✓ (UI-SPEC AC #19, cross-cuts with Plan 15-01) |
| `cd frontend && npm run build` (sanity) | exit 0 | exit 0, 2459 modules transformed in 2.18s ✓ |

All 13 grep-based mechanical ACs and the 2 build gates passed.

## Decisions Made

- **D-15.01 (carried from UI-SPEC):** Class-component DIY, NOT `react-error-boundary` library. Verified absent from `frontend/package.json` before execution. Adding a dep for a single 3-chart wrapping primitive violates Sentinel minimal-deps philosophy. Project's existing `ErrorBoundary.tsx` already follows this pattern.
- **D-15.02 (carried from UI-SPEC):** Wrapper composition lives at the call site (parent component). Wave 2 Plan 15-03 will wrap `<RevenueTrendChart>` / `<EnvironmentBarChart>` / `<GeoBreakdownPieChart>` with `<ChartErrorBoundary height={280}>` at their respective parents (`RevenueStatusSection`, `EnvironmentSplitSection`, `GeoBreakdownSection`).
- **D-15.04 (carried from UI-SPEC):** NO `window.location.reload()` button anywhere — this is the post-Phase-14-WR-02 lock. Operators reload manually if a chart fails repeatedly; the boundary keeps showing the fallback so the persistent failure stays visible.
- **D-15.05 (carried from UI-SPEC):** Default `fallbackMessage` is `CHART_ERROR_COPY.generic` from `frontend/src/lib/i18n-keys.ts` (the Plan 15-01 SSoT seed). Zero inline JSX strings.
- **D-15.06 (carried from UI-SPEC):** Placement at `frontend/src/components/primitives/` (NEW subdir). Distinguishes error-boundary infrastructure from UI primitives in `components/ui/`. The `primitives/` subdir is created implicitly by writing the file; no `index.ts` barrel for a single-primitive directory.
- **D-15.02-IMPL (this plan, mechanical):** Diagnostic logging is **additive** — `componentDidCatch` logs the full `error` object + `ErrorInfo` (componentStack) to `console.error` for devtools, while the render path NEVER consumes `this.state.error` for display (T-15-02-02 + T-15-02-03 mitigations). Only the static `CHART_ERROR_COPY.generic` or a trusted `fallbackMessage` prop reaches the user.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] JSDoc literals contradicted mechanical grep ACs**

- **Found during:** Task 1 verification (after initial Write).
- **Issue:** The plan's `<action>` block included a verbatim-locked TSX content with JSDoc lines that mentioned `window.location.reload()` and `min-h-screen` as **anti-pattern guards** (i.e. documentation explaining what the file does NOT do). However, the same plan's mechanical AC #9 + AC #16 + the `<verify>` block use `! grep -q 'window.location.reload' …` and `! grep -q 'min-h-screen' …` — gates that fail on **any** match, including JSDoc. Initial paste produced 1 match for each (both inside JSDoc comments at lines 20 + 23), failing the gate.
- **Fix:** Reworded the two JSDoc lines to express the same anti-pattern intent without the literal substrings:
  - `min-h-screen for App-level catastrophic crashes` → `full-viewport sizing for App-level catastrophic crashes`
  - `NO `window.location.reload()` button — auto-reload …` → `NO auto-reload button — auto-reload …`
- **Files modified:** `frontend/src/components/primitives/ChartErrorBoundary.tsx` (JSDoc only — functional code path unchanged byte-identical to plan-locked content).
- **Intent preserved:** Both JSDoc references retain explicit decision-ID anchors (D-15.04 / D-15.06) so a reader still understands exactly which anti-pattern the file guards against. Zero behavioral change.
- **Commit:** `38144e6` (commit body documents this auto-fix explicitly).

No other deviations. No checkpoint reached. No authentication gates encountered.

## Commits

| # | Hash | Type | Subject |
|---|---|---|---|
| 1 | `38144e6` | feat | `feat(15-02): add ChartErrorBoundary primitive (CORR-10)` |

## Handoff Notes

- **Plan 15-03 (Wave 2 — chart wiring):** Imports `{ ChartErrorBoundary }` from `'../primitives/ChartErrorBoundary'` (relative from `components/alerts/*Section.tsx`) and wraps each of the 3 chart call sites:
  - `RevenueStatusSection.tsx` → wraps `<RevenueTrendChart>` with `<ChartErrorBoundary height={280}>`
  - `EnvironmentSplitSection.tsx` → wraps `<EnvironmentBarChart>` with `<ChartErrorBoundary height={280}>`
  - `GeoBreakdownSection.tsx` → wraps `<GeoBreakdownPieChart>` with `<ChartErrorBoundary height={280}>`
  - Default `height` is 280 (matches `RevenueTrendChart` default — verified in `frontend/src/components/charts/RevenueTrendChart.tsx:35`).
- **Plan 15-04 (regression-injection method doc):** D-15.03 documents prop-injection as the canonical SC #3 verification. The boundary catches throws in `formatDateShort(p.timestamp)` when `timestamp=null`, in `metrics.revenue` access when `data={ WEB: null } as any`, in `formatCurrency(undefined)` when `current_revenue=undefined`. No code change in this plan to support the injection — it lives at the consumer's call site temporarily during dev.
- **Wave 2 readiness check:** TS compile is clean now that both Wave 1 plans (15-01 export of CHART_ERROR_COPY + 15-02 import in ChartErrorBoundary) have landed. Wave 2 plan 15-03 can begin executing.

## Threat Flags

None — class-component primitive with single `console.error` diagnostic surface, no new network endpoint, no new auth path, no new file-access pattern, no schema changes. All `<threat_model>` STRIDE entries (T-15-02-01 through T-15-02-06) are mitigated as documented:
- **T-15-02-01 Tampering** — `import { CHART_ERROR_COPY }` verified present (grep AC pass).
- **T-15-02-02 Information Disclosure (XSS, high)** — `dangerouslySetInnerHTML` grep returns 0; render path consumes only static i18n constant or trusted prop; React auto-escape applies. **Block-on-high satisfied.**
- **T-15-02-03 Information Disclosure (stack trace leak)** — render path does NOT consume `this.state.error`; only `componentDidCatch` reaches `console.error` (developer surface).
- **T-15-02-04 DoS (render loop)** — fallback uses only static string + numeric default + static Tailwind classes; no computed expressions that could throw.
- **T-15-02-05 Tampering (auto-reload masking failures)** — `window.location.reload` grep returns 0.
- **T-15-02-06 Spoofing (i18n-key injection)** — `accept` disposition; Wave 2 plan 15-03 does NOT pass `fallbackMessage` prop, so attack surface is presently zero.

## Self-Check: PASSED

- `frontend/src/components/primitives/ChartErrorBoundary.tsx` exists (verified: `test -f` exit 0, `wc -l` returns 69).
- Commit `38144e6` exists in git log (`git log --oneline -1` returns `38144e6 feat(15-02): add ChartErrorBoundary primitive (CORR-10)`).
- All 13 plan + UI-SPEC mechanical ACs grep-verified PASS (re-run post-rewording).
- `tsc --noEmit -p tsconfig.app.json` exit 0 (cross-cuts with Plan 15-01 — CHART_ERROR_COPY symbol resolves).
- `npm run build` exit 0, 2459 modules transformed in 2.18s — Vite bundle clean (file is created but not yet consumed; Wave 2 will surface a module-count delta).
- New `primitives/` subdirectory created (`ls frontend/src/components/primitives/` returns single file).
