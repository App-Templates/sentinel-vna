#!/usr/bin/env python3
"""
Phase 09 Plan 02 — MIGRATE-01 legacy alert deprecation (soft-delete).

Marks pre-v1.2 alerts as deprecated by setting:
  deprecated = 1
  deprecation_reason = 'v1.0 schema stale: legacy channel naming + v1.2 baseline divergence (Phase 09 deprecation)'

Cutoff (belt-and-suspenders, D-14):
  timestamp < '2026-02-01T00:00:00'  AND  channel_group IN ('GOOGLE', 'OPEN_BIDDING')

Idempotent: second run matches 0 rows (all candidates already have
deprecated=1) → exits 0 with IDEMPOTENT-NOOP message.

Safety (R-04 chirurgico):
- lsof pre-check on live DB (aborts if another process holds the file).
- fcntl.LOCK_EX flock on live DB (closes TOCTOU vs. concurrent apply).
- `--dry-run` prints candidate count without writing.
- lsof + flock SKIPPED for non-live DBs (tempfile tests) — per-process
  isolation already guarantees no concurrency concern.

Run:
  .venv/bin/python scripts/deprecate_legacy_alerts.py                   # live DB
  .venv/bin/python scripts/deprecate_legacy_alerts.py --dry-run         # count only
  .venv/bin/python scripts/deprecate_legacy_alerts.py --db-path X.db    # alt DB
"""
import argparse
import fcntl
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "data" / "vna_alerts.db"

# D-14 cutoff — BOTH conditions are AND'd (belt-and-suspenders).
# Timestamp literal is a FIXED DATE: future rows with ts >= 2026-02-01 can
# NEVER match, regardless of channel. Channel whitelist further narrows to
# the two legacy naming values.
CUTOFF_TIMESTAMP = "2026-02-01T00:00:00"
LEGACY_CHANNELS = ("GOOGLE", "OPEN_BIDDING")

# D-15 authoritative reason text — stable, greppable.
# DO NOT modify without amending CONTEXT.md §D-15 and
# scripts/test_deprecate_legacy_alerts.py::EXPECTED_REASON.
DEPRECATION_REASON = (
    "v1.0 schema stale: legacy channel naming + v1.2 baseline divergence "
    "(Phase 09 deprecation)"
)


def _log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def _check_lsof(db_path: Path) -> None:
    """Abort if another process holds the live DB file.

    Skipped on non-live DBs (tempfile tests) — per-process tempfile has
    no concurrency concern.
    """
    if db_path.name != "vna_alerts.db":
        return
    try:
        result = subprocess.run(
            ["lsof", str(db_path)], capture_output=True, text=True, timeout=5,
        )
    except FileNotFoundError:
        _log("FATAL: lsof not available — refusing to proceed on live DB")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        _log("FATAL: lsof timed out on live DB — refusing to proceed")
        sys.exit(1)
    # lsof exits 0 if file is open, 1 if not.
    if result.returncode == 0 and result.stdout.strip():
        _log(f"ABORT: DB is held by another process:\n{result.stdout}")
        sys.exit(1)


def _acquire_lock(db_path: Path):
    """Acquire exclusive flock for live-DB concurrency safety.

    Skipped on non-live DBs. The returned fd MUST stay alive for the
    duration of the UPDATE (garbage-collected at process exit).
    """
    if db_path.name != "vna_alerts.db":
        return None
    lock_path = db_path.with_suffix(db_path.suffix + ".deprecate.lock")
    fd = open(lock_path, "w")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        _log(f"ABORT: another deprecation run in progress (lock: {lock_path})")
        fd.close()
        sys.exit(1)
    return fd


def _count_candidates(conn: sqlite3.Connection) -> int:
    """Count rows that WOULD be updated (deprecated=0 AND match the filter)."""
    placeholders = ",".join("?" * len(LEGACY_CHANNELS))
    row = conn.execute(
        f"""SELECT COUNT(*) FROM alerts
            WHERE timestamp < ?
              AND channel_group IN ({placeholders})
              AND deprecated = 0""",
        (CUTOFF_TIMESTAMP, *LEGACY_CHANNELS),
    ).fetchone()
    return row[0]


def _apply_deprecation(conn: sqlite3.Connection) -> int:
    """Execute the UPDATE; return rowcount."""
    placeholders = ",".join("?" * len(LEGACY_CHANNELS))
    cursor = conn.execute(
        f"""UPDATE alerts
            SET deprecated = 1,
                deprecation_reason = ?
            WHERE timestamp < ?
              AND channel_group IN ({placeholders})
              AND deprecated = 0""",
        (DEPRECATION_REASON, CUTOFF_TIMESTAMP, *LEGACY_CHANNELS),
    )
    return cursor.rowcount


def main():
    ap = argparse.ArgumentParser(
        description="Phase 09 Plan 02 — soft-deprecate pre-v1.2 alerts (MIGRATE-01)"
    )
    ap.add_argument(
        "--db-path", type=Path, default=DEFAULT_DB_PATH,
        help="Path to SQLite DB (default: data/vna_alerts.db)",
    )
    ap.add_argument(
        "--dry-run", action="store_true",
        help="Print count of rows that WOULD be updated; no write performed.",
    )
    args = ap.parse_args()

    db_path: Path = args.db_path
    _log(f"MIGRATE-01 deprecation — DB={db_path}")

    if not db_path.exists():
        print(f"FATAL: DB not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    _check_lsof(db_path)
    _lock_fd = _acquire_lock(db_path)  # noqa: F841 — held for process lifetime

    conn = sqlite3.connect(str(db_path))
    try:
        candidate_count = _count_candidates(conn)
        _log(
            f"Candidate rows (timestamp < {CUTOFF_TIMESTAMP} "
            f"AND channel IN {LEGACY_CHANNELS} AND deprecated=0): {candidate_count}"
        )

        if args.dry_run:
            print(
                f"DRY RUN: {candidate_count} rows would be deprecated. "
                "No changes written."
            )
            sys.exit(0)

        if candidate_count == 0:
            print(
                "IDEMPOTENT-NOOP: no candidate rows found "
                "(deprecation already applied or no legacy alerts)."
            )
            sys.exit(0)

        rowcount = _apply_deprecation(conn)
        conn.commit()
        _log(
            f"UPDATE applied: {rowcount} rows marked deprecated=1 with reason text."
        )
        assert rowcount == candidate_count, (
            f"rowcount {rowcount} != candidate_count {candidate_count} "
            "— unexpected concurrent race"
        )
    finally:
        conn.close()

    _log("DONE. MIGRATE-01 deprecation complete.")
    sys.exit(0)


if __name__ == "__main__":
    main()
