from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as pa_csv
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
    NetworkTotalsResponse,        # Phase 11 API-01
    RecheckRequest,
    RecheckResponse,
    ResolveRequest,
    SuccessResponse,
)
from backend.backtest.runner import BacktestRunner
from backend.db.demand_layers import demand_layer_for  # Phase 19 V1
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

# Phase 11 API-01 — raw CSV upstream (bypasses parquet top-50 filter for PBI parity)
KPI_CSV_PATH = BASE_DIR / "data" / "sentinel_db" / "daily_kpi.csv"
# Phase 17.4 D2CLOSE-01 — hourly CSV for alert-level revenue (GOOGLE_ADEX only)
HOUR_KPI_CSV_PATH = BASE_DIR / "data" / "sentinel_db" / "hour_kpi.csv"
NETWORK_TOTALS_CHANNELS = {
    "GOOGLE_ADEX", "OPEN_BIDDING", "HEADER_BIDDING_MAGNITE",
    "HEADER_BIDDING_PUBMATIC", "TAM", "DIRECT", "DEAL", "GOOGLE",  # legacy alias
}

# In-memory cache
_hourly_cache: Optional[pd.DataFrame] = None
_kpi_csv_cache: Optional[pa.Table] = None
_kpi_csv_max_date: Optional[str] = None
# Phase 17.4 D2CLOSE-01 — hour_kpi.csv cache (GOOGLE_ADEX hourly, for alert-level revenue)
_hour_kpi_csv_cache: Optional[pa.Table] = None


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


def _compute_baseline_from_env_split(
    environment_split_json,
) -> tuple[Optional[int], Optional[float]]:
    """Phase 11 API-03 — aggregate baseline_bacino + baseline_coverage from env_split JSON blob.

    Replaces TriageSection.tsx:29-32 client-side heuristic
    (`revenueRatio*0.95` + `avgCoverage+0.05`) with the real values
    that data_fetcher_real.py:142-260 already computed at alert
    creation time. Returns (None, None) for empty / malformed blobs
    (deprecated alerts, legacy pre-v1.2 alerts) — no panic.

    R-13 contract: Pure function, no I/O, no side effects. Accepts both the
    raw JSON string (legacy callers) and the already-parsed dict (the path
    used by `get_alert`, where the JSON-blob loop has already deserialized
    `environment_split_json` into `data["environment_split"]`).
    """
    # Phase 17.2 HOTFIX-05 (B2 Marco 2026-05-19) note: when env_split is empty
    # this returns (None, None) — the existing contract is unchanged. Marco's
    # "Bacino + Coverage = 0" root cause turned out to be NOT here but at the
    # consumer (TriageSection.tsx was reading m.bacino / m.coverage instead of
    # the actual payload keys m.bacino_current / m.coverage_current → undefined
    # → ?? 0 → "0" on every alert). Path C fix lives frontend-side. The
    # frontend (TriageSection.tsx) additionally substitutes 'n/a' (not 0) for
    # the CURRENT column when env_split is genuinely empty (defensive Path B
    # layer for legacy pre-Phase-11 alerts). Phase 17.3 may extend the payload
    # with top-level current_bacino / current_coverage if Path A is later
    # chosen; for now Path C (frontend-only) is sufficient honesty. See
    # `.planning/phases/17.2-marco-feedback-hotfix/17.2-05-DIAGNOSIS.md`.
    if not environment_split_json:
        return None, None
    try:
        env = (json.loads(environment_split_json)
               if isinstance(environment_split_json, str)
               else environment_split_json)
    except (json.JSONDecodeError, TypeError):
        return None, None
    if not isinstance(env, dict):
        return None, None
    env_entries = {k: v for k, v in env.items() if isinstance(v, dict)}
    if not env_entries:
        return None, None
    total_bacino = sum(
        v.get("bacino_baseline", 0) or 0 for v in env_entries.values()
    )
    coverages = [
        v["coverage_baseline"]
        for v in env_entries.values()
        if v.get("coverage_baseline") is not None
    ]
    avg_coverage = sum(coverages) / len(coverages) if coverages else None
    return (
        int(total_bacino) if total_bacino > 0 else None,
        float(avg_coverage) if avg_coverage is not None else None,
    )


def _load_kpi_csv() -> Optional[pa.Table]:
    """Phase 11 API-01 — Load daily_kpi.csv with column projection. Cached in-process.

    R-13 + RESEARCH §9 R1 OOM mitigation: column projection (5 of 14 columns) +
    typed conversion + 64MB block size. Subsequent requests hit the cached pa.Table.
    """
    global _kpi_csv_cache, _kpi_csv_max_date
    if _kpi_csv_cache is not None:
        return _kpi_csv_cache
    if not KPI_CSV_PATH.exists():
        logger.warning("daily_kpi.csv not found at %s", KPI_CSV_PATH)
        return None
    try:
        # Column projection: read only what we need for network-totals.
        # Note: `date` is forced to string (not pyarrow auto-inferred date32[day])
        # so equality + ordering against the YYYY-MM-DD query param work directly
        # and `_kpi_csv_max_date` stays a plain string for the 404-range check.
        convert_opts = pa_csv.ConvertOptions(
            include_columns=["date", "channel_group", "revenue_gross",
                             "impressions", "measurable_impressions"],
            column_types={
                "date": pa.string(),
                "revenue_gross": pa.float64(),
                "impressions": pa.int64(),
                "measurable_impressions": pa.int64(),
            },
        )
        read_opts = pa_csv.ReadOptions(block_size=64 * 1024 * 1024)
        tbl = pa_csv.read_csv(str(KPI_CSV_PATH),
                              read_options=read_opts,
                              convert_options=convert_opts)
        _kpi_csv_cache = tbl
        # Compute max date once (used for 404 range check + freshness signal)
        max_date_arr = pc.max(tbl["date"])
        _kpi_csv_max_date = str(max_date_arr.as_py()) if max_date_arr.is_valid else None
        logger.info("Loaded daily_kpi.csv: %d rows, max_date=%s",
                    tbl.num_rows, _kpi_csv_max_date)
        return tbl
    except Exception as e:
        logger.error("Failed to load daily_kpi.csv: %s", e)
        return None


# ---------------------------------------------------------------------------
# Phase 17.4 D2CLOSE-01 — Hourly KPI CSV loader (GOOGLE_ADEX alert-level revenue)
# ---------------------------------------------------------------------------

def _load_hour_kpi_csv() -> Optional[pa.Table]:
    """Phase 17.4 D2CLOSE-01 — Load hour_kpi.csv with column projection. Cached in-process.

    hour_kpi.csv columns: row_id, timestamp (YYYY-MM-DD HH:MM:SS.mmm), ad_unit_id_1,
    environment, channel_gorup (typo in source), revenue_gross, impressions,
    measurable_impressions, viewable_impressions, clicks, ctr, viewability, ecpm.
    GOOGLE_ADEX only (459k rows). Used by data_fetcher_real Path A for hourly alert revenue.
    """
    global _hour_kpi_csv_cache
    if _hour_kpi_csv_cache is not None:
        return _hour_kpi_csv_cache
    if not HOUR_KPI_CSV_PATH.exists():
        logger.warning("hour_kpi.csv not found at %s", HOUR_KPI_CSV_PATH)
        return None
    try:
        convert_opts = pa_csv.ConvertOptions(
            include_columns=["timestamp", "channel_gorup", "revenue_gross",
                             "impressions", "measurable_impressions"],
            column_types={
                "timestamp": pa.string(),
                "channel_gorup": pa.string(),
                "revenue_gross": pa.float64(),
                "impressions": pa.int64(),
                "measurable_impressions": pa.int64(),
            },
        )
        read_opts = pa_csv.ReadOptions(block_size=64 * 1024 * 1024)
        tbl = pa_csv.read_csv(str(HOUR_KPI_CSV_PATH),
                              read_options=read_opts,
                              convert_options=convert_opts)
        _hour_kpi_csv_cache = tbl
        logger.info("Loaded hour_kpi.csv: %d rows", tbl.num_rows)
        return tbl
    except Exception as e:
        logger.error("Failed to load hour_kpi.csv: %s", e)
        return None


# ---------------------------------------------------------------------------
# Phase 17.4 D2CLOSE-01 — Shared network-totals aggregation helper
# ---------------------------------------------------------------------------

def _compute_network_totals_for_channel(
    date: str,
    channel: str,
    bypass_top50: bool = False,
) -> Optional[dict]:
    """Phase 17.4 D2CLOSE-01 — shared aggregation used by /metrics/network-totals
    endpoint AND by backend.agents.data_fetcher_real for GOOGLE_ADEX BACKTEST mode.

    Args:
        date: ISO date YYYY-MM-DD
        channel: must be in NETWORK_TOTALS_CHANNELS
        bypass_top50: when True AND channel == 'GOOGLE_ADEX', the aggregation
            explicitly bypasses any top-50 publisher filter. As of Phase 17.4,
            daily_kpi.csv already has no top-50 filter (Phase 11 D1 hybrid trade-off
            only applies to the parquet path), so bypass_top50=True is a no-op at
            this layer — but the param is exposed to (a) make the intent explicit
            in the consumer (data_fetcher_real) and (b) future-proof against a
            Phase 18 caching layer that might re-introduce a filter.
            For all other channels: bypass_top50=True is rejected at the endpoint
            layer (HTTP 400) per D-03. The helper itself accepts the param without
            validation — the endpoint enforces the whitelist.

    Returns:
        dict with keys {date, channel, revenue_gross, impressions,
                        measurable_impressions, source_date, source}
        OR None if no rows match (channel × date has 0 rows in daily_kpi.csv).
        Raises ValueError if channel not in NETWORK_TOTALS_CHANNELS.
        Raises FileNotFoundError if daily_kpi.csv not available.
        Raises LookupError if date out of CSV range.
    """
    if channel not in NETWORK_TOTALS_CHANNELS:
        raise ValueError(
            f"channel must be one of {sorted(NETWORK_TOTALS_CHANNELS)}; got {channel!r}"
        )
    tbl = _load_kpi_csv()
    if tbl is None:
        raise FileNotFoundError(f"daily_kpi.csv not available at {KPI_CSV_PATH}")
    if _kpi_csv_max_date is None or date > _kpi_csv_max_date:
        raise LookupError(
            f"date {date} out of CSV range (max available: {_kpi_csv_max_date})"
        )
    mask = pc.and_(
        pc.equal(tbl["date"], date),
        pc.equal(tbl["channel_group"], channel),
    )
    filtered = tbl.filter(mask)
    if filtered.num_rows == 0:
        return None
    revenue_gross = float(pc.sum(filtered["revenue_gross"]).as_py() or 0.0)
    impressions = int(pc.sum(filtered["impressions"]).as_py() or 0)
    measurable_raw = pc.sum(filtered["measurable_impressions"]).as_py()
    measurable_impressions = int(measurable_raw) if measurable_raw is not None else None
    return {
        "date": date,
        "channel": channel,
        "revenue_gross": round(revenue_gross, 2),
        "impressions": impressions,
        "measurable_impressions": measurable_impressions,
        "source_date": _kpi_csv_max_date,
        "source": "data/sentinel_db/daily_kpi.csv",
    }


def _compute_hourly_totals_for_channel(
    timestamp_str: str,
    channel: str,
) -> Optional[dict]:
    """Phase 17.4 D2CLOSE-01 — hourly aggregation from hour_kpi.csv for alert-level revenue.

    Used exclusively by backend.agents.data_fetcher_real for GOOGLE_ADEX BACKTEST mode
    (D-02 in-process call, D-03 GOOGLE_ADEX-only). Returns the hourly revenue aggregate
    matching PBI hourly figures (no top-50 filter — hour_kpi.csv is the raw upstream source).

    Args:
        timestamp_str: ISO hour slot "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD HH:00:00"
                       matching the format in hour_kpi.csv ("YYYY-MM-DD HH:MM:SS.mmm")
        channel: must be 'GOOGLE_ADEX' (hour_kpi.csv is GOOGLE_ADEX-only)

    Returns:
        dict with keys {timestamp_str, channel, revenue_gross, impressions,
                        measurable_impressions, source}
        OR None if no rows match (hour × channel not in hour_kpi.csv).
        Raises FileNotFoundError if hour_kpi.csv not available.
    """
    tbl = _load_hour_kpi_csv()
    if tbl is None:
        raise FileNotFoundError(f"hour_kpi.csv not available at {HOUR_KPI_CSV_PATH}")
    # hour_kpi.csv timestamps are "YYYY-MM-DD HH:MM:SS.mmm" format.
    # The query timestamp arrives as "YYYY-MM-DD HH:00:00" — match by prefix.
    # Use string prefix filter: filter where timestamp STARTS WITH "YYYY-MM-DD HH:"
    ts_prefix = timestamp_str[:13]  # "YYYY-MM-DD HH"
    mask = pc.and_(
        pc.starts_with(tbl["timestamp"], ts_prefix),
        pc.equal(tbl["channel_gorup"], channel),
    )
    filtered = tbl.filter(mask)
    if filtered.num_rows == 0:
        return None
    revenue_gross = float(pc.sum(filtered["revenue_gross"]).as_py() or 0.0)
    impressions = int(pc.sum(filtered["impressions"]).as_py() or 0)
    measurable_raw = pc.sum(filtered["measurable_impressions"]).as_py()
    measurable_impressions = int(measurable_raw) if measurable_raw is not None else None
    return {
        "timestamp_str": timestamp_str,
        "channel": channel,
        "revenue_gross": round(revenue_gross, 2),
        "impressions": impressions,
        "measurable_impressions": measurable_impressions,
        "source": "data/sentinel_db/hour_kpi.csv",
    }


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
    # Phase 19 V1: derive demand_layer from channel_group via the bridge mapping
    # in backend/db/demand_layers.py (Marco feedback 2026-05-19).
    for r in rows:
        r["deprecated"] = bool(r.get("deprecated", 0))
        r["demand_layer"] = demand_layer_for(r["channel_group"])
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

    # Phase 11 API-03 — compute server-side baseline. The JSON-blob loop above
    # already parsed `environment_split_json` → `data["environment_split"]` (dict).
    # The helper accepts the parsed dict directly (and tolerates None / empty /
    # legacy blobs by returning (None, None) — see _compute_baseline_from_env_split).
    baseline_bacino, baseline_coverage = _compute_baseline_from_env_split(
        data.get("environment_split", {})
    )
    data["baseline_bacino"] = baseline_bacino
    data["baseline_coverage"] = baseline_coverage

    # Coerce sqlite INTEGER 0/1 → bool for Pydantic (D-17 schema additive fields).
    data["deprecated"] = bool(data.get("deprecated", 0))

    # Phase 19 V1 — derive demand_layer for AlertDetail responses too.
    data["demand_layer"] = demand_layer_for(data["channel_group"])

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

    # Pandas 2.x: df["date"] is datetime64[us] tz-naive; coerce comparison
    # operands to matching naive pd.Timestamp to avoid TypeError on mixed tz.
    alert_ts_naive = alert_ts.replace(tzinfo=None) if alert_ts.tzinfo else alert_ts
    start_date = pd.Timestamp(alert_ts_naive - timedelta(days=7))
    end_date = pd.Timestamp(alert_ts_naive)

    mask = (df["date"] >= start_date) & (df["date"] <= end_date) & (df["channel_group"] == channel)
    filtered = df[mask]

    daily = filtered.groupby("date").agg({"revenue": "sum", "impressions": "sum"}).reset_index()

    trend_points = []
    for _, row in daily.iterrows():
        current_date = row["date"]
        baseline_revs = []
        for weeks_back in range(1, 8):
            baseline_date = pd.Timestamp(current_date - timedelta(days=7 * weeks_back))
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
    """Get feedback history for a publisher with alert context.

    Phase 17.1 MAP-08 (B-01 fix): publisher_id is a clean PBI-style name
    (e.g. "Vocento", "Mondadori"). Resolve to ALL underlying raw
    ad_unit_names via Plan 01 mapping; pass the set to
    get_publisher_feedback_history which emits IN (?, ?, ...) SQL so
    historical rows written with raw ad_unit_name values aggregate.
    """
    from backend.api.publisher_routes import _resolve_publisher_ad_units
    ad_unit_names = _resolve_publisher_ad_units(publisher_id)
    feedbacks = get_publisher_feedback_history(ad_unit_names, limit)
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
    """Get interventions for a publisher with optional date filtering.

    Phase 17.1 MAP-08 (B-01 fix): publisher_id is a clean PBI-style name.
    Resolve to ALL underlying raw ad_unit_names via Plan 01 mapping; SQL
    uses IN (?, ?, ...) over the set so historical rows with raw names
    aggregate correctly. Placeholder count is derived from len(ids); no
    user data is ever string-interpolated into the SQL.
    """
    from backend.api.publisher_routes import _resolve_publisher_ad_units
    from backend.db.operations import get_db

    ad_unit_names = _resolve_publisher_ad_units(publisher_id)
    if not ad_unit_names:
        # Reverse-mapping produced nothing — no underlying ad_units, no rows.
        return {"interventions": [], "total": 0}

    ids = list(ad_unit_names)
    placeholders = ",".join("?" * len(ids))
    params: list = list(ids)
    query = f"SELECT * FROM manual_interventions WHERE publisher_id IN ({placeholders})"

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

    # Available dates for selector — full range of complete days in the
    # parquet (Phase 17 widening from Phase 13's 7-day cap; the cristallizzato
    # snapshot covers ~90 days, operators expect to navigate the full window).
    available_dates = [str(d) for d in complete_dates]

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


# ---------------------------------------------------------------------------
# Phase 11 API-01 — Network Totals (PBI parity)
# ---------------------------------------------------------------------------

@router.get("/metrics/network-totals", response_model=NetworkTotalsResponse)
@limiter.limit("60/minute")
def network_totals(
    request: Request,
    date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$",
                      description="ISO date YYYY-MM-DD"),
    channel: str = Query(..., min_length=1, max_length=64),
    bypass_top50: bool = Query(
        False,
        description=(
            "Phase 17.4 D2CLOSE-01: when True, explicitly bypass any top-50 "
            "publisher filter (daily_kpi.csv already has no such filter as of "
            "Phase 11; param is forward-compatible). Only valid for channel="
            "'GOOGLE_ADEX' — rejected with 400 for other channels per D-03."
        ),
    ),
):
    """Phase 11 API-01 + Phase 17.4 D2CLOSE-01 — PBI-parity totals from raw daily_kpi.csv.

    Closes RC-(a) for the email Vito 2026-04-22 #2/#3 lamentele.
    Verified: Jan 12 GOOGLE_ADEX revenue_gross = €27,245.63 (PBI €27,200 +0.17%).
    Phase 17.4: adds optional bypass_top50 param (GOOGLE_ADEX-only whitelist per D-03).
    """
    # D-03: bypass_top50 is GOOGLE_ADEX-only whitelist (other channels rejected)
    if bypass_top50 and channel != "GOOGLE_ADEX":
        raise HTTPException(
            status_code=400,
            detail=(
                f"bypass_top50=true is only valid for channel='GOOGLE_ADEX'; "
                f"got channel={channel!r}. Per Phase 17.4 D-03 whitelist."
            ),
        )
    try:
        result = _compute_network_totals_for_channel(date, channel, bypass_top50)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="daily_kpi.csv not available")
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"no rows for date={date} channel={channel}",
        )
    return NetworkTotalsResponse(
        date=result["date"],
        channel=result["channel"],
        revenue_gross=result["revenue_gross"],
        revenue_net=None,  # Phase 13 CORR-03 will add net via revenue_share.yaml
        impressions=result["impressions"],
        measurable_impressions=result["measurable_impressions"],
        currency="EUR",
        source_date=result["source_date"],
        source=result["source"],
    )
