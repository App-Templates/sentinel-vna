#!/usr/bin/env python3
"""ETL: Convert 6 CSV files into 2 Parquet files with v2 schema (20 fields).

v2 = v1 (18 fields) + measurable_impressions (SCHEMA-03) + sell_type_proxy (SCHEMA-04).

Produces:
  data/baseline/daily_aggregated.parquet
  data/baseline/hourly_aggregated.parquet
"""

import os
import shutil
import yaml
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "sentinel_db")
BASELINE_DIR = os.path.join(BASE_DIR, "data", "baseline")
CONFIG_PATH = os.path.join(BASE_DIR, "config", "revenue_share.yaml")
SELL_TYPE_PROXY_CONFIG = os.path.join(BASE_DIR, "config", "sell_type_proxy.yaml")

# ── Load revenue share config ──────────────────────────────────────────────
def load_revenue_share():
    with open(CONFIG_PATH, "r") as f:
        cfg = yaml.safe_load(f)
    default = cfg.get("default_share", 0.60)
    overrides = cfg.get("publishers", {}) or {}
    return default, overrides


# ── Load sell_type proxy mapping ──────────────────────────────────────────
def load_sell_type_proxy_mapping():
    """Load channel_group → sell_type_proxy mapping from config/sell_type_proxy.yaml.

    Returns a dict mapping each channel_group value to its sell_type_proxy group name.
    Unknown channel_groups (not in the mapping) are mapped to 'Other' by the caller.
    Source of truth: SCHEMA-04 per Phase 08.
    """
    with open(SELL_TYPE_PROXY_CONFIG, "r") as f:
        cfg = yaml.safe_load(f)
    # Invert: {group_name: [channel, ...]} → {channel: group_name}
    inverted = {}
    for group_name, channels in cfg.items():
        if group_name.startswith("_"):
            continue  # skip _meta block
        for channel in channels:
            if channel in inverted:
                raise ValueError(
                    f"Duplicate channel {channel!r} in sell_type_proxy.yaml "
                    f"(already mapped to {inverted[channel]!r}, attempting to remap to {group_name!r})"
                )
            inverted[channel] = group_name
    return inverted


def derive_sell_type_proxy(df, mapping):
    """Add sell_type_proxy column derived from channel_group via mapping.

    Unknown channel_group values (not in mapping) default to 'Other'.
    """
    df["sell_type_proxy"] = df["channel_group"].map(mapping).fillna("Other")
    return df


# ── Load mapping tables ────────────────────────────────────────────────────
def load_mappings():
    pub = pd.read_csv(os.path.join(DATA_DIR, "publisher_mapping.csv"), dtype=str)
    pub_map = dict(zip(pub["ad_unit_id"], pub["ad_unit_name"]))

    country = pd.read_csv(os.path.join(DATA_DIR, "country_mapping.csv"), dtype=str)
    country_map = dict(zip(country["country_criteria"], country["country_name"]))
    return pub_map, country_map


# ── Geo cluster mapping ───────────────────────────────────────────────────
LATAM_COUNTRIES = {
    "Brazil", "Mexico", "Argentina", "Colombia", "Peru", "Chile", "Ecuador",
    "Venezuela", "Uruguay", "Paraguay", "Bolivia", "Guatemala", "Honduras",
    "El Salvador", "Costa Rica", "Panama", "Dominican Republic", "Nicaragua",
    "Cuba", "Puerto Rico",
}

def country_to_geo_cluster(country_name):
    if pd.isna(country_name) or country_name == "":
        return "OTHER"
    if country_name == "Italy":
        return "ITA"
    if country_name == "Spain":
        return "ES"
    if country_name == "Portugal":
        return "PT"
    if country_name in LATAM_COUNTRIES:
        return "LATAM"
    return "OTHER"


# ── Environment normalization ──────────────────────────────────────────────
ENV_MAP = {"web": "WEB", "amp": "AMP", "app": "APP", "webview": "WEB", "": "UNKNOWN"}

def normalize_env(env_series):
    return env_series.fillna("").str.strip().str.lower().map(ENV_MAP).fillna("UNKNOWN")


# ── Find top 50 publishers by total revenue_gross ─────────────────────────
def find_top50_publishers():
    print("Finding top 50 publishers by revenue_gross...")
    chunks = pd.read_csv(
        os.path.join(DATA_DIR, "daily_kpi.csv"),
        usecols=["ad_unit_id_1", "revenue_gross"],
        dtype={"ad_unit_id_1": str},
        chunksize=500_000,
    )
    totals = pd.Series(dtype="float64")
    for chunk in chunks:
        chunk["revenue_gross"] = pd.to_numeric(chunk["revenue_gross"], errors="coerce").fillna(0)
        part = chunk.groupby("ad_unit_id_1")["revenue_gross"].sum()
        totals = totals.add(part, fill_value=0)
    top50 = totals.nlargest(50).index.tolist()
    print(f"  Top 50 publishers selected (total revenue range: {totals.nlargest(50).iloc[0]:.2f} – {totals.nlargest(50).iloc[-1]:.2f})")
    return set(top50)


# ── Apply revenue share ───────────────────────────────────────────────────
def apply_revenue_share(df, pub_map, default_share, overrides):
    """Add revenue (net), ecpm, rpm, gross_margin_pct columns."""
    # Map publisher name for share lookup
    share_rates = df["publisher_id"].map(overrides).fillna(default_share)
    df["revenue"] = df["revenue_gross"] * share_rates
    df["ecpm"] = np.where(df["impressions"] > 0, df["revenue"] / df["impressions"] * 1000, np.nan)
    df["rpm"] = np.where(
        df["bacino"].notna() & (df["bacino"] > 0),
        df["revenue"] / df["bacino"] * 1000,
        np.nan,
    )
    df["gross_margin_pct"] = np.where(
        df["revenue_gross"] > 0,
        (df["revenue_gross"] - df["revenue"]) / df["revenue_gross"] * 100,
        np.nan,
    )
    return df


# ── Compute derived metrics ───────────────────────────────────────────────
def compute_derived(df):
    df["coverage"] = np.where(
        df["bacino"].notna() & (df["bacino"] > 0),
        df["impressions"] / df["bacino"],
        np.nan,
    )
    df["ctr"] = np.where(df["impressions"] > 0, df["clicks"] / df["impressions"], np.nan)
    df["viewability"] = np.where(
        df["impressions"] > 0,
        df["viewable_impressions"] / df["impressions"],
        np.nan,
    )
    df["floor_cpm"] = np.nan
    return df


# ── DAILY pipeline ─────────────────────────────────────────────────────────
def process_daily(top50, pub_map, country_map, default_share, overrides, sell_type_mapping):
    print("\n=== Processing DAILY data ===")

    # Chunked load + filter (WR-01): avoids loading the full 6.2M-row
    # daily_adrequests.csv into memory when only top50 rows survive.
    # R-13 compliance — peak memory = chunksize, not full file.
    print("  Loading daily_adrequests.csv in chunks...")
    ar_chunks = []
    ar_reader = pd.read_csv(
        os.path.join(DATA_DIR, "daily_adrequests.csv"),
        dtype={"ad_unit_id_1": str, "country_criteria_id": str, "environment": str},
        chunksize=500_000,
    )
    for chunk in ar_reader:
        ar_chunks.append(chunk[chunk["ad_unit_id_1"].isin(top50)])
    ar = pd.concat(ar_chunks, ignore_index=True) if ar_chunks else pd.DataFrame()
    ar = ar.drop(columns=["row_id"], errors="ignore")
    ar["ad_requests"] = pd.to_numeric(ar["ad_requests"], errors="coerce")
    print(f"  daily_adrequests after top50 filter: {len(ar):,} rows")

    # Process daily_kpi in chunks
    print("  Loading daily_kpi.csv in chunks...")
    reader = pd.read_csv(
        os.path.join(DATA_DIR, "daily_kpi.csv"),
        dtype={"ad_unit_id_1": str, "country_criteria_id": str, "environment": str, "channel_group": str},
        chunksize=500_000,
    )

    results = []
    for i, chunk in enumerate(reader):
        chunk = chunk[chunk["ad_unit_id_1"].isin(top50)]
        if len(chunk) == 0:
            continue
        chunk = chunk.drop(columns=["row_id"], errors="ignore")

        # Numeric coercion
        for col in ["revenue_gross", "impressions", "measurable_impressions", "viewable_impressions", "clicks"]:
            chunk[col] = pd.to_numeric(chunk[col], errors="coerce").fillna(0)

        # SCHEMA-03 regression guard (WR-02): refuse to emit parquet with a
        # silently zero-filled measurable_impressions. fillna(0) masks upstream
        # column loss (CSV export bug, all-null or all-string column). The
        # Phase 08 SCHEMA-03 contract exists to prevent this exact regression.
        non_zero_frac = (chunk["measurable_impressions"] > 0).mean()
        if non_zero_frac < 0.01:
            raise RuntimeError(
                f"measurable_impressions non-zero fraction {non_zero_frac:.4f} "
                f"in daily chunk {i} — upstream column likely missing or all-null; "
                "refusing to write parquet with zero-filled column (SCHEMA-03)."
            )

        # Join with adrequests
        chunk = chunk.merge(
            ar[["date", "ad_unit_id_1", "environment", "country_criteria_id", "ad_requests"]],
            on=["date", "ad_unit_id_1", "environment", "country_criteria_id"],
            how="left",
        )
        results.append(chunk)
        if (i + 1) % 5 == 0:
            print(f"    Processed {(i+1)*500_000:,} rows...")

    df = pd.concat(results, ignore_index=True)
    print(f"  Merged daily rows: {len(df):,}")

    # Map publisher
    df["publisher_id"] = df["ad_unit_id_1"].map(pub_map).fillna(df["ad_unit_id_1"])

    # Map environment
    df["environment"] = normalize_env(df["environment"])

    # Map geo_cluster
    df["country_name"] = df["country_criteria_id"].map(country_map)
    df["geo_cluster"] = df["country_name"].apply(country_to_geo_cluster)
    df = df.drop(columns=["country_name", "country_criteria_id", "ad_unit_id_1"], errors="ignore")

    # Rename ad_requests → bacino
    df = df.rename(columns={"ad_requests": "bacino"})

    # Drop old computed columns from CSV
    df = df.drop(columns=["ctr", "viewability", "ecpm"], errors="ignore")

    # Revenue share and derived metrics
    df = apply_revenue_share(df, pub_map, default_share, overrides)
    df = compute_derived(df)

    # Add sell_type_proxy derived from channel_group (SCHEMA-04)
    df = derive_sell_type_proxy(df, sell_type_mapping)

    # Final column order (v2: 20 fields)
    final_cols = [
        "date", "publisher_id", "channel_group", "sell_type_proxy", "environment", "geo_cluster",
        "revenue", "revenue_gross", "impressions", "measurable_impressions", "viewable_impressions",
        "bacino", "clicks", "floor_cpm", "coverage", "ecpm", "rpm",
        "ctr", "viewability", "gross_margin_pct",
    ]
    df = df[final_cols]

    return df


# ── HOURLY pipeline ────────────────────────────────────────────────────────
def process_hourly(top50, pub_map, default_share, overrides, sell_type_mapping):
    print("\n=== Processing HOURLY data ===")

    # Load hour_adrequests (491K rows)
    print("  Loading hour_adrequests.csv...")
    ar = pd.read_csv(
        os.path.join(DATA_DIR, "hour_adrequests.csv"),
        dtype={"ad_unit_id_1": str, "environment": str},
    )
    ar = ar[ar["ad_unit_id_1"].isin(top50)]
    ar = ar.drop(columns=["row_id", "impressions", "coverage"], errors="ignore")
    ar["ad_requests"] = pd.to_numeric(ar["ad_requests"], errors="coerce")
    print(f"  hour_adrequests after top50 filter: {len(ar):,} rows")

    # Load hour_kpi (460K rows — fits in memory)
    print("  Loading hour_kpi.csv...")
    df = pd.read_csv(
        os.path.join(DATA_DIR, "hour_kpi.csv"),
        dtype={"ad_unit_id_1": str, "environment": str, "channel_gorup": str},
    )
    df = df[df["ad_unit_id_1"].isin(top50)]
    df = df.drop(columns=["row_id"], errors="ignore")
    print(f"  hour_kpi after top50 filter: {len(df):,} rows")

    # Fix typo: channel_gorup → channel_group
    df = df.rename(columns={"channel_gorup": "channel_group"})

    # Numeric coercion
    for col in ["revenue_gross", "impressions", "measurable_impressions", "viewable_impressions", "clicks"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # SCHEMA-03 regression guard (WR-02): same protection as daily path.
    non_zero_frac_hourly = (df["measurable_impressions"] > 0).mean()
    if non_zero_frac_hourly < 0.01:
        raise RuntimeError(
            f"measurable_impressions non-zero fraction {non_zero_frac_hourly:.4f} "
            "in hour_kpi — upstream column likely missing or all-null; "
            "refusing to write parquet with zero-filled column (SCHEMA-03)."
        )

    # Join with adrequests on (timestamp, ad_unit_id_1, environment)
    df = df.merge(
        ar[["timestamp", "ad_unit_id_1", "environment", "ad_requests"]],
        on=["timestamp", "ad_unit_id_1", "environment"],
        how="left",
    )

    # Map publisher
    df["publisher_id"] = df["ad_unit_id_1"].map(pub_map).fillna(df["ad_unit_id_1"])

    # Environment
    df["environment"] = normalize_env(df["environment"])

    # Hourly has no country → geo_cluster = "ALL"
    df["geo_cluster"] = "ALL"

    df = df.drop(columns=["ad_unit_id_1"], errors="ignore")
    df = df.rename(columns={"ad_requests": "bacino"})

    # Drop old computed columns
    df = df.drop(columns=["ctr", "viewability", "ecpm"], errors="ignore")

    # Revenue share and derived metrics
    df = apply_revenue_share(df, pub_map, default_share, overrides)
    df = compute_derived(df)

    # Add sell_type_proxy derived from channel_group (SCHEMA-04)
    df = derive_sell_type_proxy(df, sell_type_mapping)

    # Final column order (v2: 20 fields)
    final_cols = [
        "timestamp", "publisher_id", "channel_group", "sell_type_proxy", "environment", "geo_cluster",
        "revenue", "revenue_gross", "impressions", "measurable_impressions", "viewable_impressions",
        "bacino", "clicks", "floor_cpm", "coverage", "ecpm", "rpm",
        "ctr", "viewability", "gross_margin_pct",
    ]
    df = df[final_cols]

    return df


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    default_share, overrides = load_revenue_share()
    pub_map, country_map = load_mappings()
    sell_type_mapping = load_sell_type_proxy_mapping()
    top50 = find_top50_publishers()

    # Backup existing parquet files
    v1_dir = os.path.join(BASELINE_DIR, "v1")
    if not os.path.exists(v1_dir):
        os.makedirs(v1_dir, exist_ok=True)
    for fname in os.listdir(BASELINE_DIR):
        if fname.endswith(".parquet"):
            src = os.path.join(BASELINE_DIR, fname)
            dst = os.path.join(v1_dir, fname)
            shutil.copy2(src, dst)
            print(f"Backed up {fname} → v1/{fname}")

    # ── DAILY ──
    daily_df = process_daily(top50, pub_map, country_map, default_share, overrides, sell_type_mapping)
    daily_path = os.path.join(BASELINE_DIR, "daily_aggregated.parquet")
    daily_df.to_parquet(daily_path, engine="pyarrow", index=False)
    print(f"\n  Wrote {daily_path}")
    print(f"  Daily rows: {len(daily_df):,}")

    # ── HOURLY ──
    hourly_df = process_hourly(top50, pub_map, default_share, overrides, sell_type_mapping)
    hourly_path = os.path.join(BASELINE_DIR, "hourly_aggregated.parquet")
    hourly_df.to_parquet(hourly_path, engine="pyarrow", index=False)
    print(f"\n  Wrote {hourly_path}")
    print(f"  Hourly rows: {len(hourly_df):,}")

    # ── Summary ──
    print("\n" + "=" * 60)
    print("ETL SUMMARY")
    print("=" * 60)

    for label, df, time_col in [("DAILY", daily_df, "date"), ("HOURLY", hourly_df, "timestamp")]:
        print(f"\n--- {label} ---")
        print(f"  Rows: {len(df):,}")
        print(f"  Columns: {list(df.columns)}")
        print(f"  Date range: {df[time_col].min()} → {df[time_col].max()}")
        print(f"  Unique publishers: {df['publisher_id'].nunique()}")
        print(f"  Channel groups: {sorted(df['channel_group'].dropna().unique())}")
        print(f"  Environments: {sorted(df['environment'].unique())}")
        print(f"  Geo clusters: {sorted(df['geo_cluster'].unique())}")
        print(f"  Revenue (net) total: {df['revenue'].sum():,.2f}")
        print(f"  Revenue (gross) total: {df['revenue_gross'].sum():,.2f}")
        print(f"  Null counts:")
        for col in df.columns:
            nulls = df[col].isna().sum()
            if nulls > 0:
                print(f"    {col}: {nulls:,}")

    # Verify readability
    print("\n--- Verification: re-read parquet files ---")
    for path in [daily_path, hourly_path]:
        check = pd.read_parquet(path)
        print(f"  {os.path.basename(path)}: {len(check):,} rows, {len(check.columns)} cols, dtypes OK")

    print("\nDONE.")


if __name__ == "__main__":
    main()
