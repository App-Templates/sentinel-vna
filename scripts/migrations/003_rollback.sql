-- Migration DOWN: 003_rollback
-- Purpose: DOWN script for 003_add_alerts_written_count. Drops the
--          `alerts_written_count` column and removes the ledger row.
--
-- Run ONLY if explicit rollback needed per
-- .planning/phases/10-pipeline-silent-failure-monitoring/10-01-PLAN.md rollback_plan.
-- Preferred rollback: restore from .pre-phase10.bak (byte-accurate snapshot);
-- this DOWN script is the fallback path when backup is missing/corrupt.
--
-- SQLite NOTE: SQLite 3.35+ supports ALTER TABLE DROP COLUMN natively.

PRAGMA foreign_keys=OFF;

BEGIN TRANSACTION;

ALTER TABLE pipeline_runs DROP COLUMN alerts_written_count;

DELETE FROM vna_schema_migrations WHERE migration_id = '003_add_alerts_written_count';

COMMIT;

PRAGMA foreign_keys=ON;
