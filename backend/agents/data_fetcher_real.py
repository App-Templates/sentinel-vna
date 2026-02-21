"""
Data Fetcher Agent with Real Parquet Data Integration
Loads from pre-aggregated parquet files with synthetic fallback.
Data source priority: Athena -> GAM -> Parquet.
"""

import hashlib
import json
import os
import time as _time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from backend.utils.config_loader import get_config
from backend.utils.logger import get_logger
from backend.workflow.state import AlertState

logger = get_logger("agent.data_fetcher")

# Paths to pre-aggregated parquet files
BASE_DIR = Path(__file__).parent.parent.parent
HOURLY_PARQUET = BASE_DIR / "data" / "baseline" / "hourly_aggregated.parquet"
DAILY_CHANNEL_PARQUET = BASE_DIR / "data" / "baseline" / "daily_channel_aggregated.parquet"
DAILY_ADREQUESTS_PARQUET = BASE_DIR / "data" / "baseline" / "daily_adrequests_aggregated.parquet"

# Cache loaded data in memory (with TTL timestamps)
_hourly_data_cache = None
_hourly_data_cache_ts: float = 0.0
_daily_channel_cache = None
_daily_channel_cache_ts: float = 0.0
_daily_adrequests_cache = None
_daily_adrequests_cache_ts: float = 0.0

# Default TTL in seconds (fallback if config unreadable)
_DEFAULT_CACHE_TTL_SECONDS = 24 * 3600  # 24 hours


def _get_cache_ttl_seconds() -> float:
    """Read cache_ttl_hours from alerting_rules.yaml, convert to seconds."""
    try:
        config = get_config()
        ttl_hours = config.data_sources.cache_ttl_hours
        return float(ttl_hours) * 3600
    except Exception:
        return _DEFAULT_CACHE_TTL_SECONDS


def _is_cache_valid(loaded_at: float) -> bool:
    """Check if a cache entry is still within its TTL."""
    if loaded_at == 0.0:
        return False
    return (_time.time() - loaded_at) < _get_cache_ttl_seconds()


def _load_hourly_data() -> Optional[pd.DataFrame]:
    """Load hourly aggregated parquet into memory (cache with TTL)."""
    global _hourly_data_cache, _hourly_data_cache_ts

    if _hourly_data_cache is not None and _is_cache_valid(_hourly_data_cache_ts):
        return _hourly_data_cache

    if _hourly_data_cache is not None:
        logger.info("Hourly data cache expired, reloading from disk")

    if not os.path.exists(HOURLY_PARQUET):
        logger.warning(f"Hourly parquet not found at {HOURLY_PARQUET}")
        return None

    try:
        df = pd.read_parquet(HOURLY_PARQUET)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        _hourly_data_cache = df
        _hourly_data_cache_ts = _time.time()
        logger.info(f"Loaded hourly data: {len(df):,} rows, date range {df['timestamp'].min()} to {df['timestamp'].max()}")
        return df
    except Exception as e:
        logger.error(f"Failed to load hourly parquet: {e}")
        return None


def _load_daily_channel_data() -> Optional[pd.DataFrame]:
    """Load daily channel aggregated parquet (cache with TTL)."""
    global _daily_channel_cache, _daily_channel_cache_ts

    if _daily_channel_cache is not None and _is_cache_valid(_daily_channel_cache_ts):
        return _daily_channel_cache

    if _daily_channel_cache is not None:
        logger.info("Daily channel cache expired, reloading from disk")

    if not os.path.exists(DAILY_CHANNEL_PARQUET):
        logger.warning(f"Daily channel parquet not found at {DAILY_CHANNEL_PARQUET}")
        return None

    try:
        df = pd.read_parquet(DAILY_CHANNEL_PARQUET)
        df['date'] = pd.to_datetime(df['date'])
        _daily_channel_cache = df
        _daily_channel_cache_ts = _time.time()
        logger.info(f"Loaded daily channel data: {len(df):,} rows")
        return df
    except Exception as e:
        logger.error(f"Failed to load daily channel parquet: {e}")
        return None


def _load_daily_adrequests_data() -> Optional[pd.DataFrame]:
    """Load daily adrequests aggregated parquet (cache with TTL)."""
    global _daily_adrequests_cache, _daily_adrequests_cache_ts

    if _daily_adrequests_cache is not None and _is_cache_valid(_daily_adrequests_cache_ts):
        return _daily_adrequests_cache

    if _daily_adrequests_cache is not None:
        logger.info("Daily adrequests cache expired, reloading from disk")

    if not os.path.exists(DAILY_ADREQUESTS_PARQUET):
        logger.warning(f"Daily adrequests parquet not found at {DAILY_ADREQUESTS_PARQUET}")
        return None

    try:
        df = pd.read_parquet(DAILY_ADREQUESTS_PARQUET)
        df['date'] = pd.to_datetime(df['date'])
        _daily_adrequests_cache = df
        _daily_adrequests_cache_ts = _time.time()
        logger.info(f"Loaded daily adrequests data: {len(df):,} rows")
        return df
    except Exception as e:
        logger.error(f"Failed to load daily adrequests parquet: {e}")
        return None


def _get_hourly_metrics(df: pd.DataFrame, ts: datetime, channel: str) -> dict:
    """
    Get aggregated metrics for a specific hour and channel.
    Returns metrics aggregated across all publishers/environments/geos.
    """
    # Filter to exact hour and channel
    mask = (df['timestamp'] == ts) & (df['channel_group'] == channel)
    df_filtered = df[mask]

    if df_filtered.empty:
        return None

    # Aggregate across all dimensions
    total_revenue = df_filtered['revenue'].sum()
    total_bacino = df_filtered['bacino'].sum()
    total_impressions = df_filtered['impressions'].sum()

    # Recalculate coverage from totals
    coverage = total_impressions / total_bacino if total_bacino > 0 else 0.0

    # Get publisher breakdown
    publishers = {}
    pub_group = df_filtered.groupby('publisher_id').agg({
        'revenue': 'sum',
        'bacino': 'sum',
        'impressions': 'sum'
    })

    for pub, row in pub_group.iterrows():
        pub_coverage = row['impressions'] / row['bacino'] if row['bacino'] > 0 else 0.0
        publishers[pub] = {
            "revenue": round(row['revenue'], 2),
            "bacino": int(row['bacino']),
            "coverage": round(pub_coverage, 4),
        }

    # Get geo breakdown (for hourly data, geo_cluster is 'ALL')
    geo = {}
    geo_group = df_filtered.groupby('geo_cluster').agg({
        'revenue': 'sum',
        'bacino': 'sum',
        'impressions': 'sum'
    })

    for cluster, row in geo_group.iterrows():
        geo_coverage = row['impressions'] / row['bacino'] if row['bacino'] > 0 else 0.0
        geo[cluster] = {
            "revenue": round(row['revenue'], 2),
            "bacino": int(row['bacino']),
            "coverage": round(geo_coverage, 4),
        }

    # Get environment breakdown
    env = {}
    env_group = df_filtered.groupby('environment').agg({
        'revenue': 'sum',
        'bacino': 'sum',
        'impressions': 'sum'
    })

    for e, row in env_group.iterrows():
        env_coverage = row['impressions'] / row['bacino'] if row['bacino'] > 0 else 0.0
        env[e] = {
            "revenue": round(row['revenue'], 2),
            "bacino": int(row['bacino']),
            "coverage": round(env_coverage, 4),
        }

    return {
        "timestamp": ts.isoformat(),
        "channel_group": channel,
        "revenue": round(total_revenue, 2),
        "bacino": int(total_bacino),
        "coverage": round(coverage, 4),
        "publishers": publishers,
        "geo": geo,
        "environment": env,
    }


def _calculate_baseline_from_hourly(df: pd.DataFrame, current_ts: datetime, channel: str) -> dict:
    """
    Calculate 7-day baseline: same hour, same weekday average over up to 7 weeks.
    Uses data points from -7d, -14d, -21d, -28d, -35d, -42d, -49d.

    Excludes periods with manual interventions to avoid contaminating baseline with
    intentional operational changes (pricing rules, floor CPM adjustments, etc).
    """
    from backend.db.operations import get_interventions_for_period

    baseline_points = []
    excluded_intervention_count = 0

    # Get interventions for the entire baseline window (49 days back)
    baseline_start = current_ts - timedelta(days=7 * 7)  # 49 days back
    baseline_end = current_ts
    interventions = get_interventions_for_period(baseline_start, baseline_end, publisher_id=None)

    # Extract intervention timestamps into set for fast lookup
    intervention_times = set()
    if interventions:
        for intervention in interventions:
            try:
                intervention_ts = pd.to_datetime(intervention['timestamp'])
                # Make timezone-naive for comparison
                if intervention_ts.tzinfo is not None:
                    intervention_ts = intervention_ts.tz_localize(None)
                intervention_times.add(intervention_ts)
            except Exception as e:
                logger.warning("Failed to parse intervention timestamp: %s", e)

    for weeks_back in range(1, 8):
        baseline_ts = current_ts - timedelta(days=7 * weeks_back)

        # Check if this timestamp has an intervention
        if baseline_ts in intervention_times:
            excluded_intervention_count += 1
            logger.debug(
                "Excluding baseline point at %s due to manual intervention",
                baseline_ts.isoformat()
            )
            continue

        metrics = _get_hourly_metrics(df, baseline_ts, channel)
        if metrics:
            baseline_points.append(metrics)

    if not baseline_points:
        return None

    # Calculate averages
    avg_rev = sum(p["revenue"] for p in baseline_points) / len(baseline_points)
    avg_bac = sum(p["bacino"] for p in baseline_points) / len(baseline_points)
    avg_cov = sum(p["coverage"] for p in baseline_points) / len(baseline_points)

    # Publisher baselines
    all_publishers = set()
    for p in baseline_points:
        all_publishers.update(p["publishers"].keys())

    pub_baselines = {}
    for pub in all_publishers:
        pub_revs = [p["publishers"].get(pub, {}).get("revenue", 0) for p in baseline_points]
        pub_bacs = [p["publishers"].get(pub, {}).get("bacino", 0) for p in baseline_points]
        pub_covs = [p["publishers"].get(pub, {}).get("coverage", 0) for p in baseline_points]

        pub_baselines[pub] = {
            "revenue": round(sum(pub_revs) / len(pub_revs), 2),
            "bacino": int(sum(pub_bacs) / len(pub_bacs)),
            "coverage": round(sum(pub_covs) / len(pub_covs), 4),
        }

    # Geo baselines
    all_geos = set()
    for p in baseline_points:
        all_geos.update(p["geo"].keys())

    geo_baselines = {}
    for cluster in all_geos:
        g_revs = [p["geo"].get(cluster, {}).get("revenue", 0) for p in baseline_points]
        g_bacs = [p["geo"].get(cluster, {}).get("bacino", 0) for p in baseline_points]
        g_covs = [p["geo"].get(cluster, {}).get("coverage", 0) for p in baseline_points]

        geo_baselines[cluster] = {
            "revenue": round(sum(g_revs) / len(g_revs), 2),
            "bacino": int(sum(g_bacs) / len(g_bacs)),
            "coverage": round(sum(g_covs) / len(g_covs), 4),
        }

    # Environment baselines
    all_envs = set()
    for p in baseline_points:
        all_envs.update(p["environment"].keys())

    env_baselines = {}
    for e in all_envs:
        e_revs = [p["environment"].get(e, {}).get("revenue", 0) for p in baseline_points]
        e_bacs = [p["environment"].get(e, {}).get("bacino", 0) for p in baseline_points]
        e_covs = [p["environment"].get(e, {}).get("coverage", 0) for p in baseline_points]

        env_baselines[e] = {
            "revenue": round(sum(e_revs) / len(e_revs), 2),
            "bacino": int(sum(e_bacs) / len(e_bacs)),
            "coverage": round(sum(e_covs) / len(e_covs), 4),
        }

    # Calculate stats with sample std (N-1) for unbiased estimation
    rev_values = [p["revenue"] for p in baseline_points]
    bac_values = [p["bacino"] for p in baseline_points]
    cov_values = [p["coverage"] for p in baseline_points]
    rev_mean = avg_rev
    bac_mean = avg_bac
    cov_mean = avg_cov
    rev_min = min(rev_values)

    n = len(baseline_points)
    if n >= 2:
        # Sample standard deviation (Bessel's correction: N-1)
        rev_std = max(1.0, (sum((v - rev_mean) ** 2 for v in rev_values) / (n - 1)) ** 0.5)
        bac_std = max(1.0, (sum((v - bac_mean) ** 2 for v in bac_values) / (n - 1)) ** 0.5)
        cov_std = max(0.001, (sum((v - cov_mean) ** 2 for v in cov_values) / (n - 1)) ** 0.5)
    else:
        # Not enough points for sample std, use floor based on % of baseline
        rev_std = max(1.0, abs(rev_mean) * 0.15)
        bac_std = max(1.0, abs(bac_mean) * 0.15)
        cov_std = max(0.001, abs(cov_mean) * 0.10)

    result = {
        "baseline_metrics": {
            "revenue": round(avg_rev, 2),
            "bacino": int(avg_bac),
            "coverage": round(avg_cov, 4),
            "publishers": pub_baselines,
            "geo": geo_baselines,
            "environment": env_baselines,
        },
        "historical_stats": {
            "revenue_std": round(rev_std, 2),
            "bacino_std": round(bac_std, 2),
            "coverage_std": round(cov_std, 6),
            "revenue_min_for_hour": round(rev_min, 2),
            "baseline_data_points": n,
        }
    }

    # Add note if interventions were excluded from baseline
    if excluded_intervention_count > 0:
        result["historical_stats"]["baseline_notes"] = (
            f"Excluded {excluded_intervention_count} intervention period(s) from baseline calculation"
        )
        logger.info(
            "Baseline calculation excluded %d manual intervention period(s)",
            excluded_intervention_count
        )

    return result


def _calculate_drift_metrics(df_daily: pd.DataFrame, current_ts: datetime, channel: str) -> dict:
    """
    Calculate 7-day drift metrics for A2 detection.
    Compares last 7 days vs previous 7 days.
    """
    # Get date from timestamp
    current_date = current_ts.date()

    # Current 7 days: [current_date - 6 days, current_date]
    start_current = current_date - timedelta(days=6)
    end_current = current_date

    # Previous 7 days: [current_date - 13 days, current_date - 7 days]
    start_prev = current_date - timedelta(days=13)
    end_prev = current_date - timedelta(days=7)

    # Filter for current 7 days
    mask_current = (
        (df_daily['date'].dt.date >= start_current) &
        (df_daily['date'].dt.date <= end_current) &
        (df_daily['channel_group'] == channel)
    )

    # Filter for previous 7 days
    mask_prev = (
        (df_daily['date'].dt.date >= start_prev) &
        (df_daily['date'].dt.date <= end_prev) &
        (df_daily['channel_group'] == channel)
    )

    current_7d = df_daily[mask_current]['revenue'].sum()
    prev_7d = df_daily[mask_prev]['revenue'].sum()

    return {
        "drift_current_7d": round(current_7d, 2),
        "drift_prev_7d": round(prev_7d, 2),
    }


def _get_daily_channel_df() -> Optional[pd.DataFrame]:
    """Accessor for daily channel cache (used by drift baseline fetcher)."""
    return _load_daily_channel_data()


def _fetch_drift_baseline(
    timestamp: pd.Timestamp,
    channel_group: str,
    window_days: int,
) -> Optional[pd.DataFrame]:
    """
    Fetch daily aggregated revenue for drift regression analysis.

    Returns DataFrame with columns: date, revenue
    Covers window_days before the given timestamp.
    Uses daily_channel parquet for aggregation.

    Args:
        timestamp: End timestamp (exclusive - we go backwards from day before this)
        channel_group: GOOGLE or OPEN_BIDDING
        window_days: How many days to fetch (14-30 typically)

    Returns:
        DataFrame with daily revenue sums, or None if data insufficient
    """
    df = _get_daily_channel_df()
    if df is None:
        return None

    # Convert timestamp to date, go back one day (we want historical baseline, not including current day)
    # Ensure timestamp is tz-naive to match parquet data
    ts_naive = timestamp.tz_localize(None) if timestamp.tzinfo is not None else timestamp
    end_date = ts_naive.normalize() - timedelta(days=1)
    start_date = end_date - timedelta(days=window_days - 1)

    # Filter by channel and date range
    mask = (
        (df["channel_group"] == channel_group)
        & (df["date"] >= start_date)
        & (df["date"] <= end_date)
    )
    subset = df[mask].copy()

    if subset.empty:
        logger.warning(
            "No drift baseline data for %s in range %s to %s",
            channel_group, start_date, end_date,
        )
        return None

    # Group by date and sum revenue across all publishers
    daily = subset.groupby("date", as_index=False)["revenue"].sum()
    daily = daily.sort_values("date")

    logger.info(
        "Fetched drift baseline: %d days, %.2f EUR total",
        len(daily), daily["revenue"].sum(),
    )

    return daily


def _get_active_source() -> str:
    """Read the active data source from datasource_config.json."""
    config_path = BASE_DIR / "data" / "datasource_config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
            return config.get("active_source", "parquet")
        except (json.JSONDecodeError, OSError):
            pass
    return "parquet"


def _try_athena_fetch(channel: str, current_ts: datetime) -> Optional[pd.DataFrame]:
    """Attempt to fetch data from Athena. Returns DataFrame or None on failure."""
    try:
        from backend.connectors.athena import fetch_from_athena
    except ImportError as e:
        logger.warning("Could not import Athena connector: %s", e)
        return None

    # Query a window: 28 days back (for baseline) to current timestamp
    start_time = (current_ts - timedelta(days=28)).isoformat()
    end_time = current_ts.isoformat()

    logger.info("Attempting Athena fetch for %s [%s, %s]", channel, start_time, end_time)
    return fetch_from_athena(channel, start_time, end_time)


def _try_gam_fetch(channel: str, current_ts: datetime) -> Optional[pd.DataFrame]:
    """Attempt to fetch data from GAM. Returns DataFrame or None on failure."""
    try:
        from backend.connectors.gam import fetch_from_gam
    except ImportError as e:
        logger.warning("Could not import GAM connector: %s", e)
        return None

    start_time = (current_ts - timedelta(days=28)).isoformat()
    end_time = current_ts.isoformat()

    logger.info("Attempting GAM fetch for %s [%s, %s]", channel, start_time, end_time)
    return fetch_from_gam(channel, start_time, end_time)


def data_fetcher_agent(state: AlertState) -> AlertState:
    """
    Fetch real data from parquet files for the current period and 7-day baseline.
    Data source priority: Athena -> GAM -> Parquet.
    Falls back to synthetic data if parquet files are not available.
    """
    logger.info("Data fetcher started (real data mode)")
    errors = list(state.get("execution_errors", []))

    channel = state.get("channel_group", "GOOGLE")
    trigger = state.get("trigger_type", "A1")
    ts_str = state.get("timestamp", datetime.now(timezone.utc).isoformat())

    try:
        current_ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        current_ts = datetime.now(timezone.utc)
        errors.append(f"Invalid timestamp '{ts_str}', using current time")

    if current_ts.tzinfo is None:
        current_ts = current_ts.replace(tzinfo=timezone.utc)

    # D6: Round timestamp to the hour BEFORE any data operations
    current_ts = current_ts.replace(minute=0, second=0, microsecond=0)

    # Determine data source
    active_source = _get_active_source()
    data_source_used = "real_parquet"

    # Data source priority: Athena -> GAM -> Parquet
    if active_source == "athena":
        logger.info("Active source is Athena, attempting Athena fetch")
        athena_df = _try_athena_fetch(channel, current_ts)

        if athena_df is not None and not athena_df.empty:
            logger.info("Athena returned %d rows, using as primary data source", len(athena_df))
            data_source_used = "athena"
            df_hourly = athena_df
        else:
            logger.warning("Athena fetch failed or returned empty, trying GAM fallback")
            errors.append("Athena fetch failed, trying GAM")
            gam_df = _try_gam_fetch(channel, current_ts)

            if gam_df is not None and not gam_df.empty:
                logger.info("GAM returned %d rows, using as secondary data source", len(gam_df))
                data_source_used = "gam"
                df_hourly = gam_df
            else:
                logger.warning("GAM fetch also failed, falling back to parquet")
                errors.append("GAM fetch failed, fell back to parquet")
                df_hourly = _load_hourly_data()

    elif active_source == "gam":
        logger.info("Active source is GAM, attempting GAM fetch")
        gam_df = _try_gam_fetch(channel, current_ts)

        if gam_df is not None and not gam_df.empty:
            logger.info("GAM returned %d rows, using as primary data source", len(gam_df))
            data_source_used = "gam"
            df_hourly = gam_df
        else:
            logger.warning("GAM fetch failed or returned empty, falling back to parquet")
            errors.append("GAM fetch failed, fell back to parquet")
            df_hourly = _load_hourly_data()
    else:
        # Default: load from parquet
        df_hourly = _load_hourly_data()

    if df_hourly is None:
        is_live = state.get("mode", "LIVE") != "BACKTEST"
        if is_live:
            logger.error("Real data not available, synthetic fallback blocked in LIVE mode")
            errors.append("Real data not available, synthetic fallback blocked in LIVE mode")
            return {
                **state,
                "validation_status": "FAIL",
                "execution_errors": errors,
                "data_source": "synthetic",
            }
        logger.warning("Real data not available, falling back to synthetic data generator (BACKTEST mode)")
        from backend.agents.data_fetcher import data_fetcher_agent as synthetic_fetcher
        return synthetic_fetcher(state)

    # Get current period metrics
    current_data = _get_hourly_metrics(df_hourly, current_ts, channel)

    if current_data is None:
        is_live = state.get("mode", "LIVE") != "BACKTEST"
        if is_live:
            logger.error(f"No data found for {current_ts} / {channel}, synthetic fallback blocked in LIVE mode")
            errors.append(f"No data found for {current_ts} / {channel}, synthetic fallback blocked in LIVE mode")
            return {
                **state,
                "validation_status": "FAIL",
                "execution_errors": errors,
                "data_source": "synthetic",
            }
        logger.warning(f"No data found for {current_ts} / {channel}, using synthetic fallback (BACKTEST mode)")
        from backend.agents.data_fetcher import data_fetcher_agent as synthetic_fetcher
        return synthetic_fetcher(state)

    # Calculate baseline
    baseline_result = _calculate_baseline_from_hourly(df_hourly, current_ts, channel)

    if baseline_result is None:
        is_live = state.get("mode", "LIVE") != "BACKTEST"
        if is_live:
            logger.error("Failed to calculate baseline, synthetic fallback blocked in LIVE mode")
            errors.append("Failed to calculate baseline, synthetic fallback blocked in LIVE mode")
            return {
                **state,
                "validation_status": "FAIL",
                "execution_errors": errors,
                "data_source": "synthetic",
            }
        logger.warning("Failed to calculate baseline, using synthetic fallback (BACKTEST mode)")
        from backend.agents.data_fetcher import data_fetcher_agent as synthetic_fetcher
        return synthetic_fetcher(state)

    baseline_metrics = baseline_result["baseline_metrics"]
    historical_stats = baseline_result["historical_stats"]

    # D4: Always calculate drift metrics for all trigger types (not just A2)
    df_daily = _load_daily_channel_data()
    if df_daily is not None:
        drift_metrics = _calculate_drift_metrics(df_daily, current_ts, channel)
        historical_stats.update(drift_metrics)
    else:
        historical_stats["drift_current_7d"] = 0.0
        historical_stats["drift_prev_7d"] = 0.0

    # Add additional context
    historical_stats["hour_of_day"] = current_ts.hour
    historical_stats["day_of_week"] = current_ts.strftime("%A")

    current_metrics = {
        "revenue": current_data["revenue"],
        "bacino": current_data["bacino"],
        "coverage": current_data["coverage"],
        "publishers": current_data["publishers"],
        "geo": current_data["geo"],
        "environment": current_data["environment"],
    }

    logger.info(
        "Data fetcher complete (%s): rev=%.2f, baseline=%.2f, points=%d",
        data_source_used.upper(),
        current_metrics["revenue"],
        baseline_metrics["revenue"],
        historical_stats["baseline_data_points"],
    )

    return {
        **state,
        "current_metrics": current_metrics,
        "baseline_metrics": baseline_metrics,
        "historical_stats": historical_stats,
        "execution_errors": errors,
        "data_source": data_source_used,
    }
