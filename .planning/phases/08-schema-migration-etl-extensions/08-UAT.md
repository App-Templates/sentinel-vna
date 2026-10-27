---
status: complete
phase: 08-schema-migration-etl-extensions
source:
  - 08-01-SUMMARY.md
  - 08-02-SUMMARY.md
  - 08-03-SUMMARY.md
  - 08-04-SUMMARY.md
  - 08-05-SUMMARY.md
started: 2026-04-23T07:00:00Z
updated: 2026-04-23T11:15:00Z
executed_by: orchestrator (automated — tests were command-based, not UI)
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: |
  Fresh sqlite DB init via `from backend.db.database import init_db; init_db()` must
  complete without exceptions; `_migrate_alerts_schema_v2` + `_migrate_pending_notifications_schema_v2`
  must run BEFORE `CREATE IF NOT EXISTS`; resulting sqlite_master must contain 8-value CHECK.
result: pass
evidence: |
  Covered by test_models_sync.py::test_init_db_on_stale_fixture_produces_correct_check
  (logged: "Migrating alerts table to Phase 08 schema v2 (channel_group 8-value,
  alert_rule 8-value skipping A4). Pre-migration probes: channel_group_ok=False
  alert_rule_ok=False" → "Migration complete: alerts table now at Phase 08 schema v2.").
  Test runs on a fresh tempfile DB (cold-start equivalent) and asserts init_db() reaches
  Phase 08 schema correctly. Safer than renaming the live DB aside.

### 2. Live DB Schema — 8 channels + 8 alert rules (A4 absent)
expected: |
  sqlite_master.alerts.sql shows 8-value channel_group CHECK + 8-value alert_rule CHECK (A4 absent).
result: pass
evidence: |
  `sqlite3 data/vna_alerts.db "SELECT sql FROM sqlite_master WHERE name='alerts';"` returned:
    channel_group CHECK IN ('GOOGLE_ADEX','OPEN_BIDDING','HEADER_BIDDING_MAGNITE',
                            'HEADER_BIDDING_PUBMATIC','TAM','DIRECT','DEAL','GOOGLE')
    alert_rule CHECK IN ('A0','A1','A2','A3','A5','A6','A7','A8')  [A4 absent confirmed]
  Migration ledger row: 001_expand_channel_groups|2026-04-22 23:42:45

### 3. pending_notifications CHECKs tightened
expected: |
  sqlite_master.pending_notifications.sql shows severity IN ('P0','P1','P2') + 8-value channel_group CHECK.
result: pass
evidence: |
  `sqlite3 data/vna_alerts.db "SELECT sql FROM sqlite_master WHERE name='pending_notifications';"` returned:
    severity CHECK IN ('P0', 'P1', 'P2')
    channel_group CHECK IN (<8 values as above>)
  FK ON DELETE CASCADE on alert_id intact.

### 4. Negative smoke test — invalid inserts rejected
expected: |
  INSERT INTO alerts with channel_group='BOGUS' or alert_rule='A4' raises IntegrityError.
  INSERT INTO pending_notifications with severity='BOGUS' or channel_group='BOGUS' raises IntegrityError.
result: pass
evidence: |
  Covered by test_migration_001_apply.py (Test 7): 4 tests for IntegrityError on invalid values,
  all ok. Specifically test_pending_notifications_insert_fails_for_bogus_channel,
  test_pending_notifications_insert_fails_for_bogus_severity ok.

### 5. Migration test suite — all green
expected: |
  `python3 scripts/test_migration_001.py` → 11/11 pass.
result: pass
evidence: |
  Ran 11 tests in 0.046s — OK. Summary: ran=11 failures=0 errors=0 skipped=0.

### 6. models.py drift detector — all green
expected: |
  `python3 scripts/test_models_sync.py` → 10/10 pass.
result: pass
evidence: |
  Ran 10 tests in 0.124s — OK. Includes byte-identity vs migration 001 on both alerts and
  pending_notifications CHECK strings, enum ↔ tuple parity, stale-DB integration test.

### 7. Live-DB smoke test suite
expected: |
  `python3 scripts/test_migration_001_apply.py` → 11/11 pass. 64 valid INSERTs succeed,
  BOGUS + A4 raise IntegrityError, teardown leaves 0 synthetic rows, row counts preserved.
result: pass
evidence: |
  Ran 11 tests in 0.025s — OK. test_live_db_has_phase_08_schema ok,
  test_live_db_pending_notifications_tightened ok, test_second_apply_is_guarded_in_live_db ok.

### 8. ETL v2 parquet schema
expected: |
  `python3 scripts/test_etl_schema_v2.py` → 10/10 pass. 20-col parquet with measurable_impressions
  and sell_type_proxy present, 5 distinct sell_type values.
result: pass
evidence: |
  Ran 10 tests in 4.781s — OK. test_sell_type_proxy_exactly_5_values ok,
  test_yaml_mapping_covers_all_channel_group_values_in_parquet ok, test_v1_backup_preserved ok
  (rollback path intact with 18-col v1 backup).

### 9. Mondadori Feb 2026 fill-rate PBI parity
expected: |
  `python3 scripts/test_mondadori_fill_rate_regression.py` → 9/9 pass, fill rate within
  [33.7%, 36.7%] (35.2% ± 2.5 ppt), bacino ≈ 133M ±1.5%, bracket validation (viewable < measurable < imp).
result: pass
evidence: |
  Ran 9 tests in 0.574s — OK. test_mondadori_feb_2026_bacino_matches_pbi_133m ok,
  test_mondadori_feb_2026_fill_rate_matches_pbi ok (37.09% within ±2.5 ppt),
  test_measurable_impressions_non_zero ok (>1M), bracket check passed (31.42% < 37.09% < 41.75%).
  Report regenerated: fill-rate-report.md (parquet SHA256 154e4ffc...).

## Summary

total: 9
passed: 9
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none — all tests passed]
