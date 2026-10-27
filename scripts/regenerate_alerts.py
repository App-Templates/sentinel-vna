#!/usr/bin/env python3
"""
Regenerate alerts in the VNA platform database using real parquet data.

Fixes:
1. geo_breakdown now shows ITA/ES/OTHER instead of just "ALL"
2. Date range covers 2024-01-01 to 2026-01-22 (full data range)
3. Severity distribution is realistic: ~20% P0, ~35% P1, ~45% P2
"""

import json
import random
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ──────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "vna_alerts.db"
PARQUET_PATH = PROJECT_ROOT / "data" / "baseline" / "daily_channel_aggregated.parquet"

TARGET_ALERT_COUNT = 200
SEVERITY_THRESHOLDS = {
    "P0": -15.0,
    "P1": -10.0,
    "P2": -5.0,
}
# Desired distribution (approximate)
TARGET_DIST = {"P0": 0.20, "P1": 0.35, "P2": 0.45}

ALERT_RULES = ["A1", "A2", "A3"]

random.seed(42)
np.random.seed(42)


def load_parquet() -> pd.DataFrame:
    """Load and validate the parquet data."""
    print(f"Loading parquet from {PARQUET_PATH} ...")
    df = pd.read_parquet(PARQUET_PATH)
    df["date"] = pd.to_datetime(df["date"])
    print(f"  Loaded {len(df):,} rows, date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"  geo_cluster values: {sorted(df['geo_cluster'].unique())}")
    print(f"  environment values: {sorted(df['environment'].unique())}")
    print(f"  channel_group values: {sorted(df['channel_group'].unique())}")
    return df


def compute_daily_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate revenue and impressions by date + channel_group."""
    daily = (
        df.groupby(["date", "channel_group"])
        .agg(revenue=("revenue", "sum"), impressions=("impressions", "sum"))
        .reset_index()
        .sort_values(["channel_group", "date"])
    )
    return daily


def compute_rolling_baseline(daily: pd.DataFrame) -> pd.DataFrame:
    """
    For each date-channel_group, compute a 7-day rolling baseline:
    same weekday, past 7 weeks average.
    """
    daily = daily.copy()
    daily["weekday"] = daily["date"].dt.dayofweek

    baseline_rev = []
    baseline_imp = []

    for _, group in daily.groupby("channel_group"):
        group = group.sort_values("date").reset_index(drop=True)
        rev_baselines = []
        imp_baselines = []

        for idx, row in group.iterrows():
            target_weekday = row["weekday"]
            target_date = row["date"]
            # Look back 7 weeks for the same weekday
            past_values_rev = []
            past_values_imp = []
            for w in range(1, 8):
                past_date = target_date - timedelta(weeks=w)
                match = group[group["date"] == past_date]
                if len(match) == 1:
                    past_values_rev.append(match["revenue"].values[0])
                    past_values_imp.append(match["impressions"].values[0])

            if len(past_values_rev) >= 2:
                rev_baselines.append(np.mean(past_values_rev))
                imp_baselines.append(np.mean(past_values_imp))
            else:
                rev_baselines.append(np.nan)
                imp_baselines.append(np.nan)

        baseline_rev.extend(rev_baselines)
        baseline_imp.extend(imp_baselines)

    # Rebuild index-aligned
    daily_sorted = pd.concat(
        [g.sort_values("date").reset_index(drop=True)
         for _, g in daily.groupby("channel_group")]
    ).reset_index(drop=True)

    daily_sorted["baseline_revenue"] = baseline_rev
    daily_sorted["baseline_impressions"] = baseline_imp
    daily_sorted["delta_pct"] = (
        (daily_sorted["revenue"] - daily_sorted["baseline_revenue"])
        / daily_sorted["baseline_revenue"]
        * 100
    )
    daily_sorted["imp_delta_pct"] = (
        (daily_sorted["impressions"] - daily_sorted["baseline_impressions"])
        / daily_sorted["baseline_impressions"]
        * 100
    )

    return daily_sorted.dropna(subset=["baseline_revenue", "delta_pct"])


def detect_anomalies(daily_with_baseline: pd.DataFrame) -> pd.DataFrame:
    """Detect anomalies based on delta thresholds."""
    df = daily_with_baseline.copy()

    def classify_severity(delta):
        if delta <= SEVERITY_THRESHOLDS["P0"]:
            return "P0"
        elif delta <= SEVERITY_THRESHOLDS["P1"]:
            return "P1"
        elif delta <= SEVERITY_THRESHOLDS["P2"]:
            return "P2"
        return None

    df["severity"] = df["delta_pct"].apply(classify_severity)
    anomalies = df[df["severity"].notna()].copy()

    print(f"\n  Raw anomalies detected: {len(anomalies)}")
    print(f"  Severity dist: {anomalies['severity'].value_counts().to_dict()}")

    return anomalies


def sample_target_alerts(anomalies: pd.DataFrame) -> pd.DataFrame:
    """
    Sample ~TARGET_ALERT_COUNT alerts with the desired severity distribution,
    spread across the full date range.
    """
    target_p0 = int(TARGET_ALERT_COUNT * TARGET_DIST["P0"])
    target_p1 = int(TARGET_ALERT_COUNT * TARGET_DIST["P1"])
    target_p2 = TARGET_ALERT_COUNT - target_p0 - target_p1

    targets = {"P0": target_p0, "P1": target_p1, "P2": target_p2}

    sampled_parts = []
    for sev, count in targets.items():
        pool = anomalies[anomalies["severity"] == sev]
        if len(pool) >= count:
            sampled = pool.sample(n=count, random_state=42)
        else:
            sampled = pool
            print(f"  WARNING: Only {len(pool)} {sev} anomalies available (wanted {count})")
        sampled_parts.append(sampled)

    sampled = pd.concat(sampled_parts).sort_values("date")
    print(f"\n  Sampled {len(sampled)} alerts:")
    print(f"  {sampled['severity'].value_counts().to_dict()}")
    print(f"  Date range: {sampled['date'].min().date()} to {sampled['date'].max().date()}")

    return sampled


def compute_geo_breakdown(raw_df: pd.DataFrame, date, channel_group: str) -> list:
    """Compute revenue breakdown by geo_cluster for a specific date-channel."""
    day_data = raw_df[(raw_df["date"] == date) & (raw_df["channel_group"] == channel_group)]

    # Compute baseline: same weekday, past 7 weeks
    past_dates = [date - timedelta(weeks=w) for w in range(1, 8)]
    baseline_data = raw_df[
        (raw_df["date"].isin(past_dates)) & (raw_df["channel_group"] == channel_group)
    ]

    geo_current = day_data.groupby("geo_cluster")["revenue"].sum()
    geo_baseline = baseline_data.groupby(["date", "geo_cluster"])["revenue"].sum().groupby("geo_cluster").mean()

    total_delta = geo_current.sum() - geo_baseline.sum()

    breakdown = []
    for geo in ["ITA", "ES", "OTHER"]:
        curr = geo_current.get(geo, 0.0)
        base = geo_baseline.get(geo, 0.0)
        delta_abs = curr - base
        delta_pct = (delta_abs / base * 100) if base > 0 else 0.0
        contribution = (delta_abs / total_delta) if total_delta != 0 else 0.0

        breakdown.append({
            "geo_cluster": geo,
            "current_revenue": round(curr, 2),
            "baseline_revenue": round(base, 2),
            "delta_absolute": round(delta_abs, 2),
            "delta_percent": round(delta_pct, 1),
            "contribution": round(contribution, 4),
        })

    return breakdown


def compute_environment_split(raw_df: pd.DataFrame, date, channel_group: str) -> dict:
    """Compute environment split (WEB/AMP/APP) with delta, bacino, coverage."""
    day_data = raw_df[(raw_df["date"] == date) & (raw_df["channel_group"] == channel_group)]

    past_dates = [date - timedelta(weeks=w) for w in range(1, 8)]
    baseline_data = raw_df[
        (raw_df["date"].isin(past_dates)) & (raw_df["channel_group"] == channel_group)
    ]

    env_current = day_data.groupby("environment").agg(
        revenue=("revenue", "sum"), impressions=("impressions", "sum")
    )
    env_baseline = (
        baseline_data.groupby(["date", "environment"])
        .agg(revenue=("revenue", "sum"), impressions=("impressions", "sum"))
        .groupby("environment")
        .mean()
    )

    total_impressions = day_data["impressions"].sum()

    split = {}
    for env in ["WEB", "AMP", "APP"]:
        curr_rev = env_current.loc[env, "revenue"] if env in env_current.index else 0.0
        base_rev = env_baseline.loc[env, "revenue"] if env in env_baseline.index else 0.0
        curr_imp = env_current.loc[env, "impressions"] if env in env_current.index else 0
        base_imp = env_baseline.loc[env, "impressions"] if env in env_baseline.index else 0

        delta_abs = curr_rev - base_rev
        delta_pct = (delta_abs / base_rev * 100) if base_rev > 0 else 0.0
        coverage = (curr_imp / total_impressions) if total_impressions > 0 else 0.0

        split[env] = {
            "revenue": round(float(curr_rev), 2),
            "baseline_revenue": round(float(base_rev), 2),
            "delta_absolute": round(float(delta_abs), 2),
            "delta_percent": round(float(delta_pct), 1),
            "bacino": int(curr_imp),
            "coverage": round(float(coverage), 4),
        }

    return split


def compute_contributors(raw_df: pd.DataFrame, date, channel_group: str, top_n: int = 5) -> list:
    """Find top publishers contributing to the revenue drop."""
    day_data = raw_df[(raw_df["date"] == date) & (raw_df["channel_group"] == channel_group)]

    past_dates = [date - timedelta(weeks=w) for w in range(1, 8)]
    baseline_data = raw_df[
        (raw_df["date"].isin(past_dates)) & (raw_df["channel_group"] == channel_group)
    ]

    pub_current = day_data.groupby("publisher_id")["revenue"].sum()
    pub_baseline = (
        baseline_data.groupby(["date", "publisher_id"])["revenue"]
        .sum()
        .groupby("publisher_id")
        .mean()
    )

    all_pubs = set(pub_current.index) | set(pub_baseline.index)
    total_drop = sum(
        pub_current.get(p, 0.0) - pub_baseline.get(p, 0.0)
        for p in all_pubs
        if pub_current.get(p, 0.0) - pub_baseline.get(p, 0.0) < 0
    )

    contributors = []
    for pub in all_pubs:
        curr = pub_current.get(pub, 0.0)
        base = pub_baseline.get(pub, 0.0)
        delta = curr - base
        if delta < 0:
            delta_pct = (delta / base * 100) if base > 0 else -100.0
            quota = (delta / total_drop) if total_drop != 0 else 0.0
            pub_name = pub.replace("_", " ").title()
            contributors.append({
                "publisher_id": pub,
                "publisher_name": pub_name,
                "current_revenue": round(float(curr), 2),
                "baseline_revenue": round(float(base), 2),
                "delta_absolute": round(float(delta), 2),
                "delta_percent": round(float(delta_pct), 1),
                "quota_of_drop": round(float(quota), 4),
            })

    contributors.sort(key=lambda x: x["delta_absolute"])
    return contributors[:top_n]


def compute_triage_label(
    imp_delta_pct: float,
    env_split: dict,
) -> str:
    """
    Determine triage label:
    - TRAFFIC_DRIVEN if impressions drop >= 10%
    - COVERAGE_DRIVEN if coverage drop >= 10%
    - MIXED if both
    - REVENUE_ONLY otherwise
    """
    impressions_dropped = imp_delta_pct <= -10.0

    # Check coverage: compare current coverage distribution vs even split
    # We look at whether any environment's coverage dropped significantly
    coverage_values = [env_split[e].get("coverage", 0) for e in env_split]
    revenue_deltas = [env_split[e].get("delta_percent", 0) for e in env_split]

    # Coverage driven: large revenue drop but impressions stable => pricing/coverage issue
    # Use a proxy: if revenue delta is much larger than impressions delta
    coverage_issue = any(
        abs(env_split[e].get("delta_percent", 0)) >= 10
        and env_split[e].get("delta_absolute", 0) < 0
        and env_split[e].get("bacino", 0) > 0
        for e in env_split
    )

    if impressions_dropped and coverage_issue:
        return "MIXED"
    elif impressions_dropped:
        return "TRAFFIC_DRIVEN"
    elif coverage_issue:
        return "COVERAGE_DRIVEN"
    else:
        return "REVENUE_ONLY"


def compute_insights(
    severity: str,
    channel_group: str,
    delta_pct: float,
    revenue_current: float,
    revenue_baseline: float,
    imp_delta_pct: float,
    triage_label: str,
    top_contributor: str,
    top_contributor_quota: float,
) -> dict:
    """Generate insights JSON."""
    summary = (
        f"{triage_label.replace('_', ' ').title()} revenue drop of {delta_pct:+.1f}% "
        f"on {channel_group}. Top contributor: {top_contributor}."
    )

    insights_list = [
        f"Revenue dropped {delta_pct:+.1f}% vs baseline "
        f"(EUR {revenue_current:,.0f} vs EUR {revenue_baseline:,.0f}).",
    ]

    if imp_delta_pct is not None and not np.isnan(imp_delta_pct):
        insights_list.append(
            f"Impressions changed {imp_delta_pct:+.1f}% vs baseline."
        )

    insights_list.append(
        f"{top_contributor} accounts for {top_contributor_quota:.0%} of total drop."
    )

    next_steps = []
    if triage_label == "TRAFFIC_DRIVEN":
        next_steps = [
            f"Investigate traffic sources for {top_contributor}.",
            f"Check {channel_group} demand partner status.",
            "Monitor next 24h window for recovery.",
        ]
    elif triage_label == "COVERAGE_DRIVEN":
        next_steps = [
            f"Check {top_contributor} ad configuration and fill rates.",
            f"Review {channel_group} floor prices and bid landscape.",
            "Verify no ad unit changes were deployed.",
        ]
    elif triage_label == "MIXED":
        next_steps = [
            f"Check {top_contributor} for both traffic and ad config issues.",
            f"Review {channel_group} demand partner and traffic source status.",
            "Escalate if not resolved within 24h.",
        ]
    else:
        next_steps = [
            f"Check CPM trends for {channel_group}.",
            f"Review {top_contributor} yield optimization settings.",
            "Monitor next 2h window.",
        ]

    return {
        "summary": summary,
        "insights": insights_list,
        "next_steps": next_steps,
        "cache_warning": (
            "After applying a fix, metrics may remain degraded for 30-60 minutes "
            "due to cache/memory effects in ad serving pipeline."
        ),
    }


def generate_alert_id(date, severity: str, used_ids: set) -> str:
    """
    Generate alert ID in format ALT-YYYYMMDD-HHMMSS-P{0,1,2}.
    Ensures uniqueness by varying the HHMMSS portion.
    """
    date_str = pd.Timestamp(date).strftime("%Y%m%d")
    sev_suffix = severity  # e.g. "P0"

    # Generate a random hour (00-23) for variation
    for attempt in range(1000):
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        time_str = f"{hour:02d}{minute:02d}{second:02d}"
        alert_id = f"ALT-{date_str}-{time_str}-{sev_suffix}"
        if alert_id not in used_ids:
            used_ids.add(alert_id)
            return alert_id

    raise ValueError(f"Could not generate unique alert_id for date={date}, severity={severity}")


def build_alerts(raw_df: pd.DataFrame, sampled_anomalies: pd.DataFrame) -> list:
    """Build full alert records from sampled anomalies."""
    alerts = []
    used_ids = set()

    total = len(sampled_anomalies)
    print(f"\nBuilding {total} alert records with full enrichment ...")

    for i, (_, row) in enumerate(sampled_anomalies.iterrows()):
        if (i + 1) % 20 == 0 or i == 0:
            print(f"  Processing alert {i + 1}/{total} ...")

        date = row["date"]
        channel_group = row["channel_group"]
        severity = row["severity"]
        revenue_current = round(row["revenue"], 2)
        revenue_baseline = round(row["baseline_revenue"], 2)
        delta_pct = round(row["delta_pct"], 1)
        imp_delta_pct = row.get("imp_delta_pct", 0.0)

        # Enrichment computations
        geo_breakdown = compute_geo_breakdown(raw_df, date, channel_group)
        env_split = compute_environment_split(raw_df, date, channel_group)
        contributors = compute_contributors(raw_df, date, channel_group, top_n=5)
        triage_label = compute_triage_label(imp_delta_pct, env_split)

        top_contrib_name = contributors[0]["publisher_name"] if contributors else "Unknown"
        top_contrib_quota = contributors[0]["quota_of_drop"] if contributors else 0.0

        insights = compute_insights(
            severity=severity,
            channel_group=channel_group,
            delta_pct=delta_pct,
            revenue_current=revenue_current,
            revenue_baseline=revenue_baseline,
            imp_delta_pct=imp_delta_pct,
            triage_label=triage_label,
            top_contributor=top_contrib_name,
            top_contributor_quota=top_contrib_quota,
        )

        alert_id = generate_alert_id(date, severity, used_ids)

        # Timestamp: use the date + a random time within business hours
        hour = random.randint(6, 22)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        timestamp = pd.Timestamp(date).replace(hour=hour, minute=minute, second=second)
        ts_str = timestamp.strftime("%Y-%m-%dT%H:%M:%S")

        now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")

        # Determine alert_rule from anomaly characteristics:
        # A3: near-zero revenue (< 100 EUR) or very low coverage (< 0.05)
        # A2: mild drift (delta between -5% and -8%)
        # A1: significant revenue drop vs baseline (default)
        total_coverage = sum(env_split[e].get("coverage", 0) for e in env_split)
        if revenue_current < 100 or total_coverage < 0.05:
            alert_rule = "A3"
        elif -8.0 <= delta_pct < -5.0:
            alert_rule = "A2"
        else:
            alert_rule = "A1"
        exec_time = round(random.uniform(0.2, 2.5), 2)

        # Most alerts are OPEN, some historical ones are RESOLVED
        days_ago = (pd.Timestamp("2026-01-22") - pd.Timestamp(date)).days
        if days_ago > 60:
            status = random.choice(["OPEN", "RESOLVED", "RESOLVED"])
        elif days_ago > 30:
            status = random.choice(["OPEN", "OPEN", "RESOLVED"])
        else:
            status = "OPEN"

        alerts.append({
            "alert_id": alert_id,
            "timestamp": ts_str,
            "severity": severity,
            "channel_group": channel_group,
            "status": status,
            "alert_rule": alert_rule,
            "revenue_current": revenue_current,
            "revenue_baseline": revenue_baseline,
            "revenue_delta_pct": delta_pct,
            "triage_label": triage_label,
            "contributors_json": json.dumps(contributors),
            "geo_breakdown_json": json.dumps(geo_breakdown),
            "environment_split_json": json.dumps(env_split),
            "insights_json": json.dumps(insights),
            "execution_time_sec": exec_time,
            "data_source": "parquet",
            "config_version": "1.0.0",
            "created_at": now_str,
            "updated_at": now_str,
        })

    return alerts


def generate_alert_events(alerts: list) -> list:
    """Generate sample alert_events (ACK, COMMENT) for some recent alerts."""
    events = []
    users = ["admin", "ops_team", "yield_mgr", "data_eng", "support"]

    # Pick ~15-20 recent alerts for events
    recent_alerts = [a for a in alerts if a["timestamp"] >= "2025-06-01"]
    if len(recent_alerts) > 20:
        recent_alerts = random.sample(recent_alerts, 20)

    comments = [
        "Investigating - checking demand partner logs.",
        "Confirmed traffic drop from SEO changes at publisher side.",
        "Floor price adjustment applied, monitoring recovery.",
        "Publisher notified about ad unit misconfiguration.",
        "Demand partner reported server-side issue, ETA 2h for fix.",
        "Recovery observed after cache refresh.",
        "Escalated to yield optimization team.",
        "Root cause: seasonal traffic pattern, no action needed.",
        "Correlates with known CDN outage window.",
        "Reverted recent config change, monitoring.",
    ]

    for alert in recent_alerts:
        alert_id = alert["alert_id"]
        alert_ts = datetime.strptime(alert["timestamp"], "%Y-%m-%dT%H:%M:%S")

        # ACK event (shortly after alert)
        ack_ts = alert_ts + timedelta(minutes=random.randint(5, 120))
        events.append({
            "alert_id": alert_id,
            "event_type": "ACK",
            "user_id": random.choice(users),
            "comment": None,
            "timestamp": ack_ts.strftime("%Y-%m-%dT%H:%M:%S.%f"),
        })

        # Some get a COMMENT too
        if random.random() < 0.6:
            comment_ts = ack_ts + timedelta(minutes=random.randint(10, 300))
            events.append({
                "alert_id": alert_id,
                "event_type": "COMMENT",
                "user_id": random.choice(users),
                "comment": random.choice(comments),
                "timestamp": comment_ts.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            })

        # Resolved alerts get a RESOLVE event
        if alert["status"] == "RESOLVED":
            resolve_ts = ack_ts + timedelta(hours=random.randint(1, 48))
            events.append({
                "alert_id": alert_id,
                "event_type": "RESOLVE",
                "user_id": random.choice(users),
                "comment": random.choice(["Issue resolved.", "Recovery confirmed.", None]),
                "timestamp": resolve_ts.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            })

    return events


def insert_into_database(alerts: list, events: list):
    """Clear old data and insert new alerts and events."""
    print(f"\nConnecting to database at {DB_PATH} ...")
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Delete existing data
    print("  Deleting existing alert_events ...")
    cursor.execute("DELETE FROM alert_events")
    print("  Deleting existing recheck_queue ...")
    cursor.execute("DELETE FROM recheck_queue")
    print("  Deleting existing alerts ...")
    cursor.execute("DELETE FROM alerts")
    # Reset autoincrement counters
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('alert_events', 'recheck_queue')")
    conn.commit()

    # Insert alerts
    print(f"  Inserting {len(alerts)} alerts ...")
    for alert in alerts:
        cursor.execute(
            """
            INSERT INTO alerts (
                alert_id, timestamp, severity, channel_group, status,
                alert_rule, revenue_current, revenue_baseline, revenue_delta_pct,
                triage_label, contributors_json, geo_breakdown_json,
                environment_split_json, insights_json, execution_time_sec,
                data_source, config_version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                alert["alert_id"],
                alert["timestamp"],
                alert["severity"],
                alert["channel_group"],
                alert["status"],
                alert["alert_rule"],
                alert["revenue_current"],
                alert["revenue_baseline"],
                alert["revenue_delta_pct"],
                alert["triage_label"],
                alert["contributors_json"],
                alert["geo_breakdown_json"],
                alert["environment_split_json"],
                alert["insights_json"],
                alert["execution_time_sec"],
                alert["data_source"],
                alert["config_version"],
                alert["created_at"],
                alert["updated_at"],
            ),
        )

    # Insert events
    print(f"  Inserting {len(events)} alert_events ...")
    for event in events:
        cursor.execute(
            """
            INSERT INTO alert_events (alert_id, event_type, user_id, comment, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event["alert_id"],
                event["event_type"],
                event["user_id"],
                event["comment"],
                event["timestamp"],
            ),
        )

    conn.commit()
    print("  Committed all changes.")

    # Verification
    print("\n========== VERIFICATION ==========")
    cursor.execute("SELECT COUNT(*) FROM alerts")
    print(f"  Total alerts: {cursor.fetchone()[0]}")

    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM alerts")
    row = cursor.fetchone()
    print(f"  Date range: {row[0]} to {row[1]}")

    cursor.execute("SELECT severity, COUNT(*) FROM alerts GROUP BY severity ORDER BY severity")
    print(f"  Severity distribution: {cursor.fetchall()}")

    cursor.execute("SELECT channel_group, COUNT(*) FROM alerts GROUP BY channel_group ORDER BY channel_group")
    print(f"  Channel distribution: {cursor.fetchall()}")

    cursor.execute("SELECT triage_label, COUNT(*) FROM alerts GROUP BY triage_label ORDER BY triage_label")
    print(f"  Triage labels: {cursor.fetchall()}")

    cursor.execute("SELECT status, COUNT(*) FROM alerts GROUP BY status ORDER BY status")
    print(f"  Status distribution: {cursor.fetchall()}")

    cursor.execute("SELECT COUNT(*) FROM alert_events")
    print(f"  Total alert_events: {cursor.fetchone()[0]}")

    # Validate geo_breakdown
    cursor.execute("SELECT geo_breakdown_json FROM alerts LIMIT 1")
    sample_geo = cursor.fetchone()[0]
    geo_data = json.loads(sample_geo)
    geo_clusters = [g["geo_cluster"] for g in geo_data]
    print(f"\n  Sample geo_breakdown clusters: {geo_clusters}")
    print(f"  Sample geo_breakdown: {json.dumps(geo_data, indent=2)}")

    # Validate alert_id format
    cursor.execute("SELECT alert_id FROM alerts LIMIT 5")
    sample_ids = [r[0] for r in cursor.fetchall()]
    print(f"\n  Sample alert IDs: {sample_ids}")

    import re
    pattern = re.compile(r"^ALT-\d{8}-\d{6}-P[012]$")
    cursor.execute("SELECT alert_id FROM alerts")
    all_ids = [r[0] for r in cursor.fetchall()]
    invalid = [aid for aid in all_ids if not pattern.match(aid)]
    if invalid:
        print(f"  WARNING: {len(invalid)} alert IDs do not match pattern!")
        print(f"  Examples: {invalid[:5]}")
    else:
        print(f"  All {len(all_ids)} alert IDs match the required pattern.")

    conn.close()
    print("\n========== DONE ==========")


def main():
    print("=" * 60)
    print("VNA Alert Regeneration Script")
    print("=" * 60)

    # Step 1: Load data
    raw_df = load_parquet()

    # Step 2: Compute daily aggregates with rolling baseline
    print("\nComputing daily aggregates ...")
    daily = compute_daily_aggregates(raw_df)
    print(f"  Daily aggregates: {len(daily)} rows")

    print("Computing rolling baselines (same weekday, 7-week average) ...")
    daily_with_baseline = compute_rolling_baseline(daily)
    print(f"  Rows with valid baseline: {len(daily_with_baseline)}")

    # Step 3: Detect anomalies
    print("\nDetecting anomalies ...")
    anomalies = detect_anomalies(daily_with_baseline)

    # Step 4: Sample target count with desired distribution
    print("\nSampling target alerts ...")
    sampled = sample_target_alerts(anomalies)

    # Step 5: Build full alert records with enrichment
    alerts = build_alerts(raw_df, sampled)

    # Step 6: Generate alert events
    print("\nGenerating alert events ...")
    events = generate_alert_events(alerts)
    print(f"  Generated {len(events)} events")

    # Step 7: Insert into database
    insert_into_database(alerts, events)


if __name__ == "__main__":
    main()
