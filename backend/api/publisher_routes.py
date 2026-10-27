from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request

from backend.api.rate_limit import limiter
from backend.utils.config_loader import get_config
from backend.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/publishers")

BASE_DIR = Path(__file__).parent.parent.parent
# v1.2: both redirect to daily_aggregated.parquet (unified schema with channel_group)
DAILY_ADREQUESTS_PARQUET = BASE_DIR / "data" / "baseline" / "daily_aggregated.parquet"
DAILY_CHANNEL_PARQUET = BASE_DIR / "data" / "baseline" / "daily_aggregated.parquet"
SEASONAL_ANALYSIS_PATH = BASE_DIR / "data" / "seasonal" / "ecpm-seasonal-analysis.json"
ENRICHED_PATTERNS_PATH = BASE_DIR / "data" / "seasonal" / "enriched-recurring-patterns.json"
RECURRING_PATTERNS_PATH_LEGACY = BASE_DIR / "data" / "seasonal" / "recurring-ecpm-patterns.json"
OPT_WINDOWS_ENRICHED_PATH = BASE_DIR / "data" / "seasonal" / "optimization-windows-enriched.json"
# Phase 17.1 MAP-01 — Marco-maintained authoritative ad_unit_name → publisher mapping.
AD_UNIT_MAPPING_PATH = BASE_DIR / "data" / "sentinel_db" / "ad_unit_1_mapping.xlsx"

# In-memory caches
_adrequests_cache: Optional[pd.DataFrame] = None
_channel_cache: Optional[pd.DataFrame] = None
_seasonal_cache: Optional[dict] = None
_recurring_patterns_cache: Optional[dict] = None
_opt_windows_enriched_cache: Optional[dict] = None
_ad_unit_mapping_cache: Optional[dict[str, str]] = None

# Phase 11 API-02 — sell_type whitelist matches config/sell_type_proxy.yaml top-level keys verbatim.
# Single source of truth: config/sell_type_proxy.yaml. If that file evolves (v1.4 OPS-02
# adds real sell_type from upstream), update this tuple AND the Pydantic Query examples.
VALID_SELL_TYPES: tuple[str, ...] = (
    "Open_Market",
    "Header_Bidding",
    "Direct",
    "Deal",
    "Other",
)


def _load_adrequests() -> Optional[pd.DataFrame]:
    """Load daily adrequests parquet into memory with caching."""
    global _adrequests_cache

    if _adrequests_cache is not None:
        return _adrequests_cache

    if not os.path.exists(DAILY_ADREQUESTS_PARQUET):
        logger.warning("Daily adrequests parquet not found at %s", DAILY_ADREQUESTS_PARQUET)
        return None

    try:
        df = pd.read_parquet(DAILY_ADREQUESTS_PARQUET)
        df["date"] = pd.to_datetime(df["date"])
        _adrequests_cache = df
        logger.info("Loaded daily adrequests data: %d rows", len(df))
        return df
    except Exception as e:
        logger.error("Failed to load daily adrequests parquet: %s", e)
        return None


def _load_channel() -> Optional[pd.DataFrame]:
    """Load daily channel parquet into memory with caching."""
    global _channel_cache

    if _channel_cache is not None:
        return _channel_cache

    if not os.path.exists(DAILY_CHANNEL_PARQUET):
        logger.warning("Daily channel parquet not found at %s", DAILY_CHANNEL_PARQUET)
        return None

    try:
        df = pd.read_parquet(DAILY_CHANNEL_PARQUET)
        df["date"] = pd.to_datetime(df["date"])
        _channel_cache = df
        logger.info("Loaded daily channel data: %d rows", len(df))
        return df
    except Exception as e:
        logger.error("Failed to load daily channel parquet: %s", e)
        return None


def _load_seasonal_analysis() -> Optional[dict]:
    """Load seasonal analysis JSON into memory with caching."""
    global _seasonal_cache

    if _seasonal_cache is not None:
        return _seasonal_cache

    if not SEASONAL_ANALYSIS_PATH.exists():
        logger.warning("Seasonal analysis JSON not found at %s", SEASONAL_ANALYSIS_PATH)
        return None

    try:
        with open(SEASONAL_ANALYSIS_PATH) as f:
            data = json.load(f)

        # Build week-to-period lookup: {week_number: {"label": ..., "signal": ...}}
        period_by_id = {p["id"]: p for p in data.get("seasonal_periods", [])}
        week_lookup: dict[int, dict] = {}
        for week_str, info in data.get("week_date_ranges", {}).items():
            period_id = info.get("period")
            period = period_by_id.get(period_id)
            if period:
                week_lookup[int(week_str)] = {
                    "label": period["label"],
                    "signal": period["signal"],
                    "period_id": period_id,
                }

        data["_week_lookup"] = week_lookup
        _seasonal_cache = data
        logger.info("Loaded seasonal analysis: %d periods, %d weeks mapped", len(data.get("seasonal_periods", [])), len(week_lookup))
        return data
    except Exception as e:
        logger.error("Failed to load seasonal analysis JSON: %s", e)
        return None


def _load_recurring_patterns() -> Optional[dict]:
    """Load enriched recurring patterns JSON (with fallback to legacy file)."""
    global _recurring_patterns_cache

    if _recurring_patterns_cache is not None:
        return _recurring_patterns_cache

    # Prefer enriched file, fall back to legacy
    if ENRICHED_PATTERNS_PATH.exists():
        path = ENRICHED_PATTERNS_PATH
    elif RECURRING_PATTERNS_PATH_LEGACY.exists():
        path = RECURRING_PATTERNS_PATH_LEGACY
    else:
        logger.warning("No recurring patterns JSON found (checked enriched and legacy paths)")
        return None

    try:
        with open(path) as f:
            data = json.load(f)
        data["_source"] = str(path)
        _recurring_patterns_cache = data
        publishers_count = len(data.get("publishers", {}))
        logger.info("Loaded recurring patterns from %s: %d publishers", path.name, publishers_count)
        return data
    except Exception as e:
        logger.error("Failed to load recurring patterns JSON: %s", e)
        return None


def _load_opt_windows_enriched() -> Optional[dict]:
    """Load optimization windows enriched JSON into memory with caching."""
    global _opt_windows_enriched_cache

    if _opt_windows_enriched_cache is not None:
        return _opt_windows_enriched_cache

    if not OPT_WINDOWS_ENRICHED_PATH.exists():
        logger.warning("Optimization windows enriched JSON not found at %s", OPT_WINDOWS_ENRICHED_PATH)
        return None

    try:
        with open(OPT_WINDOWS_ENRICHED_PATH) as f:
            data = json.load(f)
        _opt_windows_enriched_cache = data
        publishers_count = len(data.get("publishers", {}))
        logger.info("Loaded optimization windows enriched: %d publishers", publishers_count)
        return data
    except Exception as e:
        logger.error("Failed to load optimization windows enriched JSON: %s", e)
        return None


def _load_ad_unit_mapping() -> Optional[dict[str, str]]:
    """Load Marco-maintained ad_unit_name → publisher mapping (Phase 17.1, MAP-02).

    Returns a dict keyed by raw ad_unit_name (as it appears in parquet
    publisher_id field), mapping to the clean PBI-style publisher name
    (the 'publisher' column of ad_unit_1_mapping.xlsx).

    Cache: module-level singleton. Returns None on file-missing or parse-error
    — the consumer falls back to raw publisher_id with a logged warning.
    """
    global _ad_unit_mapping_cache

    if _ad_unit_mapping_cache is not None:
        return _ad_unit_mapping_cache

    if not os.path.exists(AD_UNIT_MAPPING_PATH):
        logger.warning(
            "ad_unit_1_mapping.xlsx not found at %s — Phase 17.1 MAP-01 "
            "Excel copy step missing; endpoints will fall back to raw "
            "publisher_id and may surface AdGage_* / _npa names.",
            AD_UNIT_MAPPING_PATH,
        )
        return None

    try:
        df = pd.read_excel(AD_UNIT_MAPPING_PATH)
        if "ad_unit_name" not in df.columns or "publisher" not in df.columns:
            logger.error(
                "ad_unit_1_mapping.xlsx missing required columns "
                "(have %s); expected ad_unit_name + publisher.",
                list(df.columns),
            )
            return None
        mapping = dict(zip(df["ad_unit_name"].astype(str), df["publisher"].astype(str)))
        if len(mapping) != len(df):
            logger.warning(
                "ad_unit_1_mapping.xlsx had %d rows but %d unique "
                "ad_unit_name keys — duplicates collapsed.",
                len(df), len(mapping),
            )
        _ad_unit_mapping_cache = mapping
        logger.info(
            "Loaded ad_unit mapping: %d ad_unit_name keys → %d unique publishers",
            len(mapping), len(set(mapping.values())),
        )
        return mapping
    except Exception as e:
        logger.error("Failed to load ad_unit_1_mapping.xlsx: %s", e)
        return None


def _resolve_publisher_ad_units(clean_publisher: str) -> set[str]:
    """Reverse-lookup: clean publisher name → set of raw ad_unit_name strings.

    Plan 17.1 MAP-08. Used by all 5 drilldown endpoints (3 parquet-backed
    in this file + 2 SQL-backed in backend/api/routes.py + backend/db/
    operations.py).

    Returns an empty set if the publisher name has no mapping entries — the
    caller MUST handle this as 404 for parquet endpoints, because exposing a
    raw ad_unit_name passthrough would re-create the Phase 17 leak (the whole
    point of MAP-08 is that the clean PBI-style name is the only valid surface
    for clients).

    Defensive fallback: if mapping is unavailable (file missing / parse error
    — i.e. _load_ad_unit_mapping returned None), returns {clean_publisher}
    so callers fall back to exact-match query (preserves backward-compat with
    raw names in environments where the xlsx hasn't been deployed yet).
    """
    mapping = _load_ad_unit_mapping()
    if mapping is None:
        return {clean_publisher}
    return {ad_unit for ad_unit, pub in mapping.items() if pub == clean_publisher}


@router.get("/top")
@limiter.limit("60/minute")
def get_top_publishers(
    request: Request,
    limit: int = Query(35, ge=1, le=200),
    year: int = Query(2025),
    sell_type: Optional[str] = Query(
        None,
        description=(
            "Filter publishers by sell_type_proxy derived from channel_group. "
            "One of: Open_Market, Header_Bidding, Direct, Deal, Other. "
            "Omitted = no filter (backward compat). See config/sell_type_proxy.yaml."
        ),
    ),
):
    df = _load_adrequests()
    if df is None:
        raise HTTPException(status_code=503, detail="Ad requests data not available")

    # Phase 11 API-02 — sell_type validation + filter (kept BEFORE year filter to fail fast).
    if sell_type is not None:
        if sell_type not in VALID_SELL_TYPES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"sell_type must be one of {list(VALID_SELL_TYPES)}; "
                    f"got {sell_type!r}. See config/sell_type_proxy.yaml."
                ),
            )
        if "sell_type_proxy" not in df.columns:
            raise HTTPException(
                status_code=503,
                detail=(
                    "sell_type_proxy column not present in parquet "
                    "(ETL SCHEMA-04 not yet applied or parquet outdated)."
                ),
            )
        df = df[df["sell_type_proxy"] == sell_type]
        if df.empty:
            # No rows for this sell_type — return empty list with transparency.
            return {
                "publishers": [],
                "year": year,
                "total_publishers": 0,
                "sell_type_filter": sell_type,
            }

    df_year = df[df["date"].dt.year == year]
    if df_year.empty:
        return {
            "publishers": [],
            "year": year,
            "total_publishers": 0,
            "sell_type_filter": sell_type,
        }

    # Phase 17.1 MAP-03/04/05 — Apply Marco's authoritative ad_unit → publisher
    # mapping BEFORE every groupby. The mapping collapses _npa variants, normalizes
    # AdGage_* brand prefixes, and groups multi-ad_unit publishers (e.g.
    # Grupo Multimedios = AdGage_GrupoMultimedios + AdGage_Multimedios). This
    # supersedes Phase 17's hardcoded synthetic-family aggregation block which
    # wrongly merged Mediamond and Mondocore into Mondadori (Marco audit
    # 2026-05-18 — they are SEPARATE publishers).
    #
    # Anti-pattern check (W-04): mapping is applied BEFORE groupby. The companion
    # test scripts/test_publishers_top_mapping_applied.py asserts at SOURCE LEVEL
    # that the call site of the mapping loader precedes the offset of the first
    # df_year groupby on publisher_id — a future edit that reorders these will
    # fail in CI before deploy.
    df_year = df_year.copy()
    mapping = _load_ad_unit_mapping()
    if mapping is not None:
        df_year["publisher_id"] = (
            df_year["publisher_id"].map(mapping).fillna(df_year["publisher_id"])
        )
    else:
        logger.warning(
            "ad_unit mapping unavailable — falling back to raw publisher_id. "
            "Top Publishers may surface AdGage_* / _npa names. See MAP-01."
        )

    # MAP-04 — Filter out OLD (147 legacy ad_units) and test (13 internal test
    # ad_units) clusters. Set defined once at the top of the publisher_id rewrite
    # block so the channel df below can reuse it without redefining.
    EXCLUDED_PUBLISHER_CLUSTERS = {"OLD", "test"}
    df_year = df_year[~df_year["publisher_id"].isin(EXCLUDED_PUBLISHER_CLUSTERS)]
    if df_year.empty:
        return {
            "publishers": [],
            "year": year,
            "total_publishers": 0,
            "sell_type_filter": sell_type,
        }

    total_all_revenue = df_year["revenue"].sum()

    agg_dict = {
        "total_revenue": ("revenue", "sum"),
        "total_impressions": ("impressions", "sum"),
        "avg_coverage": ("coverage", "mean"),
    }
    # v1.2 columns
    if "clicks" in df_year.columns:
        agg_dict["total_clicks"] = ("clicks", "sum")
    if "viewable_impressions" in df_year.columns:
        agg_dict["total_viewable"] = ("viewable_impressions", "sum")
    if "revenue_gross" in df_year.columns:
        agg_dict["total_revenue_gross"] = ("revenue_gross", "sum")

    pub = df_year.groupby("publisher_id").agg(**agg_dict).reset_index()

    # Bacino (ad_requests) is duplicated across channels in the parquet join.
    # First aggregate to unique (publisher, date, env, geo) to remove channel duplication,
    # then sum across all dates for each publisher.
    n_channels = df_year.groupby(["publisher_id", "date", "environment", "geo_cluster"])["channel_group"].nunique()
    bacino_per_cell = df_year.groupby(["publisher_id", "date", "environment", "geo_cluster"])["bacino"].sum()
    # Divide by channel count to undo the join duplication
    bacino_corrected = (bacino_per_cell / n_channels).groupby("publisher_id").sum()
    pub["total_bacino"] = pub["publisher_id"].map(bacino_corrected).fillna(0)

    # Coverage = Fill Rate (same metric with corrected bacino)
    pub["avg_coverage"] = (pub["total_impressions"] / pub["total_bacino"]).where(pub["total_bacino"] > 0, 0.0)
    pub["fill_rate"] = pub["avg_coverage"]  # identical after bacino correction

    # Compute dominant geo (country) for each publisher
    geo_by_pub = df_year.groupby(["publisher_id", "geo_cluster"])["revenue"].sum().reset_index()
    dominant_geo = geo_by_pub.loc[geo_by_pub.groupby("publisher_id")["revenue"].idxmax()]
    geo_map = dict(zip(dominant_geo["publisher_id"], dominant_geo["geo_cluster"]))

    # Map geo_cluster to country label
    GEO_LABEL = {"ITA": "Italy", "ES": "Spain", "LATAM": "LATAM", "PT": "Portugal", "OTHER": "Other"}

    pub["ecpm"] = (pub["total_revenue"] / pub["total_impressions"]).fillna(0) * 1000
    pub["avg_marginality"] = (pub["total_revenue"] / pub["total_bacino"]).where(pub["total_bacino"] > 0, 0.0) * 1000
    pub["revenue_share_pct"] = (pub["total_revenue"] / total_all_revenue * 100) if total_all_revenue > 0 else 0

    pub = pub.sort_values("total_revenue", ascending=False).head(limit)

    # Google % from channel data
    df_ch = _load_channel()
    google_pct_map: dict[str, float] = {}
    if df_ch is not None:
        df_ch_year = df_ch[df_ch["date"].dt.year == year]
        if not df_ch_year.empty:
            df_ch_year = df_ch_year.copy()
            # Phase 17.1 MAP-03 — same mapping applied to channel df.
            if mapping is not None:
                df_ch_year["publisher_id"] = (
                    df_ch_year["publisher_id"].map(mapping).fillna(df_ch_year["publisher_id"])
                )
            # MAP-04 — same OLD/test exclusion as df_year above (set reused).
            df_ch_year = df_ch_year[~df_ch_year["publisher_id"].isin(EXCLUDED_PUBLISHER_CLUSTERS)]
            ch_total = df_ch_year.groupby("publisher_id")["revenue"].sum()
            ch_google = df_ch_year[df_ch_year["channel_group"].isin(["GOOGLE_ADEX", "GOOGLE"])].groupby("publisher_id")["revenue"].sum()
            for pid in pub["publisher_id"]:
                total = ch_total.get(pid, 0)
                google = ch_google.get(pid, 0)
                google_pct_map[pid] = round(google / total * 100, 1) if total > 0 else 0.0

    # Trend 4w: last 4 weeks revenue vs previous 4 weeks
    trend_map: dict[str, float | None] = {}
    max_date = df_year["date"].max()
    for pid in pub["publisher_id"]:
        df_pub_daily = df_year[df_year["publisher_id"] == pid].groupby("date")["revenue"].sum().sort_index()
        last_4w = df_pub_daily[df_pub_daily.index > max_date - pd.Timedelta(days=28)].sum()
        prev_4w = df_pub_daily[
            (df_pub_daily.index > max_date - pd.Timedelta(days=56))
            & (df_pub_daily.index <= max_date - pd.Timedelta(days=28))
        ].sum()
        if prev_4w > 0:
            trend_map[pid] = round((last_4w / prev_4w - 1) * 100, 1)
        else:
            trend_map[pid] = None

    # v1.2 derived metrics
    if "total_clicks" in pub.columns:
        pub["ctr"] = (pub["total_clicks"] / pub["total_impressions"]).where(pub["total_impressions"] > 0, 0.0)
    else:
        pub["ctr"] = 0.0
    if "total_viewable" in pub.columns:
        pub["viewability_rate"] = (pub["total_viewable"] / pub["total_impressions"]).where(pub["total_impressions"] > 0, 0.0)
    else:
        pub["viewability_rate"] = 0.0
    pub["rpm"] = (pub["total_revenue"] / pub["total_bacino"]).where(pub["total_bacino"] > 0, 0.0) * 1000
    if "total_revenue_gross" in pub.columns:
        pub["gross_margin_pct"] = ((1 - pub["total_revenue"] / pub["total_revenue_gross"]).where(pub["total_revenue_gross"] > 0, 0.0) * 100)
    else:
        pub["gross_margin_pct"] = 0.0

    publishers = []
    for _, row in pub.iterrows():
        pid = row["publisher_id"]
        dominant = geo_map.get(pid, "OTHER")
        entry = {
            "publisher_id": pid,
            "country": GEO_LABEL.get(dominant, "Other"),
            "dominant_geo": dominant,
            "total_revenue": round(float(row["total_revenue"]), 2),
            "revenue_share_pct": round(float(row["revenue_share_pct"]), 2),
            "ecpm": round(float(row["ecpm"]), 2),
            "rpm": round(float(row["rpm"]), 2),
            "ctr": round(float(row["ctr"]), 4),
            "viewability": round(float(row["viewability_rate"]), 4),
            "gross_margin_pct": round(float(row["gross_margin_pct"]), 2),
            "total_impressions": int(row["total_impressions"]),
            "total_bacino": int(row["total_bacino"]),
            "avg_coverage": round(float(row["avg_coverage"]), 4),
            "avg_marginality": round(float(row["avg_marginality"]), 2),
            "fill_rate": round(float(row["fill_rate"]), 4),
            "google_pct": google_pct_map.get(pid, 0.0),
            "trend_4w": trend_map.get(pid),
        }
        publishers.append(entry)

    return {
        "publishers": publishers,
        "year": year,
        "total_publishers": len(publishers),
        "sell_type_filter": sell_type,  # Phase 11 API-02 — None when no filter applied (transparency for UI).
    }


def _aggregate_weekly(df_filtered: pd.DataFrame, target_year: int) -> dict[int, dict]:
    """Aggregate a publisher's filtered DataFrame into weekly KPIs keyed by ISO week."""
    df_w = df_filtered.copy()
    iso_cal = df_w["date"].dt.isocalendar()
    df_w["iso_week"] = iso_cal.week.astype(int)
    df_w["iso_year"] = iso_cal.year.astype(int)
    df_w = df_w[df_w["iso_year"] == target_year]

    if df_w.empty:
        return {}

    agg_dict: dict[str, tuple] = {
        "revenue": ("revenue", "sum"),
        "impressions": ("impressions", "sum"),
        "bacino": ("bacino", "sum"),
        "week_start": ("date", "min"),
    }
    # Phase 17 — surface RPM/CTR/Viewability/Gross-Margin in weekly KPI table.
    # v1.2 schema fields (clicks, viewable_impressions, revenue_gross) may be
    # absent in older parquet snapshots — guard each aggregation independently.
    if "clicks" in df_w.columns:
        agg_dict["clicks"] = ("clicks", "sum")
    if "viewable_impressions" in df_w.columns:
        agg_dict["viewable"] = ("viewable_impressions", "sum")
    if "revenue_gross" in df_w.columns:
        agg_dict["revenue_gross"] = ("revenue_gross", "sum")

    weekly = df_w.groupby("iso_week").agg(**agg_dict).reset_index()

    result: dict[int, dict] = {}
    for _, row in weekly.iterrows():
        impressions = int(row["impressions"])
        bacino = int(row["bacino"])
        revenue = float(row["revenue"])
        coverage = impressions / bacino if bacino > 0 else 0.0
        ecpm = (revenue / impressions * 1000) if impressions > 0 else 0.0
        rpm = (revenue / bacino * 1000) if bacino > 0 else 0.0
        clicks = int(row["clicks"]) if "clicks" in row else 0
        viewable = int(row["viewable"]) if "viewable" in row else 0
        ctr = (clicks / impressions) if impressions > 0 else 0.0
        viewability = (viewable / impressions) if impressions > 0 else 0.0
        revenue_gross = float(row["revenue_gross"]) if "revenue_gross" in row else 0.0
        gross_margin_pct = ((1 - revenue / revenue_gross) * 100) if revenue_gross > 0 else 0.0
        min_date = pd.Timestamp(row["week_start"])
        week_monday = min_date - pd.Timedelta(days=min_date.weekday())
        week_sunday = week_monday + pd.Timedelta(days=6)
        week_num = int(row["iso_week"])
        result[week_num] = {
            "revenue": round(revenue, 2),
            "impressions": impressions,
            "bacino": bacino,
            "coverage": round(coverage, 4),
            "ecpm": round(ecpm, 2),
            "rpm": round(rpm, 2),
            "ctr": round(ctr, 4),
            "viewability": round(viewability, 4),
            "gross_margin_pct": round(gross_margin_pct, 2),
            "week_start": week_monday.strftime("%Y-%m-%d"),
            "week_end": week_sunday.strftime("%Y-%m-%d"),
        }
    return result


def _safe_delta_pct(current: float, prev: float) -> Optional[float]:
    if prev == 0:
        return None
    return round((current - prev) / prev * 100, 1)


@router.get("/{publisher_id}/weekly-kpis")
@limiter.limit("60/minute")
def get_publisher_weekly_kpis(
    request: Request,
    publisher_id: str,
    year: int = Query(2025),
    compare_prev_year: bool = Query(False),
):
    df = _load_adrequests()
    if df is None:
        raise HTTPException(status_code=503, detail="Ad requests data not available")

    # Phase 17.1 MAP-08 — accept clean publisher name (e.g. "Vocento",
    # "Mondadori"); reverse-map to ALL underlying raw ad_unit_names via
    # Marco's mapping (Plan 01 MAP-02 loader). isin() over the set picks
    # up Mondadori + Mondadori_npa, AdGage_Vocento → Vocento, etc.
    ad_unit_names = _resolve_publisher_ad_units(publisher_id)
    df_pub = df[(df["publisher_id"].isin(ad_unit_names)) & (df["date"].dt.year == year)]
    if df_pub.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for publisher '{publisher_id}' in {year}",
        )

    # Determine if YoY comparison is applicable
    is_top = publisher_id in get_config().top_publishers
    do_yoy = compare_prev_year and is_top

    # Aggregate current year
    current_weekly = _aggregate_weekly(df_pub, year)

    # Aggregate previous year if requested
    prev_weekly: dict[int, dict] = {}
    if do_yoy:
        df_prev = df[(df["publisher_id"] == publisher_id) & (df["date"].dt.year == (year - 1))]
        if not df_prev.empty:
            prev_weekly = _aggregate_weekly(df_prev, year - 1)

    seasonal = _load_seasonal_analysis()
    week_lookup = seasonal["_week_lookup"] if seasonal else {}

    weekly_kpis = []
    for week_num in sorted(current_weekly.keys()):
        cur = current_weekly[week_num]
        period_info = week_lookup.get(week_num)

        entry: dict = {
            "week": week_num,
            "week_start": cur["week_start"],
            "week_end": cur["week_end"],
            "revenue": cur["revenue"],
            "impressions": cur["impressions"],
            "bacino": cur["bacino"],
            "coverage": cur["coverage"],
            "ecpm": cur["ecpm"],
            "rpm": cur.get("rpm", 0.0),
            "ctr": cur.get("ctr", 0.0),
            "viewability": cur.get("viewability", 0.0),
            "gross_margin_pct": cur.get("gross_margin_pct", 0.0),
            "seasonal_period": period_info["label"] if period_info else None,
        }

        if prev_weekly and week_num in prev_weekly:
            prev = prev_weekly[week_num]
            entry["prev_revenue"] = prev["revenue"]
            entry["prev_impressions"] = prev["impressions"]
            entry["prev_bacino"] = prev["bacino"]
            entry["prev_coverage"] = prev["coverage"]
            entry["prev_ecpm"] = prev["ecpm"]
            entry["delta_revenue_pct"] = _safe_delta_pct(cur["revenue"], prev["revenue"])
            entry["delta_ecpm_pct"] = _safe_delta_pct(cur["ecpm"], prev["ecpm"])
            entry["delta_bacino_pct"] = _safe_delta_pct(cur["bacino"], prev["bacino"])
            entry["delta_coverage_pct"] = _safe_delta_pct(cur["coverage"], prev["coverage"])

        weekly_kpis.append(entry)

    # Geo breakdown for the year
    df_pub_full = df_pub.copy()
    iso_cal = df_pub_full["date"].dt.isocalendar()
    df_pub_full["iso_year"] = iso_cal.year.astype(int)
    df_pub_full = df_pub_full[df_pub_full["iso_year"] == year]

    geo = df_pub_full.groupby("geo_cluster").agg(geo_revenue=("revenue", "sum")).reset_index()
    total_geo_revenue = geo["geo_revenue"].sum()
    geo_breakdown = []
    for _, row in geo.iterrows():
        share = (float(row["geo_revenue"]) / total_geo_revenue * 100) if total_geo_revenue > 0 else 0.0
        geo_breakdown.append({
            "geo_cluster": row["geo_cluster"],
            "revenue": round(float(row["geo_revenue"]), 2),
            "share_pct": round(share, 1),
        })
    geo_breakdown.sort(key=lambda x: x["revenue"], reverse=True)

    # Environment breakdown for the year
    env = df_pub_full.groupby("environment").agg(env_revenue=("revenue", "sum")).reset_index()
    total_env_revenue = env["env_revenue"].sum()
    env_breakdown = []
    for _, row in env.iterrows():
        share = (float(row["env_revenue"]) / total_env_revenue * 100) if total_env_revenue > 0 else 0.0
        env_breakdown.append({
            "environment": row["environment"],
            "revenue": round(float(row["env_revenue"]), 2),
            "share_pct": round(share, 1),
        })
    env_breakdown.sort(key=lambda x: x["revenue"], reverse=True)

    # Check if publisher has recurring patterns data
    recurring_data = _load_recurring_patterns()
    _pub_patterns = (
        recurring_data.get("publishers", {}).get(publisher_id, {})
        if recurring_data else {}
    )
    has_recurring = (
        len(_pub_patterns.get("ecpm_patterns", _pub_patterns.get("patterns", []))) > 0
        or len(_pub_patterns.get("hidden_patterns", [])) > 0
        or len(_pub_patterns.get("danger_zones", [])) > 0
    )

    result: dict = {
        "publisher_id": publisher_id,
        "year": year,
        "has_recurring_patterns": has_recurring,
        "weekly_kpis": weekly_kpis,
        "geo_breakdown": geo_breakdown,
        "environment_breakdown": env_breakdown,
    }

    # YoY summary
    if prev_weekly:
        total_cur_rev = sum(current_weekly[w]["revenue"] for w in current_weekly)
        total_prev_rev = sum(prev_weekly[w]["revenue"] for w in prev_weekly)
        total_cur_imp = sum(current_weekly[w]["impressions"] for w in current_weekly)
        total_prev_imp = sum(prev_weekly[w]["impressions"] for w in prev_weekly)
        cur_ecpm = (total_cur_rev / total_cur_imp * 1000) if total_cur_imp > 0 else 0.0
        prev_ecpm = (total_prev_rev / total_prev_imp * 1000) if total_prev_imp > 0 else 0.0

        result["yoy_summary"] = {
            "prev_year": year - 1,
            "total_revenue_delta_pct": _safe_delta_pct(total_cur_rev, total_prev_rev),
            "ecpm_delta_pct": _safe_delta_pct(cur_ecpm, prev_ecpm),
            "weeks_with_data": len(prev_weekly),
        }

    return result


def _enrich_hidden_pattern(hp: dict) -> None:
    """Generate rich Italian business_impact and compute reliability score for a hidden pattern."""
    metric = hp.get("metric", "revenue")
    signal = hp.get("signal", "DOWN")
    label = hp.get("label", "periodo")
    d2024 = hp.get("avg_delta_pct_2024", 0) or 0
    d2025 = hp.get("avg_delta_pct_2025", 0) or 0
    ecpm_status = hp.get("ecpm_during_period", "FLAT")
    impact = hp.get("weekly_revenue_impact_eur")
    n_weeks = len(hp.get("weeks", []))
    weeks_str = f" ({n_weeks} settimane)" if n_weeks > 1 else ""

    metric_it = "revenue" if metric == "revenue" else "impressions" if metric == "impressions" else "revenue e impressions"
    direction = "cala" if signal == "DOWN" else "cresce"

    # Rich Italian description
    parts = [
        f"Durante {label}{weeks_str} la {metric_it} {direction} in modo ricorrente: "
        f"{d2024:+.1f}% nel 2024, {d2025:+.1f}% nel 2025."
    ]
    if ecpm_status == "FLAT":
        parts.append(
            "L'eCPM rimane stabile nel periodo, rendendo questo pattern completamente invisibile "
            "al monitoraggio basato solo sull'eCPM."
        )
    elif ecpm_status == "UP" and signal == "DOWN":
        parts.append(
            "L'eCPM sale nel periodo, mascherando il calo di volume — "
            "il prezzo unitario compensa ma il volume perso riduce la revenue totale."
        )
    elif ecpm_status == "UP" and signal == "UP":
        parts.append(
            "L'eCPM sale nel periodo insieme ai volumi — "
            "il segnale positivo è visibile anche nell'eCPM, ma la crescita dei volumi aggiunge un effetto ulteriore."
        )
    elif ecpm_status == "DOWN" and signal == "DOWN":
        parts.append(
            "L'eCPM scende nel periodo, amplificando l'effetto negativo. "
            "Sia il volume che il prezzo unitario calano — situazione da monitorare attentamente."
        )
    elif ecpm_status == "DOWN" and signal == "UP":
        parts.append(
            "L'eCPM scende nonostante l'aumento dei volumi — "
            "l'eccesso di inventory diluisce il prezzo medio, ma la revenue beneficia comunque della crescita dei volumi."
        )
    if impact is not None:
        parts.append(
            f"Impatto stimato: ~{abs(impact):,.0f}€/settimana {'persi' if impact < 0 else 'guadagnati'}."
        )
    hp["business_impact"] = " ".join(parts)

    # Reliability score:
    # - Cross-year consistency (0.40): same direction in both years = reliable
    # - Magnitude similarity (0.30): similar delta across years
    # - Sample size (0.15): more weeks = more data
    # - eCPM masking (0.15): if eCPM is FLAT, the hidden signal is more genuine
    score = 0.0
    same_dir = (d2024 < 0 and d2025 < 0) or (d2024 > 0 and d2025 > 0)
    if same_dir:
        score += 0.40
    elif (d2024 == 0 or d2025 == 0):
        score += 0.15  # one year neutral

    # Magnitude similarity
    diff = abs(d2024 - d2025)
    max_abs = max(abs(d2024), abs(d2025), 1)
    score += 0.30 * (1 - min(diff / max_abs, 1))

    # Sample size
    if n_weeks >= 4:
        score += 0.15
    elif n_weeks >= 2:
        score += 0.15 * (n_weeks / 4)
    else:
        score += 0.05

    # eCPM masking bonus — truly hidden patterns are more valuable
    if ecpm_status == "FLAT":
        score += 0.15
    elif ecpm_status == "UP" and signal == "DOWN":
        score += 0.10  # masked by rising eCPM
    else:
        score += 0.05

    hp["reliability_score"] = round(score, 2)


def _enrich_danger_zone(dz: dict) -> None:
    """Generate rich Italian explanation and compute reliability score for a danger zone."""
    label = dz.get("label", "periodo")
    ecpm_d = dz.get("ecpm_delta_pct", 0) or 0
    cov_d = dz.get("coverage_delta_pct", 0) or 0
    bacino_d = dz.get("bacino_delta_pct")
    severity = dz.get("severity", "MEDIUM")
    n_weeks = len(dz.get("weeks", []))
    weeks_str = f" ({n_weeks} settimane)" if n_weeks > 1 else ""
    week_range = dz.get("week_range_label", "")

    parts = [
        f"Durante {label}{weeks_str} sia l'eCPM ({ecpm_d:+.1f}%) che la coverage ({cov_d:+.1f}%) "
        f"calano contemporaneamente."
    ]
    if bacino_d is not None:
        if bacino_d < -5:
            parts.append(
                f"Anche il bacino si contrae ({bacino_d:+.1f}%), indicando un calo generalizzato "
                f"dell'inventory e della monetizzazione."
            )
        elif bacino_d > 5:
            parts.append(
                f"Il bacino cresce ({bacino_d:+.1f}%) ma la coverage e l'eCPM calano — "
                f"la domanda pubblicitaria non riesce ad assorbire l'offerta aggiuntiva."
            )
    if severity == "HIGH":
        parts.append(
            "Rischio elevato: il calo congiunto è significativo e indica una debolezza strutturale della domanda. "
            "Azione raccomandata: verificare la competitività delle offerte e contattare gli advertiser."
        )
    else:
        parts.append(
            "Rischio moderato: i cali sono contenuti ma la tendenza congiunta merita attenzione. "
            "Monitorare l'evoluzione nelle settimane successive."
        )
    dz["explanation"] = " ".join(parts)

    # Reliability score:
    # - Severity of decline (0.35): larger declines = more clearly a real pattern
    # - Dual-metric confirmation (0.30): eCPM + coverage both down = strong signal
    # - Sample size (0.20): more weeks
    # - Triple-metric (0.15): bacino also declining = extra confirmation
    score = 0.0

    avg_decline = (abs(ecpm_d) + abs(cov_d)) / 2
    if avg_decline >= 15:
        score += 0.35
    elif avg_decline >= 8:
        score += 0.35 * (avg_decline / 15)
    else:
        score += 0.35 * (avg_decline / 15)

    # Dual-metric confirmation (always true for danger zones by definition)
    if ecpm_d < -5 and cov_d < -5:
        score += 0.30
    else:
        score += 0.15

    # Sample size
    if n_weeks >= 4:
        score += 0.20
    elif n_weeks >= 2:
        score += 0.20 * (n_weeks / 4)
    else:
        score += 0.05

    # Triple-metric confirmation
    if bacino_d is not None and bacino_d < -5:
        score += 0.15
    elif bacino_d is not None and bacino_d > 5:
        score += 0.05  # bacino up but coverage down = interesting but less confirmation
    else:
        score += 0.08

    dz["reliability_score"] = round(min(score, 1.0), 2)


@router.get("/{publisher_id}/recurring-patterns")
@limiter.limit("60/minute")
def get_publisher_recurring_patterns(request: Request, publisher_id: str):
    """Return enriched recurring patterns (eCPM + hidden + danger zones) for a publisher."""
    empty_response = {
        "publisher_id": publisher_id,
        "ecpm_patterns": [],
        "hidden_patterns": [],
        "danger_zones": [],
        "yearly_avg": None,
    }

    recurring_data = _load_recurring_patterns()
    if recurring_data is None:
        return empty_response

    pub_data = recurring_data.get("publishers", {}).get(publisher_id)
    # Phase 17.1 MAP-08 — JSON snapshot may be keyed by raw ad_unit_names
    # (pre-mapping) while the URL contract now uses clean publisher names.
    # Fall back through the reverse-mapped set to find a matching key.
    if pub_data is None:
        ad_unit_names = _resolve_publisher_ad_units(publisher_id)
        for raw_name in ad_unit_names:
            candidate = recurring_data.get("publishers", {}).get(raw_name)
            if candidate is not None:
                pub_data = candidate
                break
    if pub_data is None:
        return empty_response

    # Support both enriched ("ecpm_patterns") and legacy ("patterns") keys
    ecpm_patterns = pub_data.get("ecpm_patterns", pub_data.get("patterns", []))

    # Enrich hidden patterns with Italian descriptions and reliability score
    hidden_patterns = []
    for hp in pub_data.get("hidden_patterns", []):
        hp = dict(hp)  # copy to avoid mutating cache
        _enrich_hidden_pattern(hp)
        hidden_patterns.append(hp)

    # Enrich danger zones with Italian descriptions and reliability score
    danger_zones = []
    for dz in pub_data.get("danger_zones", []):
        dz = dict(dz)
        _enrich_danger_zone(dz)
        danger_zones.append(dz)

    return {
        "publisher_id": publisher_id,
        "ecpm_patterns": ecpm_patterns,
        "hidden_patterns": hidden_patterns,
        "danger_zones": danger_zones,
        "yearly_avg": pub_data.get("yearly_avg"),
    }


@router.get("/{publisher_id}/ecpm-analysis")
@limiter.limit("60/minute")
def get_publisher_ecpm_analysis(
    request: Request,
    publisher_id: str,
    year: int = Query(2025),
):
    df = _load_adrequests()
    if df is None:
        raise HTTPException(status_code=503, detail="Ad requests data not available")

    seasonal = _load_seasonal_analysis()
    if seasonal is None:
        raise HTTPException(status_code=503, detail="Seasonal analysis data not available")

    # Phase 17.1 MAP-08 — accept clean publisher name; reverse-map to all
    # underlying raw ad_unit_names (same helper as weekly-kpis).
    ad_unit_names = _resolve_publisher_ad_units(publisher_id)
    df_pub = df[(df["publisher_id"].isin(ad_unit_names)) & (df["date"].dt.year == year)]
    if df_pub.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for publisher '{publisher_id}' in {year}",
        )

    df_pub = df_pub.copy()
    iso_cal = df_pub["date"].dt.isocalendar()
    df_pub["iso_week"] = iso_cal.week.astype(int)
    df_pub["iso_year"] = iso_cal.year.astype(int)
    df_pub = df_pub[df_pub["iso_year"] == year]

    weekly = df_pub.groupby("iso_week").agg(
        revenue=("revenue", "sum"),
        impressions=("impressions", "sum"),
        week_start=("date", "min"),
    ).reset_index()

    # Yearly average eCPM as baseline
    total_revenue = float(weekly["revenue"].sum())
    total_impressions = int(weekly["impressions"].sum())
    yearly_avg_ecpm = (total_revenue / total_impressions * 1000) if total_impressions > 0 else 0.0

    week_lookup = seasonal["_week_lookup"]

    # Build weekly detail
    weekly_detail = []
    for _, row in weekly.iterrows():
        imp = int(row["impressions"])
        rev = float(row["revenue"])
        # Skip weeks with zero data (no impressions AND no revenue)
        if imp == 0 and rev == 0.0:
            continue
        ecpm = (rev / imp * 1000) if imp > 0 else 0.0
        delta_pct = ((ecpm - yearly_avg_ecpm) / yearly_avg_ecpm * 100) if yearly_avg_ecpm > 0 else 0.0

        min_date = pd.Timestamp(row["week_start"])
        week_monday = min_date - pd.Timedelta(days=min_date.weekday())
        week_sunday = week_monday + pd.Timedelta(days=6)

        week_num = int(row["iso_week"])
        period_info = week_lookup.get(week_num)

        # Signal from seasonal JSON is global; override with publisher-specific delta
        rounded_delta = round(delta_pct, 1)
        if rounded_delta > 2.0:
            effective_signal = "RAISE"
        elif rounded_delta < -2.0:
            effective_signal = "LOWER"
        else:
            effective_signal = "NEUTRAL"

        weekly_detail.append({
            "week": week_num,
            "week_start": week_monday.strftime("%Y-%m-%d"),
            "week_end": week_sunday.strftime("%Y-%m-%d"),
            "ecpm": round(ecpm, 2),
            "delta_pct": rounded_delta,
            "signal": effective_signal,
            "period": period_info["label"] if period_info else None,
        })

    weekly_detail.sort(key=lambda x: x["week"])

    # Group consecutive weeks with the same period into optimization windows
    optimization_windows = []
    current_window = None

    for w in weekly_detail:
        period_id = None
        wn = w["week"]
        if wn in week_lookup:
            period_id = week_lookup[wn]["period_id"]

        if current_window and period_id and current_window["_period_id"] == period_id:
            # Extend current window
            current_window["weeks"].append(wn)
            current_window["week_end"] = w["week_end"]
            current_window["_ecpms"].append(w["ecpm"])
            current_window["_deltas"].append(w["delta_pct"])
        else:
            # Finish previous window
            if current_window:
                _finalize_window(current_window)
                optimization_windows.append(current_window)
            # Start new window
            current_window = {
                "_period_id": period_id,
                "period_id": period_id or "unclassified",
                "period_label": w["period"] or "Non classificato",
                "signal": w["signal"],
                "weeks": [wn],
                "week_start": w["week_start"],
                "week_end": w["week_end"],
                "_ecpms": [w["ecpm"]],
                "_deltas": [w["delta_pct"]],
            }

    if current_window:
        _finalize_window(current_window)
        optimization_windows.append(current_window)

    # Enrich windows with driver labels from pre-computed enriched data
    enriched_data = _load_opt_windows_enriched()
    if enriched_data:
        pub_enriched = enriched_data.get("publishers", {}).get(publisher_id, {})
        enriched_windows = pub_enriched.get("windows", [])
        # Build lookups by period_id and period_label for flexible matching
        by_period_id: dict[str, dict] = {}
        by_period_label: dict[str, dict] = {}
        for ew in enriched_windows:
            ew_year = ew.get("year")
            if ew_year is not None and ew_year != year:
                continue
            pid = ew.get("period_id")
            plabel = ew.get("period_label")
            if pid:
                by_period_id[pid] = ew
            if plabel:
                by_period_label[plabel] = ew

        # Also build lookups for previous year to show driver stability
        by_period_id_prev: dict[str, dict] = {}
        by_period_label_prev: dict[str, dict] = {}
        for ew in pub_enriched.get("windows", []):
            ew_year = ew.get("year")
            if ew_year is not None and ew_year != year - 1:
                continue
            pid = ew.get("period_id")
            plabel = ew.get("period_label")
            if pid:
                by_period_id_prev[pid] = ew
            if plabel:
                by_period_label_prev[plabel] = ew

        enrichment_fields = [
            "driver", "bacino_delta_pct", "coverage_delta_pct",
            "impressions_delta_pct", "revenue_delta_pct", "driver_explanation",
        ]
        for window in optimization_windows:
            match = by_period_id.get(window.get("period_id")) or by_period_label.get(window.get("period_label"))
            if match:
                for field in enrichment_fields:
                    if field in match:
                        window[field] = match[field]
                # Override rationale with rich Italian driver-specific text
                driver = match.get("driver")
                delta = match.get("ecpm_delta_pct", window.get("delta_pct", 0))
                bacino_d = match.get("bacino_delta_pct", 0) or 0
                cov_d = match.get("coverage_delta_pct", 0) or 0
                imp_d = match.get("impressions_delta_pct", 0) or 0
                rev_d = match.get("revenue_delta_pct", 0) or 0
                plabel = window.get("period_label", "questo periodo")
                if driver == "DEMAND_DRIVEN":
                    window["rationale"] = (
                        f"Durante {plabel} l'eCPM registra un aumento del {delta:+.1f}% rispetto alla media annua, "
                        f"sostenuto da una domanda pubblicitaria genuina. Il bacino ({bacino_d:+.1f}%) e la coverage ({cov_d:+.1f}%) "
                        f"restano stabili, confermando che il rialzo non è un artefatto dell'inventory. "
                        f"Revenue {rev_d:+.1f}%. Opportunità concreta per ottimizzare i floor price."
                    )
                elif driver == "SUPPLY_SQUEEZE":
                    window["rationale"] = (
                        f"Durante {plabel} l'eCPM sale del {delta:+.1f}%, ma il driver principale è la contrazione dell'inventory "
                        f"(bacino {bacino_d:+.1f}%). Con meno offerta disponibile, il prezzo unitario aumenta artificialmente "
                        f"anche senza vera domanda aggiuntiva. Revenue {rev_d:+.1f}%, impressions {imp_d:+.1f}%. "
                        f"Segnale potenzialmente fuorviante — NON alzare i floor price."
                    )
                elif driver == "FILL_EFFECT":
                    window["rationale"] = (
                        f"Durante {plabel} l'eCPM sale del {delta:+.1f}%, ma la causa è il calo della coverage ({cov_d:+.1f}%): "
                        f"vengono servite solo le impressions a maggior valore (premium), gonfiando la media eCPM. "
                        f"Impressions {imp_d:+.1f}%, revenue {rev_d:+.1f}%. "
                        f"Verificare perché la coverage cala — il segnale di rialzo non indica vera domanda."
                    )
                elif driver == "VOLUME_DRIVEN":
                    window["rationale"] = (
                        f"Durante {plabel} l'eCPM scende del {delta:+.1f}% per effetto dell'aumento del volume di impressions ({imp_d:+.1f}%). "
                        f"Più inventory servito diluisce il prezzo medio unitario, ma la revenue totale ({rev_d:+.1f}%) "
                        f"potrebbe comunque crescere. Verificare il bilancio complessivo prima di intervenire sui floor."
                    )
                elif driver == "SEASONAL_DEMAND":
                    window["rationale"] = (
                        f"Durante {plabel} l'eCPM scende del {delta:+.1f}% per un eccesso di offerta rispetto alla domanda: "
                        f"il bacino cresce ({bacino_d:+.1f}%) mentre la coverage cala ({cov_d:+.1f}%), tipico effetto stagionale. "
                        f"Revenue {rev_d:+.1f}%. Considerare la riduzione dei floor price per proteggere il fill rate."
                    )
                elif driver == "MIXED":
                    parts = []
                    if abs(bacino_d) > 2:
                        parts.append(f"bacino {bacino_d:+.1f}%")
                    if abs(cov_d) > 2:
                        parts.append(f"coverage {cov_d:+.1f}%")
                    if abs(imp_d) > 2:
                        parts.append(f"impressions {imp_d:+.1f}%")
                    if abs(rev_d) > 2:
                        parts.append(f"revenue {rev_d:+.1f}%")
                    metrics_str = ", ".join(parts) if parts else "tutte le metriche in movimento"
                    window["rationale"] = (
                        f"Durante {plabel} l'eCPM varia del {delta:+.1f}% senza un driver dominante chiaro. "
                        f"Metriche coinvolte: {metrics_str}. "
                        f"Nessuna singola causa spiega l'andamento — necessaria analisi manuale per decidere se intervenire sui floor."
                    )
            # Add previous year driver for stability comparison
            prev_match = by_period_id_prev.get(window.get("period_id")) or by_period_label_prev.get(window.get("period_label"))
            if prev_match and prev_match.get("driver"):
                window["prev_year_driver"] = prev_match["driver"]

            # Compute consistency_score as RELIABILITY metric:
            # How trustworthy/precise is this pattern?
            # 1. Internal coherence (0.35): low variance of weekly deltas within window = precise
            # 2. Cross-year recurrence (0.30): same signal in prev year = structural pattern
            # 3. Magnitude similarity (0.20): similar delta across years = stable
            # 4. Sample size (0.15): more weeks = more data = more reliable
            score = 0.0

            # 1. Internal coherence — computed from weekly deltas stored during _finalize_window
            week_deltas = [wd["delta_pct"] for wd in weekly_detail if wd["week"] in window.get("weeks", [])]
            if len(week_deltas) >= 2:
                mean_d = sum(week_deltas) / len(week_deltas)
                variance = sum((d - mean_d) ** 2 for d in week_deltas) / len(week_deltas)
                std = variance ** 0.5
                cv = std / max(abs(mean_d), 1)  # coefficient of variation
                score += 0.35 * max(0, 1 - cv)
            elif len(week_deltas) == 1:
                score += 0.35 * 0.5  # single week: partial credit

            # 2. Cross-year recurrence
            if prev_match:
                cur_signal = window.get("signal", "")
                prev_signal = prev_match.get("signal", "")
                if cur_signal == prev_signal:
                    score += 0.30  # same signal = strong structural recurrence
                else:
                    score += 0.10  # exists but different signal = weak recurrence

            # 3. Magnitude similarity across years
            if prev_match:
                cur_delta = window.get("delta_pct", 0)
                prev_delta = prev_match.get("ecpm_delta_pct", prev_match.get("delta_pct", 0)) or 0
                diff = abs(cur_delta - prev_delta)
                max_abs = max(abs(cur_delta), abs(prev_delta), 1)
                score += 0.20 * (1 - min(diff / max_abs, 1))

            # 4. Sample size
            n_weeks = len(window.get("weeks", []))
            if n_weeks >= 4:
                score += 0.15
            elif n_weeks >= 2:
                score += 0.15 * (n_weeks / 4)
            else:
                score += 0.15 * 0.3  # single week: minimal credit

            window["consistency_score"] = round(score, 2) if score > 0 else None

    return {
        "publisher_id": publisher_id,
        "year": year,
        "yearly_avg_ecpm": round(yearly_avg_ecpm, 2),
        "optimization_windows": optimization_windows,
        "weekly_ecpm_detail": weekly_detail,
    }


def _finalize_window(window: dict) -> None:
    """Compute summary stats for an optimization window and remove internal keys."""
    ecpms = window.pop("_ecpms")
    deltas = window.pop("_deltas")
    window.pop("_period_id")
    avg_ecpm = round(sum(ecpms) / len(ecpms), 2) if ecpms else 0.0
    delta_pct = round(sum(deltas) / len(deltas), 1) if deltas else 0.0
    window["avg_ecpm"] = avg_ecpm
    window["delta_pct"] = delta_pct
    window["date_range"] = f"{window.pop('week_start')} to {window.pop('week_end')}"

    # Override signal to be coherent with publisher-specific delta_pct
    if delta_pct > 2.0:
        window["signal"] = "RAISE"
    elif delta_pct < -2.0:
        window["signal"] = "LOWER"
    else:
        window["signal"] = "NEUTRAL"

    # Generate rationale from signal and delta (Italian) — base version without multi-metric enrichment
    signal = window["signal"]
    label = window["period_label"]
    n_weeks = len(window.get("weeks", []))
    weeks_str = f" ({n_weeks} settimane)" if n_weeks > 1 else ""
    if signal == "RAISE":
        window["rationale"] = (
            f"Durante {label}{weeks_str} l'eCPM supera la media annua del {delta_pct:+.1f}%, "
            f"raggiungendo una media di {avg_ecpm}\u20ac. Possibile aumento della domanda pubblicitaria \u2014 "
            f"valutare l'ottimizzazione dei floor price per massimizzare la revenue."
        )
    elif signal == "LOWER":
        window["rationale"] = (
            f"Durante {label}{weeks_str} l'eCPM \u00e8 sotto la media annua del {abs(delta_pct):.1f}%, "
            f"attestandosi a {avg_ecpm}\u20ac. Domanda pi\u00f9 debole del solito \u2014 "
            f"considerare la riduzione dei floor price per proteggere il fill rate e mantenere il volume."
        )
    else:
        window["rationale"] = (
            f"Durante {label}{weeks_str} l'eCPM si attesta a {avg_ecpm}\u20ac, in linea con la media annua ({delta_pct:+.1f}%). "
            f"Domanda stabile \u2014 mantenere la strategia corrente senza interventi sui floor."
        )
