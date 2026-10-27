---
phase: 14
plan: "04"
subsystem: frontend-alert-detail-wiring
tags: [alerts, ui, scope-badge, reference-period-footnote, gross-net-toggle, corr-02, corr-03, corr-05, rc-c-closure, wave-2]
dependency_graph:
  requires: [Plan 14-01 i18n-keys + utils foundation (3807c85), Plan 14-02 UI primitives (1325b9c), Plan 14-03 dashboard wiring (f61582b)]
  provides: [ScopeBadge + ReferencePeriodFootnote on RevenueStatusSection + TriageSection; GrossNetToggle on RevenueStatusSection; page-level GrossNetMode state in AlertDetailPage; RC-(c) closure at alert detail layer]
  affects: [Plan 14-05 — AC #4 now 5/5 complete; AC #16 now 5/5 complete; AC #11 now 1/2 (Plan 14-05 delivers 2/2 on PublishersPage)]
tech_stack:
  added: []
  patterns: [B-1 iter-1 page-level state lift (AlertDetailPage owns GrossNetMode, threads to children); REV_SHARE_FACTOR multiplication in two alert components; revenue_gross ?? revenue_current fallback chain; mode-invariant delta % with mode-aware EUR values]
key_files:
  created: []
  modified:
    - frontend/src/components/alerts/RevenueStatusSection.tsx
    - frontend/src/components/alerts/TriageSection.tsx
    - frontend/src/pages/AlertDetailPage.tsx
decisions:
  - "D-14.04-B (B-1 iter-1): page-level useState<GrossNetMode>('gross') lives in AlertDetailPage and is threaded as props. RevenueStatusSection receives mode + onModeChange (renders GrossNetToggle); TriageSection receives mode only (read-only Revenue row). Closes UI-SPEC §CORR-03 line 408 mandate."
  - "D-14.04-C: REV_SHARE_FACTOR imported from i18n-keys.ts — zero inline 0.6 literals in alert components. GROSS_NET_LABELS.{gross,net}Suffix used for all label interpolation."
  - "D-14.04-D: net computation = (revenue_gross ?? revenue_current) * REV_SHARE_FACTOR for current; revenue_baseline * REV_SHARE_FACTOR for baseline. Delta % is mode-invariant in both components."
  - "D-14.04-F: TriageSection ReferencePeriodFootnote placed BEFORE BASELINE_MISSING_COPY per UI-SPEC line 736 ordering (table → footnote → BASELINE_MISSING_COPY → A6 → A7). BASELINE_MISSING_COPY + A6/A7 blocks + RC-(e) comment preserved byte-identical."
  - "D-14.04-G: RevenueStatusSection margin_metrics A5 sub-grid (lines 61-103 original) + Revenue Trend chart preserved byte-identical. Only 4-card grid and CardHeader modified."
  - "TriageSection dual import from i18n-keys: BASELINE_MISSING_COPY on line 4, GROSS_NET_LABELS+REV_SHARE_FACTOR on line 10 (separate import statements). TypeScript handles two imports from same module cleanly."
metrics:
  duration: ~6min
  completed_date: "2026-04-30"
  tasks: 4
  files: 3
---

# Phase 14 Plan 04: Alert Detail Wiring (ScopeBadge + GrossNetToggle + ReferencePeriodFootnote) — Summary

**One-liner:** Wave 2 single-commit B-1 iter-1 page-level state lift — AlertDetailPage owns GrossNetMode and threads it to RevenueStatusSection (toggle + multiplied EUR cards) + TriageSection (mode-aware Revenue row), closing RC-(c) email-Vito #4e at the alert detail layer with ScopeBadge + ReferencePeriodFootnote on both surfaces.

---

## Commit

| Commit | Hash | Files | Insertions | Deletions |
|--------|------|-------|------------|-----------|
| `feat(alerts): wire ScopeBadge + ReferencePeriodFootnote + GrossNetToggle to RevenueStatusSection + TriageSection + lift mode state to AlertDetailPage (Phase 14 CORR-02+03+05)` | `64ff8b1` | 3 | 79 | 16 |

Branch: `main`. No push (R-05 + R-06).

---

## Files Modified

### `frontend/src/components/alerts/RevenueStatusSection.tsx`

**Before (113 lines):** Props: `{ alert, trendData? }`. No mode awareness. Direct `alert.revenue_current` / `alert.revenue_baseline` for cards. Static "Current Revenue" / "Baseline (7-week avg)" labels. No ScopeBadge, no GrossNetToggle, no ReferencePeriodFootnote.

**After (130 lines):** Props extended: `{ alert, trendData?, mode, onModeChange }`. 4 new imports (ScopeBadge, ReferencePeriodFootnote, GrossNetToggle+GrossNetMode type, GROSS_NET_LABELS+REV_SHARE_FACTOR). CardHeader right-side flex group: `<ScopeBadge channel=...> + <GrossNetToggle value={mode} onChange={onModeChange}> + {A2 Badge conditional}`. 4-card grid: Current Revenue + Baseline use `displayedCurrent` / `displayedBaseline` + template-literal suffix from `GROSS_NET_LABELS`. `deltaEur = displayedCurrent - displayedBaseline`. `revenue_delta_pct` mode-invariant. `ReferencePeriodFootnote variant="card"` at end of CardContent. `useState` NOT imported (state lives in AlertDetailPage per B-1 iter-1). Margin_metrics A5 sub-grid + RevenueTrendChart byte-identical.

### `frontend/src/components/alerts/TriageSection.tsx`

**Before (230 lines):** Props: `{ alert }`. CardHeader: CardTitle + TriageBadge. Revenue row used raw `alert.revenue_current` / `alert.revenue_baseline`. No ScopeBadge, no ReferencePeriodFootnote.

**After (252 lines):** Props extended: `{ alert, mode }`. 4 new imports (ScopeBadge, ReferencePeriodFootnote, GrossNetMode type, GROSS_NET_LABELS+REV_SHARE_FACTOR). CardHeader right-side flex group: `<ScopeBadge> + <TriageBadge>`. Revenue row: `revGrossCurrent = revenue_gross ?? revenue_current`, `revDisplayedCurrent/Baseline` mode-aware, `revSuffix` from GROSS_NET_LABELS, metric label = `` `Revenue ${revSuffix}` ``. Delta % mode-invariant. `ReferencePeriodFootnote variant="inline" className="mt-3 block"` inserted BETWEEN table div and BASELINE_MISSING_COPY conditional per UI-SPEC line 736. BASELINE_MISSING_COPY + A6/A7 blocks + RC-(e) comment + DirectionIcon + helper functions BYTE-IDENTICAL.

### `frontend/src/pages/AlertDetailPage.tsx`

**Before (319 lines):** No GrossNetMode state. RevenueStatusSection and TriageSection rendered without mode props.

**After (325 lines):** Added `import type { GrossNetMode }` from GrossNetToggle. Added `const [grossNetMode, setGrossNetMode] = useState<GrossNetMode>('gross')` (B-1 iter-1 page-level state lift per UI-SPEC §CORR-03 line 408). `<RevenueStatusSection ... mode={grossNetMode} onModeChange={setGrossNetMode} />`. `<TriageSection alert={alert} mode={grossNetMode} />`.

---

## Acceptance Criteria Verification

All AC verified by grep against HEAD:

| AC | Check | Result |
|----|-------|--------|
| AlertDetailPage owns useState<GrossNetMode>('gross') | `grep -c "useState<GrossNetMode>('gross')" AlertDetailPage.tsx` | 1 |
| RevenueStatusSection no useState | `grep -c "import.*useState" RevenueStatusSection.tsx` | 0 |
| AC #9: zero 0.6 literal | `grep -nE '\* 0\.6\b\|0\.6 \*' alerts/*.tsx` | 0 matches |
| AC #5/#10/#18: zero inline copy | `grep -nE "'as of \|GOOGLE_ADEX only\|\(gross\)\|\(net\)\|Net \(post rev-share 60%"` | 0 matches |
| Phase 11 RC-(e) preserved: BASELINE_MISSING_COPY | `grep -c "BASELINE_MISSING_COPY" TriageSection.tsx` | 2 (import + render) |
| Phase 11: A6 block preserved | `grep -c "alert_rule === 'A6'"` | 1 |
| Phase 11: A7 block preserved | `grep -c "alert_rule === 'A7'"` | 1 |
| Phase 11: baseline_bacino consumption | `grep -c "baseline_bacino"` | 2 |
| TypeScript clean | `cd frontend && npx tsc --noEmit` | 0 errors |

---

## Deviations from Plan

None — plan executed exactly as written.

The B-1 iter-1 scope (mode threading to BOTH RevenueStatusSection and TriageSection's Revenue row) was already the live spec in the plan's must_haves and decisions at read time. No deviation from that framing.

---

## Known Stubs

None. All wiring is live — mode prop is functional, REV_SHARE_FACTOR multiplication is real, ScopeBadge renders actual `alert.channel_group`, ReferencePeriodFootnote renders actual `alert.timestamp`. No hardcoded values flow to UI rendering.

---

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes introduced. Frontend-only change — no threat surface added.

## Self-Check: PASSED
