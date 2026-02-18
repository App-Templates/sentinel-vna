"""
Data Validator Agent (Node 3)
Schema validation, gap detection, baseline verification, delta computation.
Pure Python - no LLM needed.

A0 (Data Gap): When data is missing beyond configured threshold,
generates an A0 alert instead of stopping the pipeline.
"""

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

    return {
        **state,
        "validation_status": "OK",
        "delta": delta,
        "execution_errors": errors,
    }
