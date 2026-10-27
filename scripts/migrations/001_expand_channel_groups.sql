-- Migration: 001_expand_channel_groups
-- Purpose: Expand `alerts.channel_group` CHECK to 8 values, `alerts.alert_rule`
--          CHECK to 8 values (A4 skipped intentionally), and tighten
--          `pending_notifications.severity` + `pending_notifications.channel_group`
--          CHECKs — closes Phase 08 SCHEMA-01.
--
-- Generated: 2026-04-23T00:00:00Z
--
-- Traceability:
--   channel_group CHECK source:  backend/db/models.py:182 (SQL_CREATE_ALERTS)
--   alert_rule CHECK source:     backend/db/models.py:184 (SQL_CREATE_ALERTS)
--   severity CHECK source:       backend/db/models.py:181 (SQL_CREATE_ALERTS)
--   Pre-migration (stale) schema: .planning/phases/07-db-wip-investigation/wip-schema.sql:59-61
--   Design decision:             .planning/phases/07-db-wip-investigation/DECISION.md
--
-- Precondition:
--   Run AFTER `000_wip_drift_baseline.sql`. Asserts `alerts` and
--   `pending_notifications` tables exist (created by 000.sql on a DB that
--   started at HEAD baseline). Applying to a DB that has NOT had 000.sql
--   applied first will fail with "no such table: alerts" (clear failure,
--   not silent corruption).
--
-- Rollback:
--   If migration apply fails mid-transaction, SQLite auto-rolls back to
--   pre-BEGIN state automatically (no manual action needed).
--   If apply succeeds but post-apply verification fails:
--     cp data/vna_alerts.db.pre-phase08.bak data/vna_alerts.db
--   See .planning/phases/08-schema-migration-etl-extensions/08-03-PLAN.md
--   for the full backup + apply + verify procedure.
--
-- IDEMPOTENCY CONTRACT:
--   This file must NOT be applied twice without a driver pre-check.
--   The ledger INSERT (without OR REPLACE) at the top of the transaction
--   intentionally raises UNIQUE constraint failed on second apply, causing
--   the entire transaction to roll back before any DDL executes. This is
--   the driver-guard invariant: the DB remains intact, the error is clear.
--
--   The driver (scripts/test_migration_001.py and Plan 03 apply script)
--   MUST read sqlite_master BEFORE invoking this file and skip re-apply
--   when `SELECT sql FROM sqlite_master WHERE name='alerts'` contains
--   'GOOGLE_ADEX'. Example driver pre-check:
--
--     import sqlite3
--     conn = sqlite3.connect("data/vna_alerts.db")
--     row = conn.execute(
--         "SELECT sql FROM sqlite_master WHERE type='table' AND name='alerts'"
--     ).fetchone()
--     if row and 'GOOGLE_ADEX' in (row[0] or ''):
--         print("001 already applied -- skipping")
--     else:
--         # apply 001.sql
--
--   Applying twice without the driver guard will fail with:
--     sqlite3.OperationalError: UNIQUE constraint failed:
--       vna_schema_migrations.migration_id
--   This is intentional: forces Plan 03 apply script to add pre-check.
--   See scripts/test_migration_001.py test_second_apply_is_guarded.
--
-- Post-apply invariants (verified by scripts/test_migration_001.py):
--   * alerts CHECK channel_group contains all 8 values per models.py:182
--   * alerts CHECK alert_rule contains A0,A1,A2,A3,A5,A6,A7,A8 (A4 NOT in list)
--   * pending_notifications.severity has CHECK IN ('P0','P1','P2')
--   * pending_notifications.channel_group has 8-value CHECK
--   * vna_schema_migrations contains row ('001_expand_channel_groups', <ts>)
--   * Row count in alerts and pending_notifications is PRESERVED vs pre-apply.
--
-- SQLite table-recreate pattern (as used in backend/db/database.py:65-92):
--   PRAGMA foreign_keys=OFF;   -- MUST be before the transaction (no-op inside)
--   ALTER TABLE <t> RENAME TO _<t>_old_001;
--   CREATE TABLE <t> ( ... new CHECKs ... );
--   INSERT INTO <t> SELECT * FROM _<t>_old_001;
--   DROP TABLE _<t>_old_001;
--   PRAGMA foreign_keys=ON;    -- MUST be after COMMIT
--   (SQLite does not support ALTER COLUMN or ALTER CHECK — recreate is mandatory)
--   (PRAGMA foreign_keys is a no-op inside a transaction per SQLite docs)

-- SQLite NOTE: PRAGMA foreign_keys cannot be changed inside a transaction
-- (it is silently ignored). It MUST precede the BEGIN statement below.
-- Reference: https://www.sqlite.org/pragma.html#pragma_foreign_keys
-- "This pragma is a no-op within a transaction."
PRAGMA foreign_keys=OFF;

BEGIN TRANSACTION;

-- ===========================================================================
-- 1. Ledger table + idempotency guard
--
--    The INSERT (without OR REPLACE) is intentionally the FIRST statement
--    after the ledger table creation. On second apply, this raises:
--      UNIQUE constraint failed: vna_schema_migrations.migration_id
--    causing the ENTIRE transaction to roll back BEFORE any DDL executes.
--    This is the driver-guard invariant (see IDEMPOTENCY CONTRACT above).
-- ===========================================================================

CREATE TABLE IF NOT EXISTS vna_schema_migrations (
    migration_id TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);

-- IDEMPOTENCY GUARD: fails on second apply with UNIQUE constraint error.
-- This is intentional — see IDEMPOTENCY CONTRACT in header.
INSERT INTO vna_schema_migrations(migration_id, applied_at)
    VALUES ('001_expand_channel_groups', datetime('now'));

-- ===========================================================================
-- 2. Recreate alerts table with expanded CHECKs
--
--    Expands:
--      channel_group: 2 values → 8 values (adds GOOGLE_ADEX, OPEN_BIDDING,
--                     HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC,
--                     TAM, DIRECT, DEAL; preserves GOOGLE from v1.0)
--      alert_rule:    4 values → 8 values (adds A5, A6, A7, A8; A4 deliberately
--                     skipped — see models.py:184 and Phase 08 SCHEMA-01)
--
--    Preserves all existing rows via INSERT SELECT.
--    Column list MUST match wip-schema.sql:55-75 exactly (any mismatch breaks
--    INSERT INTO alerts SELECT * FROM _alerts_old_001).
-- ===========================================================================

ALTER TABLE alerts RENAME TO _alerts_old_001;

CREATE TABLE alerts (
    alert_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('P0', 'P1', 'P2')),
    channel_group TEXT NOT NULL CHECK(channel_group IN ('GOOGLE_ADEX', 'OPEN_BIDDING', 'HEADER_BIDDING_MAGNITE', 'HEADER_BIDDING_PUBMATIC', 'TAM', 'DIRECT', 'DEAL', 'GOOGLE')),
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'ACK', 'RESOLVED', 'SNOOZED')),
    alert_rule TEXT NOT NULL CHECK(alert_rule IN ('A0', 'A1', 'A2', 'A3', 'A5', 'A6', 'A7', 'A8')),
    revenue_current REAL NOT NULL,
    revenue_baseline REAL NOT NULL,
    revenue_delta_pct REAL NOT NULL,
    triage_label TEXT NOT NULL,
    contributors_json TEXT DEFAULT '[]',
    geo_breakdown_json TEXT DEFAULT '[]',
    environment_split_json TEXT DEFAULT '{}',
    insights_json TEXT DEFAULT '{}',
    execution_time_sec REAL DEFAULT 0.0,
    data_source TEXT DEFAULT 'athena',
    config_version TEXT DEFAULT '1.0.0',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

INSERT INTO alerts SELECT * FROM _alerts_old_001;
DROP TABLE _alerts_old_001;

-- Recreate indexes dropped when alerts was renamed
-- (SQLite drops all indexes associated with a renamed table)
CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);

-- ===========================================================================
-- 3. Recreate pending_notifications with tightened CHECKs
--
--    Tightens (from no CHECK to explicit):
--      severity:      unconstrained → CHECK IN ('P0','P1','P2')
--      channel_group: unconstrained → CHECK IN (8-value list, same as alerts)
--
--    Closes Phase 07 test-agent gotcha: pending_notifications accepted any
--    string in severity/channel_group, silently allowing invalid values.
--    Tightened in same transaction as alerts expansion to maintain consistency.
-- ===========================================================================

ALTER TABLE pending_notifications RENAME TO _pending_notifications_old_001;

CREATE TABLE pending_notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('P0', 'P1', 'P2')),
    channel_group TEXT NOT NULL CHECK(channel_group IN ('GOOGLE_ADEX', 'OPEN_BIDDING', 'HEADER_BIDDING_MAGNITE', 'HEADER_BIDDING_PUBMATIC', 'TAM', 'DIRECT', 'DEAL', 'GOOGLE')),
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id) ON DELETE CASCADE
);

INSERT INTO pending_notifications(id, alert_id, severity, channel_group, timestamp, created_at)
    SELECT id, alert_id, severity, channel_group, timestamp, created_at
    FROM _pending_notifications_old_001;
DROP TABLE _pending_notifications_old_001;

CREATE INDEX IF NOT EXISTS idx_pending_notifications_created_at ON pending_notifications(created_at);

COMMIT;

-- SQLite NOTE: Re-enable FK enforcement AFTER COMMIT (pragma is no-op inside
-- a transaction). The PRAGMA foreign_keys=OFF at the top of this file disabled
-- it for the duration of the DDL operations; this restores it for subsequent
-- operations on the same connection.
PRAGMA foreign_keys=ON;
