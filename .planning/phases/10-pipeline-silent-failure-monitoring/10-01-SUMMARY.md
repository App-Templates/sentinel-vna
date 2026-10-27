---
phase: 10
plan: "01"
plan_name: alerts-written-count-migration
subsystem: pipeline-monitoring
tags:
  - migration
  - sqlite
  - monitor
  - hard-03
  - pipeline-runs

dependency_graph:
  requires:
    - "09-03 (Phase 09 Plan 03: backfill alerts + pipeline_runs baseline)"
  provides:
    - "alerts_written_count column in pipeline_runs (MONITOR-03)"
    - "Migration 003 SQL + rollback + apply driver + smoke tests"
    - "HARD-03 drift detector extended to 23 tests (TestModels003Sync)"
  affects:
    - "backend/db/operations.py record_pipeline_run (additive kwarg)"
    - "backend/scheduler/scheduler.py _run_trigger_for_channels (LIVE call sites)"
    - "scripts/backfill_alerts.py orchestrator (BACKTEST call sites)"
    - "data/vna_alerts.db (live DB migrated)"

tech_stack:
  added:
    - "sqlite3.Connection.backup() WAL-safe snapshot pattern (reused from Phase 09)"
    - "Phase 10 migration 003 ledger guard pattern"
  patterns:
    - "R-11 sub-commit gating: Task 0 snapshot → Task 1 SQL → Task 2 driver → Task 3 code → Task 4 DB apply"
    - "Idempotency via UNIQUE constraint on vna_schema_migrations.migration_id"
    - "TestModels003Sync: static drift detection across SQL + models.py + live DB"

key_files:
  created:
    - scripts/migrations/003_add_alerts_written_count.sql
    - scripts/migrations/003_rollback.sql
    - scripts/apply_migration_003.py
    - scripts/test_migration_003_apply.py
    - data/vna_alerts.db.pre-phase10.bak
  modified:
    - backend/db/models.py (SQL_CREATE_PIPELINE_RUNS + new column + comments)
    - scripts/test_models_sync.py (TestModels003Sync class + MIGRATION_003 constants)
    - backend/db/operations.py (record_pipeline_run signature + INSERT SQL)
    - backend/scheduler/scheduler.py (_run_trigger_for_channels call sites)
    - scripts/backfill_alerts.py (orchestrator call sites)
    - data/vna_alerts.db (live DB migrated)

decisions:
  - "alerts_written_count is INT not BOOL: preserves headroom for future co-fire path (multiple alerts per run)"
  - "Column placed LAST in SQL_CREATE_PIPELINE_RUNS: mirrors SQLite ALTER TABLE ADD COLUMN append semantics; HARD-03 gate enforces byte-identity"
  - "Pre-existing pipeline_runs rows left at DEFAULT 0: retro-filling from alert_id IS NOT NULL would muddy the signal the watchdog needs"
  - "importlib.util.spec_from_file_location used in test shim: scripts/ has no __init__.py; standard import scripts.apply_migration_003 fails"

metrics:
  duration: "~20 minutes"
  tasks_completed: 5
  files_changed: 11
  completed_date: "2026-04-23"
---

# Phase 10 Plan 01: alerts_written_count Migration (MONITOR-03) Summary

Adds `alerts_written_count INTEGER NOT NULL DEFAULT 0 CHECK(alerts_written_count >= 0)` column to `pipeline_runs` via Migration 003, extends HARD-03 drift gate to TestModels003Sync, wires the counter through all LIVE and BACKTEST pipeline call sites, and applies the migration to live DB.

## Task Completion

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 0 | Pre-phase safety checkpoint (tag + WAL-safe DB snapshot) | de9e79e | data/vna_alerts.db.pre-phase10.bak |
| 1 | Migration 003 SQL + models.py sync + HARD-03 drift gate | b7b2af1 | 003_add_alerts_written_count.sql, 003_rollback.sql, backend/db/models.py, scripts/test_models_sync.py |
| 2 | apply_migration_003.py driver + live-DB smoke tests | 2e1d222 | scripts/apply_migration_003.py, scripts/test_migration_003_apply.py |
| 3 | Wire record_pipeline_run + call-site updates | c29f35a | backend/db/operations.py, backend/scheduler/scheduler.py, scripts/backfill_alerts.py |
| 4 | [BLOCKING] Apply migration 003 to live DB | 22abf88 | data/vna_alerts.db |

## Evidence

### Migration Ledger Row

```
migration_id                  | applied_at
003_add_alerts_written_count  | 2026-04-23 17:03:28
```

### Pre/Post Row Counts

| Table | Pre-apply | Post-apply | Delta |
|-------|-----------|------------|-------|
| pipeline_runs | 4,032 | 4,032 | 0 |
| alerts | 438 | 438 | 0 |

All 4,032 pre-existing pipeline_runs rows received `alerts_written_count=0` via DEFAULT propagation (verified by driver `_verify_alerts_written_count_default`).

### Smoke Test Evidence (Task 4 STEP 5)

- **INSERT with alerts_written_count=1:** `SMOKE PASSED` — row confirmed in live DB, then deleted.
- **CHECK constraint enforcement:** `PASS: CHECK rejected negative value: CHECK constraint failed: alerts_written_count >= 0`
- **Idempotency:** second `apply_migration_003.py` run emits `SKIP: migration 003 already applied`.

### HARD-03 Gate

`.venv/bin/python scripts/test_models_sync.py` — **23 tests, all OK** (TestModelsSync + TestModels002Sync + TestModels003Sync).

### Rollback Path Verification

- `cp data/vna_alerts.db.pre-phase10.bak data/vna_alerts.db` — WAL-safe backup at tag `v1.3-pre-phase-10`.
- `sqlite3 data/vna_alerts.db < scripts/migrations/003_rollback.sql` — tested in dry-run via smoke test temp-DB.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed shim module import in test_migration_003_apply.py**
- **Found during:** Task 2 smoke test run
- **Issue:** Plan's shim used `import scripts.apply_migration_003 as d` which fails because `scripts/` has no `__init__.py` (not a Python package — it's a scripts directory).
- **Fix:** Replaced with `importlib.util.spec_from_file_location('apply_migration_003', driver_path)` + `spec.loader.exec_module(d)` to load the driver by file path.
- **Files modified:** scripts/test_migration_003_apply.py
- **Commit:** 2e1d222

**2. [Informational] STEP 4a regex in plan matched wrong VALUES clause**
- The plan's STEP 4a regex `re.search(r'VALUES\s*\(([^)]+)\)', src)` returned 19 placeholders by matching a non-pipeline-runs VALUES clause elsewhere in operations.py. The fix was to use a more targeted regex anchored to the pipeline_runs INSERT. The actual INSERT SQL is correct (13 cols, 13 placeholders) — verified by targeted check. Not committed separately (acceptance criterion was met via equivalent check).

## Known Stubs

None. All columns wired end-to-end: migration SQL → models.py → apply driver → operations.py → call sites.

## Handoff Notes for Phase 10 Plans 02 + 03

**Phase 10-02** — `/health/alerts-pipeline` endpoint:
- `pipeline_runs.alerts_written_count` is now live. Query: `SELECT COUNT(*) FROM pipeline_runs WHERE created_at >= datetime('now', '-24 hours')` (run count), `SUM(alerts_written_count)` (alerts written), `SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END)` (failures).

**Phase 10-03** — Silent-failure watchdog:
- Counter semantics: `runs_last_24h > 0 AND SUM(alerts_written_count) = 0 → P0 silent-failure`.
- Implementation should use `backend/monitoring/silent_failure_watch.py` (dedicated module, not scheduler.py inline) per the plan's `alternatives_considered` decision.
- Pre-existing 4,032 pipeline_runs rows all have `alerts_written_count=0` — watchdog must use a time window filter (e.g., `created_at >= datetime('now', '-24 hours')`) to avoid false positives from the historical corpus.

## Self-Check: PASSED
