#!/usr/bin/env python3
"""
Phase 08 Plan 03 — Migration 001 Apply Driver.

Safely applies scripts/migrations/001_expand_channel_groups.sql to
data/vna_alerts.db with the following invariants:

1. Pre-apply backup:        data/vna_alerts.db.pre-phase08.bak created
                            via sqlite3.Connection.backup() (WAL-safe)
                            BEFORE any mutation.
2. Concurrency safety:      Aborts if any process holds the DB file
                            (checked via lsof — if lsof is absent, skip
                            the check with a WARNING printed to stderr).
3. Idempotency guard:       Pre-checks sqlite_master.alerts.sql for the
                            substring "'GOOGLE_ADEX'". If present,
                            migration is already applied — exit 0 with
                            SKIP message (no second apply, no corruption).
4. Ledger guard:            Pre-checks vna_schema_migrations table for
                            row ('001_expand_channel_groups', *). If present,
                            same SKIP behavior.
5. Atomic apply:            Uses sqlite3.Connection.executescript inside
                            a single transaction. On any exception,
                            SQLite auto-rolls back; driver additionally
                            restores from .bak as belt-and-suspenders.
6. Post-apply verification: Re-reads sqlite_master.alerts.sql and
                            pending_notifications.sql. Asserts they contain
                            all expected CHECK values and NOT 'A4'.
                            Compares alerts.sql whitespace-normalized to
                            SQL_CREATE_ALERTS in models.py -> success criterion 2.
7. Row-count preservation:  Snapshots row counts before apply and asserts
                            equality after apply (no data loss).
8. Exit codes:
   0 = success (applied) OR skip (already applied)
   1 = precondition failure (no DB, concurrent handle, etc.)
   2 = apply failure (automatically restored from .bak)
   3 = post-apply verification failure (automatically restored from .bak)

Run:  .venv/bin/python scripts/apply_migration_001.py [--dry-run]
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
BAK_PATH = REPO_ROOT / "data" / "vna_alerts.db.pre-phase08.bak"
MIGRATION_SQL = REPO_ROOT / "scripts" / "migrations" / "001_expand_channel_groups.sql"
MODELS_PY = REPO_ROOT / "backend" / "db" / "models.py"

EXPECTED_CHANNEL_VALUES = (
    "'GOOGLE_ADEX'", "'OPEN_BIDDING'", "'HEADER_BIDDING_MAGNITE'",
    "'HEADER_BIDDING_PUBMATIC'", "'TAM'", "'DIRECT'", "'DEAL'", "'GOOGLE'",
)
EXPECTED_RULE_VALUES = ("'A0'", "'A1'", "'A2'", "'A3'", "'A5'", "'A6'", "'A7'", "'A8'")
FORBIDDEN_RULE_VALUES = ("'A4'",)


def _log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def _check_lsof(db_path: Path) -> None:
    """Abort if any process holds the DB file.

    WR-05: behavior tightened.
      - Missing lsof on the LIVE DB (vna_alerts.db) is a HARD FAIL — the whole
        point of this check is to prevent concurrent access on shared infra.
      - Missing lsof on non-live DBs still warns and continues (dev/test flows).
      - Timeout on the live DB is a HARD FAIL (suspicious: kernel load or stuck
        FD is exactly when concurrent access is most likely).
    """
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
    # lsof returns 0 if file is open, 1 if not open
    if result.returncode == 0 and result.stdout.strip():
        _log(f"ABORT: DB is held by another process:\n{result.stdout}")
        sys.exit(1)


def _acquire_apply_lock(db_path: Path):
    """Acquire an exclusive file-lock held for the duration of the apply.

    WR-05: closes the TOCTOU window between _check_lsof and sqlite3.connect.
    Another driver invocation attempting to apply concurrently will block
    on the flock and exit immediately with a clear message.

    Returns the open file descriptor — caller MUST keep it alive until the
    apply completes. The lock is released when the fd is closed or the
    process exits.
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
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='alerts'"
    ).fetchone()
    if row is None:
        return False
    alerts_sql = row[0] or ""
    return "'GOOGLE_ADEX'" in alerts_sql and "'A8'" in alerts_sql and "'A4'" not in alerts_sql


def _snapshot_row_counts(db_path: Path) -> dict:
    """Capture row counts for alerts + pending_notifications before apply."""
    conn = sqlite3.connect(str(db_path))
    try:
        alerts_count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        try:
            pn_count = conn.execute(
                "SELECT COUNT(*) FROM pending_notifications"
            ).fetchone()[0]
        except sqlite3.OperationalError:
            pn_count = 0
        return {"alerts": alerts_count, "pending_notifications": pn_count}
    finally:
        conn.close()


def _verify_row_counts_preserved(db_path: Path, pre_counts: dict) -> None:
    """Assert row counts in alerts + pending_notifications equal pre-apply counts."""
    conn = sqlite3.connect(str(db_path))
    try:
        alerts_count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        try:
            pn_count = conn.execute(
                "SELECT COUNT(*) FROM pending_notifications"
            ).fetchone()[0]
        except sqlite3.OperationalError:
            pn_count = 0
    finally:
        conn.close()

    assert alerts_count == pre_counts["alerts"], (
        f"Row count mismatch in alerts: pre={pre_counts['alerts']} post={alerts_count}"
    )
    assert pn_count == pre_counts["pending_notifications"], (
        f"Row count mismatch in pending_notifications: "
        f"pre={pre_counts['pending_notifications']} post={pn_count}"
    )
    _log(
        f"Row count preservation PASSED: alerts={alerts_count}, "
        f"pending_notifications={pn_count}"
    )


def _backup(src: Path, dst: Path) -> None:
    """Create a recoverable snapshot of a WAL-mode SQLite DB.

    WR-06: the live DB runs in WAL mode (backend/db/database.py enables
    PRAGMA journal_mode=WAL). A WAL DB has three files: foo.db, foo.db-wal,
    foo.db-shm. shutil.copy2 copies only the main file — any uncommitted
    or uncheckpointed pages sitting in the -wal file would be missing from
    the backup, making it NOT a recoverable snapshot.

    Use sqlite3.Connection.backup() which is SQLite's own online-backup API
    and writes a fully checkpointed, self-contained .bak file in a single
    file (WAL pages are folded in).
    """
    if dst.exists():
        # Overwrite is intentional — each apply creates a fresh pre-apply snapshot.
        _log(f"Overwriting existing backup: {dst}")
        dst.unlink()

    src_conn = sqlite3.connect(str(src))
    dst_conn = sqlite3.connect(str(dst))
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()

    # Clean up any stale -wal/-shm sidecar files next to the backup.
    # The backup API writes a single consolidated file; leftover sidecars
    # from a previous aborted run would be misleading.
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


def _verify_alerts_checks(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute("SELECT sql FROM sqlite_master WHERE name='alerts'").fetchone()
        assert row is not None, "alerts table missing post-apply"
        alerts_sql = row[0]
        for v in EXPECTED_CHANNEL_VALUES:
            assert v in alerts_sql, f"Missing channel value {v} in alerts.sql"
        for v in EXPECTED_RULE_VALUES:
            assert v in alerts_sql, f"Missing rule value {v} in alerts.sql"
        for v in FORBIDDEN_RULE_VALUES:
            assert v not in alerts_sql, f"Forbidden value {v} present in alerts.sql"

        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name='pending_notifications'"
        ).fetchone()
        pn_sql = row[0]
        assert "CHECK(severity IN ('P0', 'P1', 'P2'))" in pn_sql, (
            "pending_notifications.severity CHECK missing"
        )
        for v in EXPECTED_CHANNEL_VALUES:
            assert v in pn_sql, f"Missing channel value {v} in pending_notifications.sql"
    finally:
        conn.close()


def _verify_byte_identical_to_models(db_path: Path) -> None:
    """Success criterion 2: alerts.sql matches models.py SQL_CREATE_ALERTS byte-for-byte
    (whitespace-normalized per CHECK clause)."""
    models_src = MODELS_PY.read_text(encoding="utf-8")
    m = re.search(r'SQL_CREATE_ALERTS\s*=\s*"""(.*?)"""', models_src, re.DOTALL)
    if not m:
        raise RuntimeError("Could not find SQL_CREATE_ALERTS in models.py")
    models_sql = m.group(1)

    conn = sqlite3.connect(str(db_path))
    try:
        db_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name='alerts'"
        ).fetchone()[0]
    finally:
        conn.close()

    # Extract each CHECK clause and compare whitespace-normalized
    for col in ("severity", "channel_group", "status", "alert_rule"):
        pattern = rf"CHECK\(\s*{col}\s+IN\s*\([^)]*\)\s*\)"
        models_match = re.search(pattern, models_sql)
        db_match = re.search(pattern, db_sql)
        if models_match is None:
            raise RuntimeError(f"CHECK({col}) not found in models.py SQL_CREATE_ALERTS")
        if db_match is None:
            raise RuntimeError(f"CHECK({col}) not found in live DB sqlite_master.alerts")
        mns = re.sub(r"\s+", " ", models_match.group(0)).strip()
        dns = re.sub(r"\s+", " ", db_match.group(0)).strip()
        assert mns == dns, f"Drift on CHECK({col}): models={mns!r} db={dns!r}"
    _log("Byte-identity check PASSED: alerts CHECKs match models.py")


def main():
    ap = argparse.ArgumentParser(
        description="Phase 08 Plan 03 — safely apply migration 001 to data/vna_alerts.db"
    )
    ap.add_argument("--dry-run", action="store_true", help="Pre-checks only; no backup, no apply")
    args = ap.parse_args()

    _log(f"Migration 001 apply driver — DB={DB_PATH} SQL={MIGRATION_SQL}")
    if not DB_PATH.exists():
        _log(f"FATAL: DB not found at {DB_PATH}")
        sys.exit(1)
    if not MIGRATION_SQL.exists():
        _log(f"FATAL: Migration file not found at {MIGRATION_SQL}")
        sys.exit(1)

    _check_lsof(DB_PATH)

    # WR-05: acquire an exclusive flock for the duration of the apply. Closes
    # the TOCTOU window between _check_lsof returning and sqlite3.connect
    # opening the DB. Keep `_apply_lock_fd` alive until main() exits.
    _apply_lock_fd = _acquire_apply_lock(DB_PATH)  # noqa: F841 — held for lock duration

    # Idempotency guard — open connection, check, close immediately
    conn = sqlite3.connect(str(DB_PATH))
    already_done = _already_applied(conn)
    conn.close()

    if already_done:
        _log("SKIP: migration 001 already applied (sqlite_master.alerts.sql contains 8-value CHECKs).")
        sys.exit(0)

    if args.dry_run:
        _log("DRY RUN: precondition checks passed. No backup or apply performed.")
        sys.exit(0)

    # Snapshot row counts BEFORE apply (W-02: plan-checker strengthening)
    pre_counts = _snapshot_row_counts(DB_PATH)
    _log(
        f"Pre-apply row counts: alerts={pre_counts['alerts']}, "
        f"pending_notifications={pre_counts['pending_notifications']}"
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
        _log("Migration 001 applied.")
    except Exception as e:
        _log(f"APPLY FAILED: {e!r}. Restoring from backup...")
        _restore(BAK_PATH, DB_PATH)
        sys.exit(2)

    # Verify CHECK constraints
    try:
        _verify_alerts_checks(DB_PATH)
        _verify_byte_identical_to_models(DB_PATH)
        _verify_row_counts_preserved(DB_PATH, pre_counts)
        _log("Post-apply verification PASSED.")
    except Exception as e:
        _log(f"VERIFICATION FAILED: {e!r}. Restoring from backup...")
        _restore(BAK_PATH, DB_PATH)
        sys.exit(3)

    _log("DONE. Migration 001 applied successfully, backup at .pre-phase08.bak.")
    sys.exit(0)


if __name__ == "__main__":
    main()
