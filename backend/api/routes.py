from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request

from backend.api.auth import require_auth
from backend.api.rate_limit import limiter

from backend.api.schemas import (
    AckRequest,
    AlertDetailResponse,
    AlertListResponse,
    AlertSummary,
    AlertDetail,
    AlertEvent,
    AlertTrendResponse,
    AssignRequest,
    AssignmentResponse,
    BacktestRequest,
    BacktestResultResponse,
    BacktestStartResponse,
    CommentRequest,
    FeedbackRequest,
    FeedbackResponse,
    FeedbackHistoryResponse,
    HealthResponse,
    InterventionLinkRequest,
    InterventionRequest,
    InterventionResponse,
    RecheckRequest,
    RecheckResponse,
    ResolveRequest,
    SuccessResponse,
)
from backend.backtest.runner import BacktestRunner
from backend.db.models import (
    AlertAssignmentModel,
    AlertFeedbackModel,
    AlertStatus,
    EventType,
    FeedbackCategory,
    InterventionType,
    ManualInterventionModel,
)
from backend.db.operations import (
    assign_alert,
    create_event,
    create_feedback,
    create_intervention,
    create_recheck,
    get_alert_assignment,
    get_alert_by_id,
    get_alerts,
    get_all_backtest_results,
    get_backtest_result,
    get_feedbacks_for_alert,
    get_interventions_for_alert,
    get_pipeline_metrics,
    get_publisher_feedback_history,
    link_intervention_to_alert,
    save_backtest_result,
    unassign_alert,
    update_alert_status,
)
from backend.scheduler.scheduler import is_scheduler_running
from backend.utils.config_loader import get_config
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api")

BASE_DIR = Path(__file__).parent.parent.parent
HOURLY_PARQUET = BASE_DIR / "data" / "baseline" / "hourly_aggregated.parquet"

# In-memory cache
_hourly_cache: Optional[pd.DataFrame] = None


def _load_hourly_data() -> Optional[pd.DataFrame]:
    """Load hourly aggregated parquet into memory with caching."""
    global _hourly_cache

    if _hourly_cache is not None:
        return _hourly_cache

    if not os.path.exists(HOURLY_PARQUET):
        logger.warning("Hourly parquet not found at %s", HOURLY_PARQUET)
        return None

    try:
        df = pd.read_parquet(HOURLY_PARQUET)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        _hourly_cache = df
        logger.info("Loaded hourly data: %d rows", len(df))
        return df
    except Exception as e:
        logger.error("Failed to load hourly parquet: %s", e)
        return None


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

@router.get("/alerts", response_model=AlertListResponse)
@limiter.limit("60/minute")
def list_alerts(
    request: Request,
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    assigned_to: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    rows, total = get_alerts(
        severity=severity,
        status=status,
        channel=channel,
        date_from=date_from,
        date_to=date_to,
        assigned_to=assigned_to,
        limit=limit,
        offset=offset,
    )
    alerts = [AlertSummary(**r) for r in rows]
    return AlertListResponse(alerts=alerts, total=total, limit=limit, offset=offset)


@router.get("/alerts/{alert_id}", response_model=AlertDetailResponse)
@limiter.limit("60/minute")
def get_alert(request: Request, alert_id: str):
    data = get_alert_by_id(alert_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    events_raw = data.pop("events", [])
    events = [AlertEvent(**e) for e in events_raw]

    # Get linked interventions
    interventions = get_interventions_for_alert(alert_id)

    # Parse JSON blob fields into proper objects
    for json_field, obj_field in [
        ("contributors_json", "contributors"),
        ("geo_breakdown_json", "geo_breakdown"),
        ("environment_split_json", "environment_split"),
        ("insights_json", "insights"),
    ]:
        raw = data.pop(json_field, "[]" if "list" in json_field else "{}")
        try:
            data[obj_field] = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            data[obj_field] = [] if obj_field in ("contributors", "geo_breakdown") else {}

    alert = AlertDetail(**data, events=events, interventions=interventions)
    return AlertDetailResponse(alert=alert)


@router.get("/alerts/{alert_id}/trend", response_model=AlertTrendResponse)
@limiter.limit("60/minute")
def get_alert_trend(request: Request, alert_id: str):
    from backend.agents.data_fetcher_real import _load_daily_channel_data

    data = get_alert_by_id(alert_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert_ts = datetime.fromisoformat(data["timestamp"])
    channel = data["channel_group"]

    df = _load_daily_channel_data()
    if df is None:
        raise HTTPException(status_code=503, detail="Daily channel data not available")

    start_date = alert_ts - timedelta(days=7)
    end_date = alert_ts

    mask = (df["date"] >= start_date) & (df["date"] <= end_date) & (df["channel_group"] == channel)
    filtered = df[mask]

    daily = filtered.groupby("date").agg({"revenue": "sum", "impressions": "sum"}).reset_index()

    trend_points = []
    for _, row in daily.iterrows():
        current_date = row["date"]
        baseline_revs = []
        for weeks_back in range(1, 8):
            baseline_date = current_date - timedelta(days=7 * weeks_back)
            bl_mask = (df["date"] == baseline_date) & (df["channel_group"] == channel)
            bl_rev = df[bl_mask]["revenue"].sum()
            if bl_rev > 0:
                baseline_revs.append(bl_rev)

        baseline = sum(baseline_revs) / len(baseline_revs) if baseline_revs else 0

        trend_points.append({
            "timestamp": current_date.isoformat(),
            "revenue": round(float(row["revenue"]), 2),
            "baseline_revenue": round(baseline, 2),
            "bacino": int(row["impressions"]),
            "coverage": 0,
        })

    trend_points.sort(key=lambda x: x["timestamp"])
    return {"trend": trend_points}


@router.post("/alerts/{alert_id}/ack", response_model=SuccessResponse)
@limiter.limit("30/minute")
async def acknowledge_alert(alert_id: str, body: AckRequest, request: Request):
    user = await require_auth(request)
    user_id = user["email"]

    data = get_alert_by_id(alert_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    if data["status"] != AlertStatus.OPEN.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot ACK alert in {data['status']} state. Must be OPEN.",
        )

    update_alert_status(alert_id, AlertStatus.ACK)
    create_event(alert_id, EventType.ACK, user_id, body.comment)
    logger.info("Alert %s acknowledged by %s", alert_id, user_id)
    return SuccessResponse(message=f"Alert {alert_id} acknowledged")


@router.post("/alerts/{alert_id}/resolve", response_model=SuccessResponse)
@limiter.limit("30/minute")
async def resolve_alert(alert_id: str, body: ResolveRequest, request: Request):
    user = await require_auth(request)
    user_id = user["email"]

    data = get_alert_by_id(alert_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    if data["status"] == AlertStatus.RESOLVED.value:
        raise HTTPException(status_code=400, detail="Alert is already resolved")

    update_alert_status(alert_id, AlertStatus.RESOLVED)
    create_event(alert_id, EventType.RESOLVE, user_id, body.comment)
    logger.info("Alert %s resolved by %s", alert_id, user_id)
    return SuccessResponse(message=f"Alert {alert_id} resolved")


@router.post("/alerts/{alert_id}/recheck", response_model=RecheckResponse)
@limiter.limit("30/minute")
async def recheck_alert(alert_id: str, body: RecheckRequest, request: Request):
    user = await require_auth(request)
    user_id = user["email"]

    data = get_alert_by_id(alert_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    scheduled_at = datetime.utcnow() + timedelta(hours=1)
    create_recheck(alert_id, scheduled_at)
    create_event(alert_id, EventType.RECHECK, user_id, f"Recheck scheduled at {scheduled_at.isoformat()}")
    logger.info("Recheck scheduled for alert %s at %s", alert_id, scheduled_at)
    return RecheckResponse(scheduled_at=scheduled_at.isoformat())


@router.post("/alerts/{alert_id}/comment", response_model=SuccessResponse)
@limiter.limit("30/minute")
async def add_comment(alert_id: str, body: CommentRequest, request: Request):
    user = await require_auth(request)
    user_id = user["email"]

    data = get_alert_by_id(alert_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    create_event(alert_id, EventType.COMMENT, user_id, body.comment)
    logger.info("Comment added to alert %s by %s", alert_id, user_id)
    return SuccessResponse(message="Comment added")


# ---------------------------------------------------------------------------
# Alert Assignments
# ---------------------------------------------------------------------------

@router.post("/alerts/{alert_id}/assign")
@limiter.limit("30/minute")
async def assign_alert_to_user(alert_id: str, body: AssignRequest, request: Request):
    """Assign an alert to a team member."""
    user = await require_auth(request)
    assigned_by = user["email"]

    # Validate assigned_to email matches @adkaora.com pattern
    if not body.assigned_to.endswith("@adkaora.com"):
        raise HTTPException(status_code=400, detail="assigned_to must be an @adkaora.com email")

    # Check alert exists
    data = get_alert_by_id(alert_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Create assignment
    assignment = AlertAssignmentModel(
        alert_id=alert_id,
        assigned_to=body.assigned_to,
        assigned_by=assigned_by,
    )
    assignment_id = assign_alert(assignment)

    logger.info("Alert %s assigned to %s by %s", alert_id, body.assigned_to, assigned_by)
    return {"success": True, "assignment_id": assignment_id}


@router.delete("/alerts/{alert_id}/assign")
@limiter.limit("30/minute")
async def unassign_alert_from_user(alert_id: str, request: Request):
    """Remove assignment from an alert."""
    user = await require_auth(request)

    # Check alert exists
    data = get_alert_by_id(alert_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Remove assignment
    success = unassign_alert(alert_id)

    if success:
        logger.info("Alert %s unassigned by %s", alert_id, user["email"])
        return {"success": True, "message": "Assignment removed"}
    else:
        return {"success": False, "message": "No assignment found for this alert"}


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

@router.post("/alerts/{alert_id}/feedback")
@limiter.limit("30/minute")
async def create_alert_feedback(alert_id: str, body: FeedbackRequest, request: Request):
    """Submit feedback for an alert (REAL or FALSE_POSITIVE with category)."""
    user = await require_auth(request)
    user_id = user["email"]

    # Validate alert exists
    data = get_alert_by_id(alert_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Validate feedback_type against FeedbackCategory enum
    try:
        feedback_category = FeedbackCategory(body.feedback_type)
    except ValueError:
        valid_types = [e.value for e in FeedbackCategory]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid feedback_type. Must be one of: {', '.join(valid_types)}"
        )

    # Create feedback
    feedback = AlertFeedbackModel(
        alert_id=alert_id,
        user_id=user_id,
        feedback_type=feedback_category,
        comment=body.comment,
    )
    feedback_id = create_feedback(feedback)

    logger.info("Feedback created for alert %s by %s: %s", alert_id, user_id, feedback_category.value)
    return {"success": True, "feedback_id": feedback_id}


@router.get("/alerts/{alert_id}/feedbacks")
@limiter.limit("60/minute")
async def get_alert_feedbacks(alert_id: str, request: Request):
    """Get all feedback entries for a specific alert."""
    feedbacks = get_feedbacks_for_alert(alert_id)
    return {
        "feedbacks": [FeedbackResponse(**f) for f in feedbacks],
        "total": len(feedbacks)
    }


@router.get("/publishers/{publisher_id}/feedback-history", response_model=FeedbackHistoryResponse)
@limiter.limit("60/minute")
async def get_publisher_history(
    publisher_id: str,
    request: Request,
    limit: int = Query(50, ge=1, le=200)
):
    """Get feedback history for a publisher with alert context."""
    feedbacks = get_publisher_feedback_history(publisher_id, limit)
    return FeedbackHistoryResponse(
        feedbacks=[FeedbackResponse(**f) for f in feedbacks],
        total=len(feedbacks)
    )


# ---------------------------------------------------------------------------
# Manual Interventions
# ---------------------------------------------------------------------------

@router.post("/interventions")
@limiter.limit("30/minute")
async def create_manual_intervention(body: InterventionRequest, request: Request):
    """Create a manual intervention record (pricing rule, floor CPM, etc)."""
    user = await require_auth(request)
    user_id = user["email"]

    # Validate intervention_type against InterventionType enum
    try:
        intervention_type = InterventionType(body.intervention_type)
    except ValueError:
        valid_types = [e.value for e in InterventionType]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid intervention_type. Must be one of: {', '.join(valid_types)}"
        )

    # Parse timestamp string to datetime
    try:
        timestamp = datetime.fromisoformat(body.timestamp.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid timestamp format. Use ISO 8601 format.")

    # Create intervention model
    intervention = ManualInterventionModel(
        timestamp=timestamp,
        publisher_id=body.publisher_id,
        intervention_type=intervention_type,
        description=body.description,
        value_before=body.value_before,
        value_after=body.value_after,
        user_id=user_id,
    )

    intervention_id = create_intervention(intervention)

    logger.info(
        "Manual intervention created: id=%d, type=%s, publisher=%s, user=%s",
        intervention_id, intervention_type.value, body.publisher_id, user_id
    )
    return {"success": True, "intervention_id": intervention_id}


@router.post("/alerts/{alert_id}/link-intervention")
@limiter.limit("30/minute")
async def link_intervention(alert_id: str, body: InterventionLinkRequest, request: Request):
    """Link an existing intervention to an alert."""
    user = await require_auth(request)
    user_id = user["email"]

    # Validate alert exists
    alert_data = get_alert_by_id(alert_id)
    if alert_data is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Validate intervention exists
    from backend.db.operations import get_db
    with get_db() as conn:
        intervention_row = conn.execute(
            "SELECT intervention_id FROM manual_interventions WHERE intervention_id = ?",
            (body.intervention_id,)
        ).fetchone()
        if intervention_row is None:
            raise HTTPException(status_code=404, detail="Intervention not found")

    # Create link
    link_id = link_intervention_to_alert(alert_id, body.intervention_id, user_id)

    logger.info(
        "Intervention %d linked to alert %s by %s",
        body.intervention_id, alert_id, user_id
    )
    return {"success": True, "link_id": link_id}


@router.get("/publishers/{publisher_id}/interventions")
@limiter.limit("60/minute")
async def get_publisher_interventions(
    publisher_id: str,
    request: Request,
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """Get interventions for a publisher with optional date filtering."""
    from backend.db.operations import get_db

    params = [publisher_id]
    query = "SELECT * FROM manual_interventions WHERE publisher_id = ?"

    if date_from:
        query += " AND timestamp >= ?"
        params.append(date_from)
    if date_to:
        query += " AND timestamp <= ?"
        params.append(date_to)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        interventions = [dict(r) for r in rows]

    return {
        "interventions": [InterventionResponse(**i) for i in interventions],
        "total": len(interventions)
    }


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------

def _run_backtest(backtest_id: str, start_date: str, end_date: str, step_hours: int):
    try:
        runner = BacktestRunner(start_date, end_date, step_hours)
        runner.run(backtest_id)
    except Exception as exc:
        logger.error("Backtest %s failed: %s", backtest_id, exc, exc_info=True)
        save_backtest_result({
            "backtest_id": backtest_id,
            "status": "FAILED",
            "error": str(exc),
            "total_checks": 0,
            "alerts_generated": 0,
            "alerts": [],
        })


@router.get("/backtest")
@limiter.limit("60/minute")
def list_backtests(request: Request):
    results = get_all_backtest_results()
    return {"results": results}


@router.post("/backtest", response_model=BacktestStartResponse)
@limiter.limit("5/hour")
def start_backtest(request: Request, body: BacktestRequest, background_tasks: BackgroundTasks):
    backtest_id = f"BT-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

    save_backtest_result({
        "backtest_id": backtest_id,
        "status": "PENDING",
        "total_checks": 0,
        "alerts_generated": 0,
        "alerts": [],
    })

    background_tasks.add_task(
        _run_backtest, backtest_id, body.start_date, body.end_date, body.step_hours
    )

    logger.info("Backtest %s queued: %s to %s", backtest_id, body.start_date, body.end_date)
    return BacktestStartResponse(backtest_id=backtest_id)


@router.get("/backtest/{backtest_id}", response_model=BacktestResultResponse)
@limiter.limit("60/minute")
def get_backtest(request: Request, backtest_id: str):
    result = get_backtest_result(backtest_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Backtest not found")
    return BacktestResultResponse(**result)


# ---------------------------------------------------------------------------
# Pipeline metrics
# ---------------------------------------------------------------------------

@router.get("/metrics")
@limiter.limit("60/minute")
def get_metrics(request: Request, days: int = Query(7, ge=1, le=90)):
    return get_pipeline_metrics(days)


# ---------------------------------------------------------------------------
# Revenue Status 24h
# ---------------------------------------------------------------------------

@router.get("/metrics/revenue-status-24h")
@limiter.limit("60/minute")
def revenue_status_24h(request: Request, date: Optional[str] = Query(None)):
    df = _load_hourly_data()
    if df is None:
        raise HTTPException(status_code=503, detail="Hourly data not available")

    if date is not None:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")
    else:
        target_date = df["timestamp"].dt.date.max()

    # Pre-aggregate revenue by (date, hour) once — avoids 168 scans of 740K rows
    baseline_dates = {target_date - timedelta(weeks=w) for w in range(0, 8)}
    agg = (
        df[df["timestamp"].dt.date.isin(baseline_dates)]
        .groupby([df["timestamp"].dt.date, df["timestamp"].dt.hour])["revenue"]
        .sum()
    )
    # agg is a Series with MultiIndex (date, hour)
    rev_lookup: dict[tuple, float] = agg.to_dict()

    # Check target date has data
    target_hours = {h for (d, h) in rev_lookup if d == target_date}
    if not target_hours:
        raise HTTPException(status_code=404, detail=f"No data for date {target_date}")

    hours_data = []
    total_revenue = 0.0
    total_baseline = 0.0

    for hour in range(24):
        rev = round(rev_lookup.get((target_date, hour), 0.0), 2)

        baseline_values = []
        for week_offset in range(1, 8):
            bl_date = target_date - timedelta(weeks=week_offset)
            bl_rev = rev_lookup.get((bl_date, hour), 0.0)
            if bl_rev > 0:
                baseline_values.append(bl_rev)

        baseline = round(sum(baseline_values) / len(baseline_values), 2) if baseline_values else 0.0
        delta_pct = round((rev - baseline) / baseline * 100, 1) if baseline > 0 else None

        total_revenue += rev
        total_baseline += baseline

        hours_data.append({
            "hour": hour,
            "revenue": rev,
            "baseline": baseline,
            "delta_pct": delta_pct,
        })

    total_revenue = round(total_revenue, 2)
    total_baseline = round(total_baseline, 2)
    total_delta_pct = round((total_revenue - total_baseline) / total_baseline * 100, 1) if total_baseline > 0 else None

    # Previous year same ISO week / same weekday
    prev_year_info = None
    try:
        from backend.api.publisher_routes import _load_adrequests

        iso_year, iso_week, iso_day = target_date.isocalendar()
        prev_year_date = type(target_date).fromisocalendar(iso_year - 1, iso_week, iso_day)

        df_daily = _load_adrequests()
        if df_daily is not None:
            mask_py = df_daily["date"].dt.date == prev_year_date
            py_rev = float(df_daily[mask_py]["revenue"].sum())
            if py_rev > 0:
                py_delta = round((total_revenue - py_rev) / py_rev * 100, 1)
                prev_year_info = {
                    "date": str(prev_year_date),
                    "day_of_week": prev_year_date.strftime("%A"),
                    "total_revenue": round(py_rev, 2),
                    "delta_pct": py_delta,
                    "hourly_avg": round(py_rev / 24, 2),
                }
    except Exception as exc:
        logger.warning("Could not compute prev-year baseline: %s", exc)

    return {
        "date": str(target_date),
        "day_of_week": target_date.strftime("%A"),
        "hours": hours_data,
        "total_revenue": total_revenue,
        "total_baseline": total_baseline,
        "total_delta_pct": total_delta_pct,
        "prev_year": prev_year_info,
    }


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
@limiter.limit("60/minute")
def health_check(request: Request):
    db_ok = True
    try:
        from backend.db.database import get_db
        with get_db() as conn:
            conn.execute("SELECT 1")
    except Exception:
        db_ok = False

    config = get_config()

    # Include last-24h pipeline metrics summary
    pipeline_summary = {}
    try:
        metrics_24h = get_pipeline_metrics(days=1)
        total = metrics_24h.get("total_runs", 0) or 0
        failures = metrics_24h.get("failures", 0) or 0
        pipeline_summary = {
            "last_24h_runs": total,
            "last_24h_failure_rate": round(failures / total, 3) if total > 0 else 0.0,
        }
    except Exception:
        pass

    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        version=config.version,
        db_ok=db_ok,
        scheduler_running=is_scheduler_running(),
        timestamp=datetime.utcnow().isoformat(),
        pipeline_metrics=pipeline_summary,
    )
