---
phase: 12
plan: 06
subsystem: frontend/i18n-consumer
tags: [i18n, atomic-commit, corr-09, wave-2, kpi-cards]
dependency_graph:
  requires:
    - "Phase 12 Plan 01 (KPI_LABELS export in frontend/src/lib/i18n-keys.ts — bd7cdc9)"
  provides:
    - "KpiCards.tsx labels sourced from KPI_LABELS constants module (CORR-09 closed at UI consumer layer)"
    - "Single-import migration surface for Phase 14 CORR-06 (react-i18next / next-intl swap)"
  affects:
    - "Phase 14 CORR-06 (i18n library migration) — will swap KPI_LABELS module for runtime t() calls; KpiCards.tsx JSX unchanged"
tech_stack:
  added: []
  patterns:
    - "Compile-time i18n constant import pattern (consumer side) — matches Plan 01 'as const + keyof typeof' provider pattern"
key_files:
  created: []
  modified:
    - "frontend/src/components/dashboard/KpiCards.tsx"
decisions:
  - "Surgical 5-line diff: 1 import added + 4 JSX label-prop literal-to-constant swaps. Zero changes to grid/icons/numeric-derivation/loading-state per UI-SPEC §'Component Inventory' line 149"
  - "Local variable `grossMargin` (numeric, line 32) intentionally left unchanged despite same camelCase as `KPI_LABELS.grossMargin` (string) — independent identifiers, distinct types, no collision"
metrics:
  duration: "~1 minute"
  completed_date: "2026-04-30"
  tasks: 2
  files: 1
  commits: 1
---

# Phase 12 Plan 06: CORR-09 KpiCards i18n Consumer Summary

CORR-09 closed at the UI consumer layer. The 4 hardcoded English label
literals (`'RPM'`, `'CTR'`, `'Viewability'`, `'Gross Margin'`) in
`frontend/src/components/dashboard/KpiCards.tsx` JSX are now sourced
from the `KPI_LABELS` constants module (Plan 01 output) — single atomic
commit, single file modified, +5 / -4 lines.

## What Shipped

### `frontend/src/components/dashboard/KpiCards.tsx` (modified, +5 -4)

**Five edits in one file:**

1. **Import added** (after line 4 `useRevenueStatus24h` import, before
   `ExtendedRevenueData` interface):

   ```tsx
   import { KPI_LABELS } from '../../lib/i18n-keys'
   ```

2. **Four JSX `label=` prop replacements** (in the `<MetricCard>` blocks
   inside the `return` statement):

   | Line | Before | After |
   |------|--------|-------|
   | L37  | `label="RPM"`           | `label={KPI_LABELS.rpm}`         |
   | L43  | `label="CTR"`           | `label={KPI_LABELS.ctr}`         |
   | L49  | `label="Viewability"`   | `label={KPI_LABELS.viewability}` |
   | L55  | `label="Gross Margin"`  | `label={KPI_LABELS.grossMargin}` |

**Untouched** (per UI-SPEC §"Component Inventory" line 149 lock):
- `lucide-react` icon imports (`DollarSign`, `MousePointer`, `Eye`, `Percent`)
- `MetricCard`, `CardSkeleton`, `useRevenueStatus24h` imports
- `ExtendedRevenueData` interface (lines 6-11)
- `KpiCards` function declaration + `useRevenueStatus24h()` hook call
- `isLoading` branch returning 4 `CardSkeleton`s in 2x2/4x1 grid
- `ext` cast trick (`data as (typeof data & ExtendedRevenueData) | undefined`)
- 4 derived-numeric local variables (`rpm`, `ctr`, `viewability`, `grossMargin`)
- Grid wrapper className `grid grid-cols-2 gap-4 lg:grid-cols-4`
- All `format`, `value`, `icon` props on the 4 `<MetricCard>` blocks

## Atomic Commit

```
bbb36fa3837fd9d53753d91f3be9fdc3bab4a0fb
fix(kpi): extract KpiCards labels to i18n-keys module (CORR-09)
```

1 file changed, 5 insertions(+), 4 deletions(-). On `main`, NOT pushed (R-05).

## Verification

| Acceptance Criterion | Result |
|----------------------|--------|
| `grep -c "import { KPI_LABELS } from '../../lib/i18n-keys'" KpiCards.tsx` returns 1 | ✓ |
| `grep -c 'label={KPI_LABELS\.rpm}' KpiCards.tsx` returns 1 | ✓ |
| `grep -c 'label={KPI_LABELS\.ctr}' KpiCards.tsx` returns 1 | ✓ |
| `grep -c 'label={KPI_LABELS\.viewability}' KpiCards.tsx` returns 1 | ✓ |
| `grep -c 'label={KPI_LABELS\.grossMargin}' KpiCards.tsx` returns 1 | ✓ |
| AC #6 forbid-list: `grep -cE 'label="(RPM\|CTR\|Viewability\|Gross Margin)"' KpiCards.tsx` returns 0 | ✓ (returns 0) |
| AC #8 palette lock: `git diff HEAD~1 HEAD KpiCards.tsx \| grep -cE '^\+.*\b(bg-slate-\|text-slate-\|border-slate-\|font-light\|font-thin\|font-extrabold\|font-black)\b'` returns 0 | ✓ (returns 0) |
| AC #12 anti-creep: `grep -nE '\*\s*0\.95\|\+\s*0\.05\|\+\s*0\.04' KpiCards.tsx` returns ZERO matches | ✓ (no matches) |
| `cd frontend && npx tsc --noEmit -p tsconfig.app.json` exits 0 | ✓ |
| `git diff --shortstat HEAD~1 HEAD frontend/src/components/dashboard/KpiCards.tsx` reports `1 file changed, 5 insertions(+), 4 deletions(-)` | ✓ exact match |
| `git log -1 --pretty=%s` exact-matches `fix(kpi): extract KpiCards labels to i18n-keys module (CORR-09)` | ✓ |
| `git log -1 --stat` shows exactly 1 file (`frontend/src/components/dashboard/KpiCards.tsx`) | ✓ |
| Branch == `main` | ✓ |
| Operational state (`data/vna_alerts.db*`, `data/sentinel_db/`, `data/vna_alerts.db.apply.lock`) NOT staged | ✓ verified pre/post commit |
| No `git push` invoked | ✓ |

## Phase 14 CORR-06 Migration Path Confirmed

Phase 14 CORR-06 (i18n library migration to `react-i18next` / `next-intl`)
needs **only two surgical edits** in `KpiCards.tsx`:

1. Swap the import line:
   ```tsx
   // Before (Phase 12)
   import { KPI_LABELS } from '../../lib/i18n-keys'

   // After (Phase 14)
   import { useTranslation } from 'react-i18next'
   ```

2. Replace 4 JSX `label={KPI_LABELS.X}` accesses with `label={t('kpi.X')}`
   (or whatever key shape the chosen library prescribes).

Zero JSX structural edits required. The grid layout, the 4 `<MetricCard>`
blocks, the icon set, the `format`/`value`/`icon` props remain
byte-identical. This is the deferred-swap pattern declared in UI-SPEC
§"i18n decision" lines 65-66, now demonstrably enforced at the consumer
layer.

## Deviations from Plan

None — plan executed exactly as written. No Rule 1/2/3 auto-fixes
triggered, no Rule 4 architectural questions raised. Both tasks
completed in stated order; commit message verbatim from plan body.

## Auth Gates

None. No external services touched (no Vercel CLI, no GitHub auth, no DB
mutation, no LLM, no Slack).

## Threat Surface

No new threat surface beyond what plan's `<threat_model>` section
documented (T-12-06-01 through T-12-06-06). All mitigations applied:

- T-12-06-01 (Tampering of label string source): accept — values come
  from typed `as const` object in `lib/i18n-keys.ts`. No runtime fetch,
  no template interpolation. Set of accessible keys compile-time bounded
  by `keyof typeof KPI_LABELS`. ✓
- T-12-06-02 (Information Disclosure of label values): accept — `'RPM'`
  / `'CTR'` etc. are public business taxonomy, same posture as before. ✓
- T-12-06-03 (Repudiation): accept — commit body cites Plan 01
  dependency, UI-SPEC AC #6, Phase 14 migration path. Audit trail
  complete. ✓
- T-12-06-04 (DoS via bundle size): accept — adding one import + 4
  string accesses adds <200 bytes to the bundle; tsc cold start delta
  <1ms. ✓
- T-12-06-05 (Elevation of Privilege via `git push`): mitigate — Plan
  forbids push per R-05; deploy-gate hook would block. No `git push`
  executed in this session. ✓
- T-12-06-06 (Tampering of UI-SPEC palette lock): mitigate — diff is
  JSX `label=` attribute changes only; no `className` touched. AC #8
  grep returns 0 in both Task 1 and Task 2 verification. ✓

No `threat_flag` rows surfaced.

## Known Stubs

None. The constants module (Plan 01) is fully implemented; this plan
wires the consumer. `KpiCards.tsx` now reads its labels from a typed
canonical source. No placeholders, no TODO/FIXME markers, no empty
arrays/objects flowing to UI rendering. The numeric variables
(`rpm`, `ctr`, etc.) continue to use the `?? 0` fallback that pre-dates
this plan — that's documented out-of-scope per UI-SPEC §"States
Inventory" line 248 ("Phase 12 does NOT introduce empty-state copy
here — that's Phase 14 CORR-05").

## Wave 2 Closure Status

- ✓ Plan 04 (CORR-01 TriageSection wiring + heuristic delete) — landed prior
- ✓ Plan 05 (CORR-08 weighted avgFillRate + sell_type dropdown) — landed prior
- ✓ Plan 06 (CORR-09 KpiCards i18n keys) — **this plan, landed**

All three Wave 2 consumers of Plan 01's `lib/i18n-keys.ts` foundation
are now live on main. Phase 12 fully complete (6/6 plans) pending the
Phase 12 phase-summary that flips REQUIREMENTS.md status flags from
`Pending` → `Complete` for {WIP-02, WIP-03, WIP-04, CORR-01, CORR-08,
CORR-09}.

## Self-Check: PASSED

- frontend/src/components/dashboard/KpiCards.tsx: FOUND (62→63 lines, type-checks clean)
- Commit bbb36fa: FOUND on main (`git log --oneline | grep bbb36fa` → present)
- 1 file in commit stat: VERIFIED (KpiCards.tsx only)
- Branch `main`: VERIFIED
- No `git push` executed: VERIFIED
- Operational state NOT staged: VERIFIED (still unstaged in `git status`: data/vna_alerts.db M, sentinel_db/ ??, vna_alerts.db.apply.lock ??)
- Subject exact-match: VERIFIED
- All 8 acceptance criteria: PASSED (Task 1: 6/6 grep + tsc; Task 2: subject + 1-file + shortstat + branch + AC #8 = 5/5)
