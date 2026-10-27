# Auditor C — Cross-Phase Integration & E2E Audit — Phase 10

## Verdict
**MINOR ISSUES** — No upstream/downstream regressions from Phase 10 changes. All prior-phase tests pass. E2E pipeline flow works end-to-end. Two test failures in `test_migration_003_apply.py` are stale-test artifacts (post-apply assumptions baked into a test designed for pre-apply state), not regressions. Known MAJOR-01/03 issues are correctly mitigated by `enabled: false`. One new integration-only finding (MAJOR-03 arithmetic confirmed real; MAJOR-01 scope confirmed broader than documented).

---

## Prior-phase test suite results

| Test file | Origin Phase | Pass/Fail |
|-----------|--------------|-----------|
| scripts/test_migration_000.py | Phase 07 | PASS (7/7) |
| scripts/test_migration_001.py | Phase 08 | PASS (11/11) |
| scripts/test_migration_001_apply.py | Phase 08 | PASS (11/11) |
| scripts/test_migration_002_apply.py | Phase 09 | PASS (11/11) |
| scripts/test_operations_idempotency.py | Phase 08/09 | PASS (2/2) |
| scripts/test_backfill_alerts.py | Phase 09 | PASS (13/13) |
| scripts/test_deprecate_legacy_alerts.py | Phase 09 | PASS (12/12) |
| scripts/test_etl_schema_v2.py | Phase 08 | PASS (10/10) |
| scripts/test_models_sync.py | Phase 08/09/10 | PASS (23/23) |
| scripts/test_mondadori_fill_rate_regression.py | Phase 08 | PASS |
| scripts/test_migration_003_apply.py | Phase 10 | **FAIL (2/4)** — see finding INT-01 |
| scripts/test_health_alerts_pipeline.py | Phase 10 | PASS (4/4) |
| scripts/test_silent_failure_watch.py | Phase 10 | PASS (10/10) |

---

## E2E flow verification

### LIVE pipeline + alert + counter + watchdog cycle: PASS

Verified end-to-end against a fresh temp DB created from `models.py` schema:
1. `create_alert(AlertModel(...))` → alert row persisted with `deprecated=0`.
2. `record_pipeline_run(..., alerts_written_count=1)` → `pipeline_runs.alerts_written_count == 1` confirmed.
3. `check_silent_failure()` with `pipeline_runs_last_24h=1` AND `alerts_last_24h=1` → `triggered=False, reason='healthy'`. PASS.
4. `check_silent_failure()` with `pipeline_runs_last_24h=1` AND `alerts_last_24h=0` → `triggered=True, reason='silent_failure'`. PASS.

### BACKTEST flow + counter: PASS

- `scripts/test_backfill_alerts.py` passes 13/13.
- `scripts/backfill_alerts.py` wires `alerts_written_count=1 if alert_written else 0` at lines 275 and 289 (commit `c29f35a`). Contract preserved.
- `record_pipeline_run()` signature accepts all kwargs used by `backfill_alerts.py`.

---

## Cross-phase contract preservation

### Phase 07 migration 000
`scripts/migrations/000_wip_drift_baseline.sql` exists (5237 bytes), SQL parses and executes cleanly on a fresh DB. Idempotent. PASS.

### Phase 08 channel_group + alert_rule + drift gate
- All 8 `ChannelGroup` values present; invalid value `INVALID_CHANNEL` raises `ValueError`. PASS.
- All 8 `AlertRule` values present (A0-A3, A5-A8); `A4` absent and raises `ValueError`. PASS.
- `test_models_sync.py` 23/23 PASS — migration 001/002/003 CHECK byte-identities all hold.

### Phase 09 D-16 + D-17 + MIGRATE-01
- **D-16**: `get_alerts()` with no args returns only `deprecated=0` alerts (1 of 2 in test DB). `get_alerts(include_deprecated=True)` returns both. PASS.
- **D-17**: `GET /api/alerts` default response excludes all deprecated alerts (confirmed against live DB: 238 active of 438 total). PASS.
- **MIGRATE-01**: Live DB (`data/vna_alerts.db`) has exactly 200 `deprecated=1` rows (legacy alerts) and 238 `deprecated=0` rows. PASS.

---

## NEW findings (integration-only; don't restate MAJOR-01..03)

### [MINOR] INT-01 — `test_migration_003_apply.py` is permanently broken post-apply

- **File**: `scripts/test_migration_003_apply.py:68-90`
- **Problem**: Two tests assume the live DB copy does NOT have `alerts_written_count` yet:
  - `test_dry_run_no_mutation` (line 74): asserts column absent in a copy of live DB → FAILS because migration 003 was applied on 2026-04-23 17:03:28.
  - `test_first_apply_success` (line 90): asserts `zero_count == total` (all rows at DEFAULT 0) → FAILS because 1 row has `alerts_written_count=3` (run_id=`test-run-sc3`, a smoke-test artifact in the live DB).
- **Root cause**: Test setUp copies `data/vna_alerts.db` (post-migration state) into temp dir. The shim patches `d.DB_PATH` after `exec_module` but the idempotency guard in `_already_applied()` returns True immediately → driver emits SKIP → tests check mutation that never happened.
- **Impact**: CI/CD will see 2 persistent failures from this test file forever unless either: (a) the test is updated to build a fresh pre-003 DB from scratch instead of copying live, or (b) the test is replaced with an idempotency-only suite.
- **Recommended fix**: In `setUp()`, create a fresh SQLite DB using `SQL_CREATE_PIPELINE_RUNS` *without* `alerts_written_count` (use the pre-003 DDL from the migration rollback SQL), then run the driver against it.

### [MINOR] INT-02 — MAJOR-01 (BACKTEST contamination) scope confirmed broader than documented in REVIEW.md

- **File**: `backend/db/operations.py:357-362` (`get_alerts_pipeline_health`)
- **REVIEW.md documents**: "MAJOR-01: `pipeline_runs_last_24h` includes BACKTEST rows"
- **Actual live DB breakdown** (2026-04-23 ~23:42 UTC): `pipeline_runs_last_24h = 1447` = 1442 BACKTEST + 5 LIVE. The 1442 BACKTEST rows were created on 2026-04-23T14:12–14:52 (during Phase 10 smoke testing).
- **Impact**: If watchdog were enabled, the correct LIVE run count is 5, not 1447. The ratio inflation is 288x. This confirms the mitigation (`enabled: false`) was correct. The fix for Phase 10.1 is confirmed necessary: add `AND mode = 'LIVE'` to the `pipeline_runs_last_24h` query.
- **No new action needed** — mitigation in place.

### [MINOR] INT-03 — MAJOR-03 T-vs-space datetime produces false inclusions for same-date rows

- **File**: `backend/db/operations.py:358-362`
- **Mechanism**: `created_at` is stored as ISO-8601 with T separator (e.g., `2026-04-22T09:17:10`), but SQLite's `datetime('now', '-1 day')` returns space-separated format (e.g., `2026-04-22 23:44:18`). In SQLite string comparison, `T` (ASCII 84) > ` ` (ASCII 32), so `2026-04-22T00:00:00 >= 2026-04-22 23:44:18` evaluates TRUE regardless of time. This inflates the window: all rows from the boundary date with T-format are included even if they are >24h old.
- **Live DB evidence**: 4 LIVE rows from `2026-04-22T09:17–09:18` (approximately 38.5h old at time of audit) pass the `datetime('now', '-1 day')` filter and are counted in `pipeline_runs_last_24h` (current live count: 5 LIVE = 1 genuine recent + 4 incorrectly included from 38h ago).
- **Impact for alerts_last_24h**: 0 alerts from `2026-04-22` exist, so no false "healthy" masking in the alerts dimension. But for a hypothetical backfill run, old T-format alerts could mask a real silent failure.
- **Recommended Phase 10.1 fix**: Use `strftime('%Y-%m-%dT%H:%M:%S', datetime('now', '-1 day'))` to normalize the cutoff to T-format, or store `created_at` as space-format via `datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')`.

---

## App startup smoke

- `backend.main` imports cleanly (no import errors).
- `GET /api/health` → 200 `{status: 'healthy', db_ok: True, scheduler_running: False}`. PASS.
- `GET /api/health/alerts-pipeline` → 200 `{last_alert_at, alerts_last_24h, pipeline_runs_last_24h}` — correct schema. PASS.
- `GET /api/alerts` → 200 — excludes deprecated by default. PASS.
- Scheduler starts cleanly, registers 6 jobs (alerting_cycle, drift_cycle, recheck_queue, daily_digest, weekend_cycle_10h, weekend_cycle_18h). `silent_failure_watch_cycle` NOT registered (correctly skipped per `enabled: false`). No ghost job. PASS.
- Scheduler stops cleanly via `stop_scheduler()`, `is_scheduler_running()` → False. PASS.

---

## Requirements traceability

- MONITOR-01 `[x]` in REQUIREMENTS.md line 17: **PASS** — checkbox correctly marked complete.
- MONITOR-02 `[x]` in REQUIREMENTS.md line 18: **PASS**.
- MONITOR-03 `[x]` in REQUIREMENTS.md line 19: **PASS**.
- Trace table: MONITOR-01/02/03 all mapped to Phase 10, status Complete (lines 122-124). PASS.
- Phase 10 plans frontmatter: 10-01 references MONITOR-03, 10-02 references MONITOR-01, 10-03 references MONITOR-02. No orphan requirements found.
- One stale documentation note: 10-VERIFICATION.md line ~96 notes "MONITOR-01 checkbox was Pending in REQUIREMENTS.md" — this was resolved in commit `272eb5a` which marks MONITOR-01 `[x]`. No outstanding checkbox drift.

---

## Commit graph analysis

All 16 commits in `fbdbe13..bb34e36` are scope-appropriate and atomic:

| SHA | Scope | Files | Notes |
|-----|-------|-------|-------|
| `de9e79e` | chore(10) | data/vna_alerts.db.pre-phase10.bak | Pre-snapshot only. Clean. |
| `b7b2af1` | feat(10) | models.py, 003 migration SQL, rollback SQL, test_models_sync.py | All related. Clean. |
| `2e1d222` | feat(10) | apply_migration_003.py, test_migration_003_apply.py | Driver + test. Clean. |
| `c29f35a` | feat(10) | operations.py, scheduler.py, backfill_alerts.py | Wire-up commit. Clean. Correctly touches all 3 call sites. |
| `22abf88` | feat(10) | data/vna_alerts.db (binary) | Migration apply only. Clean. |
| `9f521e5` | docs(10-01) | planning files only | Docs-only. Clean. |
| `2bd1a0e` | feat(10) | schemas.py, operations.py | New schema + helper. Clean. |
| `64b5b19` | feat(10) | routes.py, test_health_alerts_pipeline.py | Endpoint + test. Clean. |
| `6a0ab2e` | docs(10-02) | planning files only | Clean. |
| `e4c71d8` | feat(10) | config_loader.py, alerting_rules.yaml | Config only. Clean. |
| `2977294` | feat(10) | monitoring/__init__.py, silent_failure_watch.py, test_silent_failure_watch.py | Module + test. Clean. |
| `d95196e` | feat(10) | scheduler.py only | Scheduler registration. Clean. |
| `344cdee` | docs(10) | 10-REVIEW.md | Review only. Clean. |
| `e03ddab` | docs(10-03) | planning files only | Clean. |
| `272eb5a` | docs(phase-10) | PROJECT.md, REQUIREMENTS.md, ROADMAP.md, STATE.md, 10-VERIFICATION.md | Docs close-out. Clean. |
| `bb34e36` | fix(10-mitigation) | alerting_rules.yaml only | Mitigation toggle only. Clean. |

No merge commits. No force-push artifacts. No cross-scope contamination (no `feat(10-02)` commit touching models.py). All revertible independently.

---

## Summary

Phase 10 introduces zero regressions against Phases 07, 08, and 09. All 10 prior-phase test suites pass with 0 failures. The end-to-end pipeline flow (create alert → record run with counter → watchdog detection logic) works correctly in both "healthy" and "silent failure" states. The `enabled: false` mitigation correctly prevents registration of the watchdog job and leaves no ghost entries in the scheduler. Two test failures in `test_migration_003_apply.py` are design-time artifacts (tests were written for a pre-migration DB state, now permanently stale) — they do not indicate any runtime regression and should be refactored in Phase 10.1.
