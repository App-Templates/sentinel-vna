"""
Data Fetcher Agent (Node 2)
Generates synthetic data that mimics real advertising revenue patterns.
Supports anomaly injection for testing.
"""

import hashlib
import math
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from backend.utils.config_loader import get_config
from backend.utils.logger import get_logger
from backend.workflow.state import AlertState

logger = get_logger("agent.data_fetcher")

# Hourly traffic multiplier (0-23h UTC) - models typical European ad traffic
HOURLY_PATTERN = [
    0.15, 0.10, 0.08, 0.07, 0.06, 0.08,  # 00-05: nighttime low
    0.20, 0.45, 0.65, 0.80, 0.90, 0.95,  # 06-11: morning ramp
    1.00, 0.98, 0.95, 0.90, 0.85, 0.80,  # 12-17: afternoon
    0.75, 0.70, 0.60, 0.45, 0.30, 0.20,  # 18-23: evening decline
]

# Day-of-week multiplier (Mon=0 .. Sun=6)
DOW_PATTERN = [1.0, 1.02, 1.01, 0.98, 0.95, 0.70, 0.65]

# Publisher revenue share (approximate)
PUBLISHER_SHARES = {
    "vocento": 0.12,
    "prensaiberica": 0.09,
    "mondadori": 0.08,
    "elespanol": 0.07,
    "dorvan": 0.06,
    "unidadeditorial": 0.06,
    "thecore": 0.05,
    "alayansmedia": 0.04,
    "grupogodo": 0.04,
    "piemme": 0.04,
    "talksmedia": 0.03,
    "adplay": 0.03,
    "grupojoly": 0.03,
    "mediamond": 0.03,
    "eleconomista": 0.025,
    "magellano": 0.025,
    "movingup": 0.02,
    "infobae": 0.02,
    "speed": 0.02,
    "terralatam": 0.02,
}

# Geo cluster revenue shares
GEO_SHARES = {"ITA": 0.45, "ES": 0.25, "LATAM": 0.12, "PT": 0.08, "OTHER": 0.10}

# Environment shares
ENV_SHARES = {"WEB": 0.50, "AMP": 0.22, "APP": 0.18, "UNKNOWN": 0.10}

# Base hourly revenue (EUR) per channel
BASE_HOURLY_REVENUE = {
    "GOOGLE_ADEX": 12000.0,
    "OPEN_BIDDING": 4500.0,
    "HEADER_BIDDING_MAGNITE": 3000.0,
    "HEADER_BIDDING_PUBMATIC": 2500.0,
    "TAM": 2000.0,
    "DIRECT": 1500.0,
    "DEAL": 1000.0,
    # Legacy
    "GOOGLE": 12000.0,
}

# Base hourly impressions (bacino)
BASE_HOURLY_BACINO = {
    "GOOGLE_ADEX": 2_000_000,
    "OPEN_BIDDING": 800_000,
    "HEADER_BIDDING_MAGNITE": 600_000,
    "HEADER_BIDDING_PUBMATIC": 500_000,
    "TAM": 400_000,
    "DIRECT": 300_000,
    "DEAL": 200_000,
    # Legacy
    "GOOGLE": 2_000_000,
}


def _seeded_noise(seed_str: str, scale: float = 0.05) -> float:
    """Deterministic noise based on seed string for reproducibility."""
    h = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
    # Map to [-scale, +scale]
    return (h / 0xFFFFFFFF - 0.5) * 2 * scale


def _generate_hourly_metrics(
    ts: datetime,
    channel: str,
    anomaly_config: Optional[dict] = None,
) -> dict:
    """Generate realistic metrics for a single hour."""
    hour = ts.hour
    dow = ts.weekday()
    seed = f"{ts.isoformat()}-{channel}"

    hour_mult = HOURLY_PATTERN[hour]
    dow_mult = DOW_PATTERN[dow]
    noise = _seeded_noise(seed, scale=0.08)

    base_rev = BASE_HOURLY_REVENUE.get(channel, 10000.0)
    base_bac = BASE_HOURLY_BACINO.get(channel, 1_500_000)

    revenue = base_rev * hour_mult * dow_mult * (1 + noise)
    bacino = base_bac * hour_mult * dow_mult * (1 + _seeded_noise(seed + "bac", 0.06))
    coverage = min(0.95, max(0.40, 0.82 + _seeded_noise(seed + "cov", 0.08)))

    # Apply anomaly injection if configured for current period
    if anomaly_config and anomaly_config.get("active"):
        rev_factor = anomaly_config.get("revenue_factor", 1.0)
        bac_factor = anomaly_config.get("bacino_factor", 1.0)
        cov_factor = anomaly_config.get("coverage_factor", 1.0)
        revenue *= rev_factor
        bacino *= bac_factor
        coverage *= cov_factor

    # Per-publisher breakdown
    publishers = {}
    for pub, share in PUBLISHER_SHARES.items():
        pub_noise = _seeded_noise(seed + pub, 0.10)
        pub_rev = revenue * share * (1 + pub_noise)

        pub_anomaly_factor = 1.0
        if anomaly_config and pub in anomaly_config.get("affected_publishers", []):
            pub_anomaly_factor = anomaly_config.get("publisher_factor", 0.5)
            pub_rev *= pub_anomaly_factor

        publishers[pub] = {
            "revenue": round(pub_rev, 2),
            "bacino": int(bacino * share * (1 + _seeded_noise(seed + pub + "b", 0.08))),
            "coverage": min(0.98, max(0.30, coverage + _seeded_noise(seed + pub + "c", 0.05))),
        }

    # Per-geo breakdown
    geo = {}
    for cluster, share in GEO_SHARES.items():
        g_noise = _seeded_noise(seed + cluster, 0.07)
        g_rev = revenue * share * (1 + g_noise)

        if anomaly_config and cluster in anomaly_config.get("affected_geos", []):
            g_rev *= anomaly_config.get("geo_factor", 0.7)

        geo[cluster] = {
            "revenue": round(g_rev, 2),
            "bacino": int(bacino * share * (1 + _seeded_noise(seed + cluster + "b", 0.06))),
            "coverage": min(0.98, max(0.30, coverage + _seeded_noise(seed + cluster + "c", 0.04))),
        }

    # Per-environment breakdown
    env = {}
    for e, share in ENV_SHARES.items():
        e_noise = _seeded_noise(seed + e, 0.06)
        e_rev = revenue * share * (1 + e_noise)

        if anomaly_config and e in anomaly_config.get("affected_envs", []):
            e_rev *= anomaly_config.get("env_factor", 0.8)

        env[e] = {
            "revenue": round(e_rev, 2),
            "bacino": int(bacino * share * (1 + _seeded_noise(seed + e + "b", 0.06))),
            "coverage": min(0.98, max(0.30, coverage + _seeded_noise(seed + e + "c", 0.04))),
        }

    return {
        "timestamp": ts.isoformat(),
        "channel_group": channel,
        "revenue": round(revenue, 2),
        "bacino": int(bacino),
        "coverage": round(coverage, 4),
        "publishers": publishers,
        "geo": geo,
        "environment": env,
    }


def _build_anomaly_config(trigger_type: str, channel: str) -> Optional[dict]:
    """Build anomaly injection config based on trigger type for realistic testing."""
    if trigger_type == "A1":
        # Spike/drop: sudden revenue drop, traffic-driven
        return {
            "active": True,
            "revenue_factor": 0.78,
            "bacino_factor": 0.75,
            "coverage_factor": 0.97,
            "affected_publishers": ["vocento", "prensaiberica", "mondadori"],
            "publisher_factor": 0.45,
            "affected_geos": ["ITA"],
            "geo_factor": 0.70,
            "affected_envs": [],
            "env_factor": 1.0,
        }
    elif trigger_type == "A2":
        # Drift: gradual decline, AMP environment focused
        return {
            "active": True,
            "revenue_factor": 0.92,
            "bacino_factor": 0.95,
            "coverage_factor": 0.90,
            "affected_publishers": [],
            "publisher_factor": 1.0,
            "affected_geos": [],
            "geo_factor": 1.0,
            "affected_envs": ["AMP"],
            "env_factor": 0.78,
        }
    elif trigger_type == "A3":
        # Near-zero: extreme drop
        return {
            "active": True,
            "revenue_factor": 0.05,
            "bacino_factor": 0.08,
            "coverage_factor": 0.02,
            "affected_publishers": list(PUBLISHER_SHARES.keys()),
            "publisher_factor": 0.05,
            "affected_geos": ["ITA", "ES", "OTHER"],
            "geo_factor": 0.05,
            "affected_envs": ["WEB", "AMP", "APP"],
            "env_factor": 0.05,
        }
    return None


def data_fetcher_agent(state: AlertState) -> AlertState:
    """
    Fetch data for the current period and 7-day baseline.
    Tries to load real parquet data first, falls back to synthetic if unavailable.
    Returns current_metrics, baseline_metrics, and historical_stats.
    """
    # Try to use real data first
    try:
        from backend.agents.data_fetcher_real import data_fetcher_agent as real_fetcher
        result = real_fetcher(state)
        # Accept any real data source (parquet, athena, gam)
        if result.get("data_source") in ("real_parquet", "athena", "gam"):
            return result
        # Respect validation failures from real fetcher (e.g. LIVE mode block)
        if result.get("validation_status") == "FAIL":
            return result
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Real data fetcher failed: {e}, using synthetic")

    # Fall back to synthetic data
    logger.info("Data fetcher started (synthetic mode)")
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

    # Build anomaly config for the current period
    anomaly = _build_anomaly_config(trigger, channel)

    # Generate current period metrics (with anomaly)
    current_data = _generate_hourly_metrics(current_ts, channel, anomaly)

    # Generate 7-day baseline: same hour, same weekday, 7 weeks back
    # We use 7 data points: -7d, -14d, -21d, -28d, -35d, -42d, -49d (same hour, same DOW)
    baseline_points = []
    for weeks_back in range(1, 8):
        baseline_ts = current_ts - timedelta(days=7 * weeks_back)
        bp = _generate_hourly_metrics(baseline_ts, channel, anomaly_config=None)
        baseline_points.append(bp)

    # Calculate baseline averages
    avg_rev = sum(p["revenue"] for p in baseline_points) / len(baseline_points)
    avg_bac = sum(p["bacino"] for p in baseline_points) / len(baseline_points)
    avg_cov = sum(p["coverage"] for p in baseline_points) / len(baseline_points)

    # Revenue std for z-score calculation
    rev_values = [p["revenue"] for p in baseline_points]
    rev_mean = avg_rev
    n = len(rev_values)
    if n >= 2:
        # Sample standard deviation (Bessel's correction: N-1)
        rev_std = max(1.0, (sum((v - rev_mean) ** 2 for v in rev_values) / (n - 1)) ** 0.5)
    else:
        rev_std = max(1.0, abs(rev_mean) * 0.15)

    # Historical min for this hour
    rev_min = min(rev_values)

    # Publisher baselines
    pub_baselines = {}
    for pub in PUBLISHER_SHARES:
        pub_revs = [p["publishers"].get(pub, {}).get("revenue", 0) for p in baseline_points]
        pub_bacs = [p["publishers"].get(pub, {}).get("bacino", 0) for p in baseline_points]
        pub_covs = [p["publishers"].get(pub, {}).get("coverage", 0) for p in baseline_points]
        pub_baselines[pub] = {
            "revenue": round(sum(pub_revs) / len(pub_revs), 2),
            "bacino": int(sum(pub_bacs) / len(pub_bacs)),
            "coverage": round(sum(pub_covs) / len(pub_covs), 4),
        }

    # Geo baselines
    geo_baselines = {}
    for cluster in GEO_SHARES:
        g_revs = [p["geo"].get(cluster, {}).get("revenue", 0) for p in baseline_points]
        g_bacs = [p["geo"].get(cluster, {}).get("bacino", 0) for p in baseline_points]
        g_covs = [p["geo"].get(cluster, {}).get("coverage", 0) for p in baseline_points]
        geo_baselines[cluster] = {
            "revenue": round(sum(g_revs) / len(g_revs), 2),
            "bacino": int(sum(g_bacs) / len(g_bacs)),
            "coverage": round(sum(g_covs) / len(g_covs), 4),
        }

    # Environment baselines
    env_baselines = {}
    for e in ENV_SHARES:
        e_revs = [p["environment"].get(e, {}).get("revenue", 0) for p in baseline_points]
        e_bacs = [p["environment"].get(e, {}).get("bacino", 0) for p in baseline_points]
        e_covs = [p["environment"].get(e, {}).get("coverage", 0) for p in baseline_points]
        env_baselines[e] = {
            "revenue": round(sum(e_revs) / len(e_revs), 2),
            "bacino": int(sum(e_bacs) / len(e_bacs)),
            "coverage": round(sum(e_covs) / len(e_covs), 4),
        }

    # For A2 drift detection: generate previous 7d aggregate
    drift_current_7d = 0.0
    drift_prev_7d = 0.0
    if trigger == "A2":
        for d in range(7):
            ts_cur = current_ts - timedelta(days=d)
            ts_prev = current_ts - timedelta(days=d + 7)
            cur_m = _generate_hourly_metrics(ts_cur, channel, anomaly)
            prev_m = _generate_hourly_metrics(ts_prev, channel, None)
            drift_current_7d += cur_m["revenue"]
            drift_prev_7d += prev_m["revenue"]

    current_metrics = {
        "revenue": current_data["revenue"],
        "bacino": current_data["bacino"],
        "coverage": current_data["coverage"],
        "publishers": current_data["publishers"],
        "geo": current_data["geo"],
        "environment": current_data["environment"],
    }

    baseline_metrics = {
        "revenue": round(avg_rev, 2),
        "bacino": int(avg_bac),
        "coverage": round(avg_cov, 4),
        "publishers": pub_baselines,
        "geo": geo_baselines,
        "environment": env_baselines,
    }

    historical_stats = {
        "revenue_std": round(rev_std, 2),
        "revenue_min_for_hour": round(rev_min, 2),
        "baseline_data_points": len(baseline_points),
        "drift_current_7d": round(drift_current_7d, 2),
        "drift_prev_7d": round(drift_prev_7d, 2),
        "hour_of_day": current_ts.hour,
        "day_of_week": current_ts.strftime("%A"),
    }

    logger.info(
        "Data fetcher complete: rev=%.2f, baseline=%.2f, points=%d",
        current_metrics["revenue"],
        baseline_metrics["revenue"],
        len(baseline_points),
    )

    return {
        **state,
        "current_metrics": current_metrics,
        "baseline_metrics": baseline_metrics,
        "historical_stats": historical_stats,
        "execution_errors": errors,
        "data_source": "synthetic",
    }
