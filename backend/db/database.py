from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

from backend.db.models import (
    SQL_CREATE_ALERT_ASSIGNMENTS,
    SQL_CREATE_ALERT_EVENTS,
    SQL_CREATE_ALERT_FEEDBACK,
    SQL_CREATE_ALERT_INTERVENTION_LINKS,
    SQL_CREATE_ALERTS,
    SQL_CREATE_BACKTEST_RESULTS,
    SQL_CREATE_INDEXES,
    SQL_CREATE_MANUAL_INTERVENTIONS,
    SQL_CREATE_PENDING_NOTIFICATIONS,
    SQL_CREATE_PIPELINE_RUNS,
    SQL_CREATE_RECHECK_QUEUE,
)
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_DB_PATH: Optional[str] = None
_local = threading.local()


def _get_db_path() -> str:
    global _DB_PATH
    if _DB_PATH is None:
        _DB_PATH = os.environ.get(
            "VNA_DB_PATH",
            str(Path(__file__).resolve().parent.parent.parent / "data" / "vna_alerts.db"),
        )
    return _DB_PATH


def _get_connection() -> sqlite3.Connection:
    if not hasattr(_local, "connection") or _local.connection is None:
        db_path = _get_db_path()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")  # Wait up to 5s for locks
        conn.execute("PRAGMA foreign_keys=ON;")
        _local.connection = conn
    return _local.connection


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = _get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _migrate_alerts_schema_v2(conn: sqlite3.Connection) -> None:
    """Bring `alerts` CHECK constraints up to Phase 08 SCHEMA-01/02 state.

    Detects DBs that predate migration 001 (stale 2-value channel_group CHECK
    or 4-value alert_rule CHECK) and applies the same CREATE-new + INSERT SELECT
    + DROP + RENAME recreate in-process. This covers fresh-DB scenarios where
    init_db() is called without first running scripts/migrations/001_*.sql
    (CI, dev reset, first-run after clean clone).

    SQLite does not support ALTER CHECK, so we recreate the table preserving
    all existing data. Mirrors migration 001's DDL.
    """
    # Check if alerts table exists
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='alerts'"
    ).fetchone()
    if row is None:
        return  # Table doesn't exist yet; SQL_CREATE_ALERTS will create it fresh

    create_sql = row[0] or ""

    # Probe 1: channel_group 8-value CHECK present?
    channel_group_ok = "'GOOGLE_ADEX'" in create_sql and "'HEADER_BIDDING_MAGNITE'" in create_sql
    # Probe 2: alert_rule CHECK expanded (includes A8, excludes A4)?
    alert_rule_ok = "'A8'" in create_sql and "'A4'" not in create_sql

    if channel_group_ok and alert_rule_ok:
        return  # Already at Phase 08 schema state

    logger.info(
        "Migrating alerts table to Phase 08 schema v2 (channel_group 8-value, "
        "alert_rule 8-value skipping A4). Pre-migration probes: "
        "channel_group_ok=%s alert_rule_ok=%s",
        channel_group_ok, alert_rule_ok,
    )

    # Explicit column list — positional SELECT * is the Phase-07-class silent-failure
    # pattern (CR-01). If SQL_CREATE_ALERTS ever gains/reorders columns vs the stale
    # table, SELECT * either fails loudly (row width mismatch) or — worse — silently
    # inserts into wrong columns. Named columns force a schema contract.
    ALERTS_COLUMNS = (
        "alert_id, timestamp, severity, channel_group, status, alert_rule, "
        "revenue_current, revenue_baseline, revenue_delta_pct, triage_label, "
        "contributors_json, geo_breakdown_json, environment_split_json, "
        "insights_json, execution_time_sec, data_source, config_version, "
        "created_at, updated_at"
    )

    # PRAGMA foreign_keys must be OUTSIDE any implicit transaction (SQLite doc:
    # setting is a no-op inside a transaction). Commit any pending work first.
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF;")
    try:
        conn.execute("BEGIN IMMEDIATE;")
        conn.execute("ALTER TABLE alerts RENAME TO _alerts_old_v2;")
        conn.execute(SQL_CREATE_ALERTS)
        conn.execute(
            f"INSERT INTO alerts({ALERTS_COLUMNS}) "
            f"SELECT {ALERTS_COLUMNS} FROM _alerts_old_v2;"
        )
        conn.execute("DROP TABLE _alerts_old_v2;")
        conn.execute("COMMIT;")
    except Exception:
        conn.execute("ROLLBACK;")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys=ON;")
    logger.info("Migration complete: alerts table now at Phase 08 schema v2.")


def _migrate_pending_notifications_schema_v2(conn: sqlite3.Connection) -> None:
    """Bring `pending_notifications` CHECK constraints up to Phase 08 SCHEMA-02 state.

    Detects DBs where pending_notifications was created without severity/channel_group
    CHECKs (pre-Phase-08 schema) and applies recreate + row copy.
    """
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='pending_notifications'"
    ).fetchone()
    if row is None:
        return  # Table doesn't exist yet; SQL_CREATE_PENDING_NOTIFICATIONS will create it fresh

    create_sql = row[0] or ""
    # Probe: does severity have a CHECK and does channel_group have the 8-value CHECK?
    severity_ok = "CHECK(severity IN ('P0', 'P1', 'P2'))" in create_sql
    channel_group_ok = "'GOOGLE_ADEX'" in create_sql

    if severity_ok and channel_group_ok:
        return  # Already at Phase 08 schema

    logger.info(
        "Migrating pending_notifications to Phase 08 schema v2 (tightening severity + channel_group CHECKs). "
        "Probes: severity_ok=%s channel_group_ok=%s",
        severity_ok, channel_group_ok,
    )

    # PRAGMA foreign_keys must be OUTSIDE any implicit transaction (CR-01).
    conn.commit()
    conn.execute("PRAGMA foreign_keys=OFF;")
    try:
        conn.execute("BEGIN IMMEDIATE;")
        conn.execute("ALTER TABLE pending_notifications RENAME TO _pending_notifications_old_v2;")
        conn.execute(SQL_CREATE_PENDING_NOTIFICATIONS)
        conn.execute(
            "INSERT INTO pending_notifications(id, alert_id, severity, channel_group, timestamp, created_at) "
            "SELECT id, alert_id, severity, channel_group, timestamp, created_at FROM _pending_notifications_old_v2;"
        )
        conn.execute("DROP TABLE _pending_notifications_old_v2;")
        conn.execute("COMMIT;")
    except Exception:
        conn.execute("ROLLBACK;")
        raise
    finally:
        conn.execute("PRAGMA foreign_keys=ON;")
    logger.info("Migration complete: pending_notifications at Phase 08 schema v2.")


def init_db(db_path: Optional[str] = None) -> None:
    global _DB_PATH
    if db_path is not None:
        _DB_PATH = db_path

    resolved = _get_db_path()
    Path(resolved).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(resolved)
    conn.execute("PRAGMA foreign_keys=ON;")

    try:
        # WR-07: wrap runtime migrations with explicit error logging so
        # init_db() callers (typically API startup) don't see a bare
        # exception without context. A partial failure is likely to leave
        # the DB in a state that requires the Plan 03 .bak to recover.
        try:
            _migrate_alerts_schema_v2(conn)
            _migrate_pending_notifications_schema_v2(conn)
        except Exception:
            logger.exception(
                "Phase 08 runtime migration FAILED at %s. DB may be in a "
                "partial state. If this is prod, consider restoring from "
                "data/vna_alerts.db.pre-phase08.bak.",
                resolved,
            )
            raise
        conn.execute(SQL_CREATE_ALERTS)
        conn.execute(SQL_CREATE_ALERT_EVENTS)
        conn.execute(SQL_CREATE_RECHECK_QUEUE)
        conn.execute(SQL_CREATE_PIPELINE_RUNS)
        conn.execute(SQL_CREATE_BACKTEST_RESULTS)
        conn.execute(SQL_CREATE_ALERT_FEEDBACK)
        conn.execute(SQL_CREATE_ALERT_ASSIGNMENTS)
        conn.execute(SQL_CREATE_MANUAL_INTERVENTIONS)
        conn.execute(SQL_CREATE_ALERT_INTERVENTION_LINKS)
        conn.execute(SQL_CREATE_PENDING_NOTIFICATIONS)
        for idx_sql in SQL_CREATE_INDEXES:
            conn.execute(idx_sql)
        conn.commit()
        logger.info("Database initialized at %s", resolved)
    finally:
        conn.close()


def close_db() -> None:
    if hasattr(_local, "connection") and _local.connection is not None:
        _local.connection.close()
        _local.connection = None
