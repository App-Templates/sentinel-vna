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
    BacktestRequest,
    BacktestResultResponse,
    BacktestStartResponse,
    CommentRequest,
    HealthResponse,
    RecheckRequest,
    RecheckResponse,
    ResolveRequest,
    SuccessResponse,
)
from backend.backtest.runner import BacktestRunner
from backend.db.models import AlertStatus, EventType
from backend.db.operations import (
    create_event,
    create_recheck,
    get_alert_by_id,
    get_alerts,
    get_all_backtest_results,
    get_backtest_result,
    get_pipeline_metrics,
    save_backtest_result,
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
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    rows, total = get_alerts(
        severity=severity,
        status=status,
        channel=channel,
        date_from=date_from,
        date_to=date_to,
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

    alert = AlertDetail(**data, events=events)
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
