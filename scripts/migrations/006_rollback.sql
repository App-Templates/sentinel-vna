-- Rollback: 006_backfill_split_marking
-- Purpose: Restore the 199 non-GOOGLE_ADEX backfill alerts to deprecated=0 +
--          NULL deprecation_reason, and delete the ledger row for
--          '006_backfill_split_marking'.
--
-- Generated: 2026-05-21
--
-- Idempotency: Safe to run multiple times.
--   - UPDATE has no effect once all 199 rows are already back to deprecated=0 / NULL.
--   - DELETE on a non-existent ledger row is a no-op.
--
-- Scope: Reverses Migration 006 ONLY.
--   If the rewrite script (rewrite_backfill_google_adex_post_17_4.py) has also run,
--   those changes to the 39 GOOGLE_ADEX rows are INDEPENDENT of this rollback and
--   remain. To fully restore the pre-Plan-04 state, use the full snapshot restore:
--     cp data/vna_alerts.db.pre-17.4-backfill-rewrite data/vna_alerts.db
--
-- Traceability:
--   Forward migration:    scripts/migrations/006_backfill_split_marking.sql
--   Snapshot rollback:    cp data/vna_alerts.db.pre-17.4-backfill-rewrite data/vna_alerts.db
--   Git rollback:         git checkout pre-17.4-backfill-rewrite (reverts SQL+driver source only)
--
-- Usage:
--   sqlite3 data/vna_alerts.db < scripts/migrations/006_rollback.sql

PRAGMA foreign_keys=OFF;

BEGIN TRANSACTION;

-- Restore the 199 deprecated rows to deprecated=0 + NULL reason.
-- WHERE clause targets only the rows marked by migration 006 (identified by
-- the canonical deprecation_reason string), so running this multiple times
-- or on a partially-applied state is safe.
UPDATE alerts
   SET deprecated = 0,
       deprecation_reason = NULL
 WHERE deprecation_reason = 'synthetic-era pre-H6-fix, Phase 21 Athena dependency'
   AND data_source = 'backfill'
   AND channel_group != 'GOOGLE_ADEX';

-- Remove the migration ledger entry so the forward migration can be re-applied.
DELETE FROM vna_schema_migrations
 WHERE migration_id = '006_backfill_split_marking';

COMMIT;

PRAGMA foreign_keys=ON;
