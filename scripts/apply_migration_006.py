#!/usr/bin/env python3
"""
Phase 17.4 Plan 04 — Migration 006 Apply Driver (D2CLOSE-03).

Safely applies scripts/migrations/006_backfill_split_marking.sql to
data/vna_alerts.db with the following invariants:

1. Pre-apply backup:    Creates data/vna_alerts.db.pre-17.4-backfill-rewrite
                        via sqlite3.Connection.backup() (WAL-safe online backup).
                        On failure in any subsequent step, this same .bak is used
                        for auto-restore.
2. Concurrency safety:  Aborts if any process holds the DB file
                        (checked via lsof — if lsof is absent on live DB,
                        the check is a HARD FAIL).
3. Idempotency guard:   Pre-checks vna_schema_migrations for row
                        ('006_backfill_split_marking', *).
                        Migration 006 is UPDATE-only (no DDL), so the
                        ledger row is the sole idempotency signal.
4. Atomic apply:        sqlite3.Connection.executescript() runs the
                        single transaction in 006_backfill_split_marking.sql.
5. Post-apply verify:   Asserts exactly 199 rows carry
                        deprecation_reason='synthetic-era pre-H6-fix, Phase 21 Athena dependency'
                        AND deprecated=1.  Also verifies data_source='backfill'
                        count (238 UNCHANGED) and GOOGLE_ADEX untouched (39).
6. Auto-restore:        If apply or verification fails, the pre-apply
                        backup is restored automatically (exit 2/3).
7. --dry-run mode:      Prints the COUNT of rows that WOULD be modified
                        (199 expected) without writing. Exit 0.
8. Exit codes:
   0 = success (applied) OR skip (already applied) OR dry-run pass
   1 = precondition failure (no DB, no SQL, concurrent handle, etc.)
   2 = apply failure (automatically restored from .bak)
   3 = post-apply verification failure (automatically restored from .bak)

Run:  .venv/bin/python scripts/apply_migration_006.py [--dry-run]

BLOCKING GATE: Do NOT run against data/vna_alerts.db without operator OK per R-05.
Pre-flight checklist (Task 2):
  1. git tag pre-17.4-backfill-rewrite  (on current HEAD)
  2. lsof data/vna_alerts.db | head     (confirm no FastAPI dev process holds DB)
  3. .venv/bin/python scripts/apply_migration_006.py  (this driver)
"""

import argparse
import fcntl
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "vna_alerts.db"
BAK_PATH = REPO_ROOT / "data" / "vna_alerts.db.pre-17.4-backfill-rewrite"
MIGRATION_SQL = REPO_ROOT / "scripts" / "migrations" / "006_backfill_split_marking.sql"

MIGRATION_ID = "006_backfill_split_marking"

# Canonical deprecation_reason string set by the UPDATE statement.
# Used by _verify_deprecated_count to confirm exactly 199 rows were marked.
DEPRECATION_REASON = "synthetic-era pre-H6-fix, Phase 21 Athena dependency"

# Expected post-apply counts (D-10 canonical baseline).
EXPECTED_DEPRECATED_COUNT = 199      # non-GOOGLE_ADEX backfill alerts marked
EXPECTED_TOTAL_BACKFILL = 238        # total backfill rows UNCHANGED (data_source preserved)
EXPECTED_GOOGLE_ADEX_UNTOUCHED = 39  # GOOGLE_ADEX backfill still deprecated=0 (rewrite target)


def _log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def _check_lsof(db_path: Path) -> None:
    """Abort if any process holds the DB file.

    Test escape hatch: VNA_SKIP_LSOF=1 skips this check. Used by
    scripts/test_migration_006_apply.py when the test runner legitimately
    holds read-only handles from earlier tests in the same run. This is
    an in-process reentry scenario -- NOT a concurrent-writer scenario --
    and the idempotency guard (_already_applied) catches double-apply anyway.
    """
    if os.environ.get("VNA_SKIP_LSOF") == "1":
        _log("Note: VNA_SKIP_LSOF=1 set -- skipping lsof concurrency check (test context)")
        return
    is_live = db_path.name == "vna_alerts.db"
    try:
        result = subprocess.run(
            ["lsof", str(db_path)], capture_output=True, text=True, timeout=5,
        )
    except FileNotFoundError:
        if is_live:
            _log("FATAL: lsof not available -- refusing to proceed on live DB")
            sys.exit(1)
        print("WARNING: lsof not available; skipping concurrency check", file=sys.stderr)
        return
    except subprocess.TimeoutExpired:
        if is_live:
            _log("FATAL: lsof timed out on live DB -- refusing to proceed")
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
    """Migration 006 is UPDATE-only -- ledger row is the sole signal.

    Post-apply count invariant is verified separately by _verify_deprecated_count
    (it's the post-apply success check, not the idempotency pre-check).
    """
    try:
        row = conn.execute(
            "SELECT 1 FROM vna_schema_migrations WHERE migration_id = ?",
            (MIGRATION_ID,),
        ).fetchone()
        return row is not None
    except sqlite3.OperationalError:
        # vna_schema_migrations doesn't exist yet -- definitely not applied.
        return False


def _snapshot_row_counts(db_path: Path) -> dict:
    """Capture row counts before apply to verify preservation post-apply."""
    conn = sqlite3.connect(str(db_path))
    try:
        alerts_count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        try:
            pn_count = conn.execute(
                "SELECT COUNT(*) FROM pending_notifications"
            ).fetchone()[0]
        except sqlite3.OperationalError:
            pn_count = 0
        try:
            pr_count = conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0]
        except sqlite3.OperationalError:
            pr_count = 0
        return {"alerts": alerts_count, "pending_notifications": pn_count, "pipeline_runs": pr_count}
    finally:
        conn.close()


def _backup(src: Path, dst: Path) -> None:
    """Create a recoverable snapshot of a WAL-mode SQLite DB.

    Uses sqlite3.Connection.backup() (online-backup API) -- WAL pages are
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


def _verify_deprecated_count(db_path: Path) -> None:
    """Post-apply: exactly 199 rows must carry deprecation_reason='synthetic-era...'
    AND deprecated=1. Also verifies data_source field is UNCHANGED (238 backfill
    rows total) and GOOGLE_ADEX is untouched (39 deprecated=0).
    """
    conn = sqlite3.connect(str(db_path))
    try:
        # Primary assertion: 199 rows marked deprecated with canonical reason
        deprecated_count = conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE deprecation_reason = ? AND deprecated = 1",
            (DEPRECATION_REASON,),
        ).fetchone()[0]
        assert deprecated_count == EXPECTED_DEPRECATED_COUNT, (
            f"Deprecated count mismatch: expected {EXPECTED_DEPRECATED_COUNT}, "
            f"got {deprecated_count}"
        )

        # Secondary assertion: data_source='backfill' total UNCHANGED (D-11)
        backfill_total = conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE data_source = 'backfill'"
        ).fetchone()[0]
        assert backfill_total == EXPECTED_TOTAL_BACKFILL, (
            f"Total backfill count mismatch: expected {EXPECTED_TOTAL_BACKFILL}, "
            f"got {backfill_total} (data_source field should not have changed)"
        )

        # Tertiary assertion: GOOGLE_ADEX rows NOT marked (rewrite-script target)
        google_adex_untouched = conn.execute(
            "SELECT COUNT(*) FROM alerts "
            "WHERE channel_group = 'GOOGLE_ADEX' AND data_source = 'backfill' AND deprecated = 0"
        ).fetchone()[0]
        assert google_adex_untouched == EXPECTED_GOOGLE_ADEX_UNTOUCHED, (
            f"GOOGLE_ADEX untouched count mismatch: expected {EXPECTED_GOOGLE_ADEX_UNTOUCHED}, "
            f"got {google_adex_untouched}"
        )
    finally:
        conn.close()

    _log(
        f"Post-apply verification PASSED: "
        f"{EXPECTED_DEPRECATED_COUNT} deprecated, "
        f"{EXPECTED_TOTAL_BACKFILL} backfill (data_source unchanged), "
        f"{EXPECTED_GOOGLE_ADEX_UNTOUCHED} GOOGLE_ADEX untouched"
    )


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
        try:
            pr_count = conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0]
        except sqlite3.OperationalError:
            pr_count = 0
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


def _dry_run_count(db_path: Path) -> None:
    """Print the number of rows that WOULD be modified by migration 006."""
    conn = sqlite3.connect(str(db_path))
    try:
        would_update = conn.execute(
            "SELECT COUNT(*) FROM alerts "
            "WHERE channel_group != 'GOOGLE_ADEX' AND data_source = 'backfill' AND deprecated = 0"
        ).fetchone()[0]
        already_applied_row = None
        try:
            already_applied_row = conn.execute(
                "SELECT applied_at FROM vna_schema_migrations WHERE migration_id = ?",
                (MIGRATION_ID,),
            ).fetchone()
        except sqlite3.OperationalError:
            pass
    finally:
        conn.close()

    _log(f"DRY RUN: migration 006 would UPDATE {would_update} rows (expected {EXPECTED_DEPRECATED_COUNT})")
    _log(f"DRY RUN: SQL: UPDATE alerts SET deprecated=1, "
         f"deprecation_reason='{DEPRECATION_REASON}' "
         f"WHERE channel_group != 'GOOGLE_ADEX' AND data_source='backfill' AND deprecated=0")
    if already_applied_row:
        _log(f"DRY RUN: SKIP — migration already applied at {already_applied_row[0]}")
    else:
        _log(f"DRY RUN: migration NOT yet applied (no ledger row). {would_update} rows would be modified.")


def main():
    ap = argparse.ArgumentParser(
        description="Phase 17.4 Plan 04 -- safely apply migration 006 to data/vna_alerts.db (D2CLOSE-03)"
    )
    ap.add_argument("--dry-run", action="store_true", help="Pre-checks + count only; no backup, no apply")
    args = ap.parse_args()

    _log(f"Migration 006 apply driver -- DB={DB_PATH} SQL={MIGRATION_SQL}")
    if not DB_PATH.exists():
        _log(f"FATAL: DB not found at {DB_PATH}")
        sys.exit(1)
    if not MIGRATION_SQL.exists():
        _log(f"FATAL: Migration file not found at {MIGRATION_SQL}")
        sys.exit(1)

    _check_lsof(DB_PATH)

    # Acquire an exclusive flock for the duration of the apply. Closes TOCTOU
    # window between _check_lsof returning and sqlite3.connect opening the DB.
    _apply_lock_fd = _acquire_apply_lock(DB_PATH)  # noqa: F841 -- held for lock duration

    # Idempotency guard -- open connection, check, close immediately
    conn = sqlite3.connect(str(DB_PATH))
    already_done = _already_applied(conn)
    conn.close()

    if already_done:
        _log("SKIP: migration 006 already applied (ledger row present).")
        sys.exit(0)

    if args.dry_run:
        _dry_run_count(DB_PATH)
        _log("DRY RUN: precondition checks passed. No backup or apply performed.")
        sys.exit(0)

    # Snapshot row counts BEFORE apply
    pre_counts = _snapshot_row_counts(DB_PATH)
    _log(
        f"Pre-apply row counts: alerts={pre_counts['alerts']}, "
        f"pending_notifications={pre_counts['pending_notifications']}, "
        f"pipeline_runs={pre_counts['pipeline_runs']}"
    )

    # Create WAL-safe backup BEFORE applying (R-04 chirurgico)
    try:
        _backup(DB_PATH, BAK_PATH)
    except Exception as e:
        _log(f"FATAL: backup failed: {e!r}")
        sys.exit(1)

    # Apply migration SQL in single transaction
    try:
        _apply_migration(DB_PATH, MIGRATION_SQL)
        _log("Migration 006 applied.")
    except Exception as e:
        _log(f"APPLY FAILED: {e!r}. Restoring from backup...")
        _restore(BAK_PATH, DB_PATH)
        sys.exit(2)

    # Verify deprecated count + data_source preservation + GOOGLE_ADEX untouched
    try:
        _verify_row_counts_preserved(DB_PATH, pre_counts)
        _verify_deprecated_count(DB_PATH)
        _log("Post-apply verification PASSED.")
    except Exception as e:
        _log(f"VERIFICATION FAILED: {e!r}. Restoring from backup...")
        _restore(BAK_PATH, DB_PATH)
        sys.exit(3)

    _log(
        f"DONE. Migration 006 applied successfully. "
        f"Backup at {BAK_PATH.name}. "
        f"{EXPECTED_DEPRECATED_COUNT} rows marked deprecated=1 (channel_group != 'GOOGLE_ADEX')."
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
