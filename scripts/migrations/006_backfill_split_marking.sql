-- Migration: 006_backfill_split_marking
-- Purpose: Phase 17.4 D2CLOSE-03 (D-10, D-11, D-12) — mark 199 non-GOOGLE_ADEX
--          backfill alerts as deprecated=1 with explicit reason pointing to
--          Phase 21 v1.4 Athena dependency. `data_source` field UNCHANGED
--          (per D-11 — preserves audit trail Marco baseline reference for
--          the historical synthetic-era values).
--
-- Generated: 2026-05-21
--
-- Targets:
--   Row population: 199 rows where:
--     channel_group != 'GOOGLE_ADEX'
--     AND data_source = 'backfill'
--     AND deprecated = 0
--   Breakdown by channel (verified 2026-05-21 via sqlite3 count):
--     DEAL                    : 26
--     DIRECT                  : 33
--     GOOGLE (legacy alias)   : 24
--     HEADER_BIDDING_MAGNITE  : 29
--     HEADER_BIDDING_PUBMATIC : 29
--     OPEN_BIDDING            : 30
--     TAM                     : 28
--     Total                   : 199
--
-- Why these alerts are deprecated (not rewritten):
--   Sentinel's hourly ingestion source `data/sentinel_db/hour_kpi.csv` contains
--   ONLY GOOGLE_ADEX rows (verified by Phase 17.3 DIAGNOSIS.md scan of 459,518 rows).
--   For HBM/HBP/TAM/DIRECT/DEAL/OPEN_BIDDING/GOOGLE there is no real hourly source
--   to rewrite against until Phase 21 v1.4 Athena ingestion lands.
--
-- Why not flip data_source to 'synthetic'?
--   D-11: the existing 'backfill' tag preserves the historical audit trail.
--   Marco's email 2026-05-19 audit referenced these specific revenue values;
--   changing data_source erases that reference. The `deprecated=1` flag is the
--   visibility lever — UI default `/api/alerts` already filters `WHERE deprecated=0`
--   (Phase 09 D-14 pattern); `?include_deprecated=true` is opt-in disclosure.
--
-- Traceability:
--   CONTEXT decisions:    D-10 (199 alerts marking) + D-11 (data_source preserved) + D-12 (migration not ad-hoc)
--   Phase 09 precedent:   002_add_alert_deprecation.sql (deprecated/deprecation_reason columns added MIGRATE-01)
--   Phase 10.1 driver:    004_canonicalize_alerts_created_at.sql (idempotency + ledger pattern)
--   Pre-apply backup:     data/vna_alerts.db.pre-17.4-backfill-rewrite (Task 2 BLOCKING checkpoint)
--   Reversibility:        scripts/migrations/006_rollback.sql + tag pre-17.4-backfill-rewrite
--
-- Post-apply invariants (verified by scripts/test_migration_006_apply.py):
--   * COUNT(*) WHERE channel_group != 'GOOGLE_ADEX' AND data_source='backfill' AND deprecated=1 = 199
--   * COUNT(*) WHERE data_source='backfill' = 238 (UNCHANGED — only deprecated/reason mutated)
--   * COUNT(*) WHERE channel_group='GOOGLE_ADEX' AND data_source='backfill' AND deprecated=0 = 39 (rewrite-script target)
--   * ledger has row ('006_backfill_split_marking', <datetime>)
--   * Total row count unchanged (no INSERT/DELETE)
--
-- ROLLBACK:
--   scripts/migrations/006_rollback.sql undoes the marking + deletes ledger row.
--   Alternative full DB rollback: cp data/vna_alerts.db.pre-17.4-backfill-rewrite data/vna_alerts.db
--   (snapshot taken in Task 2 BLOCKING checkpoint via apply_migration_006.py _backup()).
--
-- IDEMPOTENCY CONTRACT:
--   Ledger INSERT (no OR REPLACE) as FIRST statement after ledger CREATE IF NOT EXISTS.
--   Second apply raises UNIQUE constraint failed BEFORE any UPDATE executes;
--   transaction rolls back; DB unchanged.

PRAGMA foreign_keys=OFF;

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS vna_schema_migrations (
    migration_id TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);

-- IDEMPOTENCY GUARD: fails on second apply with UNIQUE constraint error.
-- This INSERT appears BEFORE any UPDATE so a second apply aborts cleanly
-- without touching any alert row.
INSERT INTO vna_schema_migrations(migration_id, applied_at)
    VALUES ('006_backfill_split_marking', datetime('now'));

-- Mark 199 non-GOOGLE_ADEX backfill alerts as deprecated with explicit reason.
-- data_source field intentionally NOT modified (D-11 audit trail preservation).
-- The deprecation_reason value 'synthetic-era pre-H6-fix, Phase 21 Athena dependency'
-- is the canonical string used by rollback SQL and post-apply verification.
UPDATE alerts
   SET deprecated = 1,
       deprecation_reason = 'synthetic-era pre-H6-fix, Phase 21 Athena dependency'
 WHERE channel_group != 'GOOGLE_ADEX'
   AND data_source = 'backfill'
   AND deprecated = 0;

COMMIT;

PRAGMA foreign_keys=ON;
