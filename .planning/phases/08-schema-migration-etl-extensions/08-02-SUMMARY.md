---
phase: 08-schema-migration-etl-extensions
plan: 02
subsystem: database
tags: [models, orm, check-constraint, pending-notifications, sync, python, tdd]

# Dependency graph
requires:
  - phase: 08-schema-migration-etl-extensions
    plan: 01
    provides: "scripts/migrations/001_expand_channel_groups.sql — byte-identical CHECK source of truth"

provides:
  - "backend/db/models.py — CHANNEL_GROUP_CHECK_VALUES + ALERT_RULE_CHECK_VALUES tuples; SQL_CREATE_PENDING_NOTIFICATIONS tightened with severity + channel_group CHECKs"
  - "backend/db/database.py — _migrate_alerts_schema_v2 + _migrate_pending_notifications_schema_v2: fresh-DB bypass coverage; stale CHECK detection via sqlite_master probes"
  - "scripts/test_models_sync.py — 10-test bidirectional drift detector: models.py CHECK strings must match migration 001 byte-for-byte; CI gate precursor for HARD-03"

affects:
  - 08-03-PLAN (live apply — models.py now at Phase 08 state, ready for Plan 03 backup + migrate)
  - 18-HARDENING (HARD-03 CI gate — test_models_sync.py is the test to promote to CI)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level authoritative domain tuples (CHANNEL_GROUP_CHECK_VALUES, ALERT_RULE_CHECK_VALUES): Python code references tuples instead of re-parsing SQL strings"
    - "sqlite_master substring probe for schema state detection: channel_group_ok = 'GOOGLE_ADEX' in create_sql AND 'HEADER_BIDDING_MAGNITE' in create_sql; alert_rule_ok = 'A8' in create_sql AND 'A4' not in create_sql"
    - "Fresh-DB bypass coverage: migration helpers run BEFORE CREATE IF NOT EXISTS in init_db() so stale DBs are upgraded even without running migration scripts"
    - "sys.path.insert(0, REPO_ROOT) in test scripts for direct invocation compatibility (.venv/bin/python scripts/test_models_sync.py)"

key-files:
  created:
    - scripts/test_models_sync.py
  modified:
    - backend/db/models.py
    - backend/db/database.py

key-decisions:
  - "CHANNEL_GROUP_CHECK_VALUES and ALERT_RULE_CHECK_VALUES placed after ChannelGroup class (line 44), before EventType — authoritative tuples adjacent to the enums they reflect"
  - "_migrate_alerts_check_constraint renamed to _migrate_alerts_schema_v2 (no alias needed — no external callers confirmed by grep)"
  - "sys.path.insert(0, REPO_ROOT) added to test script: test_migration_001.py avoids backend imports entirely (reads models.py as text); test_models_sync.py imports backend.db.models directly for enum/tuple assertions, requiring sys.path fix"
  - "init_db() ordering: both v2 helpers called BEFORE all CREATE IF NOT EXISTS statements — probe runs against existing stale table, then CREATE IF NOT EXISTS is idempotent for already-migrated or fresh tables"

# Metrics
duration: ~27min
completed: 2026-04-23
---

# Phase 08 Plan 02: models.py Sync Summary

**SQL_CREATE_PENDING_NOTIFICATIONS tightened with byte-identical CHECK constraints; CHANNEL_GROUP_CHECK_VALUES + ALERT_RULE_CHECK_VALUES domain tuples added; database.py fresh-DB bypass covered; 10-test bidirectional drift detector exits 0.**

## Performance

- **Duration:** ~27 min
- **Started:** 2026-04-23T01:00:00Z
- **Completed:** 2026-04-23T01:27:00Z
- **Tasks:** 3 (TDD: verify/test-first approach)
- **Files created:** 1 (scripts/test_models_sync.py)
- **Files modified:** 2 (backend/db/models.py, backend/db/database.py)

## Accomplishments

### Task 1 — models.py CHECK tightening + domain tuples

- `SQL_CREATE_PENDING_NOTIFICATIONS` now has:
  - `CHECK(severity IN ('P0', 'P1', 'P2'))` — byte-identical to migration 001 line 170
  - `CHECK(channel_group IN ('GOOGLE_ADEX', 'OPEN_BIDDING', 'HEADER_BIDDING_MAGNITE', 'HEADER_BIDDING_PUBMATIC', 'TAM', 'DIRECT', 'DEAL', 'GOOGLE'))` — byte-identical to migration 001 line 171
- `CHANNEL_GROUP_CHECK_VALUES: tuple[str, ...] = (8 values)` added after ChannelGroup class
- `ALERT_RULE_CHECK_VALUES: tuple[str, ...] = (8 values, A4 absent)` added after ChannelGroup class
- Comment block explicitly linking SQL_CREATE_ALERTS to the new tuples for drift prevention
- `SQL_CREATE_ALERTS` lines 182/184 unchanged (already correct per Phase 07)
- A4 absent from models.py: `grep -c "'A4'" backend/db/models.py` → 0

### Task 2 — database.py fresh-DB bypass coverage

- `_migrate_alerts_check_constraint` renamed to `_migrate_alerts_schema_v2`
- New probe logic:
  - `channel_group_ok = "'GOOGLE_ADEX'" in create_sql and "'HEADER_BIDDING_MAGNITE'" in create_sql`
  - `alert_rule_ok = "'A8'" in create_sql and "'A4'" not in create_sql`
  - Both probes must be true → no-op (already Phase 08 state)
  - Either false → PRAGMA FK=OFF → RENAME → CREATE (SQL_CREATE_ALERTS) → INSERT SELECT * → DROP → PRAGMA FK=ON
- New `_migrate_pending_notifications_schema_v2`:
  - Probes `severity_ok = "CHECK(severity IN ('P0', 'P1', 'P2'))" in create_sql` and `channel_group_ok = "'GOOGLE_ADEX'" in create_sql`
  - Same recreate pattern with explicit column list in INSERT SELECT
- `init_db()` ordering: both helpers called BEFORE all `CREATE IF NOT EXISTS` statements
- Integration test confirmed: stale DB (2-value channel_group, 4-value alert_rule) → `init_db()` → `'GOOGLE_ADEX' in sqlite_master.sql`, `'A8' in sql`, `'A4' not in sql`

### Task 3 — scripts/test_models_sync.py bidirectional drift detector

10 tests, all passing, stdlib-only:

1. `test_migration_001_exists` — sanity: migration file present
2. `test_channel_group_check_string_byte_identical` — alerts channel_group CHECK in models.py matches migration 001 (both occurrences in migration: alerts + pending_notifications)
3. `test_alert_rule_check_string_byte_identical` — alerts alert_rule CHECK byte-identical
4. `test_pending_notifications_severity_check_byte_identical` — pn severity CHECK byte-identical
5. `test_pending_notifications_channel_group_check_byte_identical` — pn channel_group CHECK byte-identical
6. `test_channel_group_enum_matches_check_tuple` — ChannelGroup enum values == CHANNEL_GROUP_CHECK_VALUES
7. `test_alert_rule_enum_matches_check_tuple` — AlertRule enum values == ALERT_RULE_CHECK_VALUES
8. `test_a4_absent_everywhere` — 'A4' absent from 4 locations: enum, tuple, SQL_CREATE_ALERTS, migration file
9. `test_check_values_count_8` — both tuples have exactly 8 elements
10. `test_init_db_on_stale_fixture_produces_correct_check` — integration: stale DB + init_db() → Phase 08 schema

## Task Commits

1. **Task 1 (models.py):** `0ebb0aa` — feat(08-02): tighten SQL_CREATE_PENDING_NOTIFICATIONS CHECK + add domain tuples
2. **Task 2 (database.py):** `4e6ea04` — feat(08-02): rename _migrate_alerts_check_constraint → _migrate_alerts_schema_v2 + add pending_notifications v2
3. **Task 3 (test_models_sync.py):** `4d0eb83` — test(08-02): add scripts/test_models_sync.py bidirectional drift detector

## Decisions Made

**_migrate_alerts_check_constraint renamed, no alias:** `grep -rn "_migrate_alerts_check_constraint" backend/ scripts/ tests/` found 0 external callers — only 2 internal references in database.py itself. Safe to rename without deprecation alias.

**sys.path fix in test script:** test_migration_001.py avoids importing `backend` package directly (reads models.py as text file via `MODELS_PATH.read_text()`). test_models_sync.py imports `backend.db.models` directly to assert enum values and tuple values — requires `sys.path.insert(0, REPO_ROOT)` for direct script invocation. This is idempotent and does not affect the venv or CI (CI would run from REPO_ROOT anyway).

**Probe ordering in _migrate_alerts_schema_v2:** Both probes must pass (channel_group_ok AND alert_rule_ok) to be a no-op. This means a DB that has expanded channel_group but stale alert_rule (possible if 001.sql was partially applied) will still trigger recreate — conservative and safe.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ModuleNotFoundError: No module named 'backend' when test script run directly**
- **Found during:** Task 3 first test run
- **Issue:** `scripts/test_models_sync.py` imports `backend.db.models` and `backend.db.database` directly. When invoked as `.venv/bin/python scripts/test_models_sync.py`, Python's sys.path does not include REPO_ROOT, so `import backend` fails with ModuleNotFoundError. All 5 backend-importing tests errored.
- **Fix:** Added `sys.path.insert(0, str(REPO_ROOT))` after REPO_ROOT is computed, before any test execution. test_migration_001.py avoids this by reading models.py as text instead of importing — but the sync test's enum/tuple assertions require the live Python objects.
- **Files modified:** scripts/test_models_sync.py
- **Verification:** `.venv/bin/python scripts/test_models_sync.py` exits 0, 10/10 tests pass
- **Committed in:** 4d0eb83

## Known Stubs

None — all behavior is wired to real data (migration file, models.py imports). No placeholder values.

## Threat Surface

No new network endpoints, auth paths, or file access patterns introduced. Changes are schema-level (models.py) and in-process migration helpers (database.py). All threat model items addressed:

- T-08-02-01: sync test (test_models_sync.py) asserts byte-identity at every run
- T-08-02-02: test_channel_group_enum_matches_check_tuple fails if enum drifts from tuple
- T-08-02-03: test_a4_absent_everywhere checks 4 locations
- T-08-02-04: _migrate_alerts_schema_v2 + _migrate_pending_notifications_schema_v2 in init_db() cover fresh-DB bypass; test_init_db_on_stale_fixture_produces_correct_check asserts end-to-end
- T-08-02-05: row-preserving INSERT SELECT inside PRAGMA FK=OFF/ON pair (same safe pattern as migration 001)

## Live DB Status

**Live `data/vna_alerts.db` NOT mutated by this plan.** All database operations in Task 2 verification and Task 3 Test 10 use temporary SQLite files (tempfile.mkstemp) that are deleted after each test.

## Handoff to Plan 03 (live DB apply)

Plan 03 applies migration 001 to `data/vna_alerts.db`. Prerequisites now met:

1. `scripts/migrations/001_expand_channel_groups.sql` — authoritative DDL (Plan 01)
2. `backend/db/models.py` — CHECK strings byte-identical to migration 001 (this plan)
3. `scripts/test_models_sync.py` — drift gate that confirms sync after apply (this plan)
4. `backend/db/database.py` — fresh-DB bypass so CI never starts with stale schema (this plan)

Plan 03 must:
1. Create `data/vna_alerts.db.pre-phase08.bak` before any DDL
2. Implement driver pre-check (`'GOOGLE_ADEX' in sqlite_master.sql`) to skip if already applied
3. Run `scripts/test_models_sync.py` after apply to confirm byte-identity in live DB

## Self-Check: PASSED

Files exist:
- FOUND: backend/db/models.py (modified)
- FOUND: backend/db/database.py (modified)
- FOUND: scripts/test_models_sync.py (created)

Commits exist:
- FOUND: 0ebb0aa (models.py — Task 1)
- FOUND: 4e6ea04 (database.py — Task 2)
- FOUND: 4d0eb83 (test_models_sync.py — Task 3)

Test suite: 10/10 PASS (exit 0)
Plan verification: `8 8 8 8` (ChannelGroup, AlertRule, CHANNEL_GROUP_CHECK_VALUES, ALERT_RULE_CHECK_VALUES all len=8)
A4 absent: `grep -c "'A4'" backend/db/models.py` → 0
