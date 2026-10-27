#!/usr/bin/env python3
"""
Phase 10 Plan 01 — Migration 003 Apply Driver.

Safely applies scripts/migrations/003_add_alerts_written_count.sql to
data/vna_alerts.db with the following invariants:

1. Pre-apply backup:        data/vna_alerts.db.pre-phase10.bak created
                            via sqlite3.Connection.backup() (WAL-safe)
                            BEFORE any mutation.
2. Concurrency safety:      Aborts if any process holds the DB file
                            (checked via lsof — if lsof is absent, skip
                            the check with a WARNING printed to stderr).
3. Idempotency guard:       Pre-checks sqlite_master.pipeline_runs.sql for
                            column name "alerts_written_count". If present,
                            migration is already applied — exit 0 with SKIP
                            message. Also pre-checks vna_schema_migrations
                            for row ('003_add_alerts_written_count', *).
4. Ledger guard:            Pre-checks vna_schema_migrations table for
                            row ('003_add_alerts_written_count', *). If
                            present, same SKIP behavior. Partial state
                            (cols present but ledger missing, or vice versa)
                            raises a hard error — manual inspection required.
5. Atomic apply:            sqlite3.Connection.executescript inside the
                            single transaction in 003_add_alerts_written_count.sql.
6. Post-apply verification: Re-reads sqlite_master.pipeline_runs.sql. Asserts:
                            - column `alerts_written_count` present
                            - CHECK(alerts_written_count >= 0) clause present
                            - CHECK clause byte-identical to
                              SQL_CREATE_PIPELINE_RUNS in models.py
                            - Ledger row ('003_add_alerts_written_count', *)
                              exists.
7. Row-count preservation:  Snapshots row counts before apply and asserts
                            equality after apply (no data loss).
8. DEFAULT propagation:     Asserts all pre-existing pipeline_runs rows have
                            alerts_written_count=0 post-apply (SQLite 3.35+
                            NOT NULL DEFAULT constant propagates to existing
                            rows at ALTER).
9. Exit codes:
   0 = success (applied) OR skip (already applied)
   1 = precondition failure (no DB, concurrent handle, etc.)
   2 = apply failure (automatically restored from .bak)
   3 = post-apply verification failure (automatically restored from .bak)

Run:  .venv/bin/python scripts/apply_migration_003.py [--dry-run]
"""

import argparse
import fcntl
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "vna_alerts.db"
BAK_PATH = REPO_ROOT / "data" / "vna_alerts.db.pre-phase10.bak"
MIGRATION_SQL = REPO_ROOT / "scripts" / "migrations" / "003_add_alerts_written_count.sql"
MODELS_PY = REPO_ROOT / "backend" / "db" / "models.py"

MIGRATION_ID = "003_add_alerts_written_count"
EXPECTED_COLUMN_PRESENCE = ("alerts_written_count",)
EXPECTED_COUNT_CHECK = "CHECK(alerts_written_count >= 0)"


def _log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def _check_lsof(db_path: Path) -> None:
    """Abort if any process holds the DB file.

    Live DB: missing lsof is a HARD FAIL (concurrent access is exactly what
    this check guards against). Non-live DBs: warn and continue.

    Test escape hatch: VNA_SKIP_LSOF=1 skips this check. Used by
    scripts/test_migration_003_apply.py when the test runner legitimately
    holds read-only handles from earlier tests in the same run. This is
    an in-process reentry scenario — NOT a concurrent-writer scenario —
    and the idempotency guard (_already_applied) catches double-apply anyway.
    """
    if os.environ.get("VNA_SKIP_LSOF") == "1":
        _log("Note: VNA_SKIP_LSOF=1 set — skipping lsof concurrency check (test context)")
        return
    is_live = db_path.name == "vna_alerts.db"
    try:
        result = subprocess.run(
            ["lsof", str(db_path)], capture_output=True, text=True, timeout=5,
        )
    except FileNotFoundError:
        if is_live:
            _log("FATAL: lsof not available — refusing to proceed on live DB")
            sys.exit(1)
        print("WARNING: lsof not available; skipping concurrency check", file=sys.stderr)
        return
    except subprocess.TimeoutExpired:
        if is_live:
            _log("FATAL: lsof timed out on live DB — refusing to proceed")
            sys.exit(1)
        print("WARNING: lsof timed out; skipping concurrency check", file=sys.stderr)
        return
    if result.returncode == 0 and result.stdout.strip():
        _log(f"ABORT: DB is held by another process:\n{result.stdout}")
        sys.exit(1)


def _acquire_apply_lock(db_path: Path):
    """Acquire an exclusive file-lock held for the duration of the apply.

    Closes the TOCTOU window between _check_lsof and sqlite3.connect.
    Another driver invocation attempting to apply concurrently will block
    on the flock and exit immediately with a clear message.
    """
    lock_path = db_path.with_suffix(db_path.suffix + ".apply.lock")
    fd = open(lock_path, "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        _log(f"ABORT: another migration apply is in progress (lock: {lock_path})")
        fd.close()
        sys.exit(1)
    return fd


def _already_applied(conn: sqlite3.Connection) -> bool:
    """Check whether migration 003 has already been applied.

    Primary: column presence via PRAGMA table_info(pipeline_runs) (authoritative
    post-ALTER source).
    Secondary: vna_schema_migrations ledger row.

    Returns True iff BOTH are present. Raises if exactly one is present
    (partial state = error requiring manual inspection — do NOT re-apply).
    """
    cols = conn.execute("PRAGMA table_info(pipeline_runs)").fetchall()
    col_names = {row[1] for row in cols}
    cols_present = all(c in col_names for c in EXPECTED_COLUMN_PRESENCE)

    # vna_schema_migrations table may not exist on a very-fresh DB (pre-001).
    try:
        ledger_row = conn.execute(
            "SELECT 1 FROM vna_schema_migrations WHERE migration_id = ?",
            (MIGRATION_ID,),
        ).fetchone()
        ledger_present = ledger_row is not None
    except sqlite3.OperationalError:
        # vna_schema_migrations doesn't exist yet — definitely not applied.
        ledger_present = False

    if cols_present != ledger_present:
        raise RuntimeError(
            f"Inconsistent state: cols_present={cols_present} ledger_present={ledger_present}. "
            f"Manual inspection required."
        )
    return cols_present and ledger_present


def _snapshot_row_counts(db_path: Path) -> dict:
    """Capture row counts for alerts + pending_notifications + pipeline_runs before apply."""
    conn = sqlite3.connect(str(db_path))
    try:
        alerts_count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        try:
            pn_count = conn.execute(
                "SELECT COUNT(*) FROM pending_notifications"
            ).fetchone()[0]
        except sqlite3.OperationalError:
            pn_count = 0
        pr_count = conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0]
        return {"alerts": alerts_count, "pending_notifications": pn_count, "pipeline_runs": pr_count}
    finally:
        conn.close()


def _verify_row_counts_preserved(db_path: Path, pre_counts: dict) -> None:
    """Assert row counts in alerts + pending_notifications + pipeline_runs equal pre-apply counts."""
    conn = sqlite3.connect(str(db_path))
    try:
        alerts_count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        try:
            pn_count = conn.execute(
                "SELECT COUNT(*) FROM pending_notifications"
            ).fetchone()[0]
        except sqlite3.OperationalError:
            pn_count = 0
        pr_count = conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0]
    finally:
        conn.close()

    assert alerts_count == pre_counts["alerts"], (
        f"Row count mismatch in alerts: pre={pre_counts['alerts']} post={alerts_count}"
    )
    assert pn_count == pre_counts["pending_notifications"], (
        f"Row count mismatch in pending_notifications: "
        f"pre={pre_counts['pending_notifications']} post={pn_count}"
    )
    assert pr_count == pre_counts["pipeline_runs"], (
        f"Row count mismatch in pipeline_runs: pre={pre_counts['pipeline_runs']} post={pr_count}"
    )
    _log(
        f"Row count preservation PASSED: alerts={alerts_count}, "
        f"pending_notifications={pn_count}, pipeline_runs={pr_count}"
    )


def _backup(src: Path, dst: Path) -> None:
    """Create a recoverable snapshot of a WAL-mode SQLite DB.

    Uses sqlite3.Connection.backup() (online-backup API) — WAL pages are
    folded into the backup file so the .bak is a self-contained snapshot.
    """
    if dst.exists():
        _log(f"Overwriting existing backup: {dst}")
        dst.unlink()

    src_conn = sqlite3.connect(str(src))
    dst_conn = sqlite3.connect(str(dst))
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()

    # Clean up stale -wal/-shm sidecars next to the backup.
    for suffix in ("-wal", "-shm"):
        stale = dst.with_name(dst.name + suffix)
        if stale.exists():
            stale.unlink()

    _log(f"Backup created via sqlite3.backup(): {dst} ({dst.stat().st_size} bytes)")


def _restore(bak: Path, dst: Path) -> None:
    """Restore the live DB atomically: backup to temp path, then atomic-rename.
    The live DB path is always either the pre-failure state (if killed before
    os.replace) or the fully restored state (if killed after) — never absent or
    partial. MONITOR-14 / WR-03 (Phase 10.2 Plan 03).
    """
    for suffix in ("-wal", "-shm"):
        stale = dst.with_name(dst.name + suffix)
        if stale.exists():
            stale.unlink()

    tmp = dst.with_suffix(dst.suffix + ".restore.tmp")
    if tmp.exists():
        tmp.unlink()

    bak_conn = sqlite3.connect(str(bak))
    dst_conn = sqlite3.connect(str(tmp))
    try:
        bak_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        bak_conn.close()

    os.replace(tmp, dst)
    _log(f"Restored {dst} from {bak} via sqlite3.backup() + atomic replace")


def _apply_migration(db_path: Path, sql_path: Path) -> None:
    sql_body = sql_path.read_text(encoding="utf-8")
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(sql_body)
        conn.commit()
    finally:
        conn.close()


def _verify_pipeline_runs_checks(db_path: Path) -> None:
    """Post-apply: asserts pipeline_runs has alerts_written_count col,
    CHECK(alerts_written_count >= 0) present in sqlite_master, ledger row exists.
    """
    conn = sqlite3.connect(str(db_path))
    try:
        cols = conn.execute("PRAGMA table_info(pipeline_runs)").fetchall()
        col_names = {row[1] for row in cols}
        for c in EXPECTED_COLUMN_PRESENCE:
            assert c in col_names, f"Missing column {c!r} in pipeline_runs table"
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name='pipeline_runs'"
        ).fetchone()
        assert row is not None, "pipeline_runs table missing post-apply"
        pr_sql = row[0]
        normalized = re.sub(r"\s+", " ", pr_sql)
        assert EXPECTED_COUNT_CHECK in normalized, (
            f"{EXPECTED_COUNT_CHECK!r} not found in pipeline_runs.sql. Got: {pr_sql!r}"
        )
        ledger_row = conn.execute(
            "SELECT applied_at FROM vna_schema_migrations WHERE migration_id = ?",
            (MIGRATION_ID,),
        ).fetchone()
        assert ledger_row is not None, f"Ledger row for {MIGRATION_ID!r} missing"
    finally:
        conn.close()


def _verify_byte_identical_to_models(db_path: Path) -> None:
    """Success criterion: pipeline_runs.sql matches models.py SQL_CREATE_PIPELINE_RUNS
    byte-for-byte on the alerts_written_count CHECK clause."""
    models_src = MODELS_PY.read_text(encoding="utf-8")
    m = re.search(r'SQL_CREATE_PIPELINE_RUNS\s*=\s*"""(.*?)"""', models_src, re.DOTALL)
    if not m:
        raise RuntimeError("Could not find SQL_CREATE_PIPELINE_RUNS in models.py")
    models_sql = m.group(1)

    conn = sqlite3.connect(str(db_path))
    try:
        db_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name='pipeline_runs'"
        ).fetchone()[0]
    finally:
        conn.close()

    pattern = r"CHECK\(\s*alerts_written_count\s*>=\s*0\s*\)"
    models_match = re.search(pattern, models_sql)
    db_match = re.search(pattern, db_sql)
    if models_match is None:
        raise RuntimeError("CHECK(alerts_written_count >= 0) not found in models.py SQL_CREATE_PIPELINE_RUNS")
    if db_match is None:
        raise RuntimeError("CHECK(alerts_written_count >= 0) not found in live DB sqlite_master.pipeline_runs")
    mns = re.sub(r"\s+", " ", models_match.group(0)).strip()
    dns = re.sub(r"\s+", " ", db_match.group(0)).strip()
    assert mns == dns, f"Drift on CHECK(alerts_written_count): models={mns!r} db={dns!r}"
    _log("Byte-identity check PASSED: pipeline_runs CHECK matches models.py")


def _verify_alerts_written_count_default(db_path: Path, pre_counts: dict) -> None:
    """Post-apply: all pre-existing pipeline_runs rows have alerts_written_count=0."""
    conn = sqlite3.connect(str(db_path))
    try:
        zero_count = conn.execute(
            "SELECT COUNT(*) FROM pipeline_runs WHERE alerts_written_count = 0"
        ).fetchone()[0]
    finally:
        conn.close()
    assert zero_count == pre_counts["pipeline_runs"], (
        f"DEFAULT 0 did not propagate: expected {pre_counts['pipeline_runs']} rows "
        f"with alerts_written_count=0, got {zero_count}"
    )
    _log(
        f"alerts_written_count DEFAULT verification PASSED: "
        f"{zero_count} rows with alerts_written_count=0"
    )


def main():
    ap = argparse.ArgumentParser(
        description="Phase 10 Plan 01 — safely apply migration 003 to data/vna_alerts.db"
    )
    ap.add_argument("--dry-run", action="store_true", help="Pre-checks only; no backup, no apply")
    args = ap.parse_args()

    _log(f"Migration 003 apply driver — DB={DB_PATH} SQL={MIGRATION_SQL}")
    if not DB_PATH.exists():
        _log(f"FATAL: DB not found at {DB_PATH}")
        sys.exit(1)
    if not MIGRATION_SQL.exists():
        _log(f"FATAL: Migration file not found at {MIGRATION_SQL}")
        sys.exit(1)

    # Require SQLite 3.35+ for ALTER TABLE ADD COLUMN NOT NULL DEFAULT const.
    if sqlite3.sqlite_version_info < (3, 35, 0):
        _log(
            f"FATAL: SQLite {sqlite3.sqlite_version} < 3.35 — migration 003 requires "
            f"ALTER TABLE ADD COLUMN NOT NULL DEFAULT constant support (SQLite 3.35+)."
        )
        sys.exit(1)

    _check_lsof(DB_PATH)

    # Acquire an exclusive flock for the duration of the apply. Closes TOCTOU
    # window between _check_lsof returning and sqlite3.connect opening the DB.
    _apply_lock_fd = _acquire_apply_lock(DB_PATH)  # noqa: F841 — held for lock duration

    # Idempotency guard — open connection, check, close immediately
    conn = sqlite3.connect(str(DB_PATH))
    already_done = _already_applied(conn)
    conn.close()

    if already_done:
        _log("SKIP: migration 003 already applied (alerts_written_count col present + ledger row).")
        sys.exit(0)

    if args.dry_run:
        _log("DRY RUN: precondition checks passed. No backup or apply performed.")
        sys.exit(0)

    # Snapshot row counts BEFORE apply
    pre_counts = _snapshot_row_counts(DB_PATH)
    _log(
        f"Pre-apply row counts: alerts={pre_counts['alerts']}, "
        f"pending_notifications={pre_counts['pending_notifications']}, "
        f"pipeline_runs={pre_counts['pipeline_runs']}"
    )

    # Backup
    try:
        _backup(DB_PATH, BAK_PATH)
    except Exception as e:
        _log(f"FATAL: backup failed: {e!r}")
        sys.exit(1)

    # Apply
    try:
        _apply_migration(DB_PATH, MIGRATION_SQL)
        _log("Migration 003 applied.")
    except Exception as e:
        _log(f"APPLY FAILED: {e!r}. Restoring from backup...")
        _restore(BAK_PATH, DB_PATH)
        sys.exit(2)

    # Verify CHECK constraints + byte-identity + row counts + DEFAULT propagation
    try:
        _verify_pipeline_runs_checks(DB_PATH)
        _verify_byte_identical_to_models(DB_PATH)
        _verify_row_counts_preserved(DB_PATH, pre_counts)
        _verify_alerts_written_count_default(DB_PATH, pre_counts)
        _log("Post-apply verification PASSED.")
    except Exception as e:
        _log(f"VERIFICATION FAILED: {e!r}. Restoring from backup...")
        _restore(BAK_PATH, DB_PATH)
        sys.exit(3)

    _log("DONE. Migration 003 applied successfully, backup at .pre-phase10.bak.")
    sys.exit(0)


if __name__ == "__main__":
    main()
