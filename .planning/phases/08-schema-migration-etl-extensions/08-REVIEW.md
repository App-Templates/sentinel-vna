---
phase: 08-schema-migration-etl-extensions
reviewed: 2026-04-23T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - backend/db/database.py
  - backend/db/models.py
  - config/sell_type_proxy.yaml
  - scripts/apply_migration_001.py
  - scripts/etl_csv_to_parquet.py
  - scripts/migrations/001_expand_channel_groups.sql
  - scripts/test_etl_schema_v2.py
  - scripts/test_migration_001.py
  - scripts/test_migration_001_apply.py
  - scripts/test_models_sync.py
  - scripts/test_mondadori_fill_rate_regression.py
findings:
  critical: 1
  warning: 8
  info: 7
  total: 16
status: issues_found
---

# Phase 08: Code Review Report

**Reviewed:** 2026-04-23T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 08 delivered the SCHEMA-01 CHECK-expansion migration (channel_group 2->8, alert_rule 4->8 skipping A4), tightened `pending_notifications` CHECKs, and extended the ETL to preserve `measurable_impressions` (SCHEMA-03) and derive `sell_type_proxy` from `channel_group` (SCHEMA-04). The TDD pyramid (tempfile migration validation, models sync detector, live-DB smoke tests, fill-rate regression) is thorough and traceable.

Strengths:
- Strong drift-prevention: byte-identical CHECK assertions across models.py, migration, and live DB.
- Migration apply driver follows the R-04 chirurgico pattern: lsof gate, pre-apply backup, row-count snapshot, auto-restore on failure, three distinct exit codes.
- Row-copy preserves data. Ledger-based idempotency guard forces a clear UNIQUE-constraint failure on naked double-apply.
- R-13 memory discipline respected in tests (pyarrow projection, column filters, narrow slice materialized).

Key concerns:
- **One Critical:** the runtime auto-migration in `backend/db/database.py` (`_migrate_alerts_schema_v2` / `_migrate_pending_notifications_schema_v2`) uses `INSERT INTO alerts SELECT * FROM _alerts_old_v2` without an explicit column list, which silently corrupts data if the column set or order ever changes (exactly the failure mode Phase 07 was chasing). Additionally, these paths run `PRAGMA foreign_keys=OFF` then execute DDL inside the `get_db()` context transaction on a separate connection (`init_db` opens its own), but from a caller pattern the rename+insert+drop has no explicit BEGIN/COMMIT wrapping — on partial failure the table could be renamed with no replacement, leaving the DB unrecoverable without the Plan 03 `.bak`.
- Several Warnings in the ETL around memory (a hardcoded "fits in memory" comment for a 6.2M row CSV with no chunking), an error-silencing `fillna(0)` on `measurable_impressions` that conflates "missing upstream column" with "zero", and a class-level `setUpClass` that materializes a side-effect (writing a report file) inside a test case.
- The YAML "duplicate channel" guard in `load_sell_type_proxy_mapping()` can be bypassed by a future GOOGLE legacy-alias collision because GOOGLE already appears under `Open_Market` — any addition to a second group will trip the guard correctly, but the existing `_meta` skip uses a string-prefix heuristic that would break if someone added a non-underscore top-level metadata key.

The migration SQL itself is solid: explicit pragma handling around the transaction, documented rollback path, intentional UNIQUE-constraint idempotency guard.

## Critical Issues

### CR-01: Unsafe `INSERT ... SELECT *` in runtime migration invites a Phase-07-class silent failure

**File:** `backend/db/database.py:103` (also `_migrate_pending_notifications_schema_v2` uses an explicit column list — good — so the bug is limited to the alerts variant)

**Issue:** `_migrate_alerts_schema_v2` performs:

```python
conn.execute("ALTER TABLE alerts RENAME TO _alerts_old_v2;")
conn.execute(SQL_CREATE_ALERTS)
conn.execute("INSERT INTO alerts SELECT * FROM _alerts_old_v2;")
conn.execute("DROP TABLE _alerts_old_v2;")
```

Three distinct risks:

1. **Positional column copy.** `SELECT *` is positional. Today `SQL_CREATE_ALERTS` and the stale schema have identical column lists in identical order, so this works. The moment anyone adds a column to `SQL_CREATE_ALERTS` (e.g. a future `publisher_id` or `revenue_share_applied` column) and the stale table does not have it, the insert either fails loudly (if row width differs) or — worse — silently inserts into the wrong column if column widths happen to match. This is the exact silent-failure pattern Phase 07 caught after two months. Migration 001 SQL has the same `INSERT INTO alerts SELECT * FROM _alerts_old_001;` pattern, but that is bounded to the known 2026-04-23 stale schema. The runtime path in `database.py` is unbounded — it fires on any DB that doesn't match the Phase 08 probes, for all future schema versions, not just the v1 -> v2 transition.

2. **No explicit transaction, no backup.** Unlike `apply_migration_001.py`, this helper does NOT wrap the rename/create/insert/drop in `BEGIN TRANSACTION ... COMMIT`. If the Python process is killed between the RENAME and the INSERT (e.g. SIGKILL, OOM, power loss on the CI runner), the DB is left with `_alerts_old_v2` present and no `alerts` table. `init_db()` is re-entrant but `SQL_CREATE_ALERTS` uses `CREATE TABLE IF NOT EXISTS` — a partial crash would leave the DB with an empty `alerts` (silent data loss of every pre-migration row) plus a dangling `_alerts_old_v2`. No `.bak` is made on this path.

3. **`PRAGMA foreign_keys` toggled outside a transaction on an auto-committing connection.** Line 100-105 issues `PRAGMA foreign_keys=OFF`, performs DDL, then `PRAGMA foreign_keys=ON`. The `init_db` caller (line 154-175) opens its own non-default connection with no `isolation_level` override, so sqlite3 runs each `execute` in implicit transaction mode — which means the first DDL will auto-BEGIN and the pragma change will silently not take effect for the duration of the auto-transaction (per SQLite docs, `PRAGMA foreign_keys` is a no-op inside a transaction). The migration 001 SQL file got this right by documenting it and placing the pragma outside `BEGIN`. The Python helper got it wrong.

**Impact:** A fresh-DB or dev-reset scenario (init_db on a 2-value stale DB) runs this code path. If the helper ever ships with a real schema column change, data loss is likely and silent.

**Fix:**

```python
def _migrate_alerts_schema_v2(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='alerts'"
    ).fetchone()
    if row is None:
        return
    create_sql = row[0] or ""
    channel_group_ok = "'GOOGLE_ADEX'" in create_sql and "'HEADER_BIDDING_MAGNITE'" in create_sql
    alert_rule_ok = "'A8'" in create_sql and "'A4'" not in create_sql
    if channel_group_ok and alert_rule_ok:
        return

    # Explicit column list — positional SELECT * is the Phase-07-class silent-failure pattern.
    ALERTS_COLUMNS = (
        "alert_id, timestamp, severity, channel_group, status, alert_rule, "
        "revenue_current, revenue_baseline, revenue_delta_pct, triage_label, "
        "contributors_json, geo_breakdown_json, environment_split_json, "
        "insights_json, execution_time_sec, data_source, config_version, "
        "created_at, updated_at"
    )

    # PRAGMA foreign_keys must be OUTSIDE any implicit transaction.
    # Commit any pending work first, then toggle the pragma.
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF;")
    try:
        conn.execute("BEGIN IMMEDIATE;")
        conn.execute("ALTER TABLE alerts RENAME TO _alerts_old_v2;")
        conn.execute(SQL_CREATE_ALERTS)
        conn.execute(
            f"INSERT INTO alerts({ALERTS_COLUMNS}) SELECT {ALERTS_COLUMNS} FROM _alerts_old_v2;"
        )
        conn.execute("DROP TABLE _alerts_old_v2;")
        conn.execute("COMMIT;")
    except Exception:
        conn.execute("ROLLBACK;")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys=ON;")
```

Equivalent treatment belongs on `_migrate_pending_notifications_schema_v2` (which already has an explicit column list — good — but still lacks the explicit BEGIN/COMMIT wrap).

## Warnings

### WR-01: ETL comment claims 6.2M-row CSV "fits in memory" — contradicts R-13

**File:** `scripts/etl_csv_to_parquet.py:165`

**Issue:** The docstring for `process_daily` says:

```python
# Load adrequests fully (6.2M rows, narrow — fits in memory)
ar = pd.read_csv(
    os.path.join(DATA_DIR, "daily_adrequests.csv"),
    dtype={"ad_unit_id_1": str, "country_criteria_id": str, "environment": str},
)
```

Phase 08 explicitly flags R-13 as "no `pd.read_csv` loads of the 1.3GB `daily_kpi.csv`". `daily_adrequests.csv` is named as 6.2M rows with no size stated — but the comment "fits in memory" is a correctness-by-vibes claim. Running on a low-memory CI container or developer laptop will fail with MemoryError for a large enough CSV. Additionally, the `.isin(top50)` filter is applied AFTER load, so peak memory is the full file, not the filtered slice.

**Fix:** Either load in chunks and filter in the chunk loop (same pattern as `find_top50_publishers`), or add a pre-flight assertion on file size and document the acceptable memory envelope:

```python
# Chunked load + filter — avoids loading the whole file when only top50 rows survive.
ar_chunks = []
reader = pd.read_csv(
    os.path.join(DATA_DIR, "daily_adrequests.csv"),
    dtype={"ad_unit_id_1": str, "country_criteria_id": str, "environment": str},
    chunksize=500_000,
)
for chunk in reader:
    ar_chunks.append(chunk[chunk["ad_unit_id_1"].isin(top50)])
ar = pd.concat(ar_chunks, ignore_index=True)
ar = ar.drop(columns=["row_id"], errors="ignore")
ar["ad_requests"] = pd.to_numeric(ar["ad_requests"], errors="coerce")
```

The same comment-by-faith pattern appears at line 258 for `hour_adrequests.csv` (491K rows — probably fine) and line 261 for `hour_kpi.csv` (460K rows — probably fine). Document explicit row/size bounds rather than "fits in memory".

### WR-02: `fillna(0)` on `measurable_impressions` masks upstream column loss

**File:** `scripts/etl_csv_to_parquet.py:192-193, 273-274`

**Issue:**

```python
for col in ["revenue_gross", "impressions", "measurable_impressions",
            "viewable_impressions", "clicks"]:
    chunk[col] = pd.to_numeric(chunk[col], errors="coerce").fillna(0)
```

If `daily_kpi.csv` ever omits `measurable_impressions` (upstream pipeline regression, CSV export bug), this code will raise `KeyError` at the subscript — which is the correct failure. But if the column exists with all-null or all-string values, `pd.to_numeric(..., errors="coerce").fillna(0)` will silently produce a zero column. The fill-rate regression test (`test_mondadori_fill_rate_regression.py`) catches the all-zero case for Mondadori Feb 2026, but the ETL itself should refuse to emit a parquet where a critical numeric column is >99% zero — that's what Phase 08 SCHEMA-03 exists to prevent.

**Fix:** After the coercion loop, assert a minimum non-zero fraction for `measurable_impressions` (production regression guard, not just test-time):

```python
non_zero_frac = (chunk["measurable_impressions"] > 0).mean()
if non_zero_frac < 0.01:  # <1% non-zero is almost certainly a regression
    raise RuntimeError(
        f"measurable_impressions non-zero fraction {non_zero_frac:.4f} in chunk {i} — "
        "upstream column likely missing or all-null; refusing to write parquet with zero-filled column"
    )
```

### WR-03: `setUpClass` performs I/O (SHA256 of 200MB+ parquet) on every test invocation

**File:** `scripts/test_mondadori_fill_rate_regression.py:131-156, 402`

**Issue:** `_sha256(DAILY)` in `test_writes_fill_rate_report` hashes the full parquet (docstring says "chunked — works for 200MB+ parquets"). This is O(parquet size) I/O per test run. If the test suite is ever run in a loop or as part of a pre-commit hook, each invocation re-hashes the 200MB+ file. Also, `setUpClass` reads the filtered slice eagerly — fine for a single test class, but if someone ever adds a `skipIf` that would skip most tests, the expensive load still happens.

More importantly, `test_writes_fill_rate_report` is a **test with a side effect** — it writes a markdown file to the phase directory. Tests that produce artifacts should either be separate scripts or use `addCleanup` / `tempfile`. Naming it `test_*` means a pytest run in CI will overwrite the report.

**Fix:** Separate the report generation from the test assertion:

```python
# Keep test_writes_fill_rate_report as pure assertion of the report contract (file can be written).
# Move the actual report write into a module-level main() path, not a test body.
def _write_report() -> None:
    ...

def main():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestMondadoriFillRate)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        _write_report()   # only after test pass
    ...
```

### WR-04: `_cleanup_synthetic_rows` uses string-interpolation in SQL (low-grade SQLi, also a clean-code smell)

**File:** `scripts/test_migration_001_apply.py:107, 238, 399`

**Issue:**

```python
conn.execute(f"DELETE FROM alerts WHERE data_source='{TEST_DATA_SOURCE}'")
```

`TEST_DATA_SOURCE` is a module constant ("phase08-test") — so there is no runtime injection risk today. However, this is a test file that will be copied as a template for future Phase 09+ tests. Once someone parameterizes `TEST_DATA_SOURCE` from an env var or CLI arg, the f-string becomes a real injection hole. The precedent of using string interpolation in SQL is exactly what R-13/R-10-adjacent rules warn against.

**Fix:** Always use parameter binding:

```python
conn.execute("DELETE FROM alerts WHERE data_source = ?", (TEST_DATA_SOURCE,))
```

Three occurrences at lines 107, 238, and 399 all need the same treatment.

### WR-05: `_check_lsof` allows a TOCTOU window; also emits a WARNING-instead-of-FAIL on macOS without lsof

**File:** `scripts/apply_migration_001.py:68-83`

**Issue:** Two issues here:

1. **TOCTOU:** `lsof` runs, the driver moves on to `_backup`, then `_apply_migration`. Between `_check_lsof` returning and `sqlite3.connect` opening the DB, another process can acquire the DB. SQLite's own locking handles this correctly at the file-lock level, but the driver will NOT know — it will race and the "already applied" probe may be stale by the time the apply starts.
2. **Soft-fail on missing lsof:** If `lsof` is absent (common on stripped Docker images, Alpine-based CI, Windows-WSL), the driver prints a WARNING and proceeds. On a shared staging DB this is dangerous — the whole point of the check is to prevent concurrent access. A stripped container is exactly when concurrent access is most likely (no human is watching).

**Fix:** Combine the lsof check with a file-lock that the driver holds for the duration of the apply:

```python
def _acquire_db_lock(db_path: Path):
    """Open the DB in exclusive mode as a poor-man's lock. Return connection."""
    import fcntl
    lock_path = db_path.with_suffix(db_path.suffix + ".apply.lock")
    fd = open(lock_path, "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        _log(f"ABORT: another migration apply is in progress (lock: {lock_path})")
        sys.exit(1)
    return fd  # caller keeps fd alive for the duration of the apply

# Remove the "WARNING: lsof not available; skipping" soft-fail — instead REQUIRE the flock.
```

At minimum, if `lsof` is absent the driver should **fail closed** on any DB that is not `data/vna_alerts.db` (the live production path) — printing a WARNING on a staging DB and proceeding is the same anti-pattern as `// TODO: handle this later`.

### WR-06: `_backup` / `_restore` use `shutil.copy2` on a WAL-mode SQLite DB without first checkpointing

**File:** `scripts/apply_migration_001.py:139-152`

**Issue:** `backend/db/database.py:47` enables `PRAGMA journal_mode=WAL`. A WAL-mode SQLite DB has **three files**: `foo.db`, `foo.db-wal`, `foo.db-shm`. `shutil.copy2(src, dst)` copies only the main file. If the live DB has uncommitted/uncheckpointed pages in `vna_alerts.db-wal` at the moment the backup is taken, the `.bak` will be missing those pages — the backup is **not a recoverable snapshot**.

Restoring from this `.bak` on a post-apply verification failure (exit code 3 path at line 285) could silently lose the most recent writes that existed at backup time.

`lsof` check at line 68 mitigates this by aborting if any process holds the DB, BUT:
- `lsof` has false-negatives (e.g. a reader with `O_RDONLY` on some platforms).
- `lsof` soft-fails (WR-05).
- Even after lsof passes, WAL pages can exist from a previous writer that crashed before checkpoint.

**Fix:** Before `shutil.copy2`, open the DB and checkpoint explicitly:

```python
def _backup(src: Path, dst: Path) -> None:
    # Checkpoint WAL into the main DB file first so .bak is complete.
    _conn = sqlite3.connect(str(src))
    try:
        _conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
    finally:
        _conn.close()

    if dst.exists():
        _log(f"Overwriting existing backup: {dst}")
    shutil.copy2(src, dst)
    # Also copy -wal and -shm if they exist (belt-and-suspenders).
    for suffix in ("-wal", "-shm"):
        ext_src = src.with_name(src.name + suffix)
        ext_dst = dst.with_name(dst.name + suffix)
        if ext_src.exists():
            shutil.copy2(ext_src, ext_dst)
    ...
```

Alternative: use `sqlite3`'s `.backup()` API which handles WAL correctly:

```python
def _backup(src: Path, dst: Path) -> None:
    src_conn = sqlite3.connect(str(src))
    dst_conn = sqlite3.connect(str(dst))
    try:
        src_conn.backup(dst_conn)
    finally:
        src_conn.close()
        dst_conn.close()
```

This is the SQLite-recommended pattern for online backups.

### WR-07: `init_db` swallows migration exceptions behind a `try/finally` that only closes the connection

**File:** `backend/db/database.py:157-175`

**Issue:**

```python
try:
    _migrate_alerts_schema_v2(conn)
    _migrate_pending_notifications_schema_v2(conn)
    conn.execute(SQL_CREATE_ALERTS)
    ...
    conn.commit()
    logger.info("Database initialized at %s", resolved)
finally:
    conn.close()
```

If `_migrate_alerts_schema_v2` raises partway through (e.g. the INSERT SELECT fails because column widths drift per CR-01), the `finally: conn.close()` closes the connection, but:
1. No rollback is issued — any uncommitted DDL is implicit-committed by SQLite on connection close? (Actually, SQLite auto-rolls back uncommitted transactions on close, so this is OK for the rollback, but...)
2. The exception propagates. That's actually correct behavior. But there is no logging of *what failed*, no `.bak` created, and the caller of `init_db()` (likely an API startup path) sees a raw exception with no context.

Compare to `apply_migration_001.py`, which has explicit try/except around `_apply_migration` that restores from `.bak`. `init_db` has nothing equivalent.

**Fix:** Add explicit exception handling + logging around the migration calls in `init_db`:

```python
try:
    try:
        _migrate_alerts_schema_v2(conn)
        _migrate_pending_notifications_schema_v2(conn)
    except Exception as e:
        logger.exception(
            "Phase 08 runtime migration FAILED at %s. DB may be in partial state. "
            "Consider restoring from data/vna_alerts.db.pre-phase08.bak if this is prod.",
            resolved,
        )
        raise
    conn.execute(SQL_CREATE_ALERTS)
    ...
```

### WR-08: `_ALERT_ID_COUNTER` is a module-level mutable list — hidden global state that breaks test isolation

**File:** `scripts/test_migration_001_apply.py:45, 48-56`

**Issue:**

```python
_ALERT_ID_COUNTER = [0]

def _make_alert_id(suffix: str = "") -> str:
    _ALERT_ID_COUNTER[0] += 1
    seq = _ALERT_ID_COUNTER[0]
    ...
```

The counter is never reset. If the test class is run twice in the same process (e.g. `unittest.TestLoader` discovery picks it up via a second entry-point), the second run continues from the previous counter state — which is fine for uniqueness but means alert_ids are not deterministic across runs. Worse, the `suffix: str = ""` parameter is unused — dead argument.

The `_cleanup_synthetic_rows` DELETE at line 109 uses `LIKE 'ALT-20260423-%'` which correctly scopes to this test's fixed date, so cross-run pollution is bounded. But the dead parameter signals the function was copy-pasted from somewhere with richer semantics and never cleaned up.

**Fix:** Remove the unused `suffix` parameter. Add an explicit reset in `setUp`:

```python
def _make_alert_id() -> str:
    _ALERT_ID_COUNTER[0] += 1
    ...

class TestMigration001Apply(unittest.TestCase):
    def setUp(self) -> None:
        _ALERT_ID_COUNTER[0] = 0  # reset so each test's IDs are deterministic
        ...
```

## Info

### IN-01: `load_sell_type_proxy_mapping` uses brittle `_` prefix to skip metadata

**File:** `scripts/etl_csv_to_parquet.py:44-46`

**Issue:**

```python
for group_name, channels in cfg.items():
    if group_name.startswith("_"):
        continue  # skip _meta block
    for channel in channels:
        ...
```

If someone adds a future top-level metadata key without the underscore convention (`metadata:`, `version:`, `notes:`), the loop will attempt to iterate over it as a list of channels and raise a confusing `TypeError`. The YAML already has a dedicated `_meta:` key — the loader should use an explicit allowlist or inspect whether the value is a list.

**Fix:**

```python
for group_name, channels in cfg.items():
    if group_name.startswith("_"):
        continue
    if not isinstance(channels, list):
        raise ValueError(
            f"sell_type_proxy.yaml: top-level key {group_name!r} must be a list of "
            f"channel_group values; got {type(channels).__name__}"
        )
    for channel in channels:
        ...
```

Same pattern in `scripts/test_etl_schema_v2.py:50-54` (`setUpClass`).

### IN-02: Test file contains a commented-out Phase 10 URL pointer that will rot

**File:** `config/sell_type_proxy.yaml:6-8`

**Issue:**

```yaml
# Consumed by:
#   - scripts/etl_csv_to_parquet.py (adds derived column to daily/hourly parquet)
#   - [future] backend/api/publisher_routes.py (API-02 sell_type query param, Phase 10.5)
#   - [future] frontend/src/components/PublishersPage.tsx (CORR-11 filter UI, Phase 14)
```

Forward references to Phase 10.5 and Phase 14 inside a v1.3-era config are the kind of documentation that goes stale silently. A grep in 6 months for "Phase 10.5" will return this file as a dangling promise.

**Fix:** Move forward-looking consumer list into the phase's ROADMAP or DECISION.md, keep the config comment factual (what consumes it today).

### IN-03: `generate_alert_id` uses `datetime.utcnow()` which is deprecated in Python 3.12+

**File:** `backend/db/models.py:114, 115, 149, 157, 167, 175, 187, 191`

**Issue:** `datetime.utcnow()` is soft-deprecated in Python 3.12 (`DeprecationWarning` in 3.13). Modern Python uses `datetime.now(timezone.utc)`.

**Fix:** Replace with timezone-aware form:

```python
from datetime import datetime, timezone
created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

Eight call sites to update in `models.py`.

### IN-04: `_normalize_ws` is duplicated across four test files

**File:**
- `scripts/test_migration_001.py:187-189`
- `scripts/test_migration_001_apply.py:363` (inlined as `re.sub(r"\s+", " ", ...).strip()`)
- `scripts/test_models_sync.py:32-33`
- `scripts/apply_migration_001.py:217-218` (inlined)

**Issue:** The same whitespace-normalization helper is redefined four times. If the normalization semantics ever change (e.g. to also collapse SQL comments), all four sites must be updated in lockstep — another drift vector, on top of the byte-identity check drift Phase 08 itself is guarding against.

**Fix:** Factor into a small `scripts/_sql_utils.py` with `normalize_ws(s: str) -> str` and `extract_check(sql: str, col: str) -> str`. Import from all four call sites.

### IN-05: Magic number "50" for top publishers is not a named constant

**File:** `scripts/etl_csv_to_parquet.py:107, 119, 120, 121`

**Issue:** `find_top50_publishers` hardcodes 50 in four places, including a print string. If Phase 10 wants top-N with N=100, every call site must change.

**Fix:**

```python
TOP_N_PUBLISHERS = 50

def find_top_publishers(n: int = TOP_N_PUBLISHERS):
    ...
    top = totals.nlargest(n).index.tolist()
    ...
```

### IN-06: `_check_lsof` TimeoutExpired branch prints but doesn't distinguish from FileNotFoundError

**File:** `scripts/apply_migration_001.py:77-79`

**Issue:**

```python
except subprocess.TimeoutExpired:
    print("WARNING: lsof timed out; skipping concurrency check", file=sys.stderr)
    return
```

A timeout on `lsof` is suspicious — it means the kernel is under load or there's a stuck file handle. "Skipping the check" is the wrong default on a live DB. At minimum, log this at ERROR level (not print), and record it in the apply journal for post-mortem.

**Fix:** Use the project logger (`backend.utils.logger.get_logger`) rather than print, and consider making timeout a hard-fail on the live DB path:

```python
except subprocess.TimeoutExpired:
    if db_path.name == "vna_alerts.db":  # live DB
        _log(f"FATAL: lsof timed out on live DB — refusing to proceed")
        sys.exit(1)
    _log("WARNING: lsof timed out on non-live DB; skipping concurrency check")
    return
```

### IN-07: Test 4 in test_migration_001_apply.py inserts 64 rows in a tight commit-per-row loop

**File:** `scripts/test_migration_001_apply.py:217-229`

**Issue:**

```python
for ch in VALID_CHANNELS:
    for ru in VALID_RULES:
        ...
        _insert_alert(self.conn, row)
        self.conn.commit()   # <-- per-row commit
        inserted_ids.append(aid)
```

On a WAL-mode SQLite DB this is 64 WAL writes + 64 fsyncs. Minor, but the stated intent is "INSERT must succeed for each combo" — committing once at the end (or in a batch of 8) gives the same assertion without the I/O cost. Also, if the test is interrupted mid-loop, the DB has partially-committed synthetic rows that `tearDown` will clean up — but only if `tearDown` actually runs. A single outer transaction with one `commit()` + the existing `tearDown` guarantees cleaner rollback semantics on failure.

**Fix:**

```python
try:
    for ch in VALID_CHANNELS:
        for ru in VALID_RULES:
            aid = _make_alert_id()
            row = _base_row(ch, ru, aid)
            _insert_alert(self.conn, row)
            inserted_ids.append(aid)
    self.conn.commit()
except sqlite3.IntegrityError as e:
    self.fail(f"INSERT failed during batch: {e!r}")
```

---

_Reviewed: 2026-04-23T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
