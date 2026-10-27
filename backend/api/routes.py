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
    AlertsPipelineHealth,         # Phase 10 MONITOR-01
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
    get_alerts_pipeline_health,   # Phase 10 MONITOR-01
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
DAILY_PARQUET = BASE_DIR / "data" / "baseline" / "daily_aggregated.parquet"

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
    include_deprecated: bool = Query(
        False, description="If true, surface deprecated alerts in the list."
    ),
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
        include_deprecated=include_deprecated,
    )
    # Coerce sqlite INTEGER 0/1 → bool for Pydantic (defensive even with strict=False).
    for r in rows:
        r["deprecated"] = bool(r.get("deprecated", 0))
    alerts = [AlertSummary(**r) for r in rows]
    return AlertListResponse(alerts=alerts, total=total, limit=limit, offset=offset)


@router.get("/alerts/{alert_id}", response_model=AlertDetailResponse)
@limiter.limit("60/minute")
def get_alert(
    request: Request, alert_id: str,
    include_deprecated: bool = Query(False),
):
    data = get_alert_by_id(alert_id, include_deprecated=include_deprecated)
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

    # Coerce sqlite INTEGER 0/1 → bool for Pydantic (D-17 schema additive fields).
    data["deprecated"] = bool(data.get("deprecated", 0))

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

@router.get("/metrics/revenue-status-24h/{date_path}")
@limiter.limit("60/minute")
def revenue_status_24h_by_date(request: Request, date_path: str):
    """Path-based date selector for static deploy compatibility."""
    return revenue_status_24h(request, date=date_path)


@router.get("/metrics/revenue-status-24h")
@limiter.limit("60/minute")
def revenue_status_24h(request: Request, date: Optional[str] = Query(None)):
    df = _load_hourly_data()
    if df is None:
        raise HTTPException(status_code=503, detail="Hourly data not available")

    # Build per-date hour counts to detect complete vs partial days
    _dates_col = df["timestamp"].dt.date
    _hours_per_date = df.groupby(_dates_col)["timestamp"].apply(lambda x: x.dt.hour.nunique())
    # A complete day has data for most hours (>=20 to allow small gaps)
    complete_dates = sorted(_hours_per_date[_hours_per_date >= 20].index, reverse=True)

    if date is not None:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")
    else:
        # Default to last complete day (not partial)
        if complete_dates:
            target_date = complete_dates[0]
        else:
            target_date = df["timestamp"].dt.date.max()

    # Available dates for selector (last 7 complete days)
    available_dates = [str(d) for d in complete_dates[:7]]

    # Pre-aggregate metrics by (date, hour) once — avoids 168 scans of 740K rows
    baseline_dates = {target_date - timedelta(weeks=w) for w in range(0, 8)}
    df_bl = df[df["timestamp"].dt.date.isin(baseline_dates)]
    _date_col = df_bl["timestamp"].dt.date
    _hour_col = df_bl["timestamp"].dt.hour

    agg = df_bl.groupby([_date_col, _hour_col])["revenue"].sum()
    # agg is a Series with MultiIndex (date, hour)
    rev_lookup: dict[tuple, float] = agg.to_dict()

    # v1.2 extended aggregations
    _extra_metrics = {}
    for metric in ("impressions", "bacino", "clicks", "viewable_impressions", "revenue_gross"):
        if metric in df_bl.columns:
            _extra_metrics[metric] = df_bl.groupby([_date_col, _hour_col])[metric].sum().to_dict()

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

        # v1.2: compute extended KPIs for this hour
        imp = _extra_metrics.get("impressions", {}).get((target_date, hour), 0)
        bac = _extra_metrics.get("bacino", {}).get((target_date, hour), 0)
        clicks = _extra_metrics.get("clicks", {}).get((target_date, hour), 0)
        viewable = _extra_metrics.get("viewable_impressions", {}).get((target_date, hour), 0)
        rev_gross = _extra_metrics.get("revenue_gross", {}).get((target_date, hour), 0)

        ecpm_val = (rev / imp * 1000) if imp > 0 else 0.0
        rpm_val = (rev / bac * 1000) if bac > 0 else 0.0
        ctr_val = (clicks / imp) if imp > 0 else 0.0
        view_val = (viewable / imp) if imp > 0 else 0.0
        gm_val = ((1 - rev / rev_gross) * 100) if rev_gross > 0 else 0.0

        hours_data.append({
            "hour": hour,
            "revenue": rev,
            "baseline": baseline,
            "delta_pct": delta_pct,
            "ecpm": round(ecpm_val, 2),
            "rpm": round(rpm_val, 2),
            "ctr": round(ctr_val, 4),
            "viewability": round(view_val, 4),
            "gross_margin_pct": round(gm_val, 2),
            "impressions": int(imp),
            "bacino": int(bac),
        })

    total_revenue = round(total_revenue, 2)
    total_baseline = round(total_baseline, 2)
    total_delta_pct = round((total_revenue - total_baseline) / total_baseline * 100, 1) if total_baseline > 0 else None

    # Previous year: 7-week rolling average (same weekday, same as baseline logic)
    prev_year_info = None
    try:
        from backend.api.publisher_routes import _load_adrequests

        iso_year, iso_week, iso_day = target_date.isocalendar()
        prev_year_center = type(target_date).fromisocalendar(iso_year - 1, iso_week, iso_day)

        # Collect 7 weeks of same-weekday data around the YoY center date
        prev_year_dates = [prev_year_center - timedelta(weeks=w) for w in range(7)]

        df_daily = _load_adrequests()
        if df_daily is not None:
            py_revs = []
            for py_d in prev_year_dates:
                mask_py = df_daily["date"].dt.date == py_d
                rev = float(df_daily[mask_py]["revenue"].sum())
                if rev > 0:
                    py_revs.append(rev)

            if py_revs:
                py_rev = sum(py_revs) / len(py_revs)
                py_delta = round((total_revenue - py_rev) / py_rev * 100, 1)

                # Estimate hourly YoY curve using baseline hourly distribution
                baseline_hourly_total = sum(h["baseline"] for h in hours_data)
                yoy_hours = []
                for h in hours_data:
                    proportion = h["baseline"] / baseline_hourly_total if baseline_hourly_total > 0 else 1 / 24
                    yoy_hours.append(round(py_rev * proportion, 2))

                prev_year_info = {
                    "date": str(prev_year_center),
                    "day_of_week": prev_year_center.strftime("%A"),
                    "total_revenue": round(py_rev, 2),
                    "delta_pct": py_delta,
                    "hours": yoy_hours,
                    "weeks_averaged": len(py_revs),
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
        "available_dates": available_dates,
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


@router.get("/health/alerts-pipeline", response_model=AlertsPipelineHealth)
@limiter.limit("60/minute")
def health_alerts_pipeline(request: Request):
    """Silent-failure watchdog probe (MONITOR-01, Phase 10).

    Returns a minimal contract consumable by:
      * External monitors (UptimeRobot/synthetic probes) watching for the
        divergence pattern `pipeline_runs_last_24h > 0 AND alerts_last_24h == 0`.
      * Internal meta-alert watchdog at backend/monitoring/silent_failure_watch.py
        (Phase 10-03) that fires a Slack P0 on that divergence.

    Query budget: < 5 seconds on live DB. Handler is thin -- business logic
    lives in backend.db.operations.get_alerts_pipeline_health().
    """
    try:
        metrics = get_alerts_pipeline_health()
    except Exception as e:
        logger.exception("health_alerts_pipeline query failed")
        # Fail-soft: return a signal that downstream watchdogs treat as
        # "health check itself is broken" -- intentional 503 via HTTPException
        # so uptime monitors flag the endpoint, not the data.
        raise HTTPException(status_code=503, detail=f"health_query_failed: {e!r}")

    return AlertsPipelineHealth(**metrics)
