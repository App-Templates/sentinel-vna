# Auditor A — SQL / DB Semantics Deep Audit — Phase 10

## Verdict

**MAJOR ISSUES** (2 confirmed critical + 4 new findings ranging from minor to major)

---

## New Findings (not in WR-01..WR-04 or MAJOR-01..MAJOR-03)

---

### [MAJOR-NEW-01] — Mixed aware/naive timestamp format in `alerts.created_at` corrupts `MAX()` and window queries

- **File:line:**
  - `backend/agents/notifier.py:58` — `datetime.now(timezone.utc).isoformat()` → `'2026-04-23T21:42:50+00:00'` (AWARE, with `+00:00` suffix)
  - `backend/agents/notifier.py:116` — same
  - `backend/db/operations.py:64` — `alert.created_at.isoformat()` where `alert.created_at = datetime.utcnow()` → `'2026-04-23T21:42:50.142222'` (NAIVE, no suffix)
  - `scripts/backfill_alerts.py:156` — `created_at=ts` where `ts` is a `timezone.utc`-aware datetime → AWARE format via `isoformat()`

- **Problem:** The `alerts.created_at` column receives rows in TWO incompatible string formats depending on write path:
  - **LIVE path** (notifier `_save_to_db`): `'2026-04-23T21:42:50.140889+00:00'` (aware)
  - **Backfill/create_alert path**: `'2026-04-23T21:42:50.142222'` (naive, no suffix)
  - SQLite stores these as plain TEXT and sorts lexicographically. `+00:00` termination makes the string longer. At microsecond precision the `+` character (ASCII 43) comes before any digit, so aware-format strings sort as **LESS THAN** naive-format strings of equal wall-clock time. `MAX(created_at)` over a mixed table can return a stale naive-format timestamp even when newer aware-format rows exist.

- **Impact:** `get_alerts_pipeline_health()` query 1 (`SELECT MAX(created_at) FROM alerts WHERE deprecated=0`) may return a value that is **not the most recent alert**. Watchdog `last_alert_at` is wrong. If the live DB contains both backfill (naive) and LIVE (aware) rows, `MAX()` will prefer naive rows, making the system look "newer" than it is when backfill ran recently and LIVE rows are from +00:00-format (and vice versa).

- **Recommended fix:** Standardize all writes to `alerts.created_at` on **NAIVE T-format** `datetime.utcnow().isoformat()` (already used in `operations.py:298`). Remove `timezone.utc` from `notifier.py:58,116`. Also fix `backfill_alerts.py:156`: use `ts.replace(tzinfo=None).isoformat()`.

---

### [MAJOR-NEW-02] — T-vs-space datetime format bug is WIDER than the flagged helper — affects `find_open_alert` dedup window

- **File:line:**
  - `backend/db/operations.py:194` — `AND timestamp >= datetime('now', ?)` in `find_open_alert()`

- **Problem:** `alerts.timestamp` is stored with Python `isoformat()` T-separator (e.g., `'2026-04-23T14:39:00'`). SQLite `datetime('now', '-6 hours')` returns space-separated format (e.g., `'2026-04-23 15:41:00'`). Since `'T'` (ASCII 84) > `' '` (ASCII 32), any T-format timestamp shares the SAME CALENDAR DATE PREFIX as the cutoff, and the T-position character wins the comparison — making ALL same-day T-format timestamps appear **greater than** the space-format cutoff regardless of the actual time portion.

  Verified empirically: `'2026-04-23T14:39:00' > '2026-04-23 15:41:00'` returns `True` even though the T-format timestamp is 62 minutes EARLIER.

- **Impact:** The 6-hour dedup window in `find_open_alert` is **up to 24 hours wider than intended** for all same-day items. An alert from the morning of the same calendar day as "6 hours ago" will be found and will **suppress a new LIVE alert that should fire**. This is operationally the inverse of the silent-failure problem: silent failures stay silent because stale open alerts are found in the dedup window. This bug predates Phase 10 but Phase 10 does not address it.

- **Recommended fix:** Store `alerts.timestamp` using space-format: `datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')`. Or apply `strftime('%Y-%m-%d %H:%M:%f', timestamp)` normalization on the query side. Consistent fix: standardize ALL writes and ALL comparisons to space-format.

---

### [MINOR-NEW-01] — `idx_alerts_deprecated` exists only on migrated DBs, not on fresh `init_db()` — `get_alerts_pipeline_health()` comment is misleading

- **File:line:**
  - `backend/db/models.py:368-379` — `SQL_CREATE_INDEXES` list (no `idx_alerts_deprecated`)
  - `backend/db/operations.py:342` — comment: `"Uses idx_alerts_deprecated (Phase 09 migration 002)"`
  - `scripts/migrations/002_add_alert_deprecation.sql:91` — index created only during migration 002

- **Problem:** `SQL_CREATE_INDEXES` (used by `init_db()`) does **not** include `CREATE INDEX IF NOT EXISTS idx_alerts_deprecated ON alerts(deprecated)`. This index was created by migration 002 and exists only on DBs that have run through the migration path. Any freshly initialized DB (CI, dev reset, staging clone) will lack this index. Similarly, there is **no index on `alerts(created_at)`** in `SQL_CREATE_INDEXES`, yet `get_alerts_pipeline_health()` query 2 does `WHERE deprecated=0 AND created_at >= datetime('now', '-1 day')` — without a composite index this is a full table scan.

- **Impact:** Performance regression on fresh DBs at scale. Currently acceptable (comment says 438 rows). Will bite as backfill grows the table. More importantly: the code comment asserting index usage is factually wrong for fresh-init DBs.

- **Recommended fix:** Add `idx_alerts_deprecated` and `idx_alerts_created_at` (or a composite `idx_alerts_deprecated_created_at`) to `SQL_CREATE_INDEXES`. No migration needed — `CREATE INDEX IF NOT EXISTS` is idempotent.

---

### [MINOR-NEW-02] — WAL mode: 3 sequential autocommit SELECTs in `get_alerts_pipeline_health()` can see different snapshots — false-positive P0 possible

- **File:line:**
  - `backend/db/operations.py:344-362` — three `conn.execute().fetchone()` calls with no explicit `BEGIN DEFERRED`

- **Problem:** Python `sqlite3` with default `isolation_level=''` does **not** implicitly begin a read transaction for SELECT statements. Each SELECT is autocommit. In WAL mode, each autocommit SELECT starts its own read snapshot. If the scheduler inserts a `pipeline_runs` row between query 2 (alerts count) and query 3 (pipeline_runs count), the counts come from different database states: `alerts_last_24h=0` (old snapshot) and `pipeline_runs_last_24h=1` (new snapshot). The watchdog would fire a spurious P0 meta-alert.

- **Impact:** Under concurrent scheduler + watchdog, one false P0 per cycle is possible. Bounded: next cycle sees consistent state and does not re-fire. Severity low under current load (1 watchdog cycle every N minutes vs scheduler cycle every 2 hours). Would become more frequent if watchdog interval is reduced.

- **Recommended fix:** Wrap the three SELECTs in an explicit `conn.execute("BEGIN DEFERRED")` / `conn.execute("COMMIT")` block, or add a `BEGIN DEFERRED` at the start of the `with get_db() as conn:` block for read-only access. In WAL mode, `BEGIN DEFERRED` acquires a shared read lock and provides a consistent snapshot for all reads within it.

---

### [MINOR-NEW-03] — `apply_migration_003.py` does not set `PRAGMA busy_timeout` on its migration connection — can fail with `SQLITE_BUSY` if scheduler is writing

- **File:line:**
  - `scripts/apply_migration_003.py:256-263` — `_apply_migration()` opens a vanilla `sqlite3.connect(str(db_path))` with no PRAGMAs

- **Problem:** `database.py:48` sets `PRAGMA busy_timeout=5000` on the runtime connection. The migration driver opens its own separate connection without any `busy_timeout` setting (default is 0 = fail immediately). If the scheduler is mid-write when `ALTER TABLE` executes, the migration will get `OperationalError: database is locked` and fall to the restore path. The `_check_lsof` guard partially mitigates this but has a TOCTOU window between `lsof` returning clean and `executescript` acquiring the write lock.

- **Impact:** Migration can fail on a live DB even when the scheduler is doing routine work. Exit code 2 triggers auto-restore — no data loss — but the operator must re-run the migration.

- **Recommended fix:** Add `conn.execute("PRAGMA busy_timeout=5000")` at the top of `_apply_migration()` before `executescript`.

---

### [INFO-NEW-01] — `alerts_written_count=1` in scheduler is set on `alert_triggered`, not on verified DB write — semantic mismatch with watchdog's intent

- **File:line:**
  - `backend/scheduler/scheduler.py:68` — `alerts_written = 1 if result.get("alert_triggered") else 0`
  - `backend/agents/notifier.py:88-113` — dedup UPDATE path returns `True` without inserting a new row

- **Problem:** The scheduler sets `alerts_written_count=1` when `alert_triggered=True`, but the actual write behavior depends on the notifier's dedup path:
  - If dedup fires (existing open alert found): `_save_to_db()` does an `UPDATE`, returns `True`, no new row inserted into `alerts`.
  - `alerts_written_count=1` is recorded in `pipeline_runs` even though `alerts_last_24h` count stays flat.
  
  The watchdog detects silence by `pipeline_runs_last_24h > 0 AND alerts_last_24h == 0`. If the system is healthy but all runs hit dedup (same channel+rule open alert persisting for >24h), `pipeline_runs_last_24h > 0` and `alerts_last_24h = 0` → P0 fires falsely.

  Note: `backfill_alerts.py:274-275` correctly tracks ACTUAL writes (`alert_written = True` only after `create_alert()` succeeds). The scheduler path is inconsistent with backfill.

- **Impact:** Extended dedup periods (likely during the intended use case of multi-day campaigns) will cause the watchdog to fire false P0 meta-alerts continuously. This was acknowledged as MINOR-02 but is more severe: it fires whenever a real alert persists longer than 24h across a mode where pipeline_runs keep accumulating.

- **Recommended fix:** `alerts_written_count` semantics should be redefined as "net new alert rows written". When dedup fires UPDATE, set `alerts_written_count=0` (no new row). When new INSERT, set `=1`. Requires notifier to return the actual write type (new insert vs dedup update) back to caller.

---

## Confirmation / Expansion of Known Issues

### MAJOR-01 (BACKTEST contamination in `pipeline_runs_last_24h`) — CONFIRMED AND DEEPER

The query at `operations.py:358-361` has no `WHERE mode='LIVE'` filter. Independently confirmed: `backfill_alerts.py:286` calls `record_pipeline_run(..., "BACKTEST", ...)` which writes rows with `mode='BACKTEST'` into `pipeline_runs`. A backfill run of the full 2026-01-23 → 2026-03-23 range (60 days × 8 channels × 3 triggers = 1,440 tuples) would write 1,440 BACKTEST rows into `pipeline_runs`, all with `created_at=datetime.utcnow()`. If this backfill runs within 24h of the watchdog cycle, `pipeline_runs_last_24h=1440` while `alerts_last_24h` counts only non-deprecated LIVE alerts written to the alerts table (which for LIVE mode may be 0 if system is in silent failure). The watchdog fires correctly here — but for the WRONG reason.

More critically: the watchdog is designed to detect LIVE pipeline silence. Including BACKTEST runs means the watchdog **never detects silence during a backfill run**. If the LIVE scheduler breaks while a backfill is running, `pipeline_runs_last_24h > 0` (backfill rows) but may seem "healthy" when it isn't.

Recommended fix: Add `AND mode = 'LIVE'` to query 3 in `get_alerts_pipeline_health()`.

### MAJOR-03 (T vs space datetime format in `get_alerts_pipeline_health()`) — CONFIRMED AND EXPANDED

Independent verification confirms the bug. SQLite lexicographic comparison: `'T'` (ASCII 84) > `' '` (ASCII 32). All timestamps stored with Python `isoformat()` T-separator are lexicographically GREATER than any same-date space-format SQLite cutoff. Effect:

- Any row stored on the **same calendar day** as the 24h cutoff date is ALWAYS included regardless of its time portion.
- Magnitude: up to 24h of false inclusions. Example: cutoff is `'2026-04-22 21:41:00'`; item is `'2026-04-22T05:00:00'` (40h old). String comparison: `'2026-04-22T' > '2026-04-22 '` → True → item is included.
- This affects BOTH `alerts_last_24h` (query 2, `operations.py:351-355`) AND `pipeline_runs_last_24h` (query 3, `operations.py:358-362`).
- Effect on watchdog: counts are INFLATED. A system that has been silent for >24h but had activity in the last 48h may show nonzero counts → watchdog DOES NOT FIRE → silent failure goes undetected. This is the exact opposite of the intended behavior.

This is **worse than reported**. The inflation means the watchdog gives false ALL-CLEAR during the specific failure mode it's designed to catch.

---

## Things That Are Solid

- **`CHECK(alerts_written_count >= 0)` enforcement** (`backend/db/models.py:272`, `scripts/migrations/003_add_alerts_written_count.sql:61`): SQLite enforces CHECK constraints by default. Verified empirically. No PRAGMA needed.

- **CHECK clause byte-identity between migration 003 and `models.py`** (`scripts/apply_migration_003.py:294-321`): `'alerts_written_count INTEGER NOT NULL DEFAULT 0 CHECK(alerts_written_count >= 0)'` is byte-identical in both sources. Verified by string comparison.

- **`PRAGMA foreign_keys=OFF` placement** in migration 003 (`scripts/migrations/003_add_alerts_written_count.sql:28`): Correctly placed BEFORE `BEGIN TRANSACTION`. Comment is accurate re: SQLite constraint that PRAGMA is a no-op inside a transaction.

- **Idempotency guard ordering** in migration 003: Ledger `INSERT` (line 49) comes BEFORE `ALTER TABLE` (line 61) within the transaction. A duplicate-run UNIQUE constraint failure rolls back BEFORE the DDL. Correct.

- **`_already_applied()` partial-state detection** (`scripts/apply_migration_003.py:153-158`): Correctly detects both partial states (col present, ledger missing; or ledger present, col missing) and raises `RuntimeError` instead of silently proceeding. Solid defensive coding.

- **`ALTER TABLE ADD COLUMN NOT NULL DEFAULT 0` on SQLite 3.35+** (`scripts/migrations/003_add_alerts_written_count.sql:61`): Verified on SQLite 3.51.3 — existing rows correctly receive `alerts_written_count=0` via DEFAULT propagation at ALTER time. No post-hoc UPDATE needed.

- **`ALTER TABLE DROP COLUMN` for rollback** (`scripts/migrations/003_rollback.sql:16`): Works on SQLite 3.51.3 even with CHECK constraint on the column. Data preserved.

- **`pipeline_runs.created_at NOT NULL`** (`backend/db/models.py:271`): Column is declared NOT NULL. No NULL-handling edge case.

- **Empty table `MAX()` edge case** (`backend/db/operations.py:347`): `MAX()` on an empty table returns `(None,)` not `None`. The check `if row is not None else None` is evaluated: `row = (None,)` → `row is not None` → `row[0] = None` → `last_alert_at = None`. Correct behavior.

- **`record_pipeline_run` in backfill** (`scripts/backfill_alerts.py:269-291`): Correctly passes `mode="BACKTEST"` and accurately sets `alerts_written_count=1` only AFTER `create_alert()` succeeds. More correct than the scheduler path.

- **SQLite WAL mode active** (`backend/db/database.py:47`): `PRAGMA journal_mode=WAL` + `PRAGMA busy_timeout=5000` on runtime connections. Correct for concurrent readers + single writer pattern.

- **Thread-local connection pattern** (`backend/db/database.py:28,41-51`): `threading.local()` isolates connections per thread. `check_same_thread=False` is set correctly (thread-local provides the isolation, not sqlite3's internal check).

- **`get_alerts_pipeline_health()` empty-table safety** (`backend/db/operations.py:344-362`): All three rows use `int(row[0]) if row and row[0] is not None else 0`. Handles both NULL aggregate result and missing row.

- **Rollback file completeness**: `003_rollback.sql` drops both the column AND the ledger row. Correct symmetry with the apply script.

---

## Priority Fix Ordering

1. **MAJOR-03 (T-vs-space, inflated window counts)** — Fix ALL write paths to store timestamps in `'%Y-%m-%d %H:%M:%S'` space format (matching SQLite `datetime('now')` output). Affects `operations.py:298`, `models.py:114-115` (via `isoformat()`). Or normalize queries with `strftime('%Y-%m-%d %H:%M:%S', created_at)`. Without this fix the watchdog gives false ALL-CLEAR during silent failures — it is broken in the exact scenario it's meant to catch.

2. **MAJOR-01 (BACKTEST contamination)** — Add `AND mode = 'LIVE'` to `pipeline_runs` query in `get_alerts_pipeline_health()` (`operations.py:358`). Without this, a concurrent backfill masks LIVE pipeline silence.

3. **MAJOR-NEW-01 (Mixed aware/naive format in `alerts.created_at`)** — Standardize `notifier.py:58,116` and `backfill_alerts.py:156` to use naive `datetime.utcnow().isoformat()`. Mixed formats corrupt `MAX(created_at)` ordering.

4. **MAJOR-NEW-02 (T-vs-space in `find_open_alert` dedup window)** — Widen fix from item 1 to cover `alerts.timestamp` writes as well. Dedup window is up to 24h wider than intended, suppressing legitimate LIVE alerts.

5. **INFO-NEW-01 (Dedup UPDATE not counted as write)** — Redefine `alerts_written_count` semantics to track actual new `INSERT` vs dedup `UPDATE`. Without this, the watchdog fires false P0 whenever an alert persists >24h.

6. **MINOR-NEW-02 (WAL snapshot isolation, 3 SELECTs)** — Wrap `get_alerts_pipeline_health()` in `BEGIN DEFERRED` / `COMMIT` to ensure all 3 queries see the same snapshot.

7. **MINOR-NEW-01 (Missing indexes in `SQL_CREATE_INDEXES`)** — Add `idx_alerts_deprecated` and `idx_alerts_created_at` to `SQL_CREATE_INDEXES` so fresh `init_db()` DBs get the same indexes as migrated ones.

8. **MINOR-NEW-03 (No `busy_timeout` in migration connection)** — Add `PRAGMA busy_timeout=5000` to `_apply_migration()` in `apply_migration_003.py`.
