---
phase: 18-hardening-pbi-contract-tests-docs
plan: "03"
subsystem: ci-regression-tests
tags: [ci, pbi-parity, silent-failure, regression, path-a-guard, csv-eof, athena-skip, HARD-03, HARD-04]

dependency_graph:
  requires:
    - 18-02 (schema-drift.yml pattern + workflows/README.md base)
  provides:
    - .github/workflows/pbi-parity.yml (HARD-03 + HARD-04 CI gate)
    - scripts/test_alert_revenue_pbi_parity.py extended (INV-5 + INV-6)
    - scripts/test_silent_failure_watch.py extended (TestPhase18HardeningRegression)
  affects:
    - 18-05 (final verification will run pbi-parity gate)

tech_stack:
  added:
    - .github/workflows/pbi-parity.yml (GitHub Actions workflow)
  patterns:
    - script-mode skip for D-10 INV-5 (alternative to pytest.mark.skip when collected standalone)
    - executable-line source-grep guard (narrow to non-comment lines with channel + BACKTEST)
    - ephemeral sqlite3 tempfile for watchdog signal regression (no live DB mutation)

key_files:
  created:
    - .github/workflows/pbi-parity.yml
  modified:
    - scripts/test_alert_revenue_pbi_parity.py
    - scripts/test_silent_failure_watch.py
    - .github/workflows/README.md

decisions:
  - INV-6 uses executable-line grep (non-comment lines containing both channel and BACKTEST) rather
    than the plan's 30-line window around all BACKTEST tokens; avoids false positives from the Phase
    17.4 comment on line 609 listing TAM/DIRECT/DEAL as parquet-only channels
  - INV-5 uses script-mode skip (print + return True) per D-10 semantic: standalone script cannot
    use pytest.mark.skip; comment "D-10 equivalent: script-mode skip" added for auditor traceability

metrics:
  duration: "236 seconds (~4 min)"
  completed_date: "2026-05-21"
  tasks_completed: 3
  files_modified: 4
---

# Phase 18 Plan 03: HARD-03 + HARD-04 Regression Tests + PBI Parity CI Gate Summary

PBI parity regression test extended with Sample 2 HBM placeholder (INV-5 skip) + Path A source-grep guard (INV-6); silent-failure watch extended with CSV-EOF boundary + post-cutoff synthetic + Path A cross-check; both wired into new pbi-parity.yml GitHub Actions CI gate.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend test_alert_revenue_pbi_parity.py with INV-5 + INV-6 (HARD-04) | `1f0fefe` | scripts/test_alert_revenue_pbi_parity.py |
| 2 | Extend test_silent_failure_watch.py with TestPhase18HardeningRegression (HARD-03) | `fc82805` | scripts/test_silent_failure_watch.py |
| 3 | Create pbi-parity.yml + update workflows README | `efffe6a` | .github/workflows/pbi-parity.yml, .github/workflows/README.md |

## Outcome

### HARD-04 — PBI Parity Gate (test_alert_revenue_pbi_parity.py)

Extended from 4 invariants to 6:

- **INV-1..INV-4** (Phase 17.4 baseline): remain 4/4 GREEN, zero regression
- **INV-5** (Sample 2 HBM placeholder): SKIPPED — `Phase 21 v1.4 Athena activation required`
  D-10 equivalent comment present: `# D-10 equivalent: script-mode skip (pytest.mark.skip would apply if collected under pytest)`
- **INV-6** (Path A guard source-grep): PASS — executable-line grep confirms `if channel == "GOOGLE_ADEX" and mode == "BACKTEST"` is the only guard; no forbidden channels (OPEN_BIDDING, HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC, TAM, DIRECT, DEAL) appear in executable guard lines

Suite result: 4 GREEN + 1 SKIP + 1 GREEN, exit 0.

### HARD-03 — Silent-Failure Regression (test_silent_failure_watch.py)

Extended `TestPhase18HardeningRegression` class with 3 tests:

1. `test_post_cutoff_google_adex_synthetic_class_triggers_signal` — ephemeral sqlite3 DB seeds `synthetic_no_athena` GOOGLE_ADEX post-cutoff row; canonical violator SQL flags it. PASS.
2. `test_csv_eof_boundary_marked_deprecated_not_active` — verifies ALT-20260323-010000-P1 `deprecated=1` (Phase 17.4 CSV-EOF edge case). PASS (live DB present). Graceful `skipTest` in CI.
3. `test_path_a_guard_grep_consistency` — source-grep defense-in-depth cross-check. PASS.

Total suite: 19 tests, all OK, exit 0.

### CI Gate — pbi-parity.yml

New GitHub Actions workflow, mirrors schema-drift.yml pattern:
- Triggers: `pull_request` + `push: branches: [main]`
- Job: `pbi-parity-check` on `ubuntu-latest`, Python 3.11, pip cache
- Step 1: `python scripts/test_alert_revenue_pbi_parity.py` — exits 0 with `::notice::` if DB absent (exit code 2); fails fast on any real RED invariant
- Step 2: `python scripts/test_silent_failure_watch.py -v` — all 19 tests run; ephemeral DB tests always pass; CSV-EOF test skipTest in CI (no live DB)
- D-09 scoping documented inline: INV-6 is the CI blocker; INV-1..INV-4 are operator-machine gates

README extended: new pbi-parity row in table + "Why pbi-parity second" section.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] INV-6 false positives from 30-line comment window**

- **Found during:** Task 1 execution (first run of test script)
- **Issue:** The plan specified "expands a 30-line window around each BACKTEST token." Line 609 in `data_fetcher_real.py` has a comment `# remain on parquet until v1.4 Phase 21 Athena (HBM/HBP/TAM/DIRECT/DEAL) lands.` This comment legitimately mentions TAM, DIRECT, DEAL — triggering false positives. First run: `forbidden_hits=['TAM', 'DIRECT', 'DEAL']`, exit 1 instead of 0.
- **Fix:** Changed INV-6 to grep only non-comment executable lines containing both `channel` and `BACKTEST`. This correctly identifies the guard condition line `if channel == "GOOGLE_ADEX" and mode == "BACKTEST":` with zero false positives. The spirit of D-08 (guard against accidental enablement of other channels) is fully satisfied — the check operates on the actual conditional expression, not documentation around it.
- **Files modified:** `scripts/test_alert_revenue_pbi_parity.py`
- **Commit:** `1f0fefe` (same Task 1 commit — fixed before commit)

## Known Stubs

None. INV-5 is an intentional skip (D-10 mandate), not a stub — the skip is the correct behavior until Phase 21.

## Threat Flags

No new network endpoints, auth paths, file access patterns, or schema changes at trust boundaries introduced. All files are test scripts and CI workflow definitions. Consistent with threat model T-18-03-01..T-18-03-05 (no new surface).

## Self-Check: PASSED

All created files exist on disk. All 3 task commits present in git log:
- `1f0fefe` — Task 1: test_alert_revenue_pbi_parity.py extension
- `fc82805` — Task 2: test_silent_failure_watch.py extension
- `efffe6a` — Task 3: pbi-parity.yml + README update
