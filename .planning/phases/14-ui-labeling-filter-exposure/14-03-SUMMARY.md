---
phase: 14
plan: "03"
subsystem: frontend-dashboard-wiring
tags: [dashboard, ui, scope-badge, reference-period-footnote, corr-04, corr-05, wave-2]
dependency_graph:
  requires: [Plan 14-01 i18n-keys + utils foundation (3807c85), Plan 14-02 UI primitives (1325b9c)]
  provides: [ScopeBadge rendered on KpiCards, RevenueStatus24h, RevenueByChannel; ReferencePeriodFootnote rendered on KpiCards, RevenueStatus24h, RevenueByChannel]
  affects: [Plans 14-04 14-05 — AC #4 + #16 now 3/5 closed; plan 14-04 must close remaining 2/5]
tech_stack:
  added: []
  patterns: [col-span-full grid wrapper pattern, CardHeader flex-row badge placement, CardContent end-of-content footnote]
key_files:
  created: []
  modified:
    - frontend/src/components/dashboard/KpiCards.tsx
    - frontend/src/components/dashboard/RevenueStatus24h.tsx
    - frontend/src/components/dashboard/RevenueByChannel.tsx
decisions:
  - "D-14.03-A — No GrossNetToggle on dashboard cards per UI-SPEC §'Why dashboard cards show gross-only in Phase 14' lines 404-406. Network-level aggregates are PBI-comparable in gross only. RC-(c) closes via Plan 14-04 (RevenueStatusSection) + Plan 14-05 (PublishersPage)."
  - "D-14.03-B — RevenueByChannel.tsx stale <p>...GOOGLE_ADEX only. Multi-channel breakdown pending from IT.</p> (lines 67-69 pre-commit) REPLACED by ScopeBadge. The 'pending from IT' addendum removed — Phase 14 closes the email-Vito loop; future multi-channel surface is Phase 17+."
  - "D-14.03-C — KpiCards: ScopeBadge in <div className='col-span-full flex justify-end mb-2'> above 4-card grid. ReferencePeriodFootnote in <div className='col-span-full'> below grid. Both inside the existing grid container — col-span-full spans all breakpoints."
  - "D-14.03-D — RevenueStatus24h: ScopeBadge placed in CardHeader's <div className='flex items-center gap-3'> between CardTitle and date <select>. ReferencePeriodFootnote at end of CardContent (after chart), default variant='card'."
  - "D-14.03-E — timestamp source = data.date for all 3 files. KpiCards receives data: RevenueStatus24hResponse (non-null in the render branch). RevenueStatus24h uses useRevenueStatus24h() which returns data.date. RevenueByChannel also calls useRevenueStatus24h() — data.date confirmed present (same response shape). No fallback needed."
metrics:
  duration: ~8min
  completed_date: "2026-04-30"
  tasks: 4
  files: 3
---

# Phase 14 Plan 03: Dashboard Wiring (ScopeBadge + ReferencePeriodFootnote) — Summary

**One-liner:** Wave 2 single-commit wiring of ScopeBadge + ReferencePeriodFootnote onto 3 dashboard surfaces (KpiCards, RevenueStatus24h, RevenueByChannel), replacing the stale "pending from IT" paragraph with the Phase 14 Badge primitive — 16 insertions, 3 deletions, TypeScript clean.

---

## Commit

| Commit | Hash | Files | Insertions | Deletions |
|--------|------|-------|------------|-----------|
| `feat(dashboard): wire ScopeBadge + ReferencePeriodFootnote to KpiCards/RevenueStatus24h/RevenueByChannel (Phase 14 CORR-04+05)` | `f61582b` | 3 | 16 | 3 |

`git diff HEAD~1 HEAD --shortstat` → `3 files changed, 16 insertions(+), 3 deletions(-)`.

Branch: `main`. No push (R-05 + R-06).

---

## Files Modified

### `frontend/src/components/dashboard/KpiCards.tsx`

- **Added imports (lines 6-7):**
  ```ts
  import { ScopeBadge } from '../ui/ScopeBadge'
  import { ReferencePeriodFootnote } from '../ui/ReferencePeriodFootnote'
  ```
- **Added above the 4 MetricCards (new lines 80-82):**
  ```tsx
  <div className="col-span-full flex justify-end mb-2">
    <ScopeBadge channel="GOOGLE_ADEX" />
  </div>
  ```
- **Added below the 4 MetricCards (new lines 107-109):**
  ```tsx
  <div className="col-span-full">
    <ReferencePeriodFootnote timestamp={data.date} />
  </div>
  ```
- **Phase 13 ship-state:** 4 MetricCards (RPM, CTR, Viewability, GrossMargin) unchanged. KPI_LABELS still used 5×. Loading branch and empty branch unchanged.

### `frontend/src/components/dashboard/RevenueStatus24h.tsx`

- **Added imports (lines 17-18):**
  ```ts
  import { ScopeBadge } from '../ui/ScopeBadge'
  import { ReferencePeriodFootnote } from '../ui/ReferencePeriodFootnote'
  ```
- **Added in CardHeader flex row (new line 83), between CardTitle and date selector:**
  ```tsx
  <ScopeBadge channel="GOOGLE_ADEX" />
  ```
- **Added at end of CardContent (new line 230), after Recharts chart:**
  ```tsx
  <ReferencePeriodFootnote timestamp={data.date} />
  ```
- **Phase 13 ship-state:** date `<select>`, inline-stats row (revenue / baseline7w / yoy7w), full Recharts AreaChart body, Legend, all tooltip logic unchanged.

### `frontend/src/components/dashboard/RevenueByChannel.tsx`

- **Added imports (lines 17-18):**
  ```ts
  import { ScopeBadge } from '../ui/ScopeBadge'
  import { ReferencePeriodFootnote } from '../ui/ReferencePeriodFootnote'
  ```
- **Added in CardHeader flex row (new line 54), between CardTitle and date selector:**
  ```tsx
  <ScopeBadge channel="GOOGLE_ADEX" />
  ```
- **REMOVED stale paragraph (was lines 67-69 pre-commit):**
  ```tsx
  <p className="mt-1.5 text-xs text-slate-400">
    Hourly data — GOOGLE_ADEX only. Multi-channel breakdown pending from IT.
  </p>
  ```
- **Added at end of CardContent (new line 141), after Recharts chart:**
  ```tsx
  <ReferencePeriodFootnote timestamp={data.date} />
  ```
- **Phase 13 ship-state:** Recharts AreaChart (channelGradient, Baseline 7w + Google AdX areas), date `<select>`, `<ResponsiveContainer>` all unchanged.

---

## Verification Results

### TypeScript compile

```
cd frontend && npx tsc --noEmit -p tsconfig.app.json
→ exit 0, no output (clean)
```

### AC #5 + #18 invariant (global)

```
grep -nE "'GOOGLE_ADEX only|\"GOOGLE_ADEX only" [3 dashboard files]
→ 0 matches  (AC #18 PASS)

grep -nE "'as of |\"as of " [3 dashboard files]
→ 0 matches  (AC #5 PASS)
```

### Stale paragraph removed

```
grep -c "pending from IT" frontend/src/components/dashboard/RevenueByChannel.tsx
→ 0  (PASS)
grep -c "GOOGLE_ADEX only" frontend/src/components/dashboard/RevenueByChannel.tsx
→ 0  (PASS)
```

### Per-file AC pass table

| File | ScopeBadge import | ReferencePeriodFootnote import | ScopeBadge render | RPF render | timestamp={data.date} | Phase-13 preserved |
|------|:-----------------:|:------------------------------:|:-----------------:|:----------:|:---------------------:|:-----------------:|
| KpiCards.tsx | 1 ✓ | 1 ✓ | 1 ✓ | 1 ✓ | 1 ✓ | MetricCards×4 ✓ |
| RevenueStatus24h.tsx | 1 ✓ | 1 ✓ | 1 ✓ | 1 ✓ | 1 ✓ | select×1, REVENUE_LABELS.status24h×1 ✓ |
| RevenueByChannel.tsx | 1 ✓ | 1 ✓ | 1 ✓ | 1 ✓ | 1 ✓ | ResponsiveContainer×1 ✓ |

### Commit AC

```
git log -1 --pretty=%s
→ feat(dashboard): wire ScopeBadge + ReferencePeriodFootnote to KpiCards/RevenueStatus24h/RevenueByChannel (Phase 14 CORR-04+05) ✓
git diff HEAD~1 HEAD --name-only | sort
→ frontend/src/components/dashboard/KpiCards.tsx ✓
→ frontend/src/components/dashboard/RevenueByChannel.tsx ✓
→ frontend/src/components/dashboard/RevenueStatus24h.tsx ✓
git branch --show-current → main ✓
git diff HEAD~1 HEAD --shortstat → 3 files changed ✓
```

### Browser smoke note

Visual verification deferred to Phase 14 HUMAN-UAT checkpoint. TypeScript compile is clean (exit 0), and all component imports are resolvable (ScopeBadge, ReferencePeriodFootnote, Badge, ChannelGroup type, formatTimestampUtc, REFERENCE_PERIOD_COPY, SCOPE_BADGE_COPY all verified present at HEAD from Plans 14-01 + 14-02).

---

## Decisions Made

### D-14.03-A — No GrossNetToggle on dashboard (gross-only, PBI-aligned)

Per UI-SPEC §"Why dashboard cards show gross-only in Phase 14" lines 404-406: dashboard KpiCards, RevenueStatus24h, and RevenueByChannel surface network-level PBI-comparable aggregates — gross-only by design. Adding a GrossNetToggle here would be feature creep. RC-(c) (gross/net side-by-side label) is closed by Plan 14-04 (RevenueStatusSection in alert detail) + Plan 14-05 (PublishersPage).

### D-14.03-B — Stale paragraph REMOVED, not preserved alongside ScopeBadge

The `<p className="mt-1.5 text-xs text-slate-400">Hourly data — GOOGLE_ADEX only. Multi-channel breakdown pending from IT.</p>` in RevenueByChannel.tsx was a pre-Phase-08 era operator note. Per UI-SPEC §"Component Inventory" line 193, this paragraph is REPLACED (not supplemented) by `<ScopeBadge channel="GOOGLE_ADEX" />`. Keeping both would violate AC #18 (double disclosure + "GOOGLE_ADEX only" inline literal still present). The "pending from IT" addendum is stale — Phase 14 closes the email-Vito loop with the Badge primitive. Future multi-channel surface (Phase 17+) will add a new card, not resurrect this paragraph.

### D-14.03-C — col-span-full pattern for KpiCards badge + footnote rows

`col-span-full` is the correct Tailwind class to span all grid columns in a CSS grid. Both the ScopeBadge row (above) and the ReferencePeriodFootnote row (below) use `col-span-full` inside the existing `grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4` container — they span 1 column on mobile, 2 on md, 4 on lg. `flex justify-end` on the badge row pushes ScopeBadge to the right edge (UI-SPEC line 461).

### D-14.03-D — ScopeBadge placement in RevenueStatus24h CardHeader

ScopeBadge inserted BETWEEN `<CardTitle>` and the date `<select>` (not after the select, not in a separate row). The existing `<div className="flex items-center gap-3">` provides the correct horizontal rhythm — `gap-3` separates the three elements visually. This matches UI-SPEC §"CORR-04 Placement matrix" line 462.

### D-14.03-E — timestamp = data.date confirmed on all 3 components

`RevenueStatus24hResponse.date` field (Phase 11 contract) is present on the `data` object in all 3 components:
- `KpiCards.tsx`: `data: RevenueStatus24hResponse` — non-null in the render branch (past loading + empty guards).
- `RevenueStatus24h.tsx`: calls `useRevenueStatus24h(selectedDate)` → `data.date` confirmed from the Phase 11 response shape.
- `RevenueByChannel.tsx`: also calls `useRevenueStatus24h(selectedDate)` — same response shape, `data.date` confirmed present. No fallback (`?? ''`) needed.

---

## Notes for Downstream Executors

### Plan 14-04 executor (RevenueStatusSection + TriageSection)

AC #4 (5 surfaces consume ReferencePeriodFootnote) and AC #16 (5 surfaces consume ScopeBadge) are now at **3/5 each**. Plan 14-04 must add the remaining 2:
- `RevenueStatusSection.tsx` — ScopeBadge in the section header + ReferencePeriodFootnote at section bottom
- `TriageSection.tsx` — ScopeBadge in the section header + ReferencePeriodFootnote at section bottom

Import paths from `frontend/src/components/alerts/*.tsx`:
```ts
import { ScopeBadge } from '../ui/ScopeBadge'
import { ReferencePeriodFootnote } from '../ui/ReferencePeriodFootnote'
```

`timestamp` source for alert-detail surfaces: the alert's `timestamp` field from the AlertState shape (NOT `data.date` from useRevenueStatus24h — the alert context has its own timestamp).

### Verifier note (AC #5 + #18 full-tree check)

AC #5 (no orphan `"as of "`) and AC #18 (no orphan `"GOOGLE_ADEX only"`) verifier greps must run on the **FULL frontend tree** post-Phase-14 (all 5 plans) — not just the 3 dashboard files. The primitives themselves contain the authoritative copy; consumer files must reference the primitives only (never inline the strings).

---

## Deviations from Plan

None — plan executed exactly as written. All 4 tasks completed in sequence. D-14.03-A through D-14.03-E decisions documented inline. D-14.03-E required no fallback (`?? ''`) because `data.date` was confirmed present on the `useRevenueStatus24h` response shape used by all 3 components.

---

## Known Stubs

None. All 3 components receive live `data` from TanStack Query (via `useRevenueStatus24h`). ScopeBadge renders `channel + SCOPE_BADGE_COPY.suffix` from the i18n SSoT. ReferencePeriodFootnote renders `formatTimestampUtc(data.date)` from the live response timestamp. No hardcoded empty values, no placeholder text, no disconnected props.

---

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes. The 3 modified files are frontend presentation components only. All STRIDE threats in the plan's threat register (T-14-03-01 through T-14-03-07) are mitigated or accepted as documented — specifically:
- T-14-03-01 (data.date tampering): `formatTimestampUtc` handles invalid input gracefully.
- T-14-03-02 (XSS via channel literal): `channel="GOOGLE_ADEX"` is a build-time JSX string constant, rendered as text node.
- T-14-03-06 (git push): no push executed, deploy-gate hook enforced.
- T-14-03-07 (paragraph removal): intentional per UI-SPEC §"Component Inventory" line 193 + D-14.03-B decision.

---

## Self-Check

Files exist:
- `frontend/src/components/dashboard/KpiCards.tsx` → FOUND (modified, 111 lines post-edit)
- `frontend/src/components/dashboard/RevenueStatus24h.tsx` → FOUND (modified, 233 lines post-edit)
- `frontend/src/components/dashboard/RevenueByChannel.tsx` → FOUND (modified, 142 lines post-edit)

Commit exists:
- `f61582b` → FOUND on main

## Self-Check: PASSED
