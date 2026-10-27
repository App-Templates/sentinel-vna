"""
Data Validator Agent (Node 3)
Schema validation, gap detection, baseline verification, delta computation.
Pure Python - no LLM needed.

A0 (Data Gap): When data is missing beyond configured threshold,
generates an A0 alert instead of stopping the pipeline.
"""

from typing import Optional
from pathlib import Path
from datetime import timedelta

from backend.utils.config_loader import get_config
from backend.utils.logger import get_logger
from backend.workflow.state import AlertState

logger = get_logger("agent.data_validator")

REQUIRED_METRIC_FIELDS = ["revenue", "bacino", "coverage"]


def _safe_pct(current: float, baseline: float) -> float:
    """Calculate percentage change safely."""
    if baseline == 0:
        return -100.0 if current == 0 else 100.0
    return round(((current - baseline) / abs(baseline)) * 100, 2)


def _compute_yesterday_delta(state: AlertState) -> Optional[dict]:
    """
    Compare current hour revenue vs same hour yesterday.

    Returns dict:
    {
        "same_hours_revenue_yesterday": float,
        "current_hour_revenue": float,
        "delta_pct": float,
        "triggered": bool,
        "severity": str (P0/P1/P2/NONE),
    }

    Or None if data insufficient.
    """
    import pandas as pd

    config = get_config()
    yc = config.comparative_alerting.yesterday_comparison

    if not yc.enabled:
        return None

    # Get current hour timestamp and channel
    ts_str = state.get("timestamp", "")
    if not ts_str:
        return None

    try:
        current_ts = pd.Timestamp(ts_str)
        if current_ts.tzinfo is not None:
            current_ts = current_ts.tz_localize(None)
    except Exception:
        logger.warning("Cannot parse timestamp '%s' for yesterday comparison", ts_str)
        return None

    channel = state.get("channel_group", "GOOGLE")

    # Load hourly parquet (reuse existing cache if available)
    _BASE_DIR = Path(__file__).parent.parent.parent
    _HOURLY_PARQUET = _BASE_DIR / "data" / "baseline" / "hourly_aggregated.parquet"

    if not _HOURLY_PARQUET.exists():
        logger.warning("Hourly parquet not found for yesterday comparison")
        return None

    try:
        df = pd.read_parquet(_HOURLY_PARQUET)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    except Exception as e:
        logger.error("Failed to load hourly parquet: %s", e)
        return None

    # Current hour revenue
    mask_current = (df["timestamp"] == current_ts) & (df["channel_group"] == channel)
    current_rows = df[mask_current]
    if current_rows.empty:
        return None
    current_revenue = float(current_rows["revenue"].sum())

    # Yesterday same hour revenue
    yesterday_ts = current_ts - timedelta(days=1)
    mask_yesterday = (df["timestamp"] == yesterday_ts) & (df["channel_group"] == channel)
    yesterday_rows = df[mask_yesterday]
    if yesterday_rows.empty:
        return None
    yesterday_revenue = float(yesterday_rows["revenue"].sum())

    if yesterday_revenue <= 0:
        return None

    # Calculate delta percentage
    delta_pct = ((current_revenue - yesterday_revenue) / yesterday_revenue) * 100.0

    # Determine if triggered and severity
    triggered = False
    severity = "NONE"

    if delta_pct <= yc.threshold_percent:
        triggered = True
        # Map to severity based on magnitude
        if delta_pct <= -30:
            severity = yc.severity_mapping.get("below_minus_30", "P0")
        elif delta_pct <= -20:
            severity = yc.severity_mapping.get("below_minus_20", "P1")
        elif delta_pct <= -10:
            severity = yc.severity_mapping.get("below_minus_10", "P2")
        else:
            severity = "P2"  # Default for anything beyond -10%

        logger.info(
            "Yesterday comparison ALERT: %.2f EUR today vs %.2f EUR yesterday (%.1f%%), severity=%s",
            current_revenue, yesterday_revenue, delta_pct, severity,
        )
    else:
        logger.info(
            "Yesterday comparison OK: %.2f EUR today vs %.2f EUR yesterday (%.1f%%)",
            current_revenue, yesterday_revenue, delta_pct,
        )

    return {
        "same_hours_revenue_yesterday": round(yesterday_revenue, 2),
        "current_hour_revenue": round(current_revenue, 2),
        "delta_pct": round(delta_pct, 1),
        "triggered": triggered,
        "severity": severity,
    }


def data_validator_agent(state: AlertState) -> AlertState:
    """
    Validate fetched data, detect gaps, compute deltas.
    Sets validation_status: OK, DATA_GAP, SCHEMA_ERROR, BASELINE_INSUFFICIENT.
    """
    logger.info("Data validator started")
    errors = list(state.get("execution_errors", []))

    current = state.get("current_metrics")
    baseline = state.get("baseline_metrics")
    historical = state.get("historical_stats", {})

    # Schema validation
    if not current or not isinstance(current, dict):
        errors.append("current_metrics is missing or invalid")
        return {
            **state,
            "validation_status": "SCHEMA_ERROR",
            "execution_errors": errors,
        }

    if not baseline or not isinstance(baseline, dict):
        errors.append("baseline_metrics is missing or invalid")
        return {
            **state,
            "validation_status": "SCHEMA_ERROR",
            "execution_errors": errors,
        }

    # Check required fields
    for field in REQUIRED_METRIC_FIELDS:
        if field not in current:
            errors.append(f"Missing field in current_metrics: {field}")
            return {
                **state,
                "validation_status": "SCHEMA_ERROR",
                "execution_errors": errors,
            }
        if field not in baseline:
            errors.append(f"Missing field in baseline_metrics: {field}")
            return {
                **state,
                "validation_status": "SCHEMA_ERROR",
                "execution_errors": errors,
            }

    # Data gap detection: check if baseline data points are sufficient
    data_points = historical.get("baseline_data_points", 0)
    if data_points < 4:
        errors.append(f"Insufficient baseline data: {data_points} points (need >= 4)")
        # A0: generate data gap alert if enabled
        config = get_config()
        if config.data_gap.enabled:
            gap_hours = historical.get("gap_hours", config.data_gap.max_gap_hours)
            if gap_hours >= config.data_gap.max_gap_hours:
                logger.warning(
                    "A0 triggered: baseline insufficient (%d points, gap ~%dh)",
                    data_points, gap_hours,
                )
                return {
                    **state,
                    "alert_triggered": True,
                    "alert_rule": "A0",
                    "severity": config.data_gap.severity,
                    "triage_label": "DATA_GAP",
                    "validation_status": "GAP_ALERT",
                    "alert_payload": {
                        "gap_type": "BASELINE_INSUFFICIENT",
                        "data_points_available": data_points,
                        "data_points_required": 4,
                        "gap_hours_estimated": gap_hours,
                        "last_available_timestamp": historical.get("last_available_timestamp"),
                        "channel_group": state.get("channel_group"),
                        "timestamp": state.get("timestamp"),
                    },
                    "execution_errors": errors,
                }
        return {
            **state,
            "validation_status": "BASELINE_INSUFFICIENT",
            "execution_errors": errors,
        }

    # Check for zero/None values indicating data gaps
    if current.get("revenue") is None or current.get("bacino") is None:
        errors.append("Data gap detected: null values in current metrics")
        # A0: generate data gap alert if enabled
        config = get_config()
        if config.data_gap.enabled:
            gap_hours = historical.get("gap_hours", config.data_gap.max_gap_hours)
            logger.warning(
                "A0 triggered: null values in current metrics (gap ~%dh)", gap_hours,
            )
            return {
                **state,
                "alert_triggered": True,
                "alert_rule": "A0",
                "severity": config.data_gap.severity,
                "triage_label": "DATA_GAP",
                "validation_status": "GAP_ALERT",
                "alert_payload": {
                    "gap_type": "NULL_CURRENT_METRICS",
                    "missing_fields": [
                        f for f in ("revenue", "bacino")
                        if current.get(f) is None
                    ],
                    "gap_hours_estimated": gap_hours,
                    "last_available_timestamp": historical.get("last_available_timestamp"),
                    "channel_group": state.get("channel_group"),
                    "timestamp": state.get("timestamp"),
                },
                "execution_errors": errors,
            }
        return {
            **state,
            "validation_status": "DATA_GAP",
            "execution_errors": errors,
        }

    # Compute deltas
    rev_current = float(current["revenue"])
    rev_baseline = float(baseline["revenue"])
    bac_current = float(current["bacino"])
    bac_baseline = float(baseline["bacino"])
    cov_current = float(current["coverage"])
    cov_baseline = float(baseline["coverage"])

    delta = {
        "revenue_abs": round(rev_current - rev_baseline, 2),
        "revenue_pct": _safe_pct(rev_current, rev_baseline),
        "bacino_abs": int(bac_current - bac_baseline),
        "bacino_pct": _safe_pct(bac_current, bac_baseline),
        "coverage_abs": round(cov_current - cov_baseline, 4),
        "coverage_pct": _safe_pct(cov_current, cov_baseline),
    }

    # Per-publisher deltas
    pub_current = current.get("publishers", {})
    pub_baseline = baseline.get("publishers", {})
    publisher_deltas = {}
    for pub_id in pub_current:
        pc = pub_current[pub_id]
        pb = pub_baseline.get(pub_id, {"revenue": 0, "bacino": 0, "coverage": 0})
        publisher_deltas[pub_id] = {
            "revenue_current": pc.get("revenue", 0),
            "revenue_baseline": pb.get("revenue", 0),
            "revenue_delta_abs": round(pc.get("revenue", 0) - pb.get("revenue", 0), 2),
            "revenue_delta_pct": _safe_pct(pc.get("revenue", 0), pb.get("revenue", 0)),
            "bacino_current": pc.get("bacino", 0),
            "bacino_baseline": pb.get("bacino", 0),
            "coverage_current": round(pc.get("coverage", 0), 4),
            "coverage_baseline": round(pb.get("coverage", 0), 4),
        }
    delta["publishers"] = publisher_deltas

    # Per-geo deltas
    geo_current = current.get("geo", {})
    geo_baseline = baseline.get("geo", {})
    geo_deltas = {}
    for cluster in geo_current:
        gc = geo_current[cluster]
        gb = geo_baseline.get(cluster, {"revenue": 0, "bacino": 0, "coverage": 0})
        geo_deltas[cluster] = {
            "revenue_current": gc.get("revenue", 0),
            "revenue_baseline": gb.get("revenue", 0),
            "revenue_delta_abs": round(gc.get("revenue", 0) - gb.get("revenue", 0), 2),
            "revenue_delta_pct": _safe_pct(gc.get("revenue", 0), gb.get("revenue", 0)),
        }
    delta["geo"] = geo_deltas

    # Per-environment deltas
    env_current = current.get("environment", {})
    env_baseline = baseline.get("environment", {})
    env_deltas = {}
    for env_name in env_current:
        ec = env_current[env_name]
        eb = env_baseline.get(env_name, {"revenue": 0, "bacino": 0, "coverage": 0})
        env_deltas[env_name] = {
            "revenue_current": ec.get("revenue", 0),
            "revenue_baseline": eb.get("revenue", 0),
            "revenue_delta_abs": round(ec.get("revenue", 0) - eb.get("revenue", 0), 2),
            "revenue_delta_pct": _safe_pct(ec.get("revenue", 0), eb.get("revenue", 0)),
        }
    delta["environment"] = env_deltas

    # Drift delta (A2)
    drift_cur = historical.get("drift_current_7d", 0)
    drift_prev = historical.get("drift_prev_7d", 0)
    if drift_prev > 0:
        delta["drift_7d_pct"] = _safe_pct(drift_cur, drift_prev)
    else:
        delta["drift_7d_pct"] = 0.0

    logger.info(
        "Validation OK: rev_delta=%.2f%%, bac_delta=%.2f%%, cov_delta=%.2f%%",
        delta["revenue_pct"],
        delta["bacino_pct"],
        delta["coverage_pct"],
    )

    # Compute yesterday comparison (v1.1)
    yesterday_comp = _compute_yesterday_delta(state)
    if yesterday_comp is not None:
        state["yesterday_comparison"] = yesterday_comp

    return {
        **state,
        "validation_status": "OK",
        "delta": delta,
        "execution_errors": errors,
    }
