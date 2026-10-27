-- Migration DOWN: 002_rollback
-- Purpose: DOWN script for 002_add_alert_deprecation. Drops both columns
--          (`deprecation_reason` then `deprecated`), drops the supporting
--          index, and removes the ledger row.
--
-- Run ONLY if explicit rollback needed per
-- .planning/phases/09-alert-backfill-legacy-migration/09-01-PLAN.md rollback_plan.
-- Preferred rollback: restore from .pre-phase09.bak (byte-accurate snapshot);
-- this DOWN script is the fallback path when backup is missing/corrupt.
--
-- SQLite NOTE: SQLite 3.35+ supports ALTER TABLE DROP COLUMN natively.

PRAGMA foreign_keys=OFF;

BEGIN TRANSACTION;

-- Drop nullable col first, then NOT NULL col (order irrelevant semantically,
-- but mirrors reverse of add-order for clarity).
ALTER TABLE alerts DROP COLUMN deprecation_reason;
ALTER TABLE alerts DROP COLUMN deprecated;

DROP INDEX IF EXISTS idx_alerts_deprecated;

DELETE FROM vna_schema_migrations WHERE migration_id = '002_add_alert_deprecation';

COMMIT;

PRAGMA foreign_keys=ON;
