"""
Anomaly Detector Agent (Node 4)
Detects anomalies using statistical methods with optional LLM enhancement.
Uses Anthropic SDK (Claude Haiku) with pure-Python fallback.

Consecutive-hours checks for A1 and A3 rules:
- A1 P0: drop >= -15% for 2+ consecutive hours
- A1 P1: drop >= -10% for 2+ consecutive hours
- A1 P2: drop >= -5% for 4+ consecutive hours
- A3: near-zero for 3+ consecutive periods
"""

import json
import os
import time as _time
from datetime import timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from backend.utils.config_loader import get_config
from backend.utils.logger import get_logger
from backend.workflow.state import AlertState

logger = get_logger("agent.anomaly_detector")

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "anomaly_detector_prompt.txt"

# --- Consecutive hours check helpers ---

_BASE_DIR = Path(__file__).parent.parent.parent
_HOURLY_PARQUET = _BASE_DIR / "data" / "baseline" / "hourly_aggregated.parquet"
_hourly_cache: Optional[pd.DataFrame] = None
_hourly_cache_ts: float = 0.0
_CACHE_TTL_SECONDS: float = 3600.0  # 1 hour


def _get_hourly_df() -> Optional[pd.DataFrame]:
    """Load hourly parquet with module-level caching and TTL."""
    global _hourly_cache, _hourly_cache_ts
    now = _time.monotonic()
    if _hourly_cache is not None and (now - _hourly_cache_ts) < _CACHE_TTL_SECONDS:
        return _hourly_cache
    if not _HOURLY_PARQUET.exists():
        logger.warning("Hourly parquet not found at %s", _HOURLY_PARQUET)
        return None
    try:
        df = pd.read_parquet(_HOURLY_PARQUET)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        _hourly_cache = df
        _hourly_cache_ts = now
        logger.info("Hourly parquet cache loaded/refreshed (%d rows)", len(df))
        return df
    except Exception as e:
        logger.error("Failed to load hourly parquet for consecutive check: %s", e)
        return None


def _hourly_revenue_and_baseline(
    df: pd.DataFrame, ts: pd.Timestamp, channel: str,
) -> Optional[Tuple[float, float]]:
    """
    For a single hour+channel, compute aggregate revenue and
    7-week same-hour/same-weekday baseline average.
    Returns (current_revenue, baseline_revenue) or None if data missing.
    """
    mask = (df["timestamp"] == ts) & (df["channel_group"] == channel)
    current_rows = df[mask]
    if current_rows.empty:
        return None

    current_rev = float(current_rows["revenue"].sum())

    baseline_revs: List[float] = []
    for weeks_back in range(1, 8):
        bl_ts = ts - timedelta(days=7 * weeks_back)
        bl_mask = (df["timestamp"] == bl_ts) & (df["channel_group"] == channel)
        bl_rows = df[bl_mask]
        if not bl_rows.empty:
            baseline_revs.append(float(bl_rows["revenue"].sum()))

    if not baseline_revs:
        return None

    return (current_rev, sum(baseline_revs) / len(baseline_revs))


def _hourly_near_zero_check(
    df: pd.DataFrame, ts: pd.Timestamp, channel: str,
    rev_threshold: float, cov_threshold: float,
) -> Optional[bool]:
    """
    Check if a single hour meets near-zero conditions:
    revenue < rev_threshold OR coverage < cov_threshold.
    Returns True/False, or None if data missing.
    """
    mask = (df["timestamp"] == ts) & (df["channel_group"] == channel)
    rows = df[mask]
    if rows.empty:
        return None

    total_rev = float(rows["revenue"].sum())
    total_impressions = float(rows["impressions"].sum())
    total_bacino = float(rows["bacino"].sum())
    coverage = total_impressions / total_bacino if total_bacino > 0 else 0.0

    return total_rev < rev_threshold or coverage < cov_threshold


def _parse_state_timestamp(state: AlertState) -> Optional[pd.Timestamp]:
    """Parse state timestamp into a tz-naive pd.Timestamp."""
    ts_str = state.get("timestamp", "")
    if not ts_str:
        return None
    try:
        ts = pd.Timestamp(ts_str)
        if ts.tzinfo is not None:
            ts = ts.tz_localize(None)
        return ts
    except Exception:
        logger.warning("Cannot parse timestamp '%s'", ts_str)
        return None


def _check_consecutive_a1(
    state: AlertState, severity: str, threshold_pct: float, duration_hours: int,
) -> bool:
    """
    Verify that the revenue drop exceeds threshold_pct for duration_hours
    consecutive hours (current hour + previous hours).
    Returns True if consecutive condition is met, False otherwise.
    Graceful degradation: returns False if data is insufficient.
    """
    df = _get_hourly_df()
    if df is None:
        logger.info("A1 consecutive check skipped: no hourly data")
        return False

    current_ts = _parse_state_timestamp(state)
    if current_ts is None:
        return False
    channel = state.get("channel_group", "GOOGLE")

    for hours_back in range(duration_hours):
        check_ts = current_ts - timedelta(hours=hours_back)
        result = _hourly_revenue_and_baseline(df, check_ts, channel)
        if result is None:
            logger.info(
                "A1 consecutive: no data for %s (%d/%d), not triggering",
                check_ts, hours_back + 1, duration_hours,
            )
            return False

        current_rev, baseline_rev = result
        if baseline_rev <= 0:
            return False

        delta_pct = ((current_rev - baseline_rev) / baseline_rev) * 100.0
        if delta_pct > threshold_pct:
            logger.info(
                "A1 consecutive: hour %s delta=%.1f%% above threshold %.1f%%, "
                "chain broken at %d/%d",
                check_ts, delta_pct, threshold_pct, hours_back + 1, duration_hours,
            )
            return False

    logger.info(
        "A1 consecutive PASSED: %d hours with drop <= %.1f%% (%s)",
        duration_hours, threshold_pct, severity,
    )
    return True


def _check_consecutive_a3(state: AlertState) -> bool:
    """
    Verify near-zero conditions persist for consecutive_periods consecutive hours.
    Returns True if consecutive condition met, False otherwise.
    """
    config = get_config()
    nz = config.near_zero
    periods = nz.consecutive_periods

    df = _get_hourly_df()
    if df is None:
        logger.info("A3 consecutive check skipped: no hourly data")
        return False

    current_ts = _parse_state_timestamp(state)
    if current_ts is None:
        return False
    channel = state.get("channel_group", "GOOGLE")

    for hours_back in range(periods):
        check_ts = current_ts - timedelta(hours=hours_back)
        is_nz = _hourly_near_zero_check(
            df, check_ts, channel,
            nz.revenue_threshold_eur, nz.coverage_threshold,
        )
        if is_nz is None:
            logger.info(
                "A3 consecutive: no data for %s (%d/%d), not triggering",
                check_ts, hours_back + 1, periods,
            )
            return False
        if not is_nz:
            logger.info(
                "A3 consecutive: hour %s NOT near-zero, chain broken at %d/%d",
                check_ts, hours_back + 1, periods,
            )
            return False

    logger.info("A3 consecutive PASSED: %d near-zero periods confirmed", periods)
    return True


def _detect_linear_drift(state: AlertState) -> Optional[dict]:
    """
    Detect gradual revenue decline using linear regression on 14-30 day window.

    Returns dict with drift analysis if significant trend detected:
    {
        "slope_pct_per_day": float,
        "cumulative_drop_pct": float,
        "r_squared": float,
        "days_analyzed": int,
        "projection_7d_pct": float,
    }
    Or None if drift not significant or data insufficient.
    """
    from backend.agents.data_fetcher_real import _fetch_drift_baseline

    config = get_config()
    dr = config.drift_regression

    if not dr.enabled:
        return None

    current_ts = _parse_state_timestamp(state)
    if current_ts is None:
        return None

    channel = state.get("channel_group", "GOOGLE")

    # Try to fetch max window, fall back to min if data sparse
    baseline_df = None
    for window in range(dr.window_days_max, dr.window_days_min - 1, -1):
        baseline_df = _fetch_drift_baseline(current_ts, channel, window)
        if baseline_df is not None and len(baseline_df) >= dr.min_data_points:
            break

    if baseline_df is None or len(baseline_df) < dr.min_data_points:
        logger.info(
            "Drift regression skipped: insufficient data (need %d days, got %s)",
            dr.min_data_points,
            len(baseline_df) if baseline_df is not None else 0,
        )
        return None

    # Prepare data for regression: X = day index (0, 1, 2...), Y = revenue
    revenues = baseline_df["revenue"].values
    days = np.arange(len(revenues))

    # Linear regression: revenue = slope * day + intercept
    slope, intercept, r_value, p_value, std_err = stats.linregress(days, revenues)

    # Convert slope to percentage per day relative to mean revenue
    mean_revenue = np.mean(revenues)
    if mean_revenue <= 0:
        return None

    slope_pct_per_day = (slope / mean_revenue) * 100.0

    # Calculate cumulative drop percentage over the window
    # cumulative_pct = slope_pct_per_day * days_analyzed
    days_analyzed = len(revenues)
    cumulative_drop_pct = slope_pct_per_day * days_analyzed

    # Check significance
    r_squared = r_value ** 2

    # Only trigger if:
    # 1. Slope is negative and exceeds threshold
    # 2. Cumulative drop exceeds threshold
    # 3. R² > 0.5 (reasonable linear fit)
    is_significant = (
        slope_pct_per_day <= dr.slope_threshold_percent_per_day
        and cumulative_drop_pct <= dr.cumulative_drop_threshold_percent
        and r_squared >= 0.5
        and p_value < 0.05
    )

    if not is_significant:
        logger.info(
            "Drift regression: trend not significant (slope=%.2f%%/day, "
            "cumulative=%.1f%%, R²=%.3f, p=%.4f)",
            slope_pct_per_day, cumulative_drop_pct, r_squared, p_value,
        )
        return None

    # Project 7 days forward to show where it's heading
    projection_7d_pct = slope_pct_per_day * 7

    logger.info(
        "Drift regression ALERT: slope=%.2f%%/day over %d days, "
        "cumulative=%.1f%%, R²=%.3f, 7d projection=%.1f%%",
        slope_pct_per_day, days_analyzed, cumulative_drop_pct, r_squared, projection_7d_pct,
    )

    return {
        "slope_pct_per_day": round(slope_pct_per_day, 2),
        "cumulative_drop_pct": round(cumulative_drop_pct, 1),
        "r_squared": round(r_squared, 3),
        "days_analyzed": days_analyzed,
        "projection_7d_pct": round(projection_7d_pct, 1),
    }


def _compute_14d_moving_average(state: AlertState) -> Optional[dict]:
    """
    Compare current revenue vs 14-day moving average.

    Returns dict:
    {
        "avg_revenue_14d": float,
        "current_revenue": float,
        "delta_pct": float,
        "divergence_hours": int,  # How many consecutive hours below threshold
        "triggered": bool,
        "severity": str,
    }

    Or None if data insufficient.

    This uses hourly data from the past 14 days (same hour, same weekday pattern)
    to compute a moving average baseline, then compares current hour against it.
    Triggers only if divergence is sustained for configured hours.
    """
    config = get_config()
    ma = config.comparative_alerting.moving_average_14d

    if not ma.enabled:
        return None

    current_ts = _parse_state_timestamp(state)
    if current_ts is None:
        return None

    channel = state.get("channel_group", "GOOGLE")
    df = _get_hourly_df()
    if df is None:
        return None

    # Current hour revenue
    mask_current = (df["timestamp"] == current_ts) & (df["channel_group"] == channel)
    current_rows = df[mask_current]
    if current_rows.empty:
        return None
    current_revenue = float(current_rows["revenue"].sum())

    # Compute 14-day moving average: same hour of day, last 14 days
    # Use same-hour same-weekday pattern for seasonal stability
    hour_of_day = current_ts.hour
    day_of_week = current_ts.weekday()

    baseline_revenues = []
    for days_back in range(1, 15):  # 14 days back
        past_ts = current_ts - timedelta(days=days_back)
        # Only include if same day-of-week (Monday vs Monday, etc)
        if past_ts.weekday() == day_of_week:
            mask_past = (df["timestamp"] == past_ts) & (df["channel_group"] == channel)
            past_rows = df[mask_past]
            if not past_rows.empty:
                baseline_revenues.append(float(past_rows["revenue"].sum()))

    if len(baseline_revenues) < 2:  # Need at least 2 data points
        logger.info("14d moving average: insufficient baseline data (%d points)", len(baseline_revenues))
        return None

    avg_revenue = sum(baseline_revenues) / len(baseline_revenues)

    if avg_revenue <= 0:
        return None

    delta_pct = ((current_revenue - avg_revenue) / avg_revenue) * 100.0

    # Check divergence for consecutive hours
    # For now, we compute for current hour only. To check "sustained" divergence,
    # we need to look back at previous hours. For simplicity, we'll count consecutive
    # hours in a follow-up (Phase 1.1). For now, mark as triggered if single hour exceeds.

    triggered = False
    severity = "NONE"
    divergence_hours = 0

    if delta_pct <= ma.divergence_threshold_percent:
        # Check if this is sustained (look back sustained_hours)
        consecutive_count = 0
        for hours_back in range(ma.sustained_hours):
            check_ts = current_ts - timedelta(hours=hours_back)
            mask_check = (df["timestamp"] == check_ts) & (df["channel_group"] == channel)
            check_rows = df[mask_check]
            if check_rows.empty:
                break  # Gap in data, can't verify sustained divergence

            check_revenue = float(check_rows["revenue"].sum())

            # Recompute baseline for that hour
            check_hour = check_ts.hour
            check_dow = check_ts.weekday()
            check_baseline = []
            for d in range(1, 15):
                past_check = check_ts - timedelta(days=d)
                if past_check.weekday() == check_dow:
                    mask_b = (df["timestamp"] == past_check) & (df["channel_group"] == channel)
                    b_rows = df[mask_b]
                    if not b_rows.empty:
                        check_baseline.append(float(b_rows["revenue"].sum()))

            if len(check_baseline) < 2:
                break

            check_avg = sum(check_baseline) / len(check_baseline)
            if check_avg <= 0:
                break

            check_delta = ((check_revenue - check_avg) / check_avg) * 100.0

            if check_delta <= ma.divergence_threshold_percent:
                consecutive_count += 1
            else:
                break  # Chain broken

        divergence_hours = consecutive_count

        if divergence_hours >= ma.sustained_hours:
            triggered = True
            severity = ma.severity
            logger.info(
                "14d moving average ALERT: %.2f EUR vs %.2f EUR avg (%.1f%%), "
                "sustained %d hours, severity=%s",
                current_revenue, avg_revenue, delta_pct, divergence_hours, severity,
            )
        else:
            logger.info(
                "14d moving average: divergence detected but not sustained "
                "(%d/%d hours required)",
                divergence_hours, ma.sustained_hours,
            )
    else:
        logger.info(
            "14d moving average OK: %.2f EUR vs %.2f EUR avg (%.1f%%)",
            current_revenue, avg_revenue, delta_pct,
        )

    return {
        "avg_revenue_14d": round(avg_revenue, 2),
        "current_revenue": round(current_revenue, 2),
        "delta_pct": round(delta_pct, 1),
        "divergence_hours": divergence_hours,
        "triggered": triggered,
        "severity": severity,
    }


def _detect_margin_anomaly(
    state: AlertState, config
) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Detect margin anomaly (A5) based on eCPM drop vs baseline.

    eCPM = (Revenue / Impressions) * 1000

    Returns: (triggered, severity, margin_metrics_dict)
    """
    current = state.get("current_metrics", {})
    baseline = state.get("baseline_metrics", {})

    current_rev = current.get("revenue", 0)
    current_impr = current.get("impressions", 0)
    baseline_rev = baseline.get("revenue", 0)
    baseline_impr = baseline.get("impressions", 0)

    min_impr = config.margin_alert.min_impressions

    # Skip if insufficient impressions for reliable eCPM
    if current_impr < min_impr or baseline_impr < min_impr:
        logger.debug(
            "A5 skipped: insufficient impressions (current=%d, baseline=%d, min=%d)",
            current_impr, baseline_impr, min_impr,
        )
        return (False, None, None)

    current_ecpm = (current_rev / current_impr) * 1000 if current_impr > 0 else 0
    baseline_ecpm = (baseline_rev / baseline_impr) * 1000 if baseline_impr > 0 else 0

    if baseline_ecpm == 0:
        logger.debug("A5 skipped: baseline eCPM is zero")
        return (False, None, None)

    ecpm_delta_pct = ((current_ecpm - baseline_ecpm) / baseline_ecpm) * 100

    # Check severity thresholds (P1 is stricter, check first)
    severity = None
    thresholds = config.margin_alert.ecpm_drop_thresholds
    if "P1" in thresholds and ecpm_delta_pct <= thresholds["P1"].drop_percent:
        severity = "P1"
    elif "P2" in thresholds and ecpm_delta_pct <= thresholds["P2"].drop_percent:
        severity = "P2"

    if severity:
        margin_metrics = {
            "current_ecpm": round(current_ecpm, 2),
            "baseline_ecpm": round(baseline_ecpm, 2),
            "ecpm_delta_pct": round(ecpm_delta_pct, 2),
            "current_impressions": int(current_impr),
            "baseline_impressions": int(baseline_impr),
            "severity": severity,
        }
        logger.info(
            "A5 triggered: eCPM drop %.1f%% (current=%.2f, baseline=%.2f) -> %s",
            ecpm_delta_pct, current_ecpm, baseline_ecpm, severity,
        )
        return (True, severity, margin_metrics)

    logger.debug("A5 not triggered: eCPM delta %.1f%% within thresholds", ecpm_delta_pct)
    return (False, None, None)


def _detect_coverage_zero(state: AlertState, config) -> Tuple[bool, Optional[dict]]:
    """
    Detect coverage-zero scenario (A6).

    Coverage = impressions / bacino
    Triggers when coverage < threshold for consecutive hours with sufficient bacino.

    Returns: (triggered, coverage_zero_metrics_dict)
    """
    current = state.get("current_metrics", {})
    baseline = state.get("baseline_metrics", {})

    current_impr = current.get("impressions", 0)
    current_bacino = current.get("bacino", 0)
    baseline_impr = baseline.get("impressions", 0)
    baseline_bacino = baseline.get("bacino", 0)

    # Skip if insufficient bacino (coverage-zero in low-traffic periods is expected)
    if current_bacino < config.coverage_zero_alert.min_bacino:
        logger.debug("A6 skipped: bacino too low (current=%d, min=%d)",
                     current_bacino, config.coverage_zero_alert.min_bacino)
        return (False, None)

    current_coverage = current_impr / current_bacino if current_bacino > 0 else 0
    baseline_coverage = baseline_impr / baseline_bacino if baseline_bacino > 0 else 0

    # Check if coverage is below threshold
    if current_coverage >= config.coverage_zero_alert.coverage_threshold:
        logger.debug("A6 not triggered: coverage %.4f >= threshold %.4f",
                     current_coverage, config.coverage_zero_alert.coverage_threshold)
        return (False, None)

    coverage_zero_metrics = {
        "current_coverage": round(current_coverage, 4),
        "baseline_coverage": round(baseline_coverage, 4),
        "current_impressions": int(current_impr),
        "current_bacino": int(current_bacino),
        "baseline_impressions": int(baseline_impr),
        "baseline_bacino": int(baseline_bacino),
        "severity": config.coverage_zero_alert.severity,
    }

    logger.info("A6 triggered: coverage %.4f < threshold %.4f (bacino=%d, impressions=%d)",
                current_coverage, config.coverage_zero_alert.coverage_threshold,
                current_bacino, current_impr)
    return (True, coverage_zero_metrics)


def _load_prompt_template() -> str:
    """Load the prompt template from file."""
    try:
        return PROMPT_PATH.read_text()
    except FileNotFoundError:
        logger.warning("Prompt template not found at %s, using inline", PROMPT_PATH)
        return "Analyze metrics: {rev_current} vs {rev_baseline} (delta {rev_delta}%). Z-score: {rev_zscore}. Return JSON with alert_triggered, severity, confidence, reasoning."


def _calculate_zscore(current: float, baseline: float, std: float) -> float:
    """Calculate Z-score."""
    if std <= 0:
        return 0.0
    return round((current - baseline) / std, 2)


def _evaluate_dual_thresholds(
    delta_pct: float,
    comparison_type: str,  # "revenue_drop", "yesterday_delta", "ma_14d_divergence"
    config,
) -> tuple[bool, str]:
    """
    Evaluate delta against dual thresholds (operational vs attention).

    Returns (triggered, severity):
    - If below operational threshold: (True, P0/P1/P2 based on magnitude)
    - If below attention threshold but above operational: (True, P2-WATCH)
    - Otherwise: (False, NONE)
    """
    dt = config.dual_thresholds

    if not dt.enabled:
        # Fall back to single threshold (existing behavior)
        # For backward compatibility, use operational threshold
        operational_thresh = getattr(dt.operational, f"{comparison_type}_percent")
        if delta_pct <= operational_thresh:
            return (True, "P1")  # Default severity for single threshold
        return (False, "NONE")

    operational_thresh = getattr(dt.operational, f"{comparison_type}_percent")
    attention_thresh = getattr(dt.attention, f"{comparison_type}_percent")

    # Check operational threshold first (more severe)
    if delta_pct <= operational_thresh:
        # Operational alert — map to P0/P1/P2 based on magnitude
        # Use existing severity mapping from A1 rules
        if delta_pct <= -30:
            return (True, "P0")
        elif delta_pct <= -20:
            return (True, "P1")
        else:
            return (True, "P2")

    # Check attention threshold
    if delta_pct <= attention_thresh:
        # Attention alert — needs monitoring but not immediate action
        return (True, dt.attention_severity)

    # No threshold exceeded
    return (False, "NONE")


def _statistical_fallback(state: AlertState) -> AlertState:
    """
    Pure-Python anomaly detection without LLM.
    Uses Z-scores and threshold rules from config.
    """
    logger.info("Using statistical fallback (no API key)")

    config = get_config()
    delta = state.get("delta", {})
    historical = state.get("historical_stats", {})
    trigger = state.get("trigger_type", "A1")

    rev_pct = delta.get("revenue_pct", 0)
    bac_pct = delta.get("bacino_pct", 0)
    cov_pct = delta.get("coverage_pct", 0)
    rev_std = historical.get("revenue_std", 1.0)
    hour = historical.get("hour_of_day", 12)
    dow = historical.get("day_of_week", "Monday")

    current = state.get("current_metrics", {})
    baseline = state.get("baseline_metrics", {})

    rev_zscore = _calculate_zscore(
        current.get("revenue", 0), baseline.get("revenue", 0), rev_std
    )

    # Compute 14d moving average comparison (v1.1)
    ma_14d = _compute_14d_moving_average(state)
    if ma_14d is not None:
        state["moving_average_14d"] = ma_14d

    # Time-of-day context
    is_off_peak = hour < 6 or hour >= 22
    is_weekend = dow in ("Saturday", "Sunday")
    time_factor = "off_peak" if is_off_peak else ("weekend" if is_weekend else "normal_hours")

    # Adjust thresholds for off-peak
    threshold_multiplier = 1.5 if is_off_peak else (1.2 if is_weekend else 1.0)

    # A5: Margin/eCPM drop
    if trigger == "A5" and config.margin_alert.enabled:
        logger.info("A5 margin detection triggered")
        triggered, severity, margin_metrics = _detect_margin_anomaly(state, config)
        if triggered and margin_metrics:
            return {
                **state,
                "alert_triggered": True,
                "alert_rule": "A5",
                "severity": severity,
                "margin_metrics": margin_metrics,
                "execution_errors": list(state.get("execution_errors", [])),
            }
        else:
            logger.info("A5 not triggered (eCPM within thresholds)")
            return {
                **state,
                "alert_triggered": False,
                "alert_rule": "A5",
                "severity": "NONE",
                "execution_errors": list(state.get("execution_errors", [])),
            }

    # A6: Coverage zero
    if trigger == "A6" and config.coverage_zero_alert.enabled:
        logger.info("A6 coverage-zero detection triggered")
        triggered, coverage_zero_metrics = _detect_coverage_zero(state, config)
        if triggered and coverage_zero_metrics:
            return {
                **state,
                "alert_triggered": True,
                "alert_rule": "A6",
                "severity": coverage_zero_metrics["severity"],
                "coverage_zero_metrics": coverage_zero_metrics,
                "execution_errors": list(state.get("execution_errors", [])),
            }
        else:
            logger.info("A6 not triggered (coverage above threshold)")
            return {
                **state,
                "alert_triggered": False,
                "alert_rule": "A6",
                "severity": "NONE",
                "execution_errors": list(state.get("execution_errors", [])),
            }

    # A3: Near-zero check with consecutive periods validation
    if trigger == "A3":
        nz = config.near_zero
        current_is_near_zero = (
            current.get("revenue", 0) < nz.revenue_threshold_eur
            or current.get("coverage", 1.0) < nz.coverage_threshold
        )
        if current_is_near_zero:
            # Verify consecutive periods before triggering
            consecutive_ok = _check_consecutive_a3(state)
            if consecutive_ok:
                return {
                    **state,
                    "alert_triggered": True,
                    "alert_rule": "A3",
                    "severity": "P0",
                    "z_score": rev_zscore,
                    "confidence": 0.95,
                    "execution_errors": list(state.get("execution_errors", [])),
                }
            else:
                logger.info(
                    "A3 suppressed: current hour is near-zero but consecutive check "
                    "failed (%d periods required)", nz.consecutive_periods,
                )
                return {
                    **state,
                    "alert_triggered": False,
                    "alert_rule": "A3",
                    "severity": "NONE",
                    "z_score": rev_zscore,
                    "confidence": 0.60,
                    "execution_errors": list(state.get("execution_errors", [])),
                }

    # A2: Drift check (existing 7-day logic PLUS new linear regression)
    if trigger == "A2":
        drift_pct = delta.get("drift_7d_pct", 0)
        drift_thresh = config.drift_detection.threshold_percent

        # First try linear regression drift detection
        drift_regression = _detect_linear_drift(state)

        if drift_regression is not None:
            # Regression detected significant gradual decline
            # Store regression results in state for report_builder to use
            return {
                **state,
                "alert_triggered": True,
                "alert_rule": "A2",
                "severity": "P1",  # Gradual declines are P1
                "z_score": rev_zscore,
                "confidence": 0.85,  # High confidence from regression fit
                "drift_regression": drift_regression,
                "execution_errors": list(state.get("execution_errors", [])),
            }

        # Fall back to existing 7-day drift logic if regression didn't trigger
        if drift_pct <= drift_thresh:
            severity = "P1" if drift_pct <= drift_thresh * 1.5 else "P2"
            return {
                **state,
                "alert_triggered": True,
                "alert_rule": "A2",
                "severity": severity,
                "z_score": rev_zscore,
                "confidence": 0.75,
                "execution_errors": list(state.get("execution_errors", [])),
            }
        else:
            return {
                **state,
                "alert_triggered": False,
                "alert_rule": "A2",
                "severity": "NONE",
                "z_score": rev_zscore,
                "confidence": 0.80,
                "execution_errors": list(state.get("execution_errors", [])),
            }

    # A1: Spike/drop thresholds with dual threshold support
    # First check operational thresholds (adjusted for time of day)
    p0_thresh = config.revenue_anomaly.P0.drop_percent * threshold_multiplier
    p1_thresh = config.revenue_anomaly.P1.drop_percent * threshold_multiplier
    p2_thresh = config.revenue_anomaly.P2.drop_percent * threshold_multiplier

    alert_triggered = False
    severity = "NONE"
    confidence = 0.5
    dual_eval = None

    # Use dual thresholds if enabled
    if config.dual_thresholds.enabled:
        dual_eval = _evaluate_dual_thresholds(rev_pct, "revenue_drop", config)
        if dual_eval[0]:  # Triggered
            candidate_severity = dual_eval[1]
            if candidate_severity == "P0":
                candidate_threshold = config.revenue_anomaly.P0.drop_percent
                candidate_duration = config.revenue_anomaly.P0.duration_hours
                candidate_confidence = min(0.95, 0.6 + abs(rev_zscore) * 0.1)
            elif candidate_severity == "P1":
                candidate_threshold = config.revenue_anomaly.P1.drop_percent
                candidate_duration = config.revenue_anomaly.P1.duration_hours
                candidate_confidence = min(0.90, 0.5 + abs(rev_zscore) * 0.1)
            elif candidate_severity in ("P2", "P2-WATCH"):
                candidate_threshold = config.revenue_anomaly.P2.drop_percent
                candidate_duration = config.revenue_anomaly.P2.duration_hours
                candidate_confidence = min(0.85, 0.4 + abs(rev_zscore) * 0.1)
            else:
                candidate_severity = None
                candidate_threshold = 0
                candidate_duration = 0
                candidate_confidence = 0.6
        else:
            candidate_severity = None
            candidate_threshold = 0
            candidate_duration = 0
            candidate_confidence = max(0.6, 1.0 - abs(rev_pct) / 100)
    else:
        # Original single-threshold logic (backward compatibility)
        if rev_pct <= p0_thresh:
            candidate_severity = "P0"
            candidate_threshold = config.revenue_anomaly.P0.drop_percent
            candidate_duration = config.revenue_anomaly.P0.duration_hours
            candidate_confidence = min(0.95, 0.6 + abs(rev_zscore) * 0.1)
        elif rev_pct <= p1_thresh:
            candidate_severity = "P1"
            candidate_threshold = config.revenue_anomaly.P1.drop_percent
            candidate_duration = config.revenue_anomaly.P1.duration_hours
            candidate_confidence = min(0.90, 0.5 + abs(rev_zscore) * 0.1)
        elif rev_pct <= p2_thresh:
            candidate_severity = "P2"
            candidate_threshold = config.revenue_anomaly.P2.drop_percent
            candidate_duration = config.revenue_anomaly.P2.duration_hours
            candidate_confidence = min(0.85, 0.4 + abs(rev_zscore) * 0.1)
        else:
            candidate_severity = None
            candidate_threshold = 0
            candidate_duration = 0
            candidate_confidence = max(0.6, 1.0 - abs(rev_pct) / 100)

    if candidate_severity is not None:
        # Verify consecutive hours before triggering
        # Use raw (non-multiplied) threshold for consecutive check since
        # each hour's delta is computed independently against its own baseline
        consecutive_ok = _check_consecutive_a1(
            state, candidate_severity, candidate_threshold, candidate_duration,
        )
        if consecutive_ok:
            alert_triggered = True
            severity = candidate_severity
            confidence = candidate_confidence
        else:
            logger.info(
                "A1 %s suppressed: current drop %.1f%% but consecutive check failed "
                "(%d hours required at threshold %.1f%%)",
                candidate_severity, rev_pct, candidate_duration, candidate_threshold,
            )
            alert_triggered = False
            severity = "NONE"
            confidence = 0.50
    else:
        confidence = candidate_confidence

    # Z-score sanity: if z-score < 1.5 and off-peak, likely false positive
    if alert_triggered and abs(rev_zscore) < 1.5 and is_off_peak:
        logger.info("Suppressing alert: low Z-score (%.2f) during off-peak", rev_zscore)
        alert_triggered = False
        severity = "NONE"
        confidence = 0.70

    return {
        **state,
        "alert_triggered": alert_triggered,
        "alert_rule": "A1",
        "severity": severity,
        "z_score": rev_zscore,
        "confidence": confidence,
        "execution_errors": list(state.get("execution_errors", [])),
    }


def _llm_analysis(state: AlertState) -> AlertState:
    """LLM-enhanced anomaly detection using Claude Haiku."""
    from backend.utils.llm_retry import call_llm_with_retry

    config = get_config()
    delta = state.get("delta", {})
    historical = state.get("historical_stats", {})
    current = state.get("current_metrics", {})
    baseline = state.get("baseline_metrics", {})
    rev_std = historical.get("revenue_std", 1.0)

    rev_zscore = _calculate_zscore(
        current.get("revenue", 0), baseline.get("revenue", 0), rev_std
    )
    # Use real std from historical_stats (computed from baseline data points)
    bac_std = historical.get("bacino_std", max(1, baseline.get("bacino", 1) * 0.1))
    cov_std = historical.get("coverage_std", max(0.01, baseline.get("coverage", 0.8) * 0.05))
    bac_zscore = _calculate_zscore(
        current.get("bacino", 0), baseline.get("bacino", 0), bac_std
    )
    cov_zscore = _calculate_zscore(
        current.get("coverage", 0), baseline.get("coverage", 0), cov_std
    )

    template = _load_prompt_template()
    prompt = template.format(
        channel_group=state.get("channel_group", "GOOGLE"),
        timestamp=state.get("timestamp", ""),
        trigger_type=state.get("trigger_type", "A1"),
        hour_of_day=historical.get("hour_of_day", 12),
        day_of_week=historical.get("day_of_week", "Monday"),
        rev_current=f"{current.get('revenue', 0):,.2f}",
        rev_baseline=f"{baseline.get('revenue', 0):,.2f}",
        rev_delta=f"{delta.get('revenue_pct', 0):+.1f}%",
        bac_current=f"{current.get('bacino', 0):,}",
        bac_baseline=f"{baseline.get('bacino', 0):,}",
        bac_delta=f"{delta.get('bacino_pct', 0):+.1f}%",
        cov_current=f"{current.get('coverage', 0):.4f}",
        cov_baseline=f"{baseline.get('coverage', 0):.4f}",
        cov_delta=f"{delta.get('coverage_pct', 0):+.1f}%",
        rev_zscore=f"{rev_zscore:.2f}",
        bac_zscore=f"{bac_zscore:.2f}",
        cov_zscore=f"{cov_zscore:.2f}",
        rev_std=f"{rev_std:,.2f}",
        rev_min_for_hour=f"{historical.get('revenue_min_for_hour', 0):,.2f}",
        p0_threshold=config.revenue_anomaly.P0.drop_percent,
        p0_duration=config.revenue_anomaly.P0.duration_hours,
        p1_threshold=config.revenue_anomaly.P1.drop_percent,
        p1_duration=config.revenue_anomaly.P1.duration_hours,
        p2_threshold=config.revenue_anomaly.P2.drop_percent,
        p2_duration=config.revenue_anomaly.P2.duration_hours,
    )

    raw_text = call_llm_with_retry(
        model="claude-haiku-4-5-20251001",
        prompt=prompt,
        max_tokens=1024,
    )
    if raw_text is None:
        raise RuntimeError("LLM call failed after retries")
    # Extract JSON from response
    try:
        # Try to find JSON block
        if "```json" in raw_text:
            json_str = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            json_str = raw_text.split("```")[1].split("```")[0].strip()
        else:
            json_str = raw_text.strip()
        result = json.loads(json_str)
    except (json.JSONDecodeError, IndexError):
        logger.warning("Failed to parse LLM response, falling back to statistical")
        return _statistical_fallback(state)

    alert_triggered = result.get("alert_triggered", False)
    severity = result.get("severity", "NONE")
    confidence = float(result.get("confidence", 0.5))

    if severity == "NONE":
        alert_triggered = False

    return {
        **state,
        "alert_triggered": alert_triggered,
        "alert_rule": state.get("trigger_type", "A1"),
        "severity": severity,
        "z_score": rev_zscore,
        "confidence": confidence,
        "execution_errors": list(state.get("execution_errors", [])),
    }


def anomaly_detector_agent(state: AlertState) -> AlertState:
    """
    Main entry point. Uses LLM if API key available, else pure statistical fallback.
    """
    logger.info("Anomaly detector started | trigger=%s", state.get("trigger_type"))

    # A0 bypass: data gap alert already generated by data_validator, pass through
    if state.get("alert_rule") == "A0":
        logger.info("A0 data gap alert detected, skipping anomaly analysis")
        return state

    # Check for validation errors upstream
    if state.get("validation_status") != "OK":
        logger.warning("Skipping anomaly detection: validation_status=%s", state.get("validation_status"))
        return {
            **state,
            "alert_triggered": False,
            "severity": "NONE",
            "z_score": 0.0,
            "confidence": 0.0,
        }

    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))

    if has_api_key:
        try:
            result = _llm_analysis(state)
            logger.info(
                "LLM anomaly detection: triggered=%s, severity=%s, confidence=%.2f",
                result.get("alert_triggered"),
                result.get("severity"),
                result.get("confidence", 0),
            )
            return result
        except Exception as e:
            logger.warning("LLM analysis failed (%s), using statistical fallback", e)
            errors = list(state.get("execution_errors", []))
            errors.append(f"LLM anomaly detection failed: {e}")
            state = {**state, "execution_errors": errors}

    result = _statistical_fallback(state)
    logger.info(
        "Statistical anomaly detection: triggered=%s, severity=%s, confidence=%.2f",
        result.get("alert_triggered"),
        result.get("severity"),
        result.get("confidence", 0),
    )
    return result
