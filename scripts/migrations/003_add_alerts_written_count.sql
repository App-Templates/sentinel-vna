-- Migration: 003_add_alerts_written_count
-- Purpose: Add `alerts_written_count` column to `pipeline_runs` for MONITOR-03
--          (Phase 10). INTEGER NOT NULL DEFAULT 0 CHECK(alerts_written_count >= 0)
--          so all pre-existing rows inherit alerts_written_count=0 at ALTER time
--          via DEFAULT propagation (SQLite 3.35+ NOT NULL DEFAULT constant).
--
-- Generated: 2026-04-23
--
-- Traceability:
--   alerts_written_count source: backend/db/models.py SQL_CREATE_PIPELINE_RUNS (post-003)
--   Design decisions:            .planning/phases/10-pipeline-silent-failure-monitoring/10-01-PLAN.md alternatives_considered
--   Precondition:                Run AFTER 002_add_alert_deprecation.sql.
--
-- Post-apply invariants (verified by scripts/test_migration_003_apply.py):
--   * pipeline_runs has column `alerts_written_count` INTEGER NOT NULL DEFAULT 0 CHECK(alerts_written_count >= 0)
--   * ledger has row ('003_add_alerts_written_count', <datetime>)
--   * All existing pipeline_runs rows preserved with alerts_written_count=0 via DEFAULT propagation
--
-- IDEMPOTENCY CONTRACT (same as 002):
--   Ledger INSERT without OR REPLACE raises UNIQUE constraint on second apply,
--   transaction rolls back before DDL. Driver (scripts/apply_migration_003.py)
--   pre-checks column + ledger row presence via PRAGMA + SELECT.

-- SQLite NOTE: PRAGMA foreign_keys cannot be changed inside a transaction
-- (it is silently ignored). It MUST precede the BEGIN statement below.
-- Reference: https://www.sqlite.org/pragma.html#pragma_foreign_keys
-- "This pragma is a no-op within a transaction."
PRAGMA foreign_keys=OFF;

BEGIN TRANSACTION;

-- ===========================================================================
-- 1. Ledger table + idempotency guard
--
--    Ledger table is created by 001 already; CREATE IF NOT EXISTS is
--    self-contained (safe to run on a fresh DB too).
--    The INSERT (without OR REPLACE) is intentionally the FIRST statement
--    after the ledger table creation. On second apply, this raises:
--      UNIQUE constraint failed: vna_schema_migrations.migration_id
--    causing the ENTIRE transaction to roll back BEFORE any DDL executes.
-- ===========================================================================

CREATE TABLE IF NOT EXISTS vna_schema_migrations (
    migration_id TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);

-- IDEMPOTENCY GUARD: fails on second apply with UNIQUE constraint error.
INSERT INTO vna_schema_migrations(migration_id, applied_at)
    VALUES ('003_add_alerts_written_count', datetime('now'));

-- ===========================================================================
-- 2. ALTER TABLE ADD COLUMN (SQLite 3.35+ supports NOT NULL DEFAULT const).
--
--    Per alternatives_considered: INT not BOOL for headroom (future co-fire
--    path may emit multiple alerts per run). CHECK(>= 0) enforced at DB layer.
--    All pre-existing pipeline_runs rows inherit alerts_written_count=0
--    via DEFAULT propagation at ALTER time — no post-hoc UPDATE needed.
-- ===========================================================================

ALTER TABLE pipeline_runs ADD COLUMN alerts_written_count INTEGER NOT NULL DEFAULT 0 CHECK(alerts_written_count >= 0);

COMMIT;

-- SQLite NOTE: Re-enable FK enforcement AFTER COMMIT (pragma is no-op inside
-- a transaction). The OFF pragma at the top of this file disabled FK checks
-- for the duration of the DDL operations; this restores them for subsequent
-- operations on the same connection.
PRAGMA foreign_keys=ON;
