# Auditor 2 — Adversarial Code & Contract Audit — Phase 10

## Verdict
MAJOR ISSUES

---

## Severity-classified findings

### BLOCKER (ship-stopping)

None confirmed. The most serious issue is a MAJOR false-positive risk (see below) that fires right now on the live DB, but it does not crash the system.

---

### MAJOR (fix before next prod run)

**MAJOR-01: BACKTEST runs contaminate pipeline_runs_last_24h, causing false-positive P0 Slack alerts**

**File:** `backend/db/operations.py:357-362` / `config/alerting_rules.yaml:155-157`

The watchdog query counts ALL `pipeline_runs` rows created in the last 24h without filtering by `mode`:

```sql
SELECT COUNT(*) FROM pipeline_runs
WHERE created_at >= datetime('now', '-1 day')
```

`backfill_alerts.py` writes BACKTEST mode runs with `created_at = datetime.utcnow().isoformat()` (wall clock, today), but writes the corresponding alerts with `created_at = ts` (the historical backfill date, months ago). This creates a structural asymmetry:
- `pipeline_runs_last_24h` = 1447 (1442 BACKTEST + 5 LIVE, all with today's created_at)
- `alerts_last_24h` = 0 (all 238 alerts have created_at from 2026-01-23 to 2026-03-23)

**Live DB verification right now:**
```
SELECT mode, COUNT(*) FROM pipeline_runs WHERE created_at >= datetime('now', '-1 day') GROUP BY mode;
-- BACKTEST|1442
-- LIVE|4
SELECT COUNT(*) FROM alerts WHERE deprecated=0 AND created_at >= datetime('now', '-1 day');
-- 0
```

**With `enabled: true` in `config/alerting_rules.yaml:156`, the watchdog is active and fires every 60 minutes.** `check_silent_failure()` (`silent_failure_watch.py:179-195`) sees `prl=1447 > 0 AND al=0` and classifies as `reason="silent_failure"`, triggering a P0 Slack meta-alert. This is a false positive — the pipeline is not actually silent-failing, it ran a Phase 09 backfill.

**Fix:** Add `AND mode = 'LIVE'` to the `pipeline_runs_last_24h` query at `operations.py:358-361`.

---

**MAJOR-02: `resp.status >= 500` and `resp.status else` branches are dead code (logic error in retry path)**

**File:** `backend/monitoring/silent_failure_watch.py:141-151`

Python's `urllib.request.urlopen()` raises `urllib.error.HTTPError` (which is a subclass of `URLError`) for any non-2xx HTTP response. The `with urlopen(req, ...) as resp:` context manager therefore never yields a response object for 4xx or 5xx status codes — those throw before execution reaches `resp.status`. The status check branches are unreachable:

```python
with urlopen(req, timeout=10) as resp:
    if resp.status == 200:          # ← only reachable path
        return True
    elif resp.status >= 500:        # ← DEAD: HTTPError already raised
        time.sleep(delay)
    else:                           # ← DEAD: HTTPError already raised
        return False
```

All 4xx and 5xx cases (including 429 rate-limit) flow through `except (URLError, OSError) as e:` at line 152, which DOES retry. So the retry logic works — just not via the path that was written. The consequence:

- 429 is retried up to 3× with exponential backoff (1s, 2s) but without reading the `Retry-After` header.
- 500/502/503 are retried with backoff through the exception path, not the status path.
- The documented intent ("retries on 5xx") is accidentally achieved, but the code is misleading and untested via the status path.

The dead `resp.status else: return False` branch would have suppressed retries on 4xx if it were reachable, which would be wrong behavior — so it being dead code is actually the safer outcome. But it makes the code incorrect as written.

**Fix:** Remove the `resp.status >= 500` / `else` branches entirely. The `except (URLError, OSError)` block is the only retry path needed. Optionally read `Retry-After` header from `HTTPError` for 429.

---

**MAJOR-03: T-separator vs space-separator datetime comparison overcounts 24h window**

**File:** `backend/db/operations.py:344-362`

Python's `datetime.isoformat()` and `datetime.now(timezone.utc).isoformat()` produce strings with `T` separator (e.g., `2026-04-22T09:17:10`). SQLite's `datetime('now', '-1 day')` produces strings with a **space** separator (e.g., `2026-04-22 21:31:33`). In SQLite string comparison, `'T'` (ASCII 84) > `' '` (ASCII 32), so any stored timestamp on the same calendar date as the boundary is ALWAYS considered >= the boundary:

```sql
SELECT '2026-04-22T09:17:10' >= '2026-04-22 21:31:33';  -- returns 1 (TRUE, wrong)
```

**Live DB verification:**
```
SELECT MIN(created_at), MAX(created_at) FROM pipeline_runs
WHERE created_at >= datetime('now', '-1 day');
-- 2026-04-22T09:17:10.056067  (12h before boundary, but included)
```

This overcounts `pipeline_runs_last_24h` and `alerts_last_24h` by up to several hours of same-calendar-day records. The count is inflated, not deflated, so it creates false positives (overcounting runs, potentially undercounting alerts gap). In the current state, 4 LIVE runs from April 22 09:17 are counted as "in last 24h" when they are actually ~36h old.

**Fix:** Use `datetime(REPLACE(created_at, 'T', ' '))` in comparisons, or store timestamps without the `T` separator, or use `strftime('%s', created_at)` for numeric comparison. Consistent format throughout.

---

### MINOR (cleanup)

**MINOR-01: Unused `import logging` in `silent_failure_watch.py`**

**File:** `backend/monitoring/silent_failure_watch.py:19`

`import logging` is present but unused. The module uses `get_logger(__name__)` from `backend.utils.logger` exclusively. No `logging.X` calls exist in the file.

---

**MINOR-02: `alerts_written_count=1` on dedup UPDATE path (misleading counter)**

**File:** `backend/scheduler/scheduler.py:68`

The scheduler sets `alerts_written = 1 if result.get("alert_triggered") else 0`. However, `notifier._save_to_db()` in LIVE mode first checks `find_open_alert()` and may UPDATE an existing alert rather than INSERT a new row. If dedup fires (UPDATE path), `alert_triggered=True` but no new row was written. The counter records 1 even though 0 rows were inserted. This does not affect the watchdog logic (any non-zero count means the pipeline is healthy), but the column name `alerts_written_count` is misleading — it's actually `alert_events_count` or `alert_activity_count`.

---

**MINOR-03: `idx_alerts_deprecated` missing from `SQL_CREATE_INDEXES` in `models.py`**

**File:** `backend/db/models.py:368-379`

The index `idx_alerts_deprecated` is created by `scripts/migrations/002_add_alert_deprecation.sql:91` and referenced in `operations.py:342` ("Uses idx_alerts_deprecated (Phase 09 migration 002)"). It is NOT listed in `SQL_CREATE_INDEXES`, so a fresh `init_db()` without running migration 002 will not create this index. The live DB has it (verified). This is a pre-existing Phase 09 gap, not Phase 10 specific, but MAJOR-03 datetime bug above and `get_alerts_pipeline_health()` both rely on it.

---

**MINOR-04: 3 DB queries inside `get_alerts_pipeline_health()` lack explicit BEGIN**

**File:** `backend/db/operations.py:340-368`

The three `SELECT` statements inside `with get_db() as conn:` run without an explicit `BEGIN` transaction. Python's `sqlite3` module does not auto-start a read transaction for `SELECT` statements (only for DML). In WAL mode, each `SELECT` takes its own snapshot independently. A write committed between query 1 and query 2 could cause `last_alert_at` and `alerts_last_24h` to disagree. In practice, the window is microseconds and a true silent failure persists for hours, so this is operationally harmless. However, for correctness an explicit `BEGIN DEFERRED` would guarantee snapshot consistency.

---

**MINOR-05: No circuit breaker on repeated watchdog failures**

**File:** `backend/monitoring/silent_failure_watch.py:199-230`

`run_watch_cycle()` never raises and never self-disables. If Slack is down for hours, the watchdog fires a Slack POST attempt every 60 minutes (per `cron_interval_minutes=60`). With 3 retries + exponential backoff (up to 4+8s of blocking), each failed cycle blocks the APScheduler thread pool for up to ~20 seconds. APScheduler 3.x runs sync jobs in a thread pool, so it won't block the event loop, but it WILL consume a thread per cycle. With the `max_instances=1` guard in place, the scheduler won't stack cycles, so this is bounded. No log flood because logging only emits once per cycle (3 warnings + 1 error per attempt). The absence of a circuit breaker is an operational gap but not a hard bug.

---

### INFO (observations)

**INFO-01: Webhook resolution priority documented correctly**

`_resolve_webhook_url()` (`silent_failure_watch.py:38-64`) resolves in this order:
1. `env SLACK_WEBHOOK_URL`
2. `config.silent_failure_monitor.slack_channel_override` (from YAML)
3. `config.slack_notifications.webhook_url` (YAML fallback)

The YAML currently has `slack_channel_override: null` and `slack_notifications.webhook_url: https://hooks.slack.com/services/TEST123`. So env var wins if set, then config override, then generic webhook. This matches the docstring at line 39. No surprise here.

**INFO-02: `enabled: true` in production YAML exposes live DB state now**

`config/alerting_rules.yaml:156` sets `enabled: true`. This is deliberate (the monitor should be active), but given MAJOR-01, the watchdog is currently a live false-positive generator.

**INFO-03: WR-03 default_factory is correctly implemented**

`SilentFailureMonitorConfig` at `config_loader.py:153-168` defaults `enabled=False` and is declared with `Field(default_factory=SilentFailureMonitorConfig)` at `AlertingConfig:245`. Missing YAML section safely defaults to `enabled=False`. The YAML currently explicitly sets `enabled: true`, which overrides the safe default.

**INFO-04: Saturday/Sunday 14h gap does not cause false positive**

Between Sunday 18:00 UTC (last weekend run) and Monday 08:00 UTC (first weekday run), the gap is 14h. At any point during Monday, the 24h window still sees Sunday's runs until Sunday 18:00 + 24h = Monday 18:00. Monday 08:00 runs are recorded before the Sunday runs expire. No false positive window.

**INFO-05: Startup zero-state correctly handled**

`check_silent_failure()` at `silent_failure_watch.py:179` correctly classifies `prl=0 AND al=0` as `zero_state` with `triggered=False`. A fresh deployment with no runs yet does not fire.

**INFO-06: Migration 003 atomicity and rollback are solid**

The `003_add_alerts_written_count.sql` migration uses `BEGIN TRANSACTION` + ledger `INSERT` (UNIQUE guard) + `ALTER TABLE` + `COMMIT`. The ledger-INSERT-first pattern means second application raises `UNIQUE constraint` and rolls back before DDL. The rollback script correctly uses `ALTER TABLE DROP COLUMN` (requires SQLite 3.35+, checked at driver startup). The `apply_migration_003.py` driver has strong pre-check, backup, apply, verify, and restore-on-failure semantics. The flock releases correctly on crash (OS cleanup). The lsof check correctly distinguishes live vs test DB contexts.

**INFO-07: Pydantic schema correctly handles None from empty alerts table**

`AlertsPipelineHealth.alerts_last_24h` and `pipeline_runs_last_24h` use `Field(..., ge=0)`. `COUNT(*)` in SQLite never returns NULL, and `operations.py:355` adds a `if row and row[0] is not None else 0` guard. The `get_alerts_pipeline_health()` properly returns `int`, Pydantic validation passes. `last_alert_at` is `Optional[str]` — correctly nullable when the alerts table is empty.

**INFO-08: `executescript()` + `conn.commit()` in `_apply_migration()` is a harmless double-commit**

`apply_migration_003.py:259-261`: `executescript()` commits any pending transaction before executing the script, and the SQL has its own `COMMIT`. The subsequent `conn.commit()` is a no-op on an already-committed transaction. No data loss, but slightly confusing.

**INFO-09: BACKTEST-mode dedup in watchdog context (not a bug)**

The scheduler in `_run_trigger_for_channels()` always passes `mode="LIVE"`. Only `backfill_alerts.py` uses `mode="BACKTEST"`. The watchdog fires P0 because backfill was run recently (Phase 09). Once backfill runs age out (24h window), the contamination clears — except for the T-separator overcount (MAJOR-03).

**INFO-10: Commit hygiene is clean**

Each of the 15 Phase 10 commits is scoped to a single concern. No pre-existing WIP swept in. The `de9e79e` (DB snapshot) commit correctly precedes the migration commits. The feature, docs, and chore commits are appropriately separated.

---

## Strongest evidence of correctness

1. **HARD-03 drift gate (TestModels003Sync):** The `CHECK(alerts_written_count >= 0)` byte-identity test in `scripts/test_models_sync.py:311-386` correctly verifies the SQL constraint is consistent between `models.py` and `003_add_alerts_written_count.sql`. The test covers: file existence, CHECK clause identity, column declaration presence, ledger INSERT without OR REPLACE, PRAGMA ordering, and rollback SQL content. This is a solid multi-layer guard against schema drift.

2. **Migration driver robustness (`apply_migration_003.py`):** Pre-check → backup (WAL-safe sqlite3.backup()) → apply → post-verify → restore-on-failure is a correct, well-tested sequence. The lsof + flock combination correctly guards against concurrent apply. Idempotency detection (column presence + ledger row both required) catches partial states.

3. **Watchdog never-raises contract:** `run_watch_cycle()` catches all exceptions from `check_silent_failure()` and `send_meta_alert()` separately and returns a structured result. APScheduler `max_instances=1` prevents cycle overlap. The scheduler correctly skips registration when `enabled=False`.

4. **D-16/D-17 preservation:** Both `get_alerts()` and `get_alerts_pipeline_health()` correctly apply `deprecated=0` filter. The new health endpoint correctly excludes deprecated alerts from `alerts_last_24h`.

5. **Test coverage for the happy/sad paths:** `test_silent_failure_watch.py` covers all four classification states (healthy, silent_failure, zero_state, data_anomaly) and the 500-retry path. The TestClient smoke test for `/api/health/alerts-pipeline` covers schema compliance and read-only behavior.

---

## Specific recommendations

1. **[MAJOR-01 FIX, urgent]** Add `AND mode = 'LIVE'` to `pipeline_runs_last_24h` query in `operations.py:358-361`. The monitoring intent is explicitly "LIVE pipeline runs" — BACKTEST runs should not trigger P0. Consider also filtering `alerts` by `data_source != 'backfill'` if backfill alerts need to be excluded from `alerts_last_24h` (or accept them as genuine historical data).

2. **[MAJOR-02 FIX]** Remove the dead `resp.status >= 500` / `else` branches from `send_meta_alert()` in `silent_failure_watch.py:141-151`. Replace with explicit `HTTPError` catch to handle 429 (read `Retry-After` header if present) and 5xx retry separately from network errors. Example: `except HTTPError as e: if e.code == 429: time.sleep(int(e.headers.get('Retry-After', 60)))`.

3. **[MAJOR-03 FIX]** Normalize datetime strings before comparison. Either store timestamps without microseconds and use `strftime` in queries, or apply `REPLACE(created_at, 'T', ' ')` in the WHERE clause. The most systematic fix is to audit all `datetime.utcnow().isoformat()` calls in `operations.py` and replace with a consistent format that SQLite's `datetime()` function matches.

4. **[MINOR-01]** Remove `import logging` from `silent_failure_watch.py:19`.

5. **[MINOR-03]** Add `"CREATE INDEX IF NOT EXISTS idx_alerts_deprecated ON alerts(deprecated);"` to `SQL_CREATE_INDEXES` in `models.py` so fresh `init_db()` creates the index that `get_alerts_pipeline_health()` relies on.

6. **[OPERATIONAL]** Temporarily set `enabled: false` in `config/alerting_rules.yaml` until MAJOR-01 is fixed. The watchdog is actively firing false positives on the live instance right now (1442 BACKTEST runs in last 24h, 0 alerts in last 24h).

7. **[OPERATIONAL]** Consider a `Retry-After`-aware sleep for 429 in `send_meta_alert`. Slack's incoming webhooks rate limit at ~1 message/second per webhook URL, and they do return 429 with `Retry-After`. The current 1s/2s backoff (max 3 attempts) will fail on sustained rate limits without knowing the required wait.
