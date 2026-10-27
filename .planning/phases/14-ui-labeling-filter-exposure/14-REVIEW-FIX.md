---
phase: 14-ui-labeling-filter-exposure
fixed_at: 2026-04-30T22:00:00Z
review_path: .planning/phases/14-ui-labeling-filter-exposure/14-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 14: Code Review Fix Report

**Fixed at:** 2026-04-30T22:00:00Z
**Source review:** .planning/phases/14-ui-labeling-filter-exposure/14-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (1 Critical, 2 Warning; Info skipped per fix_scope=critical_warning)
- Fixed: 3
- Skipped: 0

Post-fix verification:
- `npx tsc --noEmit -p tsconfig.app.json` → exit 0 (clean)
- Anti-creep AC #9 grep (`0\.6` in `frontend/src/`) → only `REV_SHARE_FACTOR=0.6` in `i18n-keys.ts:113` (SSoT) plus mock data, comments, unrelated thresholds, DocsPage text — matches reviewer's pre-fix PASS baseline
- Anti-creep AC #5 grep (`as of ` in `frontend/src/`) → only `ReferencePeriodFootnote.tsx` (docstring) and `i18n-keys.ts` (SSoT) — matches reviewer's pre-fix PASS baseline

## Fixed Issues

### CR-01: Rules of Hooks violation in PublishersPage — `useMemo` called after conditional early returns

**Files modified:** `frontend/src/pages/PublishersPage.tsx`
**Commit:** b1f1eee
**Applied fix:** Moved both `useMemo` calls (`tierMap` and `data`) ABOVE the `if (isLoading)` and `if (error)` early-returns, so all hooks are called in the same order on every render. Deleted the two `// eslint-disable-next-line react-hooks/rules-of-hooks` comments that were masking the bug. Added an inline comment block explaining the CR-01 fix and why the order matters. Logic for `rawData = publishers ?? []`, `tierMap`, and `data` is unchanged — only their position relative to the guards moved. TypeScript clean.

### WR-01: Division-by-zero in TriageSection baseline delta math (NaN/Infinity propagation)

**Files modified:** `frontend/src/components/alerts/TriageSection.tsx`
**Commit:** 5b78af1
**Applied fix:** Tightened the `baselineMissing` guard on line 51 to also catch literal `0` for both fields (`baselineBacino === 0 || baselineCoverage === 0`), preventing `(current - 0) / 0 → Infinity` from rendering as the raw string "Infinity%" in the table. Added an inline comment explaining the rationale and explicitly noting that the dedicated A6 coverage-zero block (lines 156-186) gates on `alert.alert_rule === 'A6' && alert.coverage_zero_cause`, NOT on `baselineMissing`, so widening this guard does not regress the A6 path. TypeScript clean.

### WR-02: Silent reload-on-401 in fetchJSON can produce a reload loop

**Files modified:** `frontend/src/api/client.ts`
**Commit:** 984b660
**Applied fix:** Added a module-level `let authReloadAttempted = false` flag at module scope, and gated `window.location.reload()` behind `if (!authReloadAttempted) { authReloadAttempted = true; window.location.reload() }`. With multiple in-flight queries (refetchInterval on `useAlerts` 30s and `useHealth` 60s), several concurrent 401s would otherwise each call reload, producing a stuck-loading UX. The flag resets on the next page load (module re-init), giving the user one reload attempt per session boot. Kept the existing `throw new Error('Session expired')` so downstream error handling still triggers. TypeScript clean.

## Skipped Issues

None — all three in-scope findings (1 Critical + 2 Warning) were fixed cleanly. Info-severity findings (IN-01 through IN-08) are out of scope for `fix_scope=critical_warning`.

---

_Fixed: 2026-04-30T22:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
