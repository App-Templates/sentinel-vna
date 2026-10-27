---
phase: 08-schema-migration-etl-extensions
plan: 03
subsystem: database
tags: [sqlite, migration-apply, live-db, backup, rollback, smoke-test, blocking, schema-01, schema-02]

# Dependency graph
requires:
  - phase: 08-schema-migration-etl-extensions
    plan: 01
    provides: "scripts/migrations/001_expand_channel_groups.sql — authoritative DDL"
  - phase: 08-schema-migration-etl-extensions
    plan: 02
    provides: "backend/db/models.py — byte-identical CHECK strings, CHANNEL_GROUP_CHECK_VALUES, ALERT_RULE_CHECK_VALUES"

provides:
  - "data/vna_alerts.db — live DB at Phase 08 v2 schema: 8-value channel_group CHECK, 8-value alert_rule CHECK (A4 absent), pending_notifications severity+channel_group CHECKs tightened"
  - "data/vna_alerts.db.pre-phase08.bak — pre-apply backup; rollback via: cp data/vna_alerts.db.pre-phase08.bak data/vna_alerts.db"
  - "scripts/apply_migration_001.py — idempotent migration driver: lsof guard, backup, apply, verify, row-count preservation, auto-restore on failure"
  - "scripts/test_migration_001_apply.py — 11-test post-apply smoke suite: 64 valid INSERTs, 4 IntegrityErrors, byte-identity, backup proof, ledger, idempotency"

affects:
  - 09-backfill (requires Phase 08 v2 schema in live DB — now unblocked)
  - 10-monitoring (pipeline_runs meta-alert — live DB ready)
  - 11-api-baseline (live alerts INSERT path — now works for all 8 channels + 8 rules)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Migration driver pattern: lsof concurrency guard + sqlite_master idempotency pre-check + shutil.copy2 backup + executescript apply + byte-identity verify + auto-restore on failure"
    - "_verify_row_counts_preserved: snapshot counts before apply, assert equality after apply — no data loss proof"
    - "Post-apply smoke suite against LIVE DB: tearDown DELETE + post-test COUNT=0 assertion prevents synthetic data pollution"
    - "Backup proof pattern (W-01): open .bak with sqlite3, assert stale schema (no GOOGLE_ADEX, no A8) — proves .bak is the pre-apply snapshot"

key-files:
  created:
    - scripts/apply_migration_001.py
    - data/vna_alerts.db.pre-phase08.bak
    - scripts/test_migration_001_apply.py
  modified:
    - data/vna_alerts.db

key-decisions:
  - "Backup size verification used instead of full SHA256 in shutil.copy2 step (speed); SHA256 captured in commit message for provenance. File size equality is sufficient to detect truncation; full hash is in git history."
  - "Test suite implements 11 tests (1 extra beyond plan's 10): test_second_apply_is_guarded_in_live_db added as regression guard for live DB idempotency (beyond tempfile-only coverage in Plan 01)"
  - "W-01 strengthening: test_backup_exists_and_is_pre_apply opens .bak via sqlite3 and asserts no GOOGLE_ADEX + no A8 — proves the file is the pre-apply stale snapshot, not just that it exists"
  - "W-02 strengthening: _verify_row_counts_preserved() added to driver — snapshots counts before apply, asserts equality post-apply as part of verification pass"

requirements-completed: [SCHEMA-01, SCHEMA-02]

# Metrics
duration: ~4min
completed: 2026-04-23
---

# Phase 08 Plan 03: Migration 001 Live Apply Summary

**Migration 001 applied to live data/vna_alerts.db: 8-value channel_group + alert_rule CHECKs, pending_notifications tightened. 200 existing rows preserved. 11-test smoke suite all passing. SCHEMA-01 and SCHEMA-02 delivered.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-23T01:42:00Z
- **Completed:** 2026-04-23T01:45:00Z
- **Tasks:** 3 (driver, live apply, smoke-test suite)
- **Files created:** 3 (driver, .bak, smoke-test)
- **Files modified:** 1 (data/vna_alerts.db)

## Provenance

### Pre-Apply State

| Item | Value |
|------|-------|
| data/vna_alerts.db SHA256 | `30c296101876330e6f0c3422022217d9588e129cdaa623cb139615bd7362ac23` |
| alerts row count | 200 |
| pending_notifications row count | 0 |
| alerts.channel_group CHECK | `IN ('GOOGLE', 'OPEN_BIDDING')` (2-value, stale) |
| alerts.alert_rule CHECK | `IN ('A0', 'A1', 'A2', 'A3')` (4-value, stale) |

### Post-Apply State

| Item | Value |
|------|-------|
| data/vna_alerts.db SHA256 | `a2df1e9bc9d2d79d7573081ac3452022e287bd33ad07e2d65b50711c02f15baf` |
| alerts row count | 200 (unchanged — data preserved) |
| pending_notifications row count | 0 (unchanged) |
| alerts.channel_group CHECK | 8-value (GOOGLE_ADEX, OPEN_BIDDING, HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC, TAM, DIRECT, DEAL, GOOGLE) |
| alerts.alert_rule CHECK | 8-value (A0, A1, A2, A3, A5, A6, A7, A8) — A4 absent |
| vna_schema_migrations ledger | `001_expand_channel_groups | 2026-04-22 23:42:45` |

### Backup File

| Item | Value |
|------|-------|
| Path | `data/vna_alerts.db.pre-phase08.bak` |
| SHA256 | `30c296101876330e6f0c3422022217d9588e129cdaa623cb139615bd7362ac23` |
| Matches pre-apply live DB | YES (byte-identical) |
| Rollback command | `cp data/vna_alerts.db.pre-phase08.bak data/vna_alerts.db` |

## Byte-Identity Verification (Success Criterion 2)

`SELECT sql FROM sqlite_master WHERE name='alerts'` CHECK clauses compared to `models.py SQL_CREATE_ALERTS` by `_verify_byte_identical_to_models()` (whitespace-normalized per clause):

| Column | Result |
|--------|--------|
| severity | MATCH |
| channel_group | MATCH |
| status | MATCH |
| alert_rule | MATCH |

All 4 CHECK clauses byte-identical to `models.py`. Success criterion 2 from ROADMAP: **PASSED**.

## Smoke-Test Results

### Test Run: 11/11 PASS (exit 0)

| Test | Result |
|------|--------|
| test_live_db_has_phase_08_schema | PASS |
| test_live_db_pending_notifications_tightened | PASS |
| test_backup_exists_and_is_pre_apply (W-01) | PASS |
| test_insert_succeeds_for_each_valid_channel_and_rule | PASS — 64/64 INSERTs succeeded |
| test_insert_fails_for_bogus_channel | PASS — IntegrityError raised |
| test_insert_fails_for_a4_rule | PASS — A4 rejected with IntegrityError |
| test_pending_notifications_insert_fails_for_bogus_severity | PASS — IntegrityError raised |
| test_pending_notifications_insert_fails_for_bogus_channel | PASS — IntegrityError raised |
| test_ledger_has_migration_row | PASS — COUNT=1 for 001_expand_channel_groups |
| test_alerts_byte_identical_to_models_py | PASS — all 4 CHECK clauses match |
| test_second_apply_is_guarded_in_live_db | PASS — UNIQUE constraint blocks double-apply |

### Teardown Verification

Post-test: `SELECT COUNT(*) FROM alerts WHERE data_source='phase08-test'` = **0** (clean).

## Task Commits

1. **Task 1 (driver):** `71aba60` — feat(08-03): author apply_migration_001.py migration driver
2. **Task 2 (live apply + backup):** `0dcdfaa` — feat(08): apply migration 001 — expand channel_group + alert_rule CHECKs on live DB
3. **Task 3 (smoke-test suite):** `10c6a78` — test(08-03): add smoke-test suite for post-migration-001 live DB state

## Accomplishments

- **SCHEMA-01 delivered:** `vna_alerts.channel_group` now accepts all 8 channels including the v1.2 additions (GOOGLE_ADEX, HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC, TAM, DIRECT, DEAL)
- **SCHEMA-02 delivered:** `vna_alerts.alert_rule` now accepts A0-A3, A5-A8 (A4 deliberately absent)
- **Silent-failure bug closed:** alerts pipeline was silently failing since 2026-01-22 (200 rows from stale era preserved, new INSERTs will now succeed for all 7 channels)
- **Backup safety net in place:** `.bak` committed as rollback artifact; `cp data/vna_alerts.db.pre-phase08.bak data/vna_alerts.db` is the one-command rollback
- **Driver is idempotent:** second run SKIPs cleanly (sqlite_master pre-check); `_already_applied()` prevents double-apply corruption
- **W-01 + W-02 plan-checker strengthenings implemented:** backup proof via sqlite3 schema check; row count verification embedded in driver

## Deviations from Plan

### Auto-fixed Issues

None. Plan executed exactly as written with two plan-checker W-01/W-02 strengthenings applied as directed.

### Plan-Checker Strengthenings Applied

**W-01: test_backup_exists_and_is_pre_apply strengthened**
- Plan flagged: "weak test — empty DB would pass"
- Fix: Test now opens `.bak` via sqlite3 and asserts `'GOOGLE_ADEX' NOT IN bak_alerts_sql` AND `'A8' NOT IN bak_alerts_sql` — proves it's the pre-apply stale snapshot, not just a file that exists
- Files modified: scripts/test_migration_001_apply.py

**W-02: _verify_row_counts_preserved() added to driver**
- Plan flagged: "add row-count preservation verification to driver"
- Fix: `_snapshot_row_counts()` called before apply; `_verify_row_counts_preserved()` called post-apply as part of verification pass; both alerts and pending_notifications counts asserted
- Files modified: scripts/apply_migration_001.py

## Rollback Procedure

If the migration needs to be reversed:

```bash
# Step 1: Stop any service using the DB
# Step 2: Restore from backup
cp data/vna_alerts.db.pre-phase08.bak data/vna_alerts.db
# Step 3: Verify restored
sqlite3 data/vna_alerts.db ".schema alerts" | grep channel_group
# Expected: CHECK(channel_group IN ('GOOGLE', 'OPEN_BIDDING'))
```

The `.bak` file will remain in the tree until Phase 17 cleanup closes the v1.3 milestone.

## Known Stubs

None. Migration is complete DDL applied to the live DB. All behavior wired to real data.

## Threat Surface

No new network endpoints, auth paths, or file access patterns introduced. Changes are purely to the local SQLite file. Threat model from PLAN.md fully addressed:

- T-08-03-01 (concurrent handle): `_check_lsof` confirmed empty before apply
- T-08-03-02 (apply failure): `shutil.copy2` backup created before apply; auto-restore on failure
- T-08-03-03 (row loss): `INSERT INTO alerts SELECT * FROM _alerts_old_001` + row-count verification — 200 rows preserved
- T-08-03-04 (sqlite_master drift): `_verify_byte_identical_to_models` + smoke-test Test 10 re-verify
- T-08-03-05 (repudiation): ledger row `001_expand_channel_groups | 2026-04-22 23:42:45` + SHA256 in commit message
- T-08-03-07 (valid INSERTs rejected): 64 valid INSERTs all succeed in smoke-test
- T-08-03-08 (A4 allowed): Test 6 explicitly asserts A4 raises IntegrityError
- T-08-03-09 (double-apply): `_already_applied` pre-check + Test 11 live ledger guard
- T-08-03-11 (test data pollution): tearDown DELETE + post-test COUNT=0 assertion

## Handoff to Plan 04 (ETL Extensions)

Plan 04 (ETL v2 schema: measurable_impressions + sell_type_proxy) does not depend on the DB schema directly — it operates on parquet files and extends the ETL script. However, with the DB now at v2 schema:

- **Phase 09 (backfill):** unblocked — can now INSERT alerts for all 8 channel_group values
- **Phase 10 (monitoring):** unblocked — pipeline_runs INSERT path works; meta-alert on `pipeline_runs > 0 AND alerts = 0` can now be verified against real alert INSERTs
- **Phase 11 (API + baseline):** unblocked — `/api/alerts` POST endpoint will now accept all 7 channels without IntegrityError

---
*Phase: 08-schema-migration-etl-extensions*
*Completed: 2026-04-23*

## Self-Check: PASSED

Files exist:
- FOUND: scripts/apply_migration_001.py
- FOUND: data/vna_alerts.db.pre-phase08.bak
- FOUND: scripts/test_migration_001_apply.py
- FOUND: data/vna_alerts.db (modified)

Commits exist:
- FOUND: 71aba60 (driver — Task 1)
- FOUND: 0dcdfaa (live apply — Task 2)
- FOUND: 10c6a78 (smoke-test — Task 3)

Test suite: 11/11 PASS (exit 0)
Synthetic rows remaining: 0
Pre-apply SHA256 = Backup SHA256: CONFIRMED (30c2961...)
Row counts preserved: alerts 200 == 200, pending_notifications 0 == 0
A4 absent from live DB: CONFIRMED
GOOGLE_ADEX present in live DB: CONFIRMED
