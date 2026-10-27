---
phase: 12-wip-atomic-commits-triage-server-side
verified: 2026-04-30T14:55:00Z
status: passed
score: 14/14 must-haves verified
overrides_applied: 0
---

# Phase 12: WIP Atomic Commits + Triage Server-Side — Verification Report

**Phase Goal:** 2-month WIP landed as reviewable atomic commits (Commits A/B/C); TriageSection client-side baseline heuristic removed; CORR-01/08/09 closed in operator UI; RC-(e) closed at the UI layer.

**Verified:** 2026-04-30T14:55:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria + Plan must-haves merged)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `git log` shows 6 atomic commits in this phase (Commit A/B/C + CORR-01/08/09) | ✓ VERIFIED | `bd7cdc9 feat(ui): land i18n keys foundation…(WIP-02 Commit A)`; `2f803e4 feat(ui): translate UI content from IT to EN (WIP-03 Commit B)`; `c29673c feat(api): backend correctness…(WIP-04 Commit C)`; `a535f86 fix(triage): server-side baseline + delete client heuristic (CORR-01)`; `94fc45f feat(publishers): sell_type dropdown filter + weighted avg fill rate (CORR-08)`; `bbb36fa fix(kpi): extract KpiCards labels to i18n-keys module (CORR-09)`. All 6 reachable from `main`. |
| 2 | `TriageSection.tsx` no longer contains `revenueRatio*0.95` or `avgCoverage+0.05`; reads `alert.baseline_bacino` / `baseline_coverage` (UI-SPEC AC #1) | ✓ VERIFIED | Anti-creep grep `revenueRatio\s*\*\s*0\.95\|avgCoverage\s*\+\s*0\.05\|Math\.min\([^)]*,\s*0\.95\)` returns 0 matches; `grep -c "alert.baseline_bacino" TriageSection.tsx` = 1; `grep -c "alert.baseline_coverage" TriageSection.tsx` = 1; `grep -c "BASELINE_MISSING_COPY" TriageSection.tsx` = 2 (import + render). |
| 3 | `KpiCards.tsx` labels i18n-enabled (CORR-09) AND PublishersPage `avgFillRate` uses weighted-by-impressions formula (CORR-08) | ✓ VERIFIED | KpiCards: `import { KPI_LABELS }` = 1; 4 `label={KPI_LABELS.X}` accesses present; 0 hardcoded `label="(RPM\|CTR\|Viewability\|Gross Margin)"`. PublishersPage: weighted formula `p.avg_coverage * p.total_impressions` present at L65; "Avg Fill Rate" label present; `! grep -q "Avg Coverage"` exits 0. |
| 4 | `git status` post-phase shows only runtime/operational state outstanding (no uncommitted Phase-12-scope source) | ✓ VERIFIED | `git status --short` shows only `data/vna_alerts.db*` (runtime mutations, intentionally never staged per CLAUDE.md), `data/sentinel_db/` (.gitignored 2GB CSVs), `data/vna_alerts.db.apply.lock` (runtime). Zero source files outstanding. (Note: SC #4 mentions Commit D/E for WIP-05/WIP-06 but those phases are 13/16 not 12; Phase 12 leaves no in-scope work uncommitted.) |
| 5 | `frontend/src/lib/i18n-keys.ts` exists and exports KPI_LABELS, SELL_TYPE_LABELS, BASELINE_MISSING_COPY, emptyPublishersFiltered, SellTypeKey (Plan 01) | ✓ VERIFIED | File exists at 48 lines; all 5 exports each grep to 1: `KPI_LABELS`, `SELL_TYPE_LABELS`, `BASELINE_MISSING_COPY`, `emptyPublishersFiltered`, `SellTypeKey`. |
| 6 | `frontend/.gitignore` contains `.vercel` (Plan 01 vercel artifact safety) | ✓ VERIFIED | `grep -c "^\.vercel$" frontend/.gitignore` = 1. |
| 7 | REQUIREMENTS.md Traceability rows for WIP-02/03/04, CORR-01/08/09 cite Phase 12 not Phase 11 (Plan 01 ledger correction) | ✓ VERIFIED | `grep -c '\| 11 \|'` for these 6 IDs = 0; `grep -c '\| 12 \|'` for these 6 IDs = 6. |
| 8 | DocsPage.tsx + PublisherDetailPage.tsx + PublishersPage.tsx have zero IT-range characters (Plan 02 IT→EN; UI-SPEC AC #5 sibling) | ✓ VERIFIED | `grep -cE '[À-ſ]' DocsPage.tsx PublisherDetailPage.tsx PublishersPage.tsx` returns 0/0/0. |
| 9 | publisher_routes.py implements channel-deduped bacino aggregation (Plan 03 WIP-04) | ✓ VERIFIED | `grep -c "bacino_per_cell"` = 2; `grep -c "n_channels"` = 2. Phase 11 ship-commit `510f5e2` `VALID_SELL_TYPES` (L37-50) BYTE-IDENTICAL diff returns empty. |
| 10 | routes.py `revenue_status_24h` exposes `available_dates` array, `weeks_averaged` field, and path-based variant `/metrics/revenue-status-24h/{date_path}` (Plan 03 WIP-04) | ✓ VERIFIED | `grep -c "available_dates"` = 2; `grep -c "weeks_averaged"` = 1; `grep -c "revenue_status_24h_by_date"` = 1; `grep -c "/metrics/revenue-status-24h/{date_path}"` = 1. Phase 11 ship-commit `3141591` `_compute_baseline_from_env_split` (L123-164) BYTE-IDENTICAL diff returns empty. |
| 11 | TriageSection baseline-missing disclosure renders em-dash + caption from BASELINE_MISSING_COPY (Plan 04 CORR-01) | ✓ VERIFIED | `import { BASELINE_MISSING_COPY }` = 1 in TriageSection.tsx; render-site usage confirmed (BASELINE_MISSING_COPY total = 2 = import + JSX use). Em-dash literal `'—'` ≥ 4 occurrences per Plan 04 SUMMARY (8 actual). `Minus` icon import + flat-direction usage retained. |
| 12 | `frontend/src/types/alert.ts` Alert interface declares `baseline_bacino?: number` and `baseline_coverage?: number` (Plan 04 CORR-01) | ✓ VERIFIED | `grep -c "baseline_bacino?: number"` = 1; `grep -c "baseline_coverage?: number"` = 1. AlertSummary unchanged. |
| 13 | `useTopPublishers` hook signature accepts optional `sellType?: string`, threads to URL only when defined and !== 'all', includes in queryKey (Plan 05 CORR-08 + sell_type) | ✓ VERIFIED | `grep -c "sellType?: string"` = 1; `grep -cF "queryKey: ['publishers', year, limit, sellType]"` = 1; `grep -cF 'sell_type=${sellType}'` = 1; `grep -c "sellType !== 'all'"` = 1. |
| 14 | PublishersPage CardHeader renders 6-option sell_type `<select>` LEFT of year `<select>`, both wrapped in `flex items-center gap-2`, sharing identical className; filtered empty state via `emptyPublishersFiltered` (Plan 05 + UI-SPEC AC #7) | ✓ VERIFIED | `useState<SellTypeKey>('all')` = 1; `useTopPublishers(year, 35, sellType)` = 1; `Object.keys(SELL_TYPE_LABELS) as SellTypeKey[]).map(...)` rendered at L254; `emptyPublishersFiltered(SELL_TYPE_LABELS[sellType], year)` = 1; both selects share byte-identical className per Plan 05 SUMMARY (count=2, AC #10 PASSED). |

**Score:** 14/14 truths verified.

---

### Required Artifacts (Three-Level Verification)

| Artifact | Expected | Exists | Substantive | Wired | Data Flows | Status |
|----------|----------|--------|-------------|-------|------------|--------|
| `frontend/src/lib/i18n-keys.ts` | EN constants module (5 exports) | ✓ | ✓ (48 lines, ≥25) | ✓ (consumed by TriageSection, PublishersPage, KpiCards) | N/A (constants) | ✓ VERIFIED |
| `frontend/.gitignore` | Contains `.vercel` line | ✓ | ✓ | ✓ (Vercel deploy artifact safety) | N/A | ✓ VERIFIED |
| `.planning/REQUIREMENTS.md` | 6 rows retargeted Phase 11→12 | ✓ | ✓ | N/A (ledger doc) | N/A | ✓ VERIFIED |
| `frontend/src/pages/DocsPage.tsx` | 0 `[À-ſ]` chars | ✓ | ✓ | ✓ (rendered by router) | N/A (text) | ✓ VERIFIED |
| `frontend/src/pages/PublisherDetailPage.tsx` | 0 `[À-ſ]` chars | ✓ | ✓ | ✓ | N/A (text) | ✓ VERIFIED |
| `frontend/src/pages/PublishersPage.tsx` | EN tooltips + sell_type dropdown + weighted formula + filtered empty state | ✓ | ✓ | ✓ (uses useTopPublishers + i18n-keys) | ✓ (data → DataTable) | ✓ VERIFIED |
| `backend/api/publisher_routes.py` | bacino dedup; Phase 11 sell_type filter byte-identical | ✓ | ✓ (Python AST parses) | ✓ (called by /api/publishers/top) | ✓ (groupby on parquet) | ✓ VERIFIED |
| `backend/api/routes.py` | 7w YoY + available_dates + weeks_averaged + path variant; Phase 11 baseline byte-identical | ✓ | ✓ (Python AST parses) | ✓ (FastAPI router) | ✓ (data via cached parquet) | ✓ VERIFIED |
| `scripts/test_wip04_backend_correctness.py` | 4-test TDD scaffold | ✓ | ✓ (298 lines) | ✓ (RED→GREEN per Plan 03 SUMMARY) | N/A (test) | ✓ VERIFIED |
| `frontend/src/components/alerts/TriageSection.tsx` | server fields read; heuristic gone; baseline-missing state | ✓ | ✓ | ✓ (consumes Alert payload + BASELINE_MISSING_COPY) | ✓ (alert prop → JSX) | ✓ VERIFIED |
| `frontend/src/types/alert.ts` | Alert.baseline_bacino?/baseline_coverage? | ✓ | ✓ | ✓ (TS compiles, types consumed by TriageSection) | N/A (type) | ✓ VERIFIED |
| `frontend/src/api/client.ts` | useTopPublishers(year, limit, sellType?) | ✓ | ✓ | ✓ (consumed by PublishersPage) | ✓ (queryKey + URL → fetch) | ✓ VERIFIED |
| `frontend/src/components/dashboard/KpiCards.tsx` | KPI_LABELS imported; 4 hardcoded labels removed | ✓ | ✓ | ✓ (consumes i18n-keys) | ✓ (labels → MetricCard JSX) | ✓ VERIFIED |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `KpiCards.tsx` | `lib/i18n-keys.ts` KPI_LABELS | `import { KPI_LABELS } from '../../lib/i18n-keys'` | ✓ WIRED | Import present (1 occurrence); 4 `label={KPI_LABELS.X}` JSX accesses; 0 hardcoded label literals |
| `PublishersPage.tsx` | `lib/i18n-keys.ts` SELL_TYPE_LABELS / SellTypeKey / emptyPublishersFiltered | `import { SELL_TYPE_LABELS, type SellTypeKey, emptyPublishersFiltered } from '../lib/i18n-keys'` | ✓ WIRED | Multi-symbol import at L9-13; `useState<SellTypeKey>('all')` at L24; SELL_TYPE_LABELS keys mapped at L254-255; emptyPublishersFiltered call at L274 |
| `TriageSection.tsx` | `lib/i18n-keys.ts` BASELINE_MISSING_COPY | `import { BASELINE_MISSING_COPY } from '../../lib/i18n-keys'` | ✓ WIRED | Import + JSX render (count=2) |
| `PublishersPage.tsx` sell_type select onChange | `useTopPublishers(year, limit, sellType)` re-fetch | queryKey extension + URL append | ✓ WIRED | queryKey includes sellType (cache isolation); URL appends `&sell_type=${sellType}` only when not 'all'; verified live: 200 unfiltered, 200 filtered, 400 invalid (Plan 05 SUMMARY E2E proof) |
| `TriageSection.tsx` table rows | `alert.baseline_bacino` / `alert.baseline_coverage` server fields | Direct prop access via `alert.baseline_bacino` and `alert.baseline_coverage` | ✓ WIRED | Both grep to 1; `baselineMissing` boolean derived; em-dash + caption render conditionally |
| `revenue_status_24h_by_date` route | `revenue_status_24h(request, date=date_path)` delegate | FastAPI path-param wrapper | ✓ WIRED | Path `/metrics/revenue-status-24h/{date_path}` registered; Plan 03 RED→GREEN test_path_variant_matches_query_variant PASSED |
| `get_top_publishers` bacino aggregation | `n_channels` per (publisher, date, env, geo) cell | `df_year.groupby(...)["channel_group"].nunique()` then `bacino_per_cell / n_channels` | ✓ WIRED | Both `bacino_per_cell` and `n_channels` grep to 2; live numeric proof: Mondadori 2,608,852,415 → 407,755,508 (~6.4× reduction, Plan 03 SUMMARY) |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `KpiCards.tsx` | `data.rpm/ctr/viewability/gross_margin_pct` | `useRevenueStatus24h()` → `/api/metrics/revenue-status-24h` | ✓ Real (FastAPI route + cached parquet) | ✓ FLOWING |
| `TriageSection.tsx` | `alert.baseline_bacino`, `alert.baseline_coverage` | Phase 11 server-side `_compute_baseline_from_env_split` | ✓ Real (Phase 11 ship-commit `3141591` byte-identical preserved + Phase 11 regression suite 5/5 GREEN per Plan 03 SUMMARY) | ✓ FLOWING |
| `PublishersPage.tsx` | `data` (publishers array) | `useTopPublishers(year, 35, sellType)` → `/api/publishers/top` | ✓ Real (Phase 11 sell_type filter `510f5e2` byte-identical preserved + live 200/400 verified per Plan 05 SUMMARY) | ✓ FLOWING |
| `PublishersPage.tsx` | `avgFillRate` (weighted) | Computed from `data.reduce(...)` over real publishers | ✓ Real (live numeric: simple 48.20% vs weighted 46.14%, Δ=2.05ppt per Plan 05 SUMMARY) | ✓ FLOWING |
| `routes.py` | `available_dates` array, `weeks_averaged` int | Real groupby + complete-day detection on cached parquet | ✓ Real (Plan 03 RED capture showed missing fields, GREEN capture shows present + correct shape) | ✓ FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 6 atomic commits reachable from main | `git log --oneline \| grep -E "(bd7cdc9\|2f803e4\|c29673c\|a535f86\|94fc45f\|bbb36fa)"` | All 6 returned | ✓ PASS |
| TypeScript compile clean | `cd frontend && npx tsc --noEmit -p tsconfig.app.json` | exit 0 | ✓ PASS |
| Python AST parse clean | `python3 -c "import ast; ast.parse(...publisher_routes.py); ast.parse(...routes.py)"` | OK both files parse | ✓ PASS |
| UI-SPEC AC #1 anti-creep grep | `grep -nE 'revenueRatio\*0.95\|avgCoverage+0.05\|Math.min(...,0.95)' TriageSection.tsx` | exit 1 (no match) | ✓ PASS |
| UI-SPEC AC #5 negated existence | `grep -q "Avg Coverage" PublishersPage.tsx` | exit 1 (no match = correct) | ✓ PASS |
| UI-SPEC AC #8 IT-character coverage | `grep -cE '[À-ſ]' DocsPage/PublisherDetailPage/PublishersPage` | 0/0/0 | ✓ PASS |
| UI-SPEC AC #12 anti-creep across alerts/ + Kpi* | `grep -rnE '\*\s*0\.95\|\+\s*0\.05\|\+\s*0\.04' alerts/ Kpi*` | exit 1 (no match) | ✓ PASS |
| KPI_LABELS consumed in KpiCards | `grep -c "KPI_LABELS" KpiCards.tsx` | 5 | ✓ PASS |
| Phase 11 byte-identity (`_compute_baseline_from_env_split`) | `diff <(git show 3141591:routes.py L123-164) <(routes.py L123-164)` | empty | ✓ PASS |
| Phase 11 byte-identity (`VALID_SELL_TYPES`) | `diff <(git show 510f5e2:publisher_routes.py L37-50) <(publisher_routes.py L37-50)` | empty | ✓ PASS |

All 10 spot-checks PASS. Test suite execution (Plan 03 RED→GREEN + Phase 11 regression 13/13) documented in `12-03-SUMMARY.md` and not re-executed here (long-running, accept SUMMARY proof for behavioral evidence given byte-identity diff confirmation).

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| WIP-02 | 12-01 | Commit A atomico — i18n keys foundation + .vercel ignore + ledger retarget | ✓ SATISFIED | Commit `bd7cdc9` on main; i18n-keys.ts + .gitignore + REQUIREMENTS.md retarget all verified |
| WIP-03 | 12-02 | Commit B atomico — IT→EN translation in DocsPage/PublisherDetailPage/PublishersPage | ✓ SATISFIED | Commit `2f803e4`; `[À-ſ]` count = 0 across all 3 files; 5 IT tooltip ban-list strings absent |
| WIP-04 | 12-03 | Commit C atomico — backend correctness (bacino dedup + 7w YoY + available_dates + path variant) | ✓ SATISFIED | Commit `c29673c`; all backend wiring greps PASS; Phase 11 byte-identity preserved; RED→GREEN tests + Phase 11 regression 13/13 GREEN per SUMMARY |
| CORR-01 | 12-04 | Triage baseline server-side — kill heuristic + wire baseline_bacino/coverage + missing-state disclosure | ✓ SATISFIED | Commit `a535f86`; AC #1 anti-creep returns 0; alert.baseline_bacino/coverage referenced; BASELINE_MISSING_COPY consumed; AC #12 across alerts/ + Kpi* returns 0 |
| CORR-08 | 12-05 | UI weighted avgFillRate + sell_type dropdown affordance | ✓ SATISFIED | Commit `94fc45f`; weighted formula `p.avg_coverage * p.total_impressions` present; "Avg Fill Rate" label; "Avg Coverage" label removed; 6-option sell_type select with shared className; useTopPublishers extended with sellType + queryKey |
| CORR-09 | 12-06 | KpiCards i18n keys (RPM/CTR/Viewability/GrossMargin) extracted to constants module | ✓ SATISFIED | Commit `bbb36fa`; `import { KPI_LABELS }` = 1; 4 KPI_LABELS accesses present; 0 hardcoded label literals |

All 6 requirement IDs from PLAN frontmatters are accounted for in REQUIREMENTS.md and have direct implementation evidence. No orphaned requirements found in REQUIREMENTS.md mapping for Phase 12.

**Note on Status column:** REQUIREMENTS.md Traceability table has Status mixed (some `Pending`, some `Complete`). Per Plan 01 design, Status flips occur in the phase-summary writeup at end-of-phase. The phase implementation work is complete; the Status column normalization is a deferred ledger-housekeeping item, not a goal-blocking gap. Truths #1-14 establish goal achievement.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | — | — | All anti-creep mechanical greps return 0 matches; no TODO/FIXME/placeholder/stub patterns introduced by Phase 12 commits in scope files |

Anti-creep grep matrix:
- AC #1 `revenueRatio*0.95\|avgCoverage+0.05\|Math.min(...,0.95)` in `TriageSection.tsx` → 0 matches
- AC #12 `\*\s*0\.95\|\+\s*0\.05\|\+\s*0\.04` across `alerts/` + `Kpi*` → 0 matches
- AC #5 IT-char coverage `[À-ſ]` in DocsPage/PublisherDetailPage/PublishersPage → 0/0/0
- AC #5 negated existence `! grep -q "Avg Coverage" PublishersPage.tsx` → exits 0 (no match = PASS)
- AC #6 forbid-list `label="(RPM\|CTR\|Viewability\|Gross Margin)"` in `KpiCards.tsx` → 0 matches

---

### Human Verification Required

(empty — no items requiring human testing)

The phase produced atomic commits with mechanical AC gates (regex, byte-identity diffs, AST parse, TS compile) all verifiable programmatically. Live behavioral validation (sell_type filter 200/400, weighted formula 2.05ppt delta, Mondadori bacino reduction 6.4×, Phase 11 regression suite GREEN) was already captured in plan SUMMARYs with verbatim command output and accepted as behavioral evidence.

No visual/UX/real-time/external-service verification is gated to the goal contract. Operator-visible UI changes (sell_type dropdown affordance, baseline-missing caption, EN content) are exercisable via dev server but the goal of this phase is "atomic commits land + heuristic removed + wiring done" — programmatic gates fully cover that contract.

---

### Gaps Summary

(none — all 14 truths VERIFIED, all 6 requirements SATISFIED, all key links WIRED, all anti-creep grep gates PASS, Phase 11 byte-identity preserved on both ship surfaces)

---

## Verification Notes

1. **Sub-roadmap quirk on SC #3:** ROADMAP.md SC #3 reads `KpiCards.tsx avgFillRate uses weighted average; labels i18n-enabled`. The avgFillRate logic actually lives in `PublishersPage.tsx` (CORR-08 / Plan 05), while KpiCards owns the i18n-enabled labels (CORR-09 / Plan 06). Both intents are achieved; SC #3 conflates two file ownerships. Considered SATISFIED via the conjoined evidence in Truth #3.

2. **REQUIREMENTS.md Status column drift:** The Traceability table shows mixed `Pending`/`Complete` — Plan 01 explicitly defers the Pending→Complete flip to the phase-summary writeup. This is intentional ledger ordering, not a verification gap. The 6 requirement rows correctly cite Phase 12 (the planner's main concern in Plan 01 Task 3).

3. **Untranslated ASCII Italian (Plan 02 SUMMARY decisions):** A handful of ASCII-Italian sentences (e.g., `VOLUME_DRIVEN`/`SEASONAL_DEMAND` driver tooltips in PublisherDetailPage L99-100, `Durante Q1 Slowdown` in DocsPage L1514) were intentionally not translated by Plan 02. They are out-of-scope per the planner's enumerated 27+13 hunk list and do not violate the `[À-ſ]` coverage gate. Documented in 12-02-SUMMARY.md "What Was NOT Translated" section. Not a goal gap.

4. **Live `vna_alerts.db` mutation in `git status`:** Per CLAUDE.md hard rule, `data/vna_alerts.db*` files are runtime-mutated continuously and NEVER staged. `git status` showing `M data/vna_alerts.db` + `D data/vna_alerts.db-shm/wal` + `?? data/sentinel_db/` + `?? data/vna_alerts.db.apply.lock` is the expected steady-state, NOT outstanding work.

5. **Plan 04 deviation (Rule 1 / R-10):** Documented in 12-04-SUMMARY.md — planner-supplied audit comment originally matched its own AC #1 grep. Executor rephrased the comment in-place and folded into the same atomic commit. Confirmed via post-edit grep returning 0. Audit trail preserved in commit body + SUMMARY. Acceptable per R-10 fix-the-code-first principle.

6. **Plan 04 SPEC-evolution candidate (advisory):** UI-SPEC §"Acceptance Criteria" #1 line 307 contains the looser pattern `Math\.min.*0\.95` which would match any future legitimate `Math.min(x, 0.95)` cap. Plan 04 used the tightened `Math\.min\([^)]*,\s*0\.95\)` for local verify because UI-SPEC.md is `approved + status: locked`. A future v1.4 milestone refresh should adopt the tightened pattern in AC #1 line 307. Documented for ROADMAP — not a goal-blocking gap.

7. **Phase 11 surface preservation:** Both byte-identity diffs return empty output, confirming `_compute_baseline_from_env_split` (commit `3141591`, routes.py L123-164) and `VALID_SELL_TYPES` (commit `510f5e2`, publisher_routes.py L37-50) are bit-for-bit unchanged after the WIP-04 cherry-pick. R-13 invariant held.

---

_Verified: 2026-04-30T14:55:00Z_
_Verifier: Claude (gsd-verifier)_
