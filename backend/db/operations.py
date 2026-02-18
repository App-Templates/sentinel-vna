from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Optional

from backend.db.database import get_db
from backend.db.models import (
    AlertEventModel,
    AlertModel,
    AlertStatus,
    EventType,
    RecheckQueueModel,
    RecheckStatus,
)
from backend.utils.logger import get_logger

logger = get_logger(__name__)


def _row_to_dict(row) -> dict[str, Any]:
    return dict(row) if row else {}


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

def create_alert(alert: AlertModel) -> str:
    with get_db() as conn:
        conn.execute(
            """INSERT INTO alerts (
                alert_id, timestamp, severity, channel_group, status, alert_rule,
                revenue_current, revenue_baseline, revenue_delta_pct, triage_label,
                contributors_json, geo_breakdown_json, environment_split_json,
                insights_json, execution_time_sec, data_source, config_version,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                alert.alert_id,
                alert.timestamp.isoformat(),
                alert.severity.value,
                alert.channel_group.value,
                alert.status.value,
                alert.alert_rule.value,
                alert.revenue_current,
                alert.revenue_baseline,
                alert.revenue_delta_pct,
                alert.triage_label,
                alert.contributors_json,
                alert.geo_breakdown_json,
                alert.environment_split_json,
                alert.insights_json,
                alert.execution_time_sec,
                alert.data_source,
                alert.config_version,
                alert.created_at.isoformat(),
                alert.updated_at.isoformat(),
            ),
        )
    logger.info("Created alert %s", alert.alert_id)
    return alert.alert_id


def get_alerts(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    channel: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    conditions: list[str] = []
    params: list[Any] = []

    if severity:
        conditions.append("severity = ?")
        params.append(severity)
    if status:
        conditions.append("status = ?")
        params.append(status)
    if channel:
        conditions.append("channel_group = ?")
        params.append(channel)
    if date_from:
        conditions.append("timestamp >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("timestamp <= ?")
        params.append(date_to)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    with get_db() as conn:
        count_row = conn.execute(
            f"SELECT COUNT(*) as cnt FROM alerts WHERE {where_clause}", params
        ).fetchone()
        total = count_row["cnt"] if count_row else 0

        rows = conn.execute(
            f"""SELECT alert_id, timestamp, severity, channel_group, status,
                       alert_rule, revenue_current, revenue_baseline,
                       revenue_delta_pct, triage_label, created_at
                FROM alerts
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?""",
            params + [limit, offset],
        ).fetchall()

    return [_row_to_dict(r) for r in rows], total


def get_alert_by_id(alert_id: str) -> Optional[dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM alerts WHERE alert_id = ?", (alert_id,)
        ).fetchone()
        if row is None:
            return None

        alert = _row_to_dict(row)

        events = conn.execute(
            "SELECT * FROM alert_events WHERE alert_id = ? ORDER BY timestamp ASC",
            (alert_id,),
        ).fetchall()
        alert["events"] = [_row_to_dict(e) for e in events]

    return alert


def update_alert_status(alert_id: str, new_status: AlertStatus) -> bool:
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE alerts SET status = ?, updated_at = ? WHERE alert_id = ?",
            (new_status.value, now, alert_id),
        )
    updated = cursor.rowcount > 0
    if updated:
        logger.info("Updated alert %s status to %s", alert_id, new_status.value)
    return updated


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

def create_event(
    alert_id: str,
    event_type: EventType,
    user_id: str,
    comment: Optional[str] = None,
) -> int:
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO alert_events (alert_id, event_type, user_id, comment, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (alert_id, event_type.value, user_id, comment, now),
        )
        event_id = cursor.lastrowid
    logger.info("Created event %s for alert %s", event_type.value, alert_id)
    return event_id


# ---------------------------------------------------------------------------
# Recheck queue
# ---------------------------------------------------------------------------

def create_recheck(alert_id: str, scheduled_at: datetime) -> int:
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO recheck_queue (alert_id, scheduled_at, status, created_at)
               VALUES (?, ?, ?, ?)""",
            (alert_id, scheduled_at.isoformat(), RecheckStatus.PENDING.value, now),
        )
        queue_id = cursor.lastrowid
    logger.info("Created recheck queue entry %d for alert %s", queue_id, alert_id)
    return queue_id


def get_pending_rechecks() -> list[dict[str, Any]]:
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM recheck_queue
               WHERE status = ? AND scheduled_at <= ?
               ORDER BY scheduled_at ASC""",
            (RecheckStatus.PENDING.value, now),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def update_recheck_status(queue_id: int, status: RecheckStatus) -> bool:
    with get_db() as conn:
        cursor = conn.execute(
            "UPDATE recheck_queue SET status = ? WHERE queue_id = ?",
            (status.value, queue_id),
        )
    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Pipeline metrics
# ---------------------------------------------------------------------------

def record_pipeline_run(
    run_id: str,
    timestamp: str,
    channel_group: str,
    trigger_type: str,
    mode: str,
    status: str,
    duration_sec: float,
    llm_used: bool = False,
    llm_fallback: bool = False,
    alert_id: Optional[str] = None,
    error_message: Optional[str] = None,
) -> None:
    with get_db() as conn:
        conn.execute(
            """INSERT INTO pipeline_runs
               (run_id, timestamp, channel_group, trigger_type, mode, status,
                duration_sec, llm_used, llm_fallback, alert_id, error_message, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id, timestamp, channel_group, trigger_type, mode, status,
                duration_sec, int(llm_used), int(llm_fallback),
                alert_id, error_message, datetime.utcnow().isoformat(),
            ),
        )
    logger.info("Recorded pipeline run %s: status=%s duration=%.2fs", run_id, status, duration_sec)


def get_pipeline_metrics(days: int = 7) -> dict[str, Any]:
    with get_db() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """SELECT
                   COUNT(*) as total_runs,
                   SUM(CASE WHEN status='success' THEN 1 ELSE 0 END) as successes,
                   SUM(CASE WHEN status='no_alert' THEN 1 ELSE 0 END) as no_alerts,
                   SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failures,
                   AVG(duration_sec) as avg_duration,
                   SUM(llm_used) as llm_used_count,
                   SUM(llm_fallback) as llm_fallback_count
               FROM pipeline_runs
               WHERE created_at >= datetime('now', ?)""",
            (f'-{days} days',),
        ).fetchone()
    return dict(row) if row else {}


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------

def save_backtest_result(result: dict[str, Any]) -> None:
    backtest_id = result["backtest_id"]
    now = datetime.utcnow().isoformat()
    alerts = result.get("alerts", [])
    alerts_json = json.dumps(alerts)
    status = result.get("status", "PENDING")
    completed_at = now if status in ("COMPLETED", "FAILED") else None

    with get_db() as conn:
        conn.execute(
            """INSERT INTO backtest_results
               (backtest_id, start_date, end_date, channel, status, total_checks,
                alerts_generated, alerts_json, step_hours, created_at, completed_at, error)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(backtest_id) DO UPDATE SET
                   status = excluded.status,
                   total_checks = excluded.total_checks,
                   alerts_generated = excluded.alerts_generated,
                   alerts_json = excluded.alerts_json,
                   completed_at = excluded.completed_at,
                   error = excluded.error""",
            (
                backtest_id,
                result.get("start_date"),
                result.get("end_date"),
                result.get("channel"),
                status,
                result.get("total_checks", 0),
                result.get("alerts_generated", len(alerts)),
                alerts_json,
                result.get("step_hours"),
                now,
                completed_at,
                result.get("error"),
            ),
        )
    logger.info("Saved backtest result %s (status=%s)", backtest_id, status)


def get_backtest_result(backtest_id: str) -> Optional[dict[str, Any]]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM backtest_results WHERE backtest_id = ?", (backtest_id,)
        ).fetchone()
    if row is None:
        return None
    return _backtest_row_to_dict(row)


def get_all_backtest_results() -> list[dict[str, Any]]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM backtest_results ORDER BY created_at DESC"
        ).fetchall()
    return [_backtest_row_to_dict(r) for r in rows]


def _backtest_row_to_dict(row) -> dict[str, Any]:
    d = dict(row)
    # Parse alerts_json back to list for API compatibility
    alerts_raw = d.pop("alerts_json", "[]")
    try:
        d["alerts"] = json.loads(alerts_raw) if isinstance(alerts_raw, str) else alerts_raw
    except (json.JSONDecodeError, TypeError):
        d["alerts"] = []
    # Nest date fields into date_range to match frontend BacktestResult type
    d["date_range"] = {
        "start": d.pop("start_date", None),
        "end": d.pop("end_date", None),
        "step_hours": d.pop("step_hours", None),
    }
    return d
