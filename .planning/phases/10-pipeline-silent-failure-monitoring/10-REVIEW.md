---
phase: 10-pipeline-silent-failure-monitoring
reviewed: 2026-04-23T00:00:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - backend/api/routes.py
  - backend/api/schemas.py
  - backend/db/models.py
  - backend/db/operations.py
  - backend/monitoring/__init__.py
  - backend/monitoring/silent_failure_watch.py
  - backend/scheduler/scheduler.py
  - backend/utils/config_loader.py
  - config/alerting_rules.yaml
  - scripts/apply_migration_003.py
  - scripts/backfill_alerts.py
  - scripts/migrations/003_add_alerts_written_count.sql
  - scripts/migrations/003_rollback.sql
  - scripts/test_health_alerts_pipeline.py
  - scripts/test_migration_003_apply.py
  - scripts/test_models_sync.py
  - scripts/test_silent_failure_watch.py
findings:
  critical: 0
  warning: 4
  info: 6
  total: 10
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-04-23T00:00:00Z
**Depth:** standard
**Files Reviewed:** 18 (17 listed source files + config YAML)
**Status:** issues_found

## Summary

Phase 10 delivers the silent-failure monitoring stack (MONITOR-01/02/03) that closes the detection gap behind the 2026-01-22 -> 2026-04-22 incident: a new `alerts_written_count` column in `pipeline_runs` (migration 003), a read-only `/api/health/alerts-pipeline` endpoint, and a scheduler-registered watchdog (`silent_failure_watch.py`) that fires a P0 Slack meta-alert on the `pipeline_runs > 0 AND alerts == 0` divergence.

**Migration 003 SQL safety: CLEAN.** The migration follows the post-Phase-08 template faithfully: `PRAGMA foreign_keys=OFF` precedes `BEGIN TRANSACTION`, ledger INSERT without `OR REPLACE` acts as the atomic idempotency guard (UNIQUE constraint forces rollback before DDL), `CHECK(alerts_written_count >= 0)` is byte-identical in models.py and migration SQL, and the rollback script correctly removes both the column and the ledger row.

**HARD-03 drift-gate: GREEN and expanded correctly.** `test_models_sync.py` grew from 16 to 22 tests (TestModels003Sync adds 6 tests covering byte-identity, column presence, ledger INSERT shape, PRAGMA ordering, and rollback correctness). Phase 10 plan claim of "23 tests" appears to be off-by-one — actual count is 22. Drift gate covers all three migrations bidirectionally.

**Watchdog logic: mostly correct with one reliability gap.** Divergence pattern, zero-state vs data-anomaly classification, fail-soft Slack, and `run_watch_cycle` never-raises contract are all implemented correctly. `SilentFailureMonitorConfig` uses `default_factory` per WR-03. The main warning is that the Slack retry loop only recovers from 5xx and network errors — 429 rate-limit responses are treated as terminal (not retried), which contradicts how real Slack webhooks behave during incident bursts.

**Cross-phase contract preservation: CLEAN.** D-16 `deprecated = 0` filter and D-17 `include_deprecated` query param are preserved in `get_alerts` / `get_alert_by_id`. `get_alerts_pipeline_health()` correctly scopes `alerts_last_24h` to non-deprecated rows, matching the D-16/D-17 contract the watchdog must respect (otherwise backfilled-then-deprecated alerts would suppress the P0).

**Known issues confirmed.** Issue #1 (fixture drift in `test_migration_003_apply.py::test_dry_run_no_mutation`) is reproducible — test FAILS locally because the fixture copies post-002/post-003 live DB into the tempdir, so `alerts_written_count` is already present before the dry-run runs. The `assertNotIn` assertion is trivially false. This is a scope-clean fixture bug, not an R-01 violation, but it does invalidate the "4/4 tests pass" claim in 10-01-SUMMARY.md. Issue #2 (Slack retry coverage) is partially a real gap — see WR-01 and IN-03.

**R-01 adherence: CLEAN.** The diff touches only source files in the declared Phase 10 scope plus a single intentional DB mutation (migration 003 application with backup). No unrelated pre-existing WIP was swept in.

## Warnings

### WR-01: Slack retry loop does not retry on 429 (rate-limit)

**File:** `backend/monitoring/silent_failure_watch.py:142-151`
**Issue:** The retry logic branches on `resp.status >= 500` for retry and any other non-200 as terminal. Slack returns HTTP 429 with `Retry-After` header when the webhook is rate-limited — which is likely exactly what happens during an incident burst when many services send at once. A rate-limited meta-alert during the very moment the silent-failure pattern fires is the worst time to silently drop the message.

The watchdog doc-comment lists "all retries exhausted" as a failure mode but the code never reaches the retry path for 429. Given the whole point of this module is to fire during incidents, this is a reliability warning (not a correctness bug — the log line `Slack returned 429` will be emitted).

**Fix:**
```python
with urlopen(req, timeout=10) as resp:
    if resp.status == 200:
        logger.info(...)
        return True
    elif resp.status == 429 or resp.status >= 500:
        # Respect Retry-After for 429 if present; fall back to exponential backoff.
        retry_after = resp.headers.get("Retry-After") if resp.status == 429 else None
        try:
            delay = int(retry_after) if retry_after else 2 ** attempt
        except ValueError:
            delay = 2 ** attempt
        logger.warning(
            "send_meta_alert: Slack %d (attempt %d/%d), retrying in %ds",
            resp.status, attempt + 1, max_retries, delay,
        )
        time.sleep(delay)
    else:
        logger.warning("send_meta_alert: Slack returned %d", resp.status)
        return False
```
Add a matching test in `test_silent_failure_watch.py` mirroring `test_send_retries_on_500`.

---

### WR-02: Dry-run fixture drift in test_migration_003_apply.py::test_dry_run_no_mutation

**File:** `scripts/test_migration_003_apply.py:68-74`
**Issue:** The fixture `setUp()` copies `LIVE_DB` (which, after commit 22abf88, already has the `alerts_written_count` column applied) into a temp DB. The dry-run test then asserts `alerts_written_count` is absent from the columns post-dry-run, but it was already present before the driver ran. Test fails locally:

```
AssertionError: 'alerts_written_count' unexpectedly found in {...,
'alerts_written_count', ...} : dry-run must not mutate
```

This contradicts the 10-01-SUMMARY.md claim of "4/4 tests pass." Once the live DB has migration 003 applied, the test shape stops working because the fixture inherits the applied state. The `test_first_apply_success` and `test_second_apply_idempotent_skip` tests also rely on the fixture being pre-migration — `test_first_apply_success` will hit the idempotency guard and exit 0 with a SKIP, which happens to pass the `returncode == 0` assertion but doesn't exercise the "first apply" path anymore.

**Fix:** Move the fixture to a synthesized post-002 / pre-003 DB instead of copying the live DB. Either:

1. Maintain a checked-in `test-fixtures/vna_alerts_post_002.db` reference snapshot and `shutil.copyfile` that into the tempdir.
2. Or build the tempdb from scratch in `setUp` using `SQL_CREATE_*` strings from models.py *minus* the post-003 column declaration (construct a pre-003 pipeline_runs schema explicitly):

```python
def setUp(self):
    self.tmpdir = Path(tempfile.mkdtemp(prefix="mig003_"))
    self.tmp_db = self.tmpdir / "vna_alerts.db"
    conn = sqlite3.connect(str(self.tmp_db))
    # Create pre-003 pipeline_runs schema (without alerts_written_count).
    conn.executescript("""
        CREATE TABLE pipeline_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL, timestamp TEXT NOT NULL,
            channel_group TEXT NOT NULL, trigger_type TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'LIVE', status TEXT NOT NULL,
            duration_sec REAL, llm_used INTEGER DEFAULT 0,
            llm_fallback INTEGER DEFAULT 0, alert_id TEXT,
            error_message TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE alerts (alert_id TEXT PRIMARY KEY, deprecated INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE vna_schema_migrations (
            migration_id TEXT PRIMARY KEY, applied_at TEXT NOT NULL
        );
        INSERT INTO vna_schema_migrations VALUES ('001_expand_channel_groups', datetime('now'));
        INSERT INTO vna_schema_migrations VALUES ('002_add_alert_deprecation', datetime('now'));
        INSERT INTO pipeline_runs (run_id, timestamp, channel_group, trigger_type, status, created_at)
            VALUES ('r1', '2026-04-01T00:00:00', 'GOOGLE_ADEX', 'A1', 'success', '2026-04-01T00:00:00');
    """)
    conn.commit()
    conn.close()
    # ... rest of shim wiring unchanged
```

---

### WR-03: `_resolve_webhook_url` silently prefers env over config when both are set (surprise precedence)

**File:** `backend/monitoring/silent_failure_watch.py:38-64`
**Issue:** The precedence ladder is: `env SLACK_WEBHOOK_URL` → `config.silent_failure_monitor.slack_channel_override` → `config.slack_notifications.webhook_url`. This is documented in the docstring and matches the intent in 10-03-PLAN. However, there is no log line when `env SLACK_WEBHOOK_URL` is used while an explicit `slack_channel_override` is also configured. Operators who set `slack_channel_override` in YAML expecting the watchdog to post there will be surprised when an orphaned `SLACK_WEBHOOK_URL` shell export silently wins.

This is a warning because the current `config/alerting_rules.yaml` has `slack_channel_override: null`, so the conflict doesn't trigger in practice — but the failure mode is subtle and survives only by config accident.

**Fix:** Add one debug log on the chosen source:
```python
def _resolve_webhook_url() -> Optional[str]:
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if url:
        logger.debug("_resolve_webhook_url: using env SLACK_WEBHOOK_URL")
        try:
            cfg = get_config()
            if cfg.silent_failure_monitor.slack_channel_override:
                logger.info(
                    "_resolve_webhook_url: env SLACK_WEBHOOK_URL takes precedence "
                    "over config.silent_failure_monitor.slack_channel_override"
                )
        except Exception:
            pass
        return url
    # ... rest unchanged
```

---

### WR-04: `_check_lsof` has a narrow TOCTOU window despite the flock mitigation

**File:** `scripts/apply_migration_003.py:73-125`
**Issue:** The driver calls `_check_lsof()` *before* `_acquire_apply_lock()`. Between lsof returning "clean" and the flock being acquired, a concurrent process can open the DB (the intended race this guards against). The comment at line 114 even calls out that the flock closes the TOCTOU between `_check_lsof` and `sqlite3.connect` — but the lsof check itself runs first, so there's still a window before the flock is held.

In practice, the flock is what prevents concurrent driver invocations from racing; the lsof check is a courtesy that catches running app servers. A different process (e.g. `sqlite3` REPL, backend API server still running) can still open the DB between lsof-clean and flock-acquired, and the flock doesn't prevent that — SQLite's own locking would, but the driver would have already dumped "all clear" to the log.

This is a warning (not critical) because the real safety is the `sqlite3.Connection.backup()` snapshot before any mutation and the restore path on failure — both present and correct.

**Fix:** Acquire the flock *first*, then run lsof while holding it (the flock is process-level, not DB-level, but it serializes multiple driver invocations; lsof after flock-hold catches non-driver handles):
```python
_apply_lock_fd = _acquire_apply_lock(DB_PATH)
_check_lsof(DB_PATH)
```
Alternatively, leave as-is and document that the `_check_lsof` is best-effort; rely on sqlite3 busy handling + backup/restore for the hard safety guarantee.

## Info

### IN-01: Unused `logging` import in silent_failure_watch.py

**File:** `backend/monitoring/silent_failure_watch.py:19`
**Issue:** `import logging` at line 19 is not used — the module uses `get_logger(__name__)` from `backend.utils.logger` at line 31. The `logging` stdlib module is never referenced.
**Fix:** Remove `import logging` at line 19.

---

### IN-02: Phase 10 plan claims "23 tests" but suite has 22

**File:** `scripts/test_models_sync.py`
**Issue:** Phase plans / ROADMAP text references `test_models_sync.py expansion to 23 tests`. Actual count: `TestModelsSync` (9) + `TestModels002Sync` (7) + `TestModels003Sync` (6) = 22 tests. This is a documentation / metadata drift, not a test bug. The added coverage is correct.
**Fix:** Either add one more test (e.g. a `test_a07_rollback_sql_drops_column_and_no_or_replace` symmetric to the 002 suite) or correct the "23 tests" count in plan docs to 22.

---

### IN-03: Connection-level timeout is set (10s) but no retry on `URLError`-wrapped TimeoutError is tested

**File:** `backend/monitoring/silent_failure_watch.py:135,152-163`
**Issue:** The `urlopen` call uses `timeout=10`, and the except clause catches `(URLError, OSError)` — which will catch `socket.timeout` raised on connect/read timeout (it's re-raised wrapped in `URLError` on most Pythons). The code path is correct, but `test_silent_failure_watch.py` does not exercise timeout behavior explicitly; known issue #2 lists "timeout (unclear)" as unverified. Since the catch is correct (URLError/OSError covers timeout), this is an Info, not a Warning.
**Fix:** Add a `test_send_retries_on_timeout` method mirroring `test_send_retries_on_500` but setting `mock_urlopen.side_effect = [URLError("timed out"), URLError("timed out"), ctx_200]` for explicit coverage.

---

### IN-04: `get_alerts_pipeline_health` does not bind the 24h window to a single `datetime('now')` evaluation

**File:** `backend/db/operations.py:340-368`
**Issue:** Three separate queries each call `datetime('now', '-1 day')`. Between query 1 and query 3, SQLite re-evaluates `now` — worst case a few milliseconds of skew. Not a correctness bug (24h window tolerates ms skew) but means `alerts_last_24h` and `pipeline_runs_last_24h` can reference slightly different window boundaries. Given the watchdog's triggering condition is `pipeline_runs_last_24h > 0 AND alerts_last_24h == 0`, the skew is immaterial — both values can only be off by items that land exactly on the boundary, and "close enough to a day" is fine for a 60-min cron.
**Fix:** If pedantic stability is desired, bind once:
```python
cutoff = (datetime.utcnow() - timedelta(days=1)).isoformat()
row = conn.execute(
    "SELECT COUNT(*) FROM alerts WHERE deprecated = 0 AND created_at >= ?",
    (cutoff,),
).fetchone()
# ... same cutoff for pipeline_runs
```
Otherwise, leave as-is with a comment.

---

### IN-05: MIGRATION_SQL file path is hardcoded at module level (line 61) — tests can't redirect it via DB_PATH override alone

**File:** `scripts/apply_migration_003.py:61` and `scripts/test_migration_003_apply.py:46-57`
**Issue:** The shim in `test_migration_003_apply.py` overrides `d.DB_PATH` and `d.BAK_PATH` but not `d.MIGRATION_SQL`, so the driver always reads the canonical `scripts/migrations/003_add_alerts_written_count.sql`. This is fine because the SQL file is the system-under-test, but it's fragile: if someone edits the canonical SQL mid-test-run, the tests read the in-flight version. Low priority.
**Fix:** Optional — also override `d.MIGRATION_SQL` in the shim to a copy written to tempdir. Not necessary unless tests need to mutate the SQL.

---

### IN-06: `_backup()` overwrites existing `.pre-phase10.bak` without interactive confirmation

**File:** `scripts/apply_migration_003.py:215-218`
**Issue:** `_backup` auto-unlinks an existing `.pre-phase10.bak` before writing. If an operator re-runs the driver (even in dry-run mode) after a prior successful apply, and then realizes they need the original backup — it has been silently overwritten by a post-apply snapshot. The idempotency guard means `_backup` is only called on a first apply, so this is mostly theoretical — but the "overwriting existing backup" log line is INFO level; a WARNING would surface the risk better.

The preferred rollback path documented in `003_rollback.sql` header is "restore from .pre-phase10.bak" — losing that snapshot to a second driver run would force the fallback DOWN script.
**Fix:** Rename to include a timestamp, or escalate to WARNING:
```python
if dst.exists():
    logger.warning(
        "Overwriting existing backup: %s -- previous snapshot will be lost", dst
    )
```

---

_Reviewed: 2026-04-23T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
