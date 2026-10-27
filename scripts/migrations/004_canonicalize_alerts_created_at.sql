-- Migration: 004_canonicalize_alerts_created_at
-- Purpose: Normalize `alerts.created_at` to canonical space-separator naive
--          UTC microseconds format ('YYYY-MM-DD HH:MM:SS.ffffff') per
--          D-10.1-01. Fixes MAJOR-NEW-01 (auditor A): pre-migration rows are
--          written in 3 formats depending on code path:
--            - aware T: '2026-04-23T21:42:50+00:00' (notifier._save_to_db)
--            - naive T microseconds: '2026-04-23T21:42:50.142222' (operations.create_alert)
--            - space second: '2026-04-23 21:42:50' (SQLite datetime('now') default)
--          The '+' in aware rows sorts below digits breaking MAX(created_at);
--          the 'T' vs ' ' separator breaks 24h string comparisons against
--          SQLite datetime('now','-1 day') output (which is space-sep).
--
-- Generated: 2026-04-24
--
-- Traceability:
--   Canonical format source:        D-10.1-01 (10.1-CONTEXT.md)
--   Audit:                          /tmp/auditor_a_sql_report.md MAJOR-NEW-01
--   Write-path unification:         Plan 10.1-02 (notifier.py + operations.py)
--   Precondition:                   Run AFTER migration 003 (ledger row present).
--
-- Post-apply invariants (verified by scripts/test_migration_004_apply.py):
--   * 100% of alerts.created_at rows match ^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}$
--   * ledger has row ('004_canonicalize_alerts_created_at', <datetime>)
--   * row count unchanged (438 live -- no INSERT/DELETE)
--   * MAX(created_at) returns the true chronologically-latest row
--
-- ROLLBACK:
--   Format normalization is a one-way decision. Rollback script only removes
--   the ledger row -- reverting row contents to the original mixed formats
--   requires restoring from data/vna_alerts.db.pre-phase10.1.bak:
--     cp data/vna_alerts.db.pre-phase10.1.bak data/vna_alerts.db
--
-- IDEMPOTENCY CONTRACT:
--   Ledger INSERT (no OR REPLACE) as FIRST statement after ledger CREATE IF
--   NOT EXISTS. Second apply raises UNIQUE constraint failed BEFORE any
--   UPDATE executes; transaction rolls back; DB unchanged.

PRAGMA foreign_keys=OFF;

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS vna_schema_migrations (
    migration_id TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);

-- IDEMPOTENCY GUARD: fails on second apply with UNIQUE constraint error.
INSERT INTO vna_schema_migrations(migration_id, applied_at)
    VALUES ('004_canonicalize_alerts_created_at', datetime('now'));

-- Normalize aware format ('2026-04-23T21:42:50+00:00' or +HH:MM variant):
-- Strip the timezone offset (everything from the rightmost '+' or '-' after
-- the 'T') -- live data is UTC-only (Phase 07/09 audit confirmed no non-UTC
-- values). Then swap 'T' for space. If no microseconds, append '.000000'.
UPDATE alerts
   SET created_at = (
       CASE
         -- Pattern A: aware T with +00:00 offset (e.g. '2026-04-23T21:42:50+00:00')
         -- Format: YYYY-MM-DDTHH:MM:SS+HH:MM (25 chars without microseconds)
         --         YYYY-MM-DDTHH:MM:SS.ffffff+HH:MM (32 chars with microseconds)
         -- Offset is always last 6 chars (+HH:MM or -HH:MM per Python isoformat())
         WHEN created_at LIKE '%T%' AND created_at LIKE '%+%'
         THEN
           REPLACE(
             CASE
               WHEN created_at LIKE '%.%'
               -- Has microseconds: 'YYYY-MM-DDTHH:MM:SS.ffffff+HH:MM' -> strip last 6 -> swap T
               THEN substr(created_at, 1, length(created_at) - 6)
               -- No microseconds: 'YYYY-MM-DDTHH:MM:SS+HH:MM' -> strip last 6 -> swap T -> append .000000
               ELSE substr(created_at, 1, length(created_at) - 6) || '.000000'
             END,
             'T', ' '
           )
         -- Pattern B: naive T with microseconds (e.g. '2026-04-23T21:42:50.142222')
         WHEN created_at LIKE '%T%' AND created_at LIKE '%.%'
         THEN REPLACE(created_at, 'T', ' ')
         -- Pattern C: naive T without microseconds (e.g. '2026-04-23T21:42:50')
         WHEN created_at LIKE '%T%'
         THEN REPLACE(created_at, 'T', ' ') || '.000000'
         -- Pattern D: already space-sep without microseconds (e.g. '2026-04-23 21:42:50')
         WHEN created_at NOT LIKE '%.%'
         THEN created_at || '.000000'
         -- Pattern E: already canonical (space + microseconds) -- no-op
         ELSE created_at
       END
   )
 WHERE created_at IS NOT NULL;

COMMIT;

-- SQLite NOTE: Re-enable FK enforcement AFTER COMMIT (pragma is no-op inside
-- a transaction). The OFF pragma at the top of this file disabled FK checks
-- for the duration of the DML operations; this restores them for subsequent
-- operations on the same connection.
PRAGMA foreign_keys=ON;
