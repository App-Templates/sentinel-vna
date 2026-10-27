-- Migration: 002_add_alert_deprecation
-- Purpose: Add `deprecated` + `deprecation_reason` columns to the `alerts` table
--          for MIGRATE-01 legacy alert soft-delete (Phase 09). `deprecated` is
--          INTEGER NOT NULL DEFAULT 0 CHECK(deprecated IN (0, 1)) so all 200
--          pre-existing legacy alerts inherit `deprecated=0` at ALTER time via
--          DEFAULT propagation (SQLite 3.35+ NOT NULL DEFAULT constant support).
--
-- Generated: 2026-04-23
--
-- Traceability:
--   deprecated CHECK source:        backend/db/models.py SQL_CREATE_ALERTS (post-002)
--   deprecation_reason TEXT source: backend/db/models.py SQL_CREATE_ALERTS (post-002)
--   Design decisions:               .planning/phases/09-alert-backfill-legacy-migration/09-CONTEXT.md D-10..D-13
--   Precondition:                   Run AFTER 001_expand_channel_groups.sql (live DB
--                                   must be at Phase 08 v2 schema — 8-channel + 8-rule CHECKs).
--
-- Post-apply invariants (verified by scripts/test_migration_002_apply.py):
--   * alerts has column `deprecated` INTEGER NOT NULL DEFAULT 0 CHECK(deprecated IN (0,1))
--   * alerts has column `deprecation_reason` TEXT (nullable, no CHECK)
--   * ledger has row ('002_add_alert_deprecation', <datetime>)
--   * 200 existing alert rows preserved with deprecated=0 via DEFAULT propagation
--   * deprecation_reason is NULL for all 200 existing rows
--   * idx_alerts_deprecated index exists on alerts(deprecated)
--
-- Rollback:
--   If migration apply fails mid-transaction, SQLite auto-rolls back to pre-BEGIN
--   state automatically (no manual action needed).
--   If apply succeeds but rollback is later needed:
--     sqlite3 data/vna_alerts.db < scripts/migrations/002_rollback.sql
--   OR (belt-and-suspenders):
--     cp data/vna_alerts.db.pre-phase09.bak data/vna_alerts.db
--
-- IDEMPOTENCY CONTRACT:
--   The ledger INSERT (without OR REPLACE) at the top of the transaction
--   intentionally raises UNIQUE constraint failed on second apply, causing
--   the entire transaction to roll back before any DDL executes. This is
--   the driver-guard invariant: the DB remains intact, the error is clear.
--
--   The driver (scripts/apply_migration_002.py) MUST pre-check column presence
--   via PRAGMA table_info(alerts) AND ledger row presence BEFORE invoking this
--   file. Mismatched (cols present but ledger missing, or vice versa) is a
--   hard error requiring manual inspection.

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
    VALUES ('002_add_alert_deprecation', datetime('now'));

-- ===========================================================================
-- 2. ALTER TABLE ADD COLUMN (SQLite 3.35+ supports NOT NULL DEFAULT const).
--
--    Per D-13 all 200 existing rows inherit deprecated=0 via DEFAULT at
--    ALTER time — NO post-hoc UPDATE needed here (legacy UPDATE runs in
--    plan 09-02 via scripts/deprecate_legacy_alerts.py).
-- ===========================================================================

ALTER TABLE alerts ADD COLUMN deprecated INTEGER NOT NULL DEFAULT 0 CHECK(deprecated IN (0, 1));
ALTER TABLE alerts ADD COLUMN deprecation_reason TEXT;

-- ===========================================================================
-- 3. Supporting index
--
--    Frequent query pattern after plan 09-03: `WHERE deprecated = 0` is the
--    default filter in /api/alerts. Partial/full index on deprecated keeps
--    the list endpoint fast as the legacy+backfill dataset grows.
-- ===========================================================================

CREATE INDEX IF NOT EXISTS idx_alerts_deprecated ON alerts(deprecated);

COMMIT;

-- SQLite NOTE: Re-enable FK enforcement AFTER COMMIT (pragma is no-op inside
-- a transaction). The OFF pragma at the top of this file disabled FK checks
-- for the duration of the DDL operations; this restores them for subsequent
-- operations on the same connection.
PRAGMA foreign_keys=ON;
