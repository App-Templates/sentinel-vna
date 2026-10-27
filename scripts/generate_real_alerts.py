#!/usr/bin/env python3
"""
Generate comprehensive alerts from real parquet data (2024-2026).

Reads daily_channel_aggregated and daily_adrequests_aggregated parquet files,
detects revenue anomalies using 7-week same-weekday baseline, and populates
both vna_alerts.db and alerts.db with ~150 fully enriched alerts.

JSON field names match the frontend TypeScript interfaces exactly:
  - GeoBreakdown: geo_cluster, current_revenue, baseline_revenue, delta_absolute, delta_percent, contribution
  - Contributor: publisher_id, publisher_name, current_revenue, baseline_revenue, delta_absolute, delta_percent, quota_of_drop
  - EnvironmentMetrics: revenue, baseline_revenue, delta_absolute, delta_percent, bacino, coverage
  - AlertInsights: summary, insights, next_steps, cache_warning
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
DB_PATHS = [
    PROJECT_ROOT / "data" / "vna_alerts.db",
    PROJECT_ROOT / "data" / "alerts.db",
]
CHANNEL_PARQUET = PROJECT_ROOT / "data" / "baseline" / "daily_channel_aggregated.parquet"
ADREQ_PARQUET = PROJECT_ROOT / "data" / "baseline" / "daily_adrequests_aggregated.parquet"

TARGET_ALERT_COUNT = 150
SEVERITY_THRESHOLDS = {"P0": -15.0, "P1": -10.0, "P2": -5.0}
TARGET_DIST = {"P0": 0.20, "P1": 0.35, "P2": 0.45}
ALERT_RULES = ["A1", "A2", "A3"]

random.seed(42)
np.random.seed(42)

LOG_FILE = "/tmp/vna-datascience.log"


def log(msg: str):
    ts = datetime.utcnow().strftime("%H:%M:%S")
    line = f"[{ts}] generate_real_alerts: {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


# ──────────────────────────────────────────────────────────────────────
# Data loading
# ──────────────────────────────────────────────────────────────────────
def load_data():
    log(f"Loading channel parquet from {CHANNEL_PARQUET}")
    ch = pd.read_parquet(CHANNEL_PARQUET)
    ch["date"] = pd.to_datetime(ch["date"])
    log(f"  Channel data: {len(ch):,} rows, {ch['date'].min().date()} to {ch['date'].max().date()}")

    log(f"Loading adrequests parquet from {ADREQ_PARQUET}")
    ar = pd.read_parquet(ADREQ_PARQUET)
    ar["date"] = pd.to_datetime(ar["date"])
    log(f"  Adrequests data: {len(ar):,} rows, {ar['date'].min().date()} to {ar['date'].max().date()}")

    return ch, ar


# ──────────────────────────────────────────────────────────────────────
# Baseline computation
# ──────────────────────────────────────────────────────────────────────
def compute_daily_totals(ch: pd.DataFrame) -> pd.DataFrame:
    """Aggregate revenue by date + channel_group."""
    daily = (
        ch.groupby(["date", "channel_group"])
        .agg(revenue=("revenue", "sum"), impressions=("impressions", "sum"))
        .reset_index()
        .sort_values(["channel_group", "date"])
    )
    return daily


def compute_baselines(daily: pd.DataFrame) -> pd.DataFrame:
    """7-week same-weekday rolling baseline for each date+channel_group."""
    results = []
    for cg, group in daily.groupby("channel_group"):
        group = group.sort_values("date").reset_index(drop=True)
        date_to_rev = dict(zip(group["date"], group["revenue"]))
        date_to_imp = dict(zip(group["date"], group["impressions"]))

        for _, row in group.iterrows():
            d = row["date"]
            past_revs, past_imps = [], []
            for w in range(1, 8):
                pd_date = d - timedelta(weeks=w)
                if pd_date in date_to_rev:
                    past_revs.append(date_to_rev[pd_date])
                    past_imps.append(date_to_imp[pd_date])

            if len(past_revs) >= 2:
                bl_rev = np.mean(past_revs)
                bl_imp = np.mean(past_imps)
                delta_pct = (row["revenue"] - bl_rev) / bl_rev * 100
                imp_delta = (row["impressions"] - bl_imp) / bl_imp * 100
                results.append({
                    "date": d,
                    "channel_group": cg,
                    "revenue": row["revenue"],
                    "impressions": row["impressions"],
                    "baseline_revenue": bl_rev,
                    "baseline_impressions": bl_imp,
                    "delta_pct": delta_pct,
                    "imp_delta_pct": imp_delta,
                })

    df = pd.DataFrame(results)
    log(f"  Baseline computed: {len(df)} date-channel rows with valid baseline")
    return df


# ──────────────────────────────────────────────────────────────────────
# Anomaly detection and sampling
# ──────────────────────────────────────────────────────────────────────
def detect_and_sample(bl: pd.DataFrame) -> pd.DataFrame:
    """Classify anomalies by severity and sample to target distribution."""

    def classify(delta):
        if delta <= SEVERITY_THRESHOLDS["P0"]:
            return "P0"
        elif delta <= SEVERITY_THRESHOLDS["P1"]:
            return "P1"
        elif delta <= SEVERITY_THRESHOLDS["P2"]:
            return "P2"
        return None

    bl["severity"] = bl["delta_pct"].apply(classify)
    anomalies = bl[bl["severity"].notna()].copy()
    log(f"  Raw anomalies: {len(anomalies)} -- {anomalies['severity'].value_counts().to_dict()}")

    target_p0 = int(TARGET_ALERT_COUNT * TARGET_DIST["P0"])
    target_p1 = int(TARGET_ALERT_COUNT * TARGET_DIST["P1"])
    target_p2 = TARGET_ALERT_COUNT - target_p0 - target_p1

    parts = []
    for sev, target in [("P0", target_p0), ("P1", target_p1), ("P2", target_p2)]:
        pool = anomalies[anomalies["severity"] == sev]
        if len(pool) >= target:
            parts.append(pool.sample(n=target, random_state=42))
        else:
            parts.append(pool)
            log(f"  WARNING: Only {len(pool)} {sev} available (wanted {target})")

    sampled = pd.concat(parts).sort_values("date")
    log(f"  Sampled {len(sampled)} alerts: {sampled['severity'].value_counts().to_dict()}")
    log(f"  Channel dist: {sampled['channel_group'].value_counts().to_dict()}")
    return sampled


# ──────────────────────────────────────────────────────────────────────
# Enrichment functions
# ──────────────────────────────────────────────────────────────────────
def _past_dates(date, weeks=7):
    return [date - timedelta(weeks=w) for w in range(1, weeks + 1)]


def compute_geo_breakdown(ch: pd.DataFrame, date, channel_group: str) -> list:
    """Real per-geo revenue breakdown matching GeoBreakdown interface."""
    day = ch[(ch["date"] == date) & (ch["channel_group"] == channel_group)]
    past = ch[(ch["date"].isin(_past_dates(date))) & (ch["channel_group"] == channel_group)]

    geo_curr = day.groupby("geo_cluster")["revenue"].sum()
    geo_base = past.groupby(["date", "geo_cluster"])["revenue"].sum().groupby("geo_cluster").mean()
    total_delta = geo_curr.sum() - geo_base.sum()

    breakdown = []
    for geo in ["ITA", "ES", "OTHER"]:
        curr = float(geo_curr.get(geo, 0.0))
        base = float(geo_base.get(geo, 0.0))
        delta_abs = curr - base
        delta_pct = (delta_abs / base * 100) if base > 0 else 0.0
        contrib = (delta_abs / total_delta) if total_delta != 0 else 0.0
        breakdown.append({
            "geo_cluster": geo,
            "current_revenue": round(curr, 2),
            "baseline_revenue": round(base, 2),
            "delta_absolute": round(delta_abs, 2),
            "delta_percent": round(delta_pct, 1),
            "contribution": round(contrib, 4),
        })
    return breakdown


def compute_environment_split(ch: pd.DataFrame, ar: pd.DataFrame, date, channel_group: str) -> dict:
    """Real environment split with bacino/coverage from adrequests data."""
    # Revenue from channel data
    day_ch = ch[(ch["date"] == date) & (ch["channel_group"] == channel_group)]
    past_ch = ch[(ch["date"].isin(_past_dates(date))) & (ch["channel_group"] == channel_group)]

    env_curr_rev = day_ch.groupby("environment")["revenue"].sum()
    env_base_rev = (
        past_ch.groupby(["date", "environment"])["revenue"].sum()
        .groupby("environment").mean()
    )

    # Bacino/coverage from adrequests (no channel_group dimension)
    day_ar = ar[ar["date"] == date]
    past_ar = ar[ar["date"].isin(_past_dates(date))]

    env_curr_ar = day_ar.groupby("environment").agg(
        bacino=("bacino", "sum"), coverage=("coverage", "mean")
    )
    env_base_ar = (
        past_ar.groupby(["date", "environment"]).agg(
            bacino=("bacino", "sum"), coverage=("coverage", "mean")
        ).groupby("environment").mean()
    )

    total_bacino = day_ar["bacino"].sum()

    split = {}
    for env in ["WEB", "AMP", "APP"]:
        curr_rev = float(env_curr_rev.get(env, 0.0))
        base_rev = float(env_base_rev.get(env, 0.0)) if env in env_base_rev.index else 0.0
        delta_abs = curr_rev - base_rev
        delta_pct = (delta_abs / base_rev * 100) if base_rev > 0 else 0.0

        curr_bacino = int(env_curr_ar.loc[env, "bacino"]) if env in env_curr_ar.index else 0
        curr_coverage = float(env_curr_ar.loc[env, "coverage"]) if env in env_curr_ar.index else 0.0

        split[env] = {
            "revenue": round(curr_rev, 2),
            "baseline_revenue": round(base_rev, 2),
            "delta_absolute": round(delta_abs, 2),
            "delta_percent": round(delta_pct, 1),
            "bacino": curr_bacino,
            "coverage": round(curr_coverage, 4),
        }
    return split


def compute_contributors(ch: pd.DataFrame, date, channel_group: str, top_n: int = 5) -> list:
    """Top publishers by revenue drop matching Contributor interface."""
    day = ch[(ch["date"] == date) & (ch["channel_group"] == channel_group)]
    past = ch[(ch["date"].isin(_past_dates(date))) & (ch["channel_group"] == channel_group)]

    pub_curr = day.groupby("publisher_id")["revenue"].sum()
    pub_base = (
        past.groupby(["date", "publisher_id"])["revenue"].sum()
        .groupby("publisher_id").mean()
    )

    all_pubs = set(pub_curr.index) | set(pub_base.index)
    total_drop = sum(
        pub_curr.get(p, 0.0) - pub_base.get(p, 0.0)
        for p in all_pubs
        if pub_curr.get(p, 0.0) - pub_base.get(p, 0.0) < 0
    )

    contributors = []
    for pub in all_pubs:
        curr = float(pub_curr.get(pub, 0.0))
        base = float(pub_base.get(pub, 0.0))
        delta = curr - base
        if delta < 0:
            delta_pct = (delta / base * 100) if base > 0 else -100.0
            quota = (delta / total_drop) if total_drop != 0 else 0.0
            contributors.append({
                "publisher_id": pub,
                "publisher_name": pub.replace("_", " ").title(),
                "current_revenue": round(curr, 2),
                "baseline_revenue": round(base, 2),
                "delta_absolute": round(delta, 2),
                "delta_percent": round(delta_pct, 1),
                "quota_of_drop": round(quota, 4),
            })

    contributors.sort(key=lambda x: x["delta_absolute"])
    return contributors[:top_n]


def compute_triage_label(imp_delta_pct: float, env_split: dict, ar: pd.DataFrame, date) -> str:
    """
    Triage label based on bacino vs coverage changes:
      - TRAFFIC_DRIVEN: bacino drops significantly (>= 8%)
      - COVERAGE_DRIVEN: coverage drops significantly (>= 5%) but bacino stable
      - MIXED: both bacino and coverage drop
      - REVENUE_ONLY: neither dimension explains the drop well
    """
    # Compute bacino and coverage deltas from adrequests
    day_ar = ar[ar["date"] == date]
    past_ar = ar[ar["date"].isin(_past_dates(date))]

    curr_bacino = day_ar["bacino"].sum()
    curr_coverage = day_ar["coverage"].mean()
    base_bacino = past_ar.groupby("date")["bacino"].sum().mean()
    base_coverage = past_ar.groupby("date")["coverage"].mean().mean()

    bacino_delta = ((curr_bacino - base_bacino) / base_bacino * 100) if base_bacino > 0 else 0
    coverage_delta = ((curr_coverage - base_coverage) / base_coverage * 100) if base_coverage > 0 else 0

    bacino_drop = bacino_delta <= -8.0
    coverage_drop = coverage_delta <= -5.0

    if bacino_drop and coverage_drop:
        return "MIXED"
    elif bacino_drop:
        return "TRAFFIC_DRIVEN"
    elif coverage_drop:
        return "COVERAGE_DRIVEN"
    else:
        # Fallback: use impression delta as proxy
        if imp_delta_pct <= -10.0:
            return "TRAFFIC_DRIVEN"
        return "REVENUE_ONLY"


def compute_insights(
    severity: str, channel_group: str, delta_pct: float,
    revenue_current: float, revenue_baseline: float,
    imp_delta_pct: float, triage_label: str,
    top_contributor: str, top_contributor_quota: float,
) -> dict:
    """Generate insights JSON matching AlertInsights interface."""
    summary = (
        f"{triage_label.replace('_', ' ').title()} revenue drop of {delta_pct:+.1f}% "
        f"on {channel_group}. Top contributor: {top_contributor}."
    )

    insights_list = [
        f"Revenue dropped {delta_pct:+.1f}% vs baseline "
        f"(EUR {revenue_current:,.0f} vs EUR {revenue_baseline:,.0f}).",
    ]
    if not np.isnan(imp_delta_pct):
        insights_list.append(f"Impressions changed {imp_delta_pct:+.1f}% vs baseline.")
    insights_list.append(
        f"{top_contributor} accounts for {top_contributor_quota:.0%} of total drop."
    )

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


# ──────────────────────────────────────────────────────────────────────
# Alert ID generation
# ──────────────────────────────────────────────────────────────────────
def generate_alert_id(date, severity: str, used_ids: set) -> str:
    date_str = pd.Timestamp(date).strftime("%Y%m%d")
    for _ in range(1000):
        h, m, s = random.randint(0, 23), random.randint(0, 59), random.randint(0, 59)
        aid = f"ALT-{date_str}-{h:02d}{m:02d}{s:02d}-{severity}"
        if aid not in used_ids:
            used_ids.add(aid)
            return aid
    raise ValueError(f"Could not generate unique alert_id for {date}/{severity}")


# ──────────────────────────────────────────────────────────────────────
# Build full alert records
# ──────────────────────────────────────────────────────────────────────
def build_alerts(ch: pd.DataFrame, ar: pd.DataFrame, sampled: pd.DataFrame) -> list:
    alerts = []
    used_ids = set()
    total = len(sampled)
    log(f"Building {total} alert records with full enrichment ...")

    max_date = ch["date"].max()

    for i, (_, row) in enumerate(sampled.iterrows()):
        if (i + 1) % 25 == 0 or i == 0:
            log(f"  Processing alert {i + 1}/{total} ...")

        date = row["date"]
        channel_group = row["channel_group"]
        severity = row["severity"]
        revenue_current = round(row["revenue"], 2)
        revenue_baseline = round(row["baseline_revenue"], 2)
        delta_pct = round(row["delta_pct"], 1)
        imp_delta_pct = row.get("imp_delta_pct", 0.0)

        # Enrichment
        geo_breakdown = compute_geo_breakdown(ch, date, channel_group)
        env_split = compute_environment_split(ch, ar, date, channel_group)
        contributors = compute_contributors(ch, date, channel_group, top_n=5)
        triage_label = compute_triage_label(imp_delta_pct, env_split, ar, date)

        top_name = contributors[0]["publisher_name"] if contributors else "Unknown"
        top_quota = contributors[0]["quota_of_drop"] if contributors else 0.0

        insights = compute_insights(
            severity, channel_group, delta_pct, revenue_current, revenue_baseline,
            imp_delta_pct, triage_label, top_name, top_quota,
        )

        alert_id = generate_alert_id(date, severity, used_ids)

        # Timestamp: date + noon (12:00) for daily data
        hour = 12
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        ts = pd.Timestamp(date).replace(hour=hour, minute=minute, second=second)
        ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S")

        now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")

        # Status distribution: older => more likely resolved/ack
        days_ago = (max_date - pd.Timestamp(date)).days
        if days_ago > 180:
            status = random.choices(
                ["RESOLVED", "ACK", "OPEN"], weights=[65, 20, 15], k=1
            )[0]
        elif days_ago > 90:
            status = random.choices(
                ["RESOLVED", "ACK", "OPEN"], weights=[45, 25, 30], k=1
            )[0]
        elif days_ago > 30:
            status = random.choices(
                ["RESOLVED", "ACK", "OPEN"], weights=[25, 30, 45], k=1
            )[0]
        else:
            status = random.choices(
                ["OPEN", "ACK", "RESOLVED"], weights=[60, 25, 15], k=1
            )[0]

        alerts.append({
            "alert_id": alert_id,
            "timestamp": ts_str,
            "severity": severity,
            "channel_group": channel_group,
            "status": status,
            "alert_rule": random.choice(ALERT_RULES),
            "revenue_current": revenue_current,
            "revenue_baseline": revenue_baseline,
            "revenue_delta_pct": delta_pct,
            "triage_label": triage_label,
            "contributors_json": json.dumps(contributors),
            "geo_breakdown_json": json.dumps(geo_breakdown),
            "environment_split_json": json.dumps(env_split),
            "insights_json": json.dumps(insights),
            "execution_time_sec": round(random.uniform(0.3, 2.8), 2),
            "data_source": "parquet",
            "config_version": "1.0.0",
            "created_at": now_str,
            "updated_at": now_str,
        })

    return alerts


# ──────────────────────────────────────────────────────────────────────
# Alert events
# ──────────────────────────────────────────────────────────────────────
def generate_alert_events(alerts: list) -> list:
    events = []
    users = ["admin", "ops_team", "yield_mgr", "data_eng", "support"]

    ack_comments = [
        "Looking into this, checking demand partner dashboards.",
        "Acknowledged, investigating publisher-side changes.",
        "On it - will check traffic source and floor prices.",
        "Taking ownership, correlating with known events.",
        None,
        None,
    ]

    investigation_comments = [
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
        "Spike in invalid traffic flagged by verification vendor.",
        "Publisher pushed new page layout, impacting viewability.",
        "Demand source paused spending temporarily per their account manager.",
        "Holiday/event-driven traffic shift, expected to normalize.",
    ]

    resolve_comments = [
        "Issue resolved - demand partner back online.",
        "Recovery confirmed after floor price adjustment.",
        "Publisher fixed their configuration, metrics recovered.",
        "Resolved - seasonal dip as expected, closing.",
        "Traffic recovered after CDN issue was fixed.",
        "Auto-resolved: metrics returned to baseline within 24h.",
        None,
    ]

    for alert in alerts:
        alert_id = alert["alert_id"]
        alert_ts = datetime.strptime(alert["timestamp"], "%Y-%m-%dT%H:%M:%S")
        status = alert["status"]

        if status == "OPEN":
            # Some OPEN alerts have a COMMENT (someone looked but didn't ACK)
            if random.random() < 0.15:
                comment_ts = alert_ts + timedelta(minutes=random.randint(30, 480))
                events.append({
                    "alert_id": alert_id,
                    "event_type": "COMMENT",
                    "user_id": random.choice(users),
                    "comment": random.choice(investigation_comments),
                    "timestamp": comment_ts.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                })

        elif status == "ACK":
            # ACK event
            ack_ts = alert_ts + timedelta(minutes=random.randint(5, 180))
            events.append({
                "alert_id": alert_id,
                "event_type": "ACK",
                "user_id": random.choice(users),
                "comment": random.choice(ack_comments),
                "timestamp": ack_ts.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            })
            # Some ACK alerts have investigation comments
            if random.random() < 0.5:
                comment_ts = ack_ts + timedelta(minutes=random.randint(15, 360))
                events.append({
                    "alert_id": alert_id,
                    "event_type": "COMMENT",
                    "user_id": random.choice(users),
                    "comment": random.choice(investigation_comments),
                    "timestamp": comment_ts.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                })

        elif status == "RESOLVED":
            # ACK event first
            ack_ts = alert_ts + timedelta(minutes=random.randint(5, 120))
            events.append({
                "alert_id": alert_id,
                "event_type": "ACK",
                "user_id": random.choice(users),
                "comment": random.choice(ack_comments),
                "timestamp": ack_ts.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            })

            # Optional investigation comment
            if random.random() < 0.4:
                comment_ts = ack_ts + timedelta(minutes=random.randint(15, 300))
                events.append({
                    "alert_id": alert_id,
                    "event_type": "COMMENT",
                    "user_id": random.choice(users),
                    "comment": random.choice(investigation_comments),
                    "timestamp": comment_ts.strftime("%Y-%m-%dT%H:%M:%S.%f"),
                })

            # RESOLVE event
            resolve_ts = ack_ts + timedelta(hours=random.randint(1, 72))
            events.append({
                "alert_id": alert_id,
                "event_type": "RESOLVE",
                "user_id": random.choice(users),
                "comment": random.choice(resolve_comments),
                "timestamp": resolve_ts.strftime("%Y-%m-%dT%H:%M:%S.%f"),
            })

    log(f"  Generated {len(events)} alert events")
    return events


# ──────────────────────────────────────────────────────────────────────
# Database insertion
# ──────────────────────────────────────────────────────────────────────
SQL_CREATE_ALERTS = """
CREATE TABLE IF NOT EXISTS alerts (
    alert_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('P0', 'P1', 'P2')),
    channel_group TEXT NOT NULL CHECK(channel_group IN ('GOOGLE', 'OPEN_BIDDING')),
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'ACK', 'RESOLVED', 'SNOOZED')),
    alert_rule TEXT NOT NULL CHECK(alert_rule IN ('A1', 'A2', 'A3')),
    revenue_current REAL NOT NULL,
    revenue_baseline REAL NOT NULL,
    revenue_delta_pct REAL NOT NULL,
    triage_label TEXT NOT NULL,
    contributors_json TEXT DEFAULT '[]',
    geo_breakdown_json TEXT DEFAULT '[]',
    environment_split_json TEXT DEFAULT '{}',
    insights_json TEXT DEFAULT '{}',
    execution_time_sec REAL DEFAULT 0.0,
    data_source TEXT DEFAULT 'athena',
    config_version TEXT DEFAULT '1.0.0',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

SQL_CREATE_ALERT_EVENTS = """
CREATE TABLE IF NOT EXISTS alert_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK(event_type IN ('ACK', 'RESOLVE', 'RECHECK', 'COMMENT')),
    user_id TEXT NOT NULL,
    comment TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
);
"""

SQL_CREATE_RECHECK_QUEUE = """
CREATE TABLE IF NOT EXISTS recheck_queue (
    queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id TEXT NOT NULL,
    scheduled_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'COMPLETED', 'FAILED')),
    created_at TEXT NOT NULL,
    FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
);
"""

SQL_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);",
    "CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);",
]


def insert_into_database(alerts: list, events: list):
    for db_path in DB_PATHS:
        log(f"Writing to {db_path} ...")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Ensure tables exist
        cursor.execute(SQL_CREATE_ALERTS)
        cursor.execute(SQL_CREATE_ALERT_EVENTS)
        cursor.execute(SQL_CREATE_RECHECK_QUEUE)
        for idx_sql in SQL_CREATE_INDEXES:
            cursor.execute(idx_sql)
        conn.commit()

        # Clear existing data
        cursor.execute("DELETE FROM alert_events")
        cursor.execute("DELETE FROM recheck_queue")
        cursor.execute("DELETE FROM alerts")
        try:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('alert_events', 'recheck_queue')")
        except sqlite3.OperationalError:
            pass
        conn.commit()

        # Insert alerts
        for alert in alerts:
            cursor.execute(
                """INSERT INTO alerts (
                    alert_id, timestamp, severity, channel_group, status,
                    alert_rule, revenue_current, revenue_baseline, revenue_delta_pct,
                    triage_label, contributors_json, geo_breakdown_json,
                    environment_split_json, insights_json, execution_time_sec,
                    data_source, config_version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    alert["alert_id"], alert["timestamp"], alert["severity"],
                    alert["channel_group"], alert["status"], alert["alert_rule"],
                    alert["revenue_current"], alert["revenue_baseline"],
                    alert["revenue_delta_pct"], alert["triage_label"],
                    alert["contributors_json"], alert["geo_breakdown_json"],
                    alert["environment_split_json"], alert["insights_json"],
                    alert["execution_time_sec"], alert["data_source"],
                    alert["config_version"], alert["created_at"], alert["updated_at"],
                ),
            )

        # Insert events
        for event in events:
            cursor.execute(
                """INSERT INTO alert_events (alert_id, event_type, user_id, comment, timestamp)
                VALUES (?, ?, ?, ?, ?)""",
                (event["alert_id"], event["event_type"], event["user_id"],
                 event["comment"], event["timestamp"]),
            )

        conn.commit()
        log(f"  {db_path.name}: {len(alerts)} alerts, {len(events)} events inserted")
        conn.close()


def verify(alerts: list, events: list):
    db_path = DB_PATHS[0]
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    log("=" * 50)
    log("VERIFICATION")
    log("=" * 50)

    cursor.execute("SELECT COUNT(*) FROM alerts")
    log(f"  Total alerts: {cursor.fetchone()[0]}")

    cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM alerts")
    r = cursor.fetchone()
    log(f"  Date range: {r[0]} to {r[1]}")

    cursor.execute("SELECT severity, COUNT(*) FROM alerts GROUP BY severity ORDER BY severity")
    log(f"  Severity: {cursor.fetchall()}")

    cursor.execute("SELECT channel_group, COUNT(*) FROM alerts GROUP BY channel_group")
    log(f"  Channel: {cursor.fetchall()}")

    cursor.execute("SELECT triage_label, COUNT(*) FROM alerts GROUP BY triage_label")
    log(f"  Triage: {cursor.fetchall()}")

    cursor.execute("SELECT status, COUNT(*) FROM alerts GROUP BY status ORDER BY status")
    log(f"  Status: {cursor.fetchall()}")

    cursor.execute("SELECT COUNT(*) FROM alert_events")
    log(f"  Total events: {cursor.fetchone()[0]}")

    cursor.execute("SELECT event_type, COUNT(*) FROM alert_events GROUP BY event_type")
    log(f"  Event types: {cursor.fetchall()}")

    # Validate geo_breakdown
    cursor.execute("SELECT geo_breakdown_json FROM alerts LIMIT 1")
    geo = json.loads(cursor.fetchone()[0])
    clusters = [g["geo_cluster"] for g in geo]
    log(f"  Sample geo clusters: {clusters}")
    log(f"  Sample geo: {json.dumps(geo[0])}")

    # Validate alert_id format
    import re
    pattern = re.compile(r"^ALT-\d{8}-\d{6}-P[012]$")
    cursor.execute("SELECT alert_id FROM alerts")
    all_ids = [r[0] for r in cursor.fetchall()]
    invalid = [a for a in all_ids if not pattern.match(a)]
    if invalid:
        log(f"  WARNING: {len(invalid)} invalid alert IDs: {invalid[:3]}")
    else:
        log(f"  All {len(all_ids)} alert IDs valid")

    conn.close()
    log("=" * 50)
    log("DONE")


# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────
def main():
    log("=" * 60)
    log("VNA Generate Real Alerts")
    log("=" * 60)

    ch, ar = load_data()

    log("Computing daily totals ...")
    daily = compute_daily_totals(ch)

    log("Computing 7-week same-weekday baselines ...")
    bl = compute_baselines(daily)

    log("Detecting anomalies and sampling ...")
    sampled = detect_and_sample(bl)

    alerts = build_alerts(ch, ar, sampled)

    log("Generating alert events ...")
    events = generate_alert_events(alerts)

    insert_into_database(alerts, events)
    verify(alerts, events)


if __name__ == "__main__":
    main()
