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


def _migrate_alerts_check_constraint(conn: sqlite3.Connection) -> None:
    """Migrate alerts table to include A0 in alert_rule CHECK constraint.

    SQLite does not support ALTER CHECK, so we recreate the table
    preserving all existing data via rename-create-copy-drop.
    """
    # Check if alerts table exists
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='alerts'"
    ).fetchone()
    if row is None:
        return  # Table doesn't exist yet, will be created fresh

    create_sql = row[0] or ""
    if "'A0'" in create_sql:
        return  # Already has A0, no migration needed

    logger.info("Migrating alerts table to add A0 to alert_rule CHECK constraint...")
    # Must disable FK checks during migration to avoid issues with temp rename
    conn.execute("PRAGMA foreign_keys=OFF;")
    conn.execute("ALTER TABLE alerts RENAME TO _alerts_old;")
    conn.execute(SQL_CREATE_ALERTS)
    conn.execute(
        "INSERT INTO alerts SELECT * FROM _alerts_old;"
    )
    conn.execute("DROP TABLE _alerts_old;")
    conn.execute("PRAGMA foreign_keys=ON;")
    logger.info("Migration complete: alerts table now accepts A0 alert_rule.")


def init_db(db_path: Optional[str] = None) -> None:
    global _DB_PATH
    if db_path is not None:
        _DB_PATH = db_path

    resolved = _get_db_path()
    Path(resolved).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(resolved)
    conn.execute("PRAGMA foreign_keys=ON;")

    try:
        _migrate_alerts_check_constraint(conn)
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
