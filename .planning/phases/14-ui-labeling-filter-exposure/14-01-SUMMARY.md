---
phase: 14
plan: "01"
subsystem: frontend-i18n
tags: [i18n, constants, utils, labeling, wave-1-foundation]
dependency_graph:
  requires: [phase-13 HEAD a4baf2e, frontend/src/lib/i18n-keys.ts Phase-12+13-state, frontend/src/lib/utils.ts Phase-12+13-state]
  provides: [REV_SHARE_FACTOR SSoT, formatTimestampUtc helper, REFERENCE_PERIOD_COPY, SCOPE_BADGE_COPY, GROSS_NET_LABELS, TOP_N_DISCLAIMER_COPY, MONTH_LABELS, GEO_LABELS, PUBLISHER_TIER_LABELS, ENVIRONMENT_LABELS, emptyPublishersMultiFiltered]
  affects: [Plans 14-02 14-03 14-04 14-05 — all consumers of the above exports]
tech_stack:
  added: []
  patterns: [constants-first wave, pure-append diff, SSoT scalar export for numeric constant]
key_files:
  created: []
  modified:
    - frontend/src/lib/i18n-keys.ts
    - frontend/src/lib/utils.ts
decisions:
  - "D-14.01-A — REV_SHARE_FACTOR scalar = single source of truth at module-level UPPER_CASE export. No inline 0.6 in any component file. AC #9 anti-creep verified: grep -rn '\\* 0\\.6\\b|0\\.6 \\*' frontend/src/ returns ZERO matches."
  - "D-14.01-B — formatTimestampUtc lives in lib/utils.ts (existing helper file), NOT a new file. Output locked to '13 Jan 2026 08:57 UTC' format using toLocaleDateString('en-GB', {timeZone:'UTC'}) + toLocaleTimeString('en-GB', {hour12:false, timeZone:'UTC'}). Smoke-tested via tsx: input '2026-01-13T08:57:00Z' → output exact string confirmed."
  - "D-14.01-C — All 9 new exports (including ENVIRONMENT_LABELS from W-1 iter-1) APPENDED to i18n-keys.ts after existing Phase 12+13 exports. NO reordering, NO modification of existing content. Pure-append diff: 125 insertions in i18n-keys.ts, 0 deletions."
  - "D-14.01-D — formatTimestampUtc placed at END of utils.ts (after formatTimestamp). Existing functions preserved byte-identical (no-semicolon convention maintained). New function uses semicolons inside body matching typed-module convention per D-12.01-04."
  - "D-14.01-E (iter-1 W-1) — ENVIRONMENT_LABELS added with 5 keys: all/WEB/AMP/APP/UNKNOWN, mirroring Environment type from frontend/src/types/alert.ts line 6. Ships as forward-compat no-op pending backend extension."
metrics:
  duration: ~5min
  completed_date: "2026-04-30"
  tasks: 3
  files: 2
---

# Phase 14 Plan 01: i18n-keys + utils Foundation — Summary

**One-liner:** Constants-first Wave 1 foundation: 9 new i18n exports (including `REV_SHARE_FACTOR = 0.6` SSoT and `ENVIRONMENT_LABELS`) plus `formatTimestampUtc` helper with locked `'13 Jan 2026 08:57 UTC'` format, pure-append 139-line diff on 2 files.

---

## Commit

| Commit | Hash | Files | Insertions | Deletions |
|--------|------|-------|------------|-----------|
| `feat(i18n): extend i18n-keys + utils for Phase 14 labeling primitives` | `3807c85` | 2 | 139 | 0 |

Pure-append diff, zero deletions. `git diff HEAD~1 HEAD --shortstat` → `2 files changed, 139 insertions(+)`.

Branch: `main`. No push (R-05 + R-06).

---

## Files Modified

### `frontend/src/lib/i18n-keys.ts`

- **Before:** 75 lines (Phase 12+13 ship-state at HEAD `568ffb0`)
- **After:** 199 lines (+125 lines, 0 deletions)
- **New exports (9 constants + 1 helper):**
  1. `REFERENCE_PERIOD_COPY` — CORR-02 + CORR-05, RC-(f) closure copy
  2. `SCOPE_BADGE_COPY` — CORR-04, RC-(a) partial closure
  3. `GROSS_NET_LABELS` — CORR-03, RC-(c) closure
  4. `REV_SHARE_FACTOR = 0.6` — SSoT for revenue multiplier (scalar, not `as const` object)
  5. `TOP_N_DISCLAIMER_COPY` — CORR-04, RC-(a) full closure
  6. `MONTH_LABELS` — CORR-11, 13 keys (all + 01-12)
  7. `GEO_LABELS` — CORR-11, 6 keys (all + ITA/ES/LATAM/PT/OTHER)
  8. `PUBLISHER_TIER_LABELS` — CORR-11, 4 keys (all + A/B/C)
  9. `ENVIRONMENT_LABELS` — CORR-11 W-1 iter-1, 5 keys (all + WEB/AMP/APP/UNKNOWN)
  10. `emptyPublishersMultiFiltered(activeFilters, year)` — multi-filter empty-state helper

### `frontend/src/lib/utils.ts`

- **Before:** 30 lines
- **After:** 43 lines (+14 lines, 0 deletions)
- **New export:** `formatTimestampUtc(iso: string): string`
  - Uses `toLocaleDateString('en-GB', {day:'2-digit', month:'short', year:'numeric', timeZone:'UTC'})`
  - Uses `toLocaleTimeString('en-GB', {hour:'2-digit', minute:'2-digit', hour12:false, timeZone:'UTC'})`
  - Returns `${date} ${time} UTC`

---

## Verification Results

### TypeScript compile

```
cd frontend && npx tsc --noEmit -p tsconfig.app.json
→ exit 0, no output (clean)
```

### Smoke test: `formatTimestampUtc` locked output

```
cd frontend && npx tsx -e "import {formatTimestampUtc} from './src/lib/utils.ts'; console.log(JSON.stringify(formatTimestampUtc('2026-01-13T08:57:00Z')))"
→ "13 Jan 2026 08:57 UTC"  ✓ (exact match to locked format)
```

### Anti-creep AC #9

```
grep -rn '\* 0\.6\b\|0\.6 \*' frontend/src/ --include='*.tsx' --include='*.ts'
→ (no output) ✓ Zero matches — REV_SHARE_FACTOR is the sole 0.6 in the codebase
```

### Export presence checks (all return 1)

| Export | Count |
|--------|-------|
| `export const REFERENCE_PERIOD_COPY` | 1 |
| `export const SCOPE_BADGE_COPY` | 1 |
| `export const GROSS_NET_LABELS` | 1 |
| `export const REV_SHARE_FACTOR = 0.6` | 1 |
| `export const TOP_N_DISCLAIMER_COPY` | 1 |
| `export const MONTH_LABELS` | 1 |
| `export const GEO_LABELS` | 1 |
| `export const PUBLISHER_TIER_LABELS` | 1 |
| `export const ENVIRONMENT_LABELS` | 1 |
| `export function emptyPublishersMultiFiltered` | 1 |
| `export function formatTimestampUtc(iso: string): string` | 1 |

### Copy strings (all return 1 unless noted)

| Check | Count |
|-------|-------|
| `'Net (post rev-share 60%)'` | 1 |
| `'Showing top '` | 1 |
| `'as of '` | 1 |
| `', EUR'` | 1 |
| `alertSuffix: ''` | 1 |
| `'GOOGLE_ADEX'` (AC #18 — must be 0) | 0 ✓ |
| `' only'` | 1 |

### Phase 12+13 ship-state preserved (all return 1)

| Check | Count |
|-------|-------|
| `export const KPI_LABELS` | 1 |
| `export const SELL_TYPE_LABELS` | 1 |
| `export const BASELINE_MISSING_COPY` | 1 |
| `export function emptyPublishersFiltered` | 1 |
| `export type SellTypeKey` | 1 |
| `export const REVENUE_LABELS` | 1 |
| `export const KPI_NO_DATA_COPY` | 1 |
| `export function cn` (utils.ts) | 1 |
| `export function formatCurrency` (utils.ts) | 1 |
| `export function formatPercent` (utils.ts) | 1 |
| `export function formatTimestamp(ts: string)` (utils.ts) | 1 |

### Pre-commit deletion check

```
git diff --cached | grep -cE "^-.*\b(KPI_LABELS|SELL_TYPE_LABELS|...)\b"
→ 0  ✓ (zero Phase 12+13 exports deleted)
```

### Commit verification

```
git log -1 --pretty=%s → feat(i18n): extend i18n-keys + utils for Phase 14 labeling primitives ✓
git log -1 --stat → 2 files changed, 139 insertions(+) ✓
git diff HEAD~1 HEAD --name-only → frontend/src/lib/i18n-keys.ts, frontend/src/lib/utils.ts (exactly 2) ✓
git branch --show-current → main ✓
git log -1 --name-only | grep data/vna_alerts.db → 0 (not committed) ✓
```

---

## Decisions Made

### D-14.01-A — REV_SHARE_FACTOR SSoT

`REV_SHARE_FACTOR = 0.6` exported as a scalar number constant (no `as const`) from `i18n-keys.ts`. This is the **sole** location of the value `0.6` as a revenue multiplier in the frontend codebase. UI-SPEC AC #9 verifier greps `\* 0\.6\b` and `0\.6 \*` over `frontend/src/` — must return zero matches outside `i18n-keys.ts`. Verified pre-commit: zero matches.

Plans 14-04 (RevenueStatusSection) and 14-05 (PublishersPage) MUST import this constant:
```ts
import { REV_SHARE_FACTOR } from '../../lib/i18n-keys';
// usage: value * REV_SHARE_FACTOR
```

### D-14.01-B — `formatTimestampUtc` placement and format lock

Function lives in `lib/utils.ts`, not a new file. Output format locked: `'13 Jan 2026 08:57 UTC'` for input `'2026-01-13T08:57:00Z'`. Smoke-tested via `npx tsx` — exact string match confirmed. Format uses `en-GB` locale + `timeZone:'UTC'` + `hour12:false`, closing email-Vito #5 (timeframe ambiguity).

### D-14.01-C — Pure-append discipline

All 9 new exports + 1 helper appended AFTER the closing line of `KPI_NO_DATA_COPY` (line 74). No reordering, no modification of existing content. Convention match: SCREAMING_SNAKE_CASE object consts, UPPER_CASE scalar (`REV_SHARE_FACTOR`), camelCase helper (`emptyPublishersMultiFiltered`), single quotes, semicolons, `as const` on objects.

### D-14.01-D — utils.ts convention preservation

`utils.ts` is the project outlier (no-semicolon convention per D-12.05-01). Existing functions preserved byte-identical. New `formatTimestampUtc` function uses semicolons inside its body (matching typed-module convention per D-12.01-04) while the export statement style follows the file's existing pattern.

### D-14.01-E — ENVIRONMENT_LABELS (W-1 iter-1)

`ENVIRONMENT_LABELS` added reconciling UI-SPEC with ROADMAP success criterion #3 (`environment drill-down`). 5 keys: `all/WEB/AMP/APP/UNKNOWN`. Mirrors `Environment` type from `frontend/src/types/alert.ts` line 6. Ships as forward-compat no-op predicate — no backend extension needed to land the constant now, no UI changes required when backend exposes per-publisher environment field.

---

## Notes for Downstream Executors

### Plan 14-02 (ScopeBadge / ReferencePeriodFootnote / GrossNetToggle / TopNDisclaimer primitives)

Import paths from `frontend/src/components/ui/*.tsx`:
- `import { REFERENCE_PERIOD_COPY, SCOPE_BADGE_COPY, GROSS_NET_LABELS, TOP_N_DISCLAIMER_COPY } from '../../lib/i18n-keys';`
- `import { formatTimestampUtc } from '../../lib/utils';`

All 9 constants + `formatTimestampUtc` are available at HEAD `3807c85`.

### Plans 14-04 + 14-05 (RevenueStatusSection + PublishersPage)

`REV_SHARE_FACTOR` is the SSoT for the 0.6 multiplier. NEVER inline `0.6`; always:
```ts
import { REV_SHARE_FACTOR } from '../../lib/i18n-keys';
// then: value * REV_SHARE_FACTOR
```
AC #9 verifier greps for inline `* 0.6` matches — must be ZERO outside `i18n-keys.ts`.

---

## Deviations from Plan

None — plan executed exactly as written. Task 1 and Task 2 were pure-append edits; Task 3 was the atomic commit. ENVIRONMENT_LABELS was specified in the plan frontmatter (D-14.01-E iter-1 W-1) and included as required.

---

## Known Stubs

None. This plan ships static constants and pure functions only. No component data sources, no rendering, no UI stubs.

---

## Threat Flags

None. All new exports are static string literals (`as const` frozen), a numeric scalar (`REV_SHARE_FACTOR = 0.6`), and a pure function with no side effects. No new network endpoints, no auth paths, no file access patterns, no schema changes. T-14-01-01 through T-14-01-08 (threat register in PLAN.md) fully mitigated.

---

## Self-Check

Files exist:
- `frontend/src/lib/i18n-keys.ts` → FOUND (199 lines)
- `frontend/src/lib/utils.ts` → FOUND (43 lines)

Commit exists:
- `3807c85` → FOUND on main

## Self-Check: PASSED
