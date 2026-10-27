---
phase: 08-schema-migration-etl-extensions
plan: 01
subsystem: database
tags: [sqlite, migration, check-constraint, silent-failure, channel-group, alert-rule, pending-notifications, tdd]

# Dependency graph
requires:
  - phase: 07-db-wip-investigation
    provides: wip-schema.sql (stale DDL source), DECISION.md (FORWARD_PORT), 000_wip_drift_baseline.sql (baseline migration)

provides:
  - "scripts/migrations/001_expand_channel_groups.sql — idempotent DDL expanding alerts CHECK constraints to v1.2 8-value domain, tightening pending_notifications CHECKs"
  - "scripts/test_migration_001.py — 11-case stdlib validation suite proving migration correctness (row preservation, byte-identity, A4 negative, idempotency guard)"
  - "vna_schema_migrations ledger table pattern established for all future migrations"

affects:
  - 08-02-PLAN (models.py sync — must match migration's byte-for-byte CHECK strings)
  - 08-03-PLAN (live apply — must implement driver pre-check per IDEMPOTENCY CONTRACT)
  - 09-backfill (requires 001 applied to live DB so new alerts can INSERT)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SQLite table-recreate migration pattern: PRAGMA FK=OFF → RENAME → CREATE → INSERT SELECT → DROP → PRAGMA FK=ON (FK pragma must be outside transaction)"
    - "Migration ledger: vna_schema_migrations (migration_id TEXT PRIMARY KEY, applied_at TEXT) — first INSERT (no OR REPLACE) as idempotency guard"
    - "TDD order for paired (test, migration) plans: write test suite first (RED), then migration (GREEN)"
    - "PRAGMA foreign_keys must be set BEFORE BEGIN TRANSACTION (SQLite no-op inside transaction)"

key-files:
  created:
    - scripts/migrations/001_expand_channel_groups.sql
    - scripts/test_migration_001.py
  modified: []

key-decisions:
  - "PRAGMA foreign_keys=OFF must be placed BEFORE BEGIN TRANSACTION, not inside — SQLite silently ignores pragma changes inside a transaction, causing ON DELETE CASCADE to fire unexpectedly during DROP TABLE _alerts_old_001 (discovered via test failure, fixed in migration)"
  - "Idempotency guard via ledger INSERT (no OR REPLACE) at start of transaction: second apply raises IntegrityError before any DDL, DB remains intact — cleaner than ALTER RENAME failure since _alerts_old_001 doesn't persist post-apply"
  - "pending_notifications CHECKs tightened in same migration as alerts expansion (not deferred) — closes Phase 07 test-agent gotcha in-phase"
  - "Test suite uses STALE_DDL constants (not models.py) for baseline DB creation — survives Plan 02 models.py changes"

patterns-established:
  - "SQLite migration idempotency: ledger INSERT as first transactional statement, driver pre-checks sqlite_master before invocation"
  - "Migration FK pragma placement: FK=OFF before BEGIN, FK=ON after COMMIT"
  - "TDD test file for each migration: stdlib-only, tempfile DB, explicit positive+negative+idempotency assertions"

requirements-completed: [SCHEMA-01]

# Metrics
duration: 12min
completed: 2026-04-23
---

# Phase 08 Plan 01: 001_expand_channel_groups.sql Summary

**Transactional SQLite migration expanding alerts.channel_group (2→8 values), alerts.alert_rule (4→8, A4 skipped), and tightening pending_notifications CHECKs; 11-case TDD validation suite all passing including PRAGMA FK bug discovered and fixed.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-04-23T00:56:00Z
- **Completed:** 2026-04-23T01:03:30Z
- **Tasks:** 2 (TDD: test first, then migration)
- **Files modified:** 2 created

## Accomplishments

- Migration SQL authored per SQLite recreate pattern: 8-value channel_group CHECK, 8-value alert_rule CHECK (A4 skipped), pending_notifications severity + channel_group tightened — all CHECK strings byte-for-byte identical to models.py:182/184
- Discovered and fixed PRAGMA foreign_keys= behavior: pragma MUST be placed before BEGIN TRANSACTION (not inside, where it is silently ignored by SQLite) — was causing ON DELETE CASCADE to fire during DROP TABLE _alerts_old_001, deleting pending_notifications rows
- Idempotency guard via ledger INSERT (no OR REPLACE) as first statement in transaction: second naked apply raises IntegrityError before any DDL executes, DB remains intact
- 11-test stdlib suite: all passing including byte-identity assertion, explicit A4 negative, row preservation (5 alerts + 3 PN), second-apply guard, git tracking, rollback/IDEMPOTENCY CONTRACT header content
- Live data/vna_alerts.db NOT touched by this plan (migration reserved for Plan 03)

## Task Commits

1. **Task 2 (TDD RED): test_migration_001.py** — `765ab1f` (test)
2. **Task 1 (TDD GREEN): 001_expand_channel_groups.sql** — `ed54ec1` (feat)

_TDD order: test suite authored first (Task 2 labeling), then migration to make tests pass._

## Files Created/Modified

- `scripts/migrations/001_expand_channel_groups.sql` — Idempotent SQLite DDL: expands alerts.channel_group (2→8), alerts.alert_rule (4→8, A4 skipped), tightens pending_notifications.severity (3-value) + pending_notifications.channel_group (8-value); vna_schema_migrations ledger table; IDEMPOTENCY CONTRACT documented in header
- `scripts/test_migration_001.py` — stdlib unittest suite (658 lines): 11 test cases covering apply-on-baseline, 8-value channel group, 8-value alert rule with A4 negative, PN CHECK tightening, byte-identity vs models.py, row preservation, DDL-only assertion, ledger row, second-apply guard, git tracking, header content

## Decisions Made

**PRAGMA FK placement (Root cause of test failure):** SQLite PRAGMA foreign_keys is a no-op inside a transaction. The original migration had `BEGIN TRANSACTION` first, then `PRAGMA foreign_keys=OFF` — this meant FK enforcement remained ON during the migration DDL. When `DROP TABLE _alerts_old_001` executed, ON DELETE CASCADE fired through pending_notifications (which has FK to "alerts") and deleted all pending_notifications rows. Fix: move `PRAGMA foreign_keys=OFF` to before `BEGIN TRANSACTION`, and `PRAGMA foreign_keys=ON` to after `COMMIT`.

**Ledger-first idempotency (Revised from plan's ALTER RENAME approach):** The plan proposed second apply would fail via ALTER TABLE RENAME conflict. However, since `_alerts_old_001` is dropped at end of first apply, second apply would simply re-execute the entire migration silently (no error). Instead, the `INSERT INTO vna_schema_migrations` (without OR REPLACE) is placed as the FIRST transactional statement after ledger table creation. Second apply hits UNIQUE constraint failure immediately, before any DDL executes. This is safer and provides a cleaner error message pointing directly at the ledger.

**Test expects DatabaseError not OperationalError:** UNIQUE constraint failure in Python's sqlite3 raises `IntegrityError` (subclass of `DatabaseError`), not `OperationalError`. Test updated to `assertRaises(sqlite3.DatabaseError)` to correctly capture this.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] PRAGMA foreign_keys=OFF ineffective inside transaction**
- **Found during:** Task 2 (test_row_preservation failure — PN count 3→0)
- **Issue:** Plan's migration structure placed `PRAGMA foreign_keys=OFF` inside `BEGIN TRANSACTION`. SQLite silently ignores pragma changes inside transactions, so FK enforcement remained ON, causing ON DELETE CASCADE to delete pending_notifications rows when `DROP TABLE _alerts_old_001` executed.
- **Fix:** Moved `PRAGMA foreign_keys=OFF` to before `BEGIN TRANSACTION`, and `PRAGMA foreign_keys=ON` to after `COMMIT`. Added SQLite docs reference in header comments.
- **Files modified:** scripts/migrations/001_expand_channel_groups.sql
- **Verification:** test_row_preservation passes (3 PN rows preserved)
- **Committed in:** ed54ec1

**2. [Rule 1 - Bug] Second apply idempotency: INSERT (not ALTER RENAME) is the guard**
- **Found during:** Task 2 (test_second_apply_is_guarded failure — no error raised)
- **Issue:** Plan assumed second apply would fail via `ALTER TABLE alerts RENAME TO _alerts_old_001` conflict. However, after first apply completes, `_alerts_old_001` is dropped and `alerts` exists with expanded CHECKs. Second apply renames expanded `alerts` to `_alerts_old_001`, creates new `alerts` with same DDL, copies rows, drops old — silently succeeds (no corruption, but no error either).
- **Fix:** Changed `INSERT OR REPLACE INTO vna_schema_migrations` to `INSERT INTO vna_schema_migrations` (removing `OR REPLACE`) and moved this INSERT to be the FIRST transactional statement. Second apply now raises IntegrityError (UNIQUE constraint on migration_id) before any DDL executes.
- **Files modified:** scripts/migrations/001_expand_channel_groups.sql
- **Verification:** test_second_apply_is_guarded passes
- **Committed in:** ed54ec1

**3. [Rule 1 - Bug] Test expected OperationalError; actual error is IntegrityError**
- **Found during:** Task 2 (test_second_apply_is_guarded — OperationalError not raised)
- **Issue:** Test initially used `assertRaises(sqlite3.OperationalError)`. UNIQUE constraint failure raises `sqlite3.IntegrityError` (subclass of `DatabaseError`), not `OperationalError`.
- **Fix:** Updated test to `assertRaises(sqlite3.DatabaseError)` with updated docstring explaining IntegrityError as expected subtype.
- **Files modified:** scripts/test_migration_001.py
- **Verification:** test_second_apply_is_guarded passes
- **Committed in:** 765ab1f (test file)

---

**Total deviations:** 3 auto-fixed (3 Rule 1 bugs — all in PRAGMA FK behavior and idempotency guard logic)
**Impact on plan:** All bugs discovered through TDD (test-first revealed them before migration was considered complete). No scope creep. Migration is now correct, safe, and clearly documented.

## Issues Encountered

None beyond the 3 bugs documented above (all caught by TDD, all fixed inline).

## Known Stubs

None — migration is complete DDL with no stub behavior. Test suite validates all behavior against real tempfile SQLite DBs.

## Threat Surface

No new network endpoints, auth paths, or file access patterns introduced. Migration is static DDL with no external input. Threat model from PLAN.md fully addressed:

- T-08-01-01/02: CHECK expansion byte-identical to models.py (byte-identity test asserts)
- T-08-01-03: pending_notifications CHECKs tightened (test_pending_notifications_check_tightened asserts)
- T-08-01-05: Ledger table with (migration_id, applied_at) — test_vna_schema_migrations_ledger_row asserts
- T-08-01-08: Row preservation via INSERT SELECT — test_row_preservation asserts 5+3 rows preserved
- T-08-01-09: Double-apply raises IntegrityError — test_second_apply_is_guarded asserts

## Handoff to Plan 02 (models.py sync)

Plan 02 must sync `backend/db/models.py` SQL_CREATE_ALERTS and SQL_CREATE_PENDING_NOTIFICATIONS to match the migration's CHECK strings. Byte-identity constraint: the CHECK clauses in the updated models.py must exactly match those in 001.sql. The `test_alerts_checks_byte_identical_to_models_py` test (which reads models.py at runtime) will catch any drift.

## Handoff to Plan 03 (live DB apply)

Plan 03 MUST implement the driver pre-check before invoking `sqlite3 < 001.sql`:

```python
row = conn.execute(
    "SELECT sql FROM sqlite_master WHERE type='table' AND name='alerts'"
).fetchone()
if row and 'GOOGLE_ADEX' in (row[0] or ''):
    print("001 already applied -- skipping")
else:
    # apply 001.sql via subprocess or executescript
```

Second naked apply raises `sqlite3.IntegrityError` (ledger UNIQUE constraint). The driver pre-check prevents this. The backup (`data/vna_alerts.db.pre-phase08.bak`) must be created BEFORE Plan 03 applies the migration to the live DB.

## Next Phase Readiness

- Plan 02 (models.py sync): ready — migration's byte-exact CHECK strings are the source of truth
- Plan 03 (live apply): ready pending Plan 02 completion and backup creation
- Live `data/vna_alerts.db`: still at pre-Phase-08 state (`M` status, 2 months WIP binary)

---
*Phase: 08-schema-migration-etl-extensions*
*Completed: 2026-04-23*

## Self-Check: PASSED

Files exist:
- FOUND: scripts/migrations/001_expand_channel_groups.sql
- FOUND: scripts/test_migration_001.py

Commits exist:
- FOUND: 765ab1f (test)
- FOUND: ed54ec1 (feat)

Test suite: 11/11 PASS (exit 0)
