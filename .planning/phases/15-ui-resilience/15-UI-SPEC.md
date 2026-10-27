---
phase: 15
slug: ui-resilience
status: approved
shadcn_initialized: false
preset: none
created: 2026-05-01
reviewed_at: 2026-05-01
mode: lock-don't-redesign
requirements: [CORR-07, CORR-10]
depends_on: phase-14 (HEAD b3bb281, shipped 2026-04-30)
truth_source: .planning/REQUIREMENTS.md (CORR-07 + CORR-10 verbatim)
---

# Phase 15 — UI Design Contract

> Visual and interaction contract for Phase 15: UI Resilience.
> Requirements: CORR-07 (diagnostic empty states) + CORR-10 (ErrorBoundary on chart components).
>
> **Phase 15 is a behavioral resilience phase, NOT a visual redesign.**
> The Phase 12+13+14 design baseline (primitives, color tokens, spacing, typography) is inherited
> verbatim. Phase 15 only:
> 1. Wraps 3 chart components in per-component ErrorBoundary fallbacks (CORR-10).
> 2. Upgrades existing inline empty-state strings to i18n-keys-sourced diagnostic copy (CORR-07).
> 3. Documents a regression injection method for manual SC #3 verification.
>
> **Mode: lock-don't-redesign.** No layout, no palette, no spacing, no new primitives beyond
> the chart-scoped ErrorBoundary fallback.

---

## Scope

| Surface | Phase 15 change | Lock-don't-redesign? |
|---------|-----------------|----------------------|
| `RevenueTrendChart.tsx` | Wrap render in `<ChartErrorBoundary>`; upgrade inline empty string to `CHART_EMPTY_COPY.revenueTrend` from i18n-keys | YES — chart layout UNCHANGED |
| `EnvironmentBarChart.tsx` | Wrap render in `<ChartErrorBoundary>`; upgrade inline empty string to `CHART_EMPTY_COPY.environmentBar` | YES — chart layout UNCHANGED |
| `GeoBreakdownPieChart.tsx` | Wrap render in `<ChartErrorBoundary>`; upgrade inline empty string to `CHART_EMPTY_COPY.geoBreakdown` | YES — chart layout UNCHANGED |
| `ChartErrorBoundary.tsx` (NEW) | Per-chart-area class-component ErrorBoundary. Sized to match parent chart area via `style={{ width: '100%', height }}`. NO full-page takeover. NO auto-reload. | N/A — new primitive in `frontend/src/components/primitives/` |
| `i18n-keys.ts` | Add `CHART_EMPTY_COPY` export (3 keys) and `CHART_ERROR_COPY` export (1 key for fallback message) | N/A — copy-only extension |

**Out of scope in Phase 15:**

- Dashboard chart-like components (`RevenueStatus24h`, `RevenueByChannel`) — these are NOT chart/* components per ROADMAP CORR-10 scope. Do NOT wrap them.
- KpiCards, TriageSection, PublishersPage — NOT in CORR-10 scope.
- Any new backend endpoint or data shape change.
- Visual redesign of the existing chart UI.
- Auto-reload on error (anti-pattern documented in D-15.04 below).

---

## Design System

Inherited verbatim from Phase 12 + Phase 13 + Phase 14. No change.

| Property | Value |
|----------|-------|
| Tool | none (Tailwind v4 CSS-first via `@theme` in `frontend/src/index.css`) |
| Preset | not applicable |
| Component library | bespoke primitives in `frontend/src/components/ui/` and `primitives/` (Card, Button, Badge, MetricCard, DataTable, Skeleton, AlertBox, DeltaIndicator, DatePicker, ScopeBadge, ReferencePeriodFootnote, GrossNetToggle, TopNDisclaimer). Phase 15 adds 1 new primitive: `ChartErrorBoundary`. |
| Icon library | `lucide-react@^0.563.0` |
| Variant engine | `class-variance-authority@^0.7.1` |
| Class merge | `clsx` + `tailwind-merge` via `cn()` in `lib/utils.ts` |
| Font | `'Inter', system-ui, -apple-system, sans-serif` |
| Currency / number locale | `Intl.NumberFormat('it-IT', currency: 'EUR')` via `formatCurrency` |
| State management | TanStack Query (server state) + `useState` (transient) — no change |

**shadcn gate:** Not applicable. Same rationale as Phases 12+13+14 — bespoke primitives cover all needed surfaces.

**react-error-boundary library:** NOT present in `frontend/package.json` (confirmed by grep 2026-05-01). Decision: DIY class-component pattern in `frontend/src/components/primitives/ChartErrorBoundary.tsx` using `static getDerivedStateFromError` + `componentDidCatch`. This matches the project's existing `frontend/src/components/ErrorBoundary.tsx` pattern (class component, Phase <12 origin) — zero new dependency, zero install required. Locked as D-15.01.

---

## Spacing Scale

Locked from Phase 12 + Phase 13 + Phase 14. Phase 15 adds zero new spacing tokens.

| Token | Tailwind class | Value | Phase 15 usage |
|-------|----------------|-------|----------------|
| xs | `gap-1`, `p-1` | 4px | (not used in Phase 15 additions) |
| sm | `gap-2`, `px-2`, `py-2` | 8px | ErrorBoundary fallback inner padding |
| md | `gap-4`, `p-4` | 16px | (not used in Phase 15 additions) |
| lg | `gap-6`, `p-6` | 24px | (not used in Phase 15 additions) |
| xl | `space-y-6`, `gap-6` | 24-32px | (inherited, not touched) |

**Exceptions (none new):** ErrorBoundary fallback container uses `style={{ width: '100%', height }}` for sizing (inline style required for dynamic `height` prop matching — consistent with all 3 existing chart empty-state patterns). This is an existing exception, not a new one.

---

## Typography

Locked from Phase 12 + Phase 13 + Phase 14. Phase 15 adds zero new typographic tokens.

| Role | Tailwind class | Size | Weight | Line Height | Phase 15 usage |
|------|----------------|------|--------|-------------|----------------|
| Caption / hint | `text-xs` | 12px | `font-normal` (400) | 1.5 | (not used in Phase 15 additions) |
| Body / table cell | `text-sm` | 14px | `font-medium` (500) for labels, default (400) for values | 1.5 | Empty-state copy, ErrorBoundary fallback message |
| Heading (CardTitle) | `text-lg` | 18px | `font-semibold` (600) | 1.2 | (not used in Phase 15 additions) |
| Display (KPI value) | `text-2xl` | 24px | `font-bold` (700) | 1.2 | (not used in Phase 15 additions) |

**Empty-state and error-fallback text:** `text-sm text-gray-400` — exactly the existing inline class on all 3 charts' current empty-state paragraphs. Phase 15 does NOT change visual weight or color.

---

## Color

60/30/10 inherited from `index.css` `@theme`. No new tokens introduced in Phase 15.

| Role | Token / class | Hex | Phase 15 surfaces |
|------|---------------|-----|-------------------|
| Dominant (60%) — surface | `bg-white` | `#ffffff` | Inherited chart containers |
| Secondary (30%) — chrome | `bg-gray-50`, `border-gray-200` | `#f9fafb`, `#e5e7eb` | ErrorBoundary fallback background |
| Empty/error text | `text-gray-400` | `#9ca3af` | Empty-state `<p>` text (matches existing pattern on 3 charts) |
| Error accent (subtle) | `text-red-500` | `#ef4444` | Optional: only if `componentDidCatch` surfaces error label. RESTRICTED — do NOT use for empty-state (empty != error). |

**Accent reserved-for list (UNCHANGED from Phase 12+13+14):** Severity badge, triage badge, metric direction, channel badge, status badge, A6/A7 sub-cards. Phase 15 does NOT extend this list.

**ErrorBoundary fallback color:** `bg-gray-50 border border-gray-200` container, `text-sm text-gray-500` message. Matches the visual weight of the chart-area container. NOT `bg-red-50` (that would imply a user-visible error requiring action — ErrorBoundary fallback here means "this chart broke, others are fine").

**Anti-creep grep:** Phase 15 diff MUST NOT introduce any new `bg-X-Y` or `text-X-Y` Tailwind class where `X-Y` does not already appear in Phase 14 ship-state, EXCEPT `text-red-500` for optional error-detail (restricted to `componentDidCatch` only, not empty-state).

---

## ErrorBoundary Fallback Layout (CORR-10 — Locked)

### `ChartErrorBoundary` primitive specification

**File:** `frontend/src/components/primitives/ChartErrorBoundary.tsx`

**Props interface:**
```tsx
interface ChartErrorBoundaryProps {
  children: ReactNode
  height?: number          // mirrors chart height prop; default 280
  fallbackMessage?: string // override; default from CHART_ERROR_COPY.generic
}
```

**Fallback render (locked):**
```tsx
<div
  style={{ width: '100%', height: height ?? 280 }}
  className="flex items-center justify-center rounded-md border border-gray-200 bg-gray-50"
>
  <p className="text-sm text-gray-500">{fallbackMessage ?? CHART_ERROR_COPY.generic}</p>
</div>
```

**Key constraints:**
- Same `style={{ width: '100%', height }}` container as existing chart empty-state pattern — fallback occupies the SAME visual footprint as the chart it replaces.
- NO `min-h-screen` (the existing global `ErrorBoundary.tsx` uses that for full-page — `ChartErrorBoundary` is chart-scoped).
- NO `window.location.reload()` button — charts auto-reload would mask repeat failures (D-15.04 anti-pattern, reference Phase 14 WR-02 reload-loop incident).
- `componentDidCatch(error, info)` MUST call `console.error('[ChartErrorBoundary]', error, info)` for diagnostic logging WITHOUT suppressing the error. This is NOT a try/catch swallow — the error is logged and the boundary catches the throw at the React tree boundary.

**Class component pattern (matches project's existing `ErrorBoundary.tsx`):**
```tsx
class ChartErrorBoundary extends Component<ChartErrorBoundaryProps, ChartErrorBoundaryState> {
  static getDerivedStateFromError(error: Error): ChartErrorBoundaryState {
    return { hasError: true, error }
  }
  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('[ChartErrorBoundary]', error, info)
  }
  render(): ReactNode {
    if (this.state.hasError) {
      return <fallback as above>
    }
    return this.props.children
  }
}
```

### Chart wrapping pattern (ALL 3 charts)

```tsx
// In parent component (e.g. EnvironmentSplitSection.tsx or AlertDetailPage):
<ChartErrorBoundary height={280}>
  <EnvironmentBarChart data={...} height={280} />
</ChartErrorBoundary>
```

**Decision: where does the wrapper live?** The `<ChartErrorBoundary>` wrapper is placed at the CALL SITE (parent that renders the chart), NOT inside the chart component file itself. Rationale: chart components are pure render functions; the boundary is a concern of the parent composition layer. This follows the same pattern as the existing global `ErrorBoundary.tsx` usage (wraps `<App />` in `main.tsx`). Locked as D-15.02.

---

## Empty-State Specification (CORR-07 — Locked)

### Diagnostic copy (verbatim from REQUIREMENTS.md CORR-07)

The 3 existing inline strings MUST be replaced with i18n-keys constants. Copy is PER-CHART, parallel structure: cause + diagnostic hint.

| Chart | Current inline string | Replacement constant | Locked copy |
|-------|----------------------|----------------------|-------------|
| `RevenueTrendChart` | `'No revenue trend data available for this alert period.'` | `CHART_EMPTY_COPY.revenueTrend` | `'No 7-week history. Alert < 7 days old or data not yet aggregated.'` |
| `EnvironmentBarChart` | `'No environment data available.'` | `CHART_EMPTY_COPY.environmentBar` | `'No environment split data. Alert < 7 days old or data not yet aggregated.'` |
| `GeoBreakdownPieChart` | `'No geographic data available.'` | `CHART_EMPTY_COPY.geoBreakdown` | `'No geo breakdown data. Alert < 7 days old or data not yet aggregated.'` |

**Copy rationale:**
- `RevenueTrendChart` copy is verbatim from REQUIREMENTS.md CORR-07 (canonical source).
- `EnvironmentBarChart` + `GeoBreakdownPieChart` copies follow the SAME parallel structure: "No [data type] data. Alert < 7 days old or data not yet aggregated." — cause first, hint second. This is the diagnostic pattern locked by CORR-07.
- HTML entity `&lt;` from REQUIREMENTS.md is the ASCII `<` in JS strings (not JSX entity — the string is in a `<p>` JSX element, no escaping needed).

### Empty-state layout (LOCKED — matches existing chart pattern)

```tsx
if (/* data is empty or falsy */) {
  return (
    <div style={{ width: '100%', height }} className="flex items-center justify-center">
      <p className="text-sm text-gray-400">{CHART_EMPTY_COPY.revenueTrend}</p>
    </div>
  )
}
```

- Container: identical `style={{ width: '100%', height }}` + `flex items-center justify-center` — same as existing pattern on all 3 charts. Phase 15 does NOT change the visual container.
- Text: `text-sm text-gray-400` — same as existing (no change in visual weight or color).
- No icon (existing charts have none; Phase 15 does not add one — lock-don't-redesign).
- No retry button in empty-state (empty state is data-driven, not an error — no action available to operator).

---

## i18n-keys.ts Extension (CORR-07 — Locked)

**File:** `frontend/src/lib/i18n-keys.ts`

**New exports to add (pure append — no modification of existing exports):**

```ts
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
```

**Convention compliance:**
- `UPPER_SNAKE_CASE` for object exports (matches `KPI_LABELS`, `SELL_TYPE_LABELS`, `REVENUE_LABELS`, `CHART_EMPTY_COPY`).
- `as const` for literal type inference (matches all existing exports).
- Single-quote + semicolon style (matches typed-module convention per D-12.01-04).
- Appended AFTER existing `emptyPublishersMultiFiltered` function — pure append, zero diff on existing lines.

---

## Regression Injection Method (SC #3 — Locked)

**Decision D-15.03: prop injection at the call site (Option C).**

For the manual regression test ("inject malformed payload → UI shows fallback instead of crash"), use **component-level prop injection in dev** — pass intentionally malformed data to the chart component via its existing props in the relevant call site during development verification.

Rationale for choosing Option C over alternatives:
- **Option A (Vite proxy override):** Requires proxy config edit and coordinated backend. More setup than needed for a manual verification.
- **Option B (MSW Mock Service Worker):** MSW is not in `package.json`; adding it violates Sentinel minimal-deps philosophy for a one-time manual test.
- **Option C (prop injection — CHOSEN):** Zero new dependency. The verifier edits the relevant parent component temporarily (e.g. `EnvironmentSplitSection.tsx`) to pass a known-bad value (e.g. `data={null as any}` or `data={[{ timestamp: null, revenue: 'bad' }]}`), visually confirms fallback, then reverts. Locked as the canonical SC #3 verification method.
- **Option D (JSON fixture):** More formal but adds a fixture file that must be maintained. Overkill for a 3-component visual check.

**Injection targets per chart:**

| Chart | Prop to inject | Malformed value | Expected result |
|-------|---------------|-----------------|-----------------|
| `RevenueTrendChart` | `data` | `[]` (empty array) OR `undefined` | Empty-state copy renders |
| `RevenueTrendChart` | `data` | `[{ timestamp: null, revenue: NaN }]` | ErrorBoundary fallback (throws in `formatDateShort`) |
| `EnvironmentBarChart` | `data` | `{}` (empty object) OR `null as any` | Empty-state copy renders |
| `EnvironmentBarChart` | `data` | `{ WEB: null } as any` | ErrorBoundary fallback (throws on `metrics.revenue`) |
| `GeoBreakdownPieChart` | `data` | `[]` (empty array) OR `null as any` | Empty-state copy renders |
| `GeoBreakdownPieChart` | `data` | `[{ geo_cluster: 'ITA', current_revenue: undefined }] as any` | ErrorBoundary fallback (throws in `formatCurrency`) |

**Anti-pattern documented:** A try/catch block INSIDE the chart component that catches render errors and returns null silently IS NOT equivalent to an ErrorBoundary. If any executor is tempted to add try/catch inside chart render functions to "fix" crashes → STOP. The ErrorBoundary catches throws at the React tree boundary; internal try/catch would mask the error from the boundary (violation of anti-creep intent). See AC #14.

---

## Decisions Table

| ID | Decision | Rationale |
|----|----------|-----------|
| D-15.01 | DIY class-component `ChartErrorBoundary` (NOT `react-error-boundary` library) | `react-error-boundary` not in `package.json`; project's existing `ErrorBoundary.tsx` is already a class-component pattern; adding a new dependency for 3-chart wrapping is disproportionate |
| D-15.02 | Wrapper at call site (parent), NOT inside chart file | Chart components are pure render functions; boundary is a composition concern of the parent. Consistent with `ErrorBoundary` wrapping `<App>` in `main.tsx` |
| D-15.03 | Regression injection via prop injection in dev (Option C) | Zero new dependency; minimal setup; single verifier session; consistent with Sentinel minimal-deps philosophy |
| D-15.04 | NO auto-reload on ErrorBoundary (no `window.location.reload()` button) | Auto-reload would mask repeat failures; documented as anti-pattern from Phase 14 WR-02 (401 reload-loop guard). ErrorBoundary reveals the failure state visually; operator can reload manually if needed |
| D-15.05 | Empty-state copy upgraded via i18n-keys.ts SSoT (no inline literals in JSX) | Pattern locked Phase 12+13+14: all user-visible strings live in `i18n-keys.ts`. Zero inline strings in component JSX. |
| D-15.06 | `ChartErrorBoundary` placed in `frontend/src/components/primitives/` (new subdirectory) | Distinguishes error-boundary infrastructure from UI primitives in `components/ui/`. New `primitives/` dir for framework-level concerns (one file only in Phase 15). |
| D-15.07 | `CHART_EMPTY_COPY` keys: `revenueTrend`, `environmentBar`, `geoBreakdown` (camelCase object keys) | Matches existing pattern: `REVENUE_LABELS.status24h`, `REVENUE_LABELS.baseline7w` etc. Object keys are camelCase; object name is UPPER_SNAKE. |

---

## File-Count Gate

Exactly **5 files modified or created** in Phase 15. No more, no less.

| # | File | Operation | Change |
|---|------|-----------|--------|
| 1 | `frontend/src/lib/i18n-keys.ts` | MODIFY | Append `CHART_EMPTY_COPY` + `CHART_ERROR_COPY` exports (pure append, zero deletions on existing lines) |
| 2 | `frontend/src/components/primitives/ChartErrorBoundary.tsx` | CREATE | New class-component ErrorBoundary (chart-area scoped, no full-page, no reload) |
| 3 | `frontend/src/components/charts/RevenueTrendChart.tsx` | MODIFY | Replace inline empty string with `CHART_EMPTY_COPY.revenueTrend` |
| 4 | `frontend/src/components/charts/EnvironmentBarChart.tsx` | MODIFY | Replace inline empty string with `CHART_EMPTY_COPY.environmentBar` |
| 5 | `frontend/src/components/charts/GeoBreakdownPieChart.tsx` | MODIFY | Replace inline empty string with `CHART_EMPTY_COPY.geoBreakdown` |

**Note on ErrorBoundary wrapping (D-15.02):** The `<ChartErrorBoundary>` wrapper is placed at the CALL SITE in parent components (e.g. `EnvironmentSplitSection.tsx`, `GeoBreakdownSection.tsx`, the alert detail page rendering `RevenueTrendChart`). These parent files ARE modified (additional wrapper tag + import). The planner MUST identify and count these call-site files in the PLAN.md file list. They are NOT listed above because they depend on the grep of actual call sites (verified at plan-time, not spec-time).

---

## Mechanical Acceptance Criteria

Executor uses these as grep-verifiable assertions before marking Phase 15 complete.

### i18n-keys.ts additions (AC #1–4)

- **AC #01** — `grep -c "CHART_EMPTY_COPY" frontend/src/lib/i18n-keys.ts` returns >= 1 (export exists)
- **AC #02** — `grep "revenueTrend:" frontend/src/lib/i18n-keys.ts` returns exactly the locked string: `'No 7-week history. Alert < 7 days old or data not yet aggregated.'`
- **AC #03** — `grep "environmentBar:" frontend/src/lib/i18n-keys.ts` returns string containing `'No environment split data.'`
- **AC #04** — `grep "geoBreakdown:" frontend/src/lib/i18n-keys.ts` returns string containing `'No geo breakdown data.'`

### ChartErrorBoundary primitive (AC #5–9)

- **AC #05** — `test -f frontend/src/components/primitives/ChartErrorBoundary.tsx` exits 0
- **AC #06** — `grep "getDerivedStateFromError" frontend/src/components/primitives/ChartErrorBoundary.tsx` returns >= 1 match
- **AC #07** — `grep "componentDidCatch" frontend/src/components/primitives/ChartErrorBoundary.tsx` returns >= 1 match
- **AC #08** — `grep "console.error" frontend/src/components/primitives/ChartErrorBoundary.tsx` returns >= 1 match (diagnostic log present)
- **AC #09** — `grep "window.location.reload" frontend/src/components/primitives/ChartErrorBoundary.tsx` returns 0 matches (no auto-reload — anti-pattern D-15.04)

### Chart empty-state copy replacement (AC #10–12)

- **AC #10** — `grep "CHART_EMPTY_COPY.revenueTrend" frontend/src/components/charts/RevenueTrendChart.tsx` returns >= 1 match
- **AC #11** — `grep "CHART_EMPTY_COPY.environmentBar" frontend/src/components/charts/EnvironmentBarChart.tsx` returns >= 1 match
- **AC #12** — `grep "CHART_EMPTY_COPY.geoBreakdown" frontend/src/components/charts/GeoBreakdownPieChart.tsx` returns >= 1 match

### No-inline-string anti-creep (AC #13)

- **AC #13** — None of the 3 chart files contain the OLD inline strings post-phase:
  ```bash
  grep "No revenue trend data available" frontend/src/components/charts/RevenueTrendChart.tsx  # → 0
  grep "No environment data available" frontend/src/components/charts/EnvironmentBarChart.tsx   # → 0
  grep "No geographic data available" frontend/src/components/charts/GeoBreakdownPieChart.tsx  # → 0
  ```

### No try/catch suppression anti-creep (AC #14)

- **AC #14** — No silent catch introduced inside chart render functions:
  ```bash
  grep -n "catch" frontend/src/components/charts/RevenueTrendChart.tsx      # → 0
  grep -n "catch" frontend/src/components/charts/EnvironmentBarChart.tsx     # → 0
  grep -n "catch" frontend/src/components/charts/GeoBreakdownPieChart.tsx    # → 0
  ```

### ErrorBoundary composition at call sites (AC #15–17)

- **AC #15** — `grep -r "ChartErrorBoundary" frontend/src/` returns >= 3 matches (primitive definition + minimum 3 call-site usages, one per chart)
- **AC #16** — `grep -r "min-h-screen" frontend/src/components/primitives/ChartErrorBoundary.tsx` returns 0 matches (no full-page takeover — chart-scoped only)
- **AC #17** — Each chart component file still exports its named component function (no restructuring):
  ```bash
  grep "export function RevenueTrendChart" frontend/src/components/charts/RevenueTrendChart.tsx   # → 1
  grep "export function EnvironmentBarChart" frontend/src/components/charts/EnvironmentBarChart.tsx # → 1
  grep "export function GeoBreakdownPieChart" frontend/src/components/charts/GeoBreakdownPieChart.tsx # → 1
  ```

### Design token anti-creep (AC #18)

- **AC #18** — No new color token introduced in Phase 15 diff (beyond `text-red-500` which is the only permitted exception, and only inside `ChartErrorBoundary.tsx`):
  ```bash
  git diff frontend/src/components/charts/ | grep "^\+" | grep -E "bg-[a-z]+-[0-9]+" | grep -v "^+++"
  # → 0 matches (chart files receive no new bg- classes)
  ```

### TypeScript compile gate (AC #19)

- **AC #19** — `npx tsc --noEmit` exits 0 after all Phase 15 changes (no new TS errors introduced)

### i18n-keys.ts pure-append discipline (AC #20)

- **AC #20** — Existing exports in `i18n-keys.ts` byte-identical post-phase:
  ```bash
  git diff frontend/src/lib/i18n-keys.ts | grep "^-" | grep -v "^---"
  # → 0 lines deleted (pure append only)
  ```

---

## Visual UAT Checks (Manual — localhost:5173)

Three visual sign-off items for the operator to verify at runtime before marking Phase 15 complete.

### UAT #1 — Empty-state diagnostic copy renders correctly

**Setup:** Navigate to an alert detail page where `RevenueTrendChart`, `EnvironmentBarChart`, or `GeoBreakdownPieChart` has no data (alert < 7 days old or empty env/geo split).

**Expected:** Each chart area shows the diagnostic sentence (not the old generic strings). For example: "No 7-week history. Alert < 7 days old or data not yet aggregated." — visible in the chart container at chart-area height.

**Pass criteria:** All 3 diagnostic strings are readable, correctly sized (`text-sm`), gray (`text-gray-400`), and vertically centered within the chart container.

### UAT #2 — ErrorBoundary fallback renders at chart-area size (not full-page)

**Setup:** Using prop injection (D-15.03 Option C), temporarily pass `data={null as any}` to one of the 3 chart components at its call site. Reload the alert detail page.

**Expected:** The fallback message "Chart unavailable. Reload the page if this persists." appears within the chart-area container (gray background, bordered, same height as the chart would have been). The rest of the alert detail page (other sections, header, sidebar) remains fully functional.

**Pass criteria:** (a) Fallback is chart-sized, NOT full-page. (b) Adjacent sections (TriageSection, ContributorsSection, etc.) render normally. (c) No `console.error` exception about React tree crash (the boundary caught it cleanly — `console.error('[ChartErrorBoundary]', ...)` IS expected in devtools from `componentDidCatch`).

### UAT #3 — No page crash on malformed payload (SC #3 of ROADMAP)

**Setup:** Using prop injection (D-15.03), pass intentionally malformed data that causes the chart render to throw (e.g. `[{ timestamp: null, revenue: NaN }]` to `RevenueTrendChart`).

**Expected:** The page does NOT crash to blank. The `<ChartErrorBoundary>` fallback UI replaces only the broken chart. The rest of the page remains intact.

**Pass criteria:** ROADMAP Success Criterion #3 satisfied: "inject malformed payload → UI shows fallback instead of crash."

---

## Open Questions

None. All design decisions are fully locked from:
- REQUIREMENTS.md CORR-07 (copy verbatim) and CORR-10 (component scope verbatim)
- Existing `frontend/package.json` (no `react-error-boundary` → DIY confirmed)
- Existing `ErrorBoundary.tsx` (class-component pattern confirmed as project standard)
- Existing 3 chart components (container pattern, class names, empty-state shape — all inspected)
- Phase 12+13+14 UI-SPECs (design system, anti-creep rules inherited)

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
