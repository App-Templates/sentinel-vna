---
phase: 12
plan: 01
subsystem: frontend/i18n + planning/ledger
tags: [i18n, atomic-commit, wip-02, foundation, requirements-ledger]
dependency_graph:
  requires:
    - "Phase 11 API-03 (server-side baseline contract — referenced by BASELINE_MISSING_COPY consumer in Plan 04)"
    - "Phase 11 API-02 (server-side sell_type filter — referenced by SELL_TYPE_LABELS consumer in Plan 05)"
  provides:
    - "frontend/src/lib/i18n-keys.ts module (KPI_LABELS, SELL_TYPE_LABELS, BASELINE_MISSING_COPY, emptyPublishersFiltered, SellTypeKey type)"
    - ".vercel ignore in frontend/.gitignore (deploy-artifact safety)"
    - "REQUIREMENTS.md Traceability ledger consistent with ROADMAP.md Phase 12 ownership"
  affects:
    - "Plan 12-04 (CORR-01 TriageSection baseline-missing wire) — consumes BASELINE_MISSING_COPY"
    - "Plan 12-05 (CORR-08 + sell_type dropdown) — consumes SELL_TYPE_LABELS, SellTypeKey, emptyPublishersFiltered"
    - "Plan 12-06 (CORR-09 KpiCards i18n) — consumes KPI_LABELS"
tech_stack:
  added: []
  patterns:
    - "EN-only constants module pattern (deferred swap to react-i18next/next-intl in Phase 14 CORR-06)"
    - "as const + keyof typeof for compile-time literal-string keys (SellTypeKey)"
key_files:
  created:
    - "frontend/src/lib/i18n-keys.ts"
  modified:
    - "frontend/.gitignore"
    - ".planning/REQUIREMENTS.md"
decisions:
  - "Constants module (not full i18n library) for Phase 12 — explicit downgrade from WIP 94a48cd LanguageProvider per UI-SPEC §i18n decision"
  - "emptyPublishersFiltered exported as function (no EMPTY_PUBLISHER_FILTERED string alias) — W-2 plan-checker iter-1"
  - "Single quotes + semicolons (TypeScript module convention from frontend/src/types/alert.ts; frontend/src/lib/utils.ts is the outlier)"
  - "REQUIREMENTS.md retarget closed inline in Commit A (atomic ledger correction, not deferred) — restores ROADMAP↔REQUIREMENTS consistency before Wave 2"
metrics:
  duration: "~6 minutes"
  completed_date: "2026-04-30"
  tasks: 4
  files: 3
  commits: 1
---

# Phase 12 Plan 01: WIP-02 Commit A i18n Foundation Summary

WIP-02 atomic commit landed: canonical EN constants module
(`frontend/src/lib/i18n-keys.ts`) plus `.vercel` ignore plus REQUIREMENTS.md
Phase 11→12 retarget — single atomic commit, three files, no Wave 2 consumer
wiring.

## What Shipped

### 1. `frontend/src/lib/i18n-keys.ts` (new, 48 lines)

Canonical EN constants module — the import surface every Phase 12 frontend
plan consumes. Full file content:

```ts
// Phase 12 — EN-only constants module (UI-SPEC §"i18n decision" line 65-66).
// Single source of truth for copy strings. Intentionally NOT a full i18n
// provider — Phase 14 (CORR-06) may swap this module for `react-i18next` /
// `next-intl` without touching component JSX.

/**
 * KpiCards labels (CORR-09). Imported by
 * frontend/src/components/dashboard/KpiCards.tsx.
 */
export const KPI_LABELS = {
  rpm: 'RPM',
  ctr: 'CTR',
  viewability: 'Viewability',
  grossMargin: 'Gross Margin',
} as const;

/**
 * Sell-type dropdown labels for PublishersPage filter
 * (UI-SPEC §"Sell Type Filter UI" line 188-194). The 5 canonical sell_types
 * mirror backend/api/publisher_routes.py VALID_SELL_TYPES tuple verbatim.
 * Key 'all' maps to `sellType=undefined` in the hook (no query param sent).
 */
export const SELL_TYPE_LABELS = {
  all: 'All sell types',
  Open_Market: 'Open Market',
  Header_Bidding: 'Header Bidding',
  Direct: 'Direct',
  Deal: 'Deal',
  Other: 'Other',
} as const;

export type SellTypeKey = keyof typeof SELL_TYPE_LABELS;

/**
 * TriageSection baseline-missing disclosure (UI-SPEC §"Color" line 138 +
 * §"Copywriting Contract" line 220).
 */
export const BASELINE_MISSING_COPY =
  'Baseline unavailable for this alert (no environment split data).';

/**
 * PublishersPage empty-with-filter copy (UI-SPEC §"Copywriting Contract" line
 * 216, §"States Inventory" line 258). Caller substitutes {label} and {year}
 * with the active sell_type label and the active year.
 */
export function emptyPublishersFiltered(label: string, year: number): string {
  return `No publishers match ${label} for ${year}.`;
}
```

- `KPI_LABELS` — 4 keys (rpm, ctr, viewability, grossMargin) → 4 EN labels
  (`RPM`, `CTR`, `Viewability`, `Gross Margin`). Literal types via `as const`.
- `SELL_TYPE_LABELS` — 6 keys (`all` + 5 backend canonical sell_types) → 6
  EN labels. Mirrors `backend/api/publisher_routes.py VALID_SELL_TYPES`
  verbatim (Phase 11 Plan 03 D-11.03-01 precedent).
- `SellTypeKey` — `keyof typeof SELL_TYPE_LABELS` for Plan 05 dropdown
  state typing (`useState<SellTypeKey>('all')`).
- `BASELINE_MISSING_COPY` — verbatim UI-SPEC line 220 caption (period
  included).
- `emptyPublishersFiltered(label, year)` — function (NOT string alias) —
  caller-side template-literal interpolation; T-12-01-01 mitigation requires
  callers pass labels from `SELL_TYPE_LABELS`, never user input.

Style: 2-space indent, single quotes, semicolons (TypeScript module
convention from `frontend/src/types/alert.ts`).

### 2. `frontend/.gitignore` — appended `.vercel`

One-line append after `*.sw?`. Matches WIP commit `94a48cd` `.gitignore`
hunk verbatim. Prevents future `git add .` from leaking
`frontend/.vercel/.env*.local` (org IDs) — same posture as the
`data/sentinel_db/*` ignore precedent.

### 3. `.planning/REQUIREMENTS.md` — Phase 11 → Phase 12 retarget (6 rows)

Traceability table rows for WIP-02, WIP-03, WIP-04, CORR-01, CORR-08, CORR-09
flipped from `| 11 |` to `| 12 |`. Status column UNCHANGED (`Pending` →
`Pending`); flip-to-Complete deferred to Phase 12 phase-summary at
end-of-phase. Restores ROADMAP↔REQUIREMENTS consistency that drifted on
2026-04-22 evening milestone expansion (per STATE.md).

## Atomic Commit

```
bd7cdc9568a837fbf98e1adfdba0d99a88c7768b
feat(ui): land i18n keys foundation + retarget WIP/CORR ledger (WIP-02 Commit A)
```

3 files, 55 insertions, 6 deletions. On `main`, NOT pushed (R-05).

## Verification

| Acceptance Criterion | Result |
|----------------------|--------|
| `frontend/src/lib/i18n-keys.ts` exists with all 4 export blocks | ✓ |
| `grep -c "^export const KPI_LABELS"` returns 1 | ✓ |
| `grep -c "^export const SELL_TYPE_LABELS"` returns 1 | ✓ |
| `grep -c "^export const BASELINE_MISSING_COPY"` returns 1 | ✓ |
| `grep -c "^export function emptyPublishersFiltered"` returns 1 | ✓ |
| `grep -c "Baseline unavailable for this alert (no environment split data)\."` returns 1 | ✓ |
| `grep -c "All sell types"` returns 1 | ✓ |
| `grep -c "Open Market"` returns 1 | ✓ |
| File ≥ 25 non-empty lines (43 actual) | ✓ |
| `cd frontend && npx tsc --noEmit -p tsconfig.app.json` exits 0 | ✓ |
| `grep -c "^\.vercel$" frontend/.gitignore` returns 1 | ✓ |
| `git diff frontend/.gitignore` shows exactly 1 added line `+.vercel` | ✓ |
| REQUIREMENTS.md `\| 11 \|` count for {WIP-02,03,04,CORR-01,08,09} == 0 | ✓ |
| REQUIREMENTS.md `\| 12 \|` count for {WIP-02,03,04,CORR-01,08,09} == 6 | ✓ |
| REQUIREMENTS.md diff: 6 lines changed (replace `\| 11 \|` → `\| 12 \|`) | ✓ |
| Subject `feat(ui): land i18n keys foundation + retarget WIP/CORR ledger (WIP-02 Commit A)` exact-match | ✓ |
| `git log -1 --stat` shows exactly 3 files | ✓ |
| Branch == `main` | ✓ |
| `git log origin/main..main --oneline | wc -l` ≥ 159 (183 actual) | ✓ |
| No `git push` invoked | ✓ |
| Runtime DB files NOT staged (`data/vna_alerts.db*`, `sentinel_db/`) | ✓ |
| No file under `frontend/src/components/` or `frontend/src/pages/` modified | ✓ |

## Deviations from Plan

None — plan executed exactly as written. No Rule 1/2/3 auto-fixes
triggered, no Rule 4 architectural questions raised. All 4 tasks completed
in stated order; commit message verbatim from plan body.

Note on style sanity-check: plan asserts main-tree convention is
"single quotes + semicolons (verify by reading utils.ts)". `utils.ts`
itself is the outlier (no semicolons, mixed quotes); the broader convention
in `frontend/src/types/alert.ts` and other typed modules IS single quotes
+ semicolons. Followed plan directive — matches the typed-module convention,
not the utility-helper outlier.

## Auth Gates

None. No external services touched (no Vercel CLI, no GitHub auth, no DB
mutation, no LLM, no Slack).

## Threat Surface

No new threat surface beyond what plan's `<threat_model>` section
documented (T-12-01-01 through T-12-01-06). All mitigations
applied:

- T-12-01-01 (Tampering): no template interpolation of user input in
  `emptyPublishersFiltered` — callers (Plan 05) MUST pass labels from
  `SELL_TYPE_LABELS` const. No `eval`. ✓
- T-12-01-02 (Information Disclosure): `.vercel` ignore landed; future
  org-ID leakage via `git add .` blocked. ✓
- T-12-01-05 (Elevation of Privilege): no `git push` invoked; commit
  stays local on `main`. ✓
- Other dispositions: accept (T-12-01-03 audit trail intact, T-12-01-04
  TS compile <1ms, T-12-01-06 namespace unambiguous).

No `threat_flag` rows surfaced.

## Known Stubs

None. The constants module is fully implemented; consumers (Plans 04/05/06
in Wave 2) wire the imports — that's the design, not a stub.

## Wave 2 Handoff

Plans 04, 05, and 06 can now import from `lib/i18n-keys.ts` without any
further setup:

```ts
// Plan 04 (TriageSection)
import { BASELINE_MISSING_COPY } from '../../lib/i18n-keys';

// Plan 05 (PublishersPage)
import { SELL_TYPE_LABELS, emptyPublishersFiltered } from '../lib/i18n-keys';
import type { SellTypeKey } from '../lib/i18n-keys';

// Plan 06 (KpiCards)
import { KPI_LABELS } from '../../lib/i18n-keys';
```

The `key_links.pattern` regex declared in this plan's frontmatter is what
the gsd-verifier checker will grep for in Plans 04/05/06 to confirm
consumption.

## Self-Check: PASSED

- frontend/src/lib/i18n-keys.ts: FOUND (48 lines, type-checks clean)
- frontend/.gitignore: FOUND (`.vercel` line present, +1 line vs HEAD~1)
- .planning/REQUIREMENTS.md: FOUND (6 rows retargeted, 0 Phase 11 hits, 6 Phase 12 hits)
- Commit bd7cdc9: FOUND on main (`git log --oneline | grep bd7cdc9` → present)
- 3 files in commit stat: VERIFIED
- Branch `main`: VERIFIED
- No `git push` executed: VERIFIED
- Runtime DB files NOT staged: VERIFIED (still unstaged in `git status`)
