---
phase: 18-hardening-pbi-contract-tests-docs
plan: 02
subsystem: ci-schema-drift-gate
tags: [ci, github-actions, schema-drift, migration-derived-schema, models-py-check, HARD-02]
dependency_graph:
  requires:
    - 18-01-PLAN.md (Plan 01 completed — test infrastructure + .venv confirmed present)
    - scripts/migrations/001..006 (full chain on disk, 005 absent intentionally)
    - backend/db/models.py (CHECK constants source of truth)
  provides:
    - .github/workflows/schema-drift.yml — first CI gate in repo, fires on every PR/push to main
    - .github/workflows/README.md — workflow convention index for future phases
    - scripts/test_models_sync.py extended with Migration 006 + composite chain assertion
  affects:
    - Every future PR: schema-drift.yml will gate merges where models.py diverges from migrations
    - Phase 18-03 (HARD-03+HARD-04): will add a second workflow following same README convention
tech_stack:
  added:
    - GitHub Actions (first workflow in repo)
    - actions/checkout@v4
    - actions/setup-python@v5
  patterns:
    - sqlite3 :memory: for migration chain replay (no live DB dependency in CI)
    - One workflow file per gate, kebab-case naming convention established
key_files:
  created:
    - .github/workflows/schema-drift.yml (30 lines)
    - .github/workflows/README.md (31 lines)
  modified:
    - scripts/test_models_sync.py (511 → 729 lines, +218 lines)
decisions:
  - "D-04 honored: workflow covers ALL CHECK constants (channel_group + alert_rule), not just created_at"
  - "D-05 honored: sqlite3 :memory: + migrations 001..006 applied sequentially (no live DB write)"
  - "D-06 honored: schema-drift.yml is a new file separate from any existing workflow (first workflow in repo)"
  - "Auto-fix: _STALE_ALERTS_DDL baseline added to setUpClass because migration 001 requires pre-existing tables (ALTER TABLE RENAME requires source table to exist in :memory: DB)"
  - "pipeline_runs baseline excludes alerts_written_count to avoid duplicate column when migration 003 applies ALTER TABLE ADD COLUMN"
metrics:
  duration_minutes: 12
  completed_date: "2026-05-21"
  tasks_completed: 2
  tasks_total: 2
  test_count_before: 28
  test_count_after: 36
  files_created: 2
  files_modified: 1
---

# Phase 18 Plan 02: Schema-Drift CI Gate (HARD-02) Summary

**One-liner:** First GitHub Actions workflow in Sentinel repo — schema-drift gate applies migrations 001→002→003→004→006 against sqlite3 :memory: and fails CI if models.py CHECK constants diverge.

## What Was Built

### Task 1: Extended scripts/test_models_sync.py

Added module-level constants `MIGRATION_004`, `MIGRATION_004_ROLLBACK`, `MIGRATION_006`, `MIGRATION_006_ROLLBACK`.

Added two new test classes:

**TestMigration006Sync** (3 tests):
1. `test_migration_006_file_exists` — both forward and rollback SQL present on disk
2. `test_migration_006_does_not_alter_channel_group_check` — 006 is data-only, must not touch CHECK clauses
3. `test_migration_006_marks_backfill_alerts_deprecated` — UPDATE alerts references deprecated + backfill

**TestComposeChainAgainstModels** (5 tests):
1. `test_channel_group_check_matches_models_constants` — every value in models.CHANNEL_GROUP_CHECK_VALUES appears in migration-derived alerts schema
2. `test_alert_rule_check_matches_models_constants` — analogous for ALERT_RULE_CHECK_VALUES
3. `test_deprecated_column_present_after_chain` — deprecated column present after migration 002
4. `test_data_source_column_present_after_chain` — data_source column present
5. `test_no_orphan_channels_in_schema_vs_models` — inverse check: schema does not accept channels absent from models.py

Total test count: 36 (up from 28). All GREEN. Exit 0.

### Task 2: .github/workflows/schema-drift.yml + README.md

Created first GitHub Actions workflow in the Sentinel repo:
- Triggers: `pull_request` (any branch) + `push` to `main`
- Job `schema-drift-check` on `ubuntu-latest`
- Steps: checkout@v4, setup-python@v5 (Python 3.11 pinned), pip install -r requirements.txt, python scripts/test_models_sync.py -v
- Zero `secrets.*` references (T-18-02-01 mitigated)

Created `.github/workflows/README.md` documenting:
- Convention: one file per gate, kebab-case, pin action versions
- Current workflows table (schema-drift.yml row)
- 3-step recipe for adding future workflows
- v1.2 silent-failure rationale (2-month gap, 7-channel drift root cause)

## Commits

| Task | Commit | Message |
|------|--------|---------|
| Task 1 | `a51e7d2` | test(18-02): extend test_models_sync.py with Migration 006 + chain-against-models composite assertion (HARD-02) |
| Task 2 | `91bc1cb` | ci(18-02): add schema-drift GitHub Actions gate + workflows/README.md (HARD-02 CI gate) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added _STALE_ALERTS_DDL baseline before migration chain in setUpClass**

- **Found during:** Task 1 implementation + test run
- **Issue:** Migration 001 uses `ALTER TABLE alerts RENAME TO _alerts_old_001` — requires the `alerts` table to already exist in the `:memory:` DB. The plan's skeleton called `executescript` directly on migrations without creating a base schema first. First test run yielded `sqlite3.OperationalError: no such table: alerts`.
- **Fix:** Added `_STALE_ALERTS_DDL` module-level constant with the pre-001 stale schema (2-channel channel_group, 4-rule alert_rule), applied via `executescript` before the migration chain in `setUpClass`.
- **Secondary fix:** `pipeline_runs` baseline intentionally omits `alerts_written_count` since migration 003 adds it via `ALTER TABLE ADD COLUMN` — including it in baseline caused `duplicate column name: alerts_written_count` on first run.
- **Files modified:** scripts/test_models_sync.py
- **Commits:** included in Task 1 commit `a51e7d2`

## Known Stubs

None — plan goals fully achieved with live data paths wired.

## Threat Flags

None — scan of created/modified files found no new security-relevant surface beyond what the plan's threat model already documented (T-18-02-01 through T-18-02-04 all mitigated).

Verified: `grep -c "secrets\." .github/workflows/schema-drift.yml` returns 0.

## Self-Check: PASSED

- `.github/workflows/schema-drift.yml` exists: FOUND
- `.github/workflows/README.md` exists: FOUND
- `scripts/test_models_sync.py` contains `MIGRATION_006 = REPO_ROOT`: FOUND
- `scripts/test_models_sync.py` contains `class TestMigration006Sync`: FOUND
- `scripts/test_models_sync.py` contains `class TestComposeChainAgainstModels`: FOUND
- Commit `a51e7d2` exists: FOUND
- Commit `91bc1cb` exists: FOUND
- Test suite exits 0 (36/36 GREEN): VERIFIED
