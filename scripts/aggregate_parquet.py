#!/usr/bin/env python3
"""
Aggregate Parquet Data Integration Script
Processes large parquet files (150M+ rows) in chunks and creates aggregated baseline data.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Data paths
HOURLY_PATH = "/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_hourly/data.parquet"
DAILY_CHANNEL_PATH = "/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_daily/data_channel.parquet"
DAILY_ADREQUESTS_PATH = "/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_daily/data_adrequests.parquet"

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "baseline"


def log(msg: str):
    """Log to console and file"""
    print(f"[{datetime.now().isoformat()}] {msg}")
    with open("/tmp/vna-dataintegration.log", "a") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")


def normalize_publisher(name: str) -> str:
    """Normalize publisher names: remove AdGage_ prefix and lowercase"""
    if pd.isna(name):
        return "unknown"
    name = str(name).replace("AdGage_", "")
    return name.lower()


def map_country_to_geo_cluster(country: str) -> str:
    """Map country to geo cluster"""
    if pd.isna(country):
        return "OTHER"
    country = str(country).strip()
    if country == "Italy":
        return "ITA"
    elif country == "Spain":
        return "ES"
    else:
        return "OTHER"


def map_channel_to_channel_group(channel: str) -> str:
    """Map channel to channel_group"""
    if pd.isna(channel):
        return "OPEN_BIDDING"
    channel = str(channel).strip()
    if channel == "Ad Exchange":
        return "GOOGLE"
    else:
        return "OPEN_BIDDING"


def safe_divide(numerator, denominator):
    """Safely divide, returning 0 if denominator is 0"""
    if denominator == 0 or pd.isna(denominator):
        return 0.0
    return numerator / denominator


def aggregate_hourly():
    """
    Aggregate hourly parquet data (4.3M rows - manageable in memory)
    Output: hourly_aggregated.parquet
    """
    log("=" * 80)
    log("TASK 1: AGGREGATING HOURLY DATA")
    log("=" * 80)

    if not os.path.exists(HOURLY_PATH):
        log(f"ERROR: Hourly file not found at {HOURLY_PATH}")
        return False

    log(f"Reading hourly data from: {HOURLY_PATH}")
    df = pd.read_parquet(HOURLY_PATH)
    log(f"Loaded {len(df):,} rows")

    # Show columns
    log(f"Columns: {list(df.columns)}")

    # Normalize columns
    df['publisher_id'] = df['Ad unit 1'].apply(normalize_publisher)
    df['site_id'] = df['Ad unit 2']
    df['environment'] = df['Environment'].str.upper()
    df['timestamp'] = pd.to_datetime(df['Timestamp'])
    df['geo_cluster'] = 'ALL'  # Hourly data doesn't have Country

    # Rename revenue columns
    df['revenue_google'] = df['Revenue'].fillna(0)
    df['revenue_open'] = df['Revenue_open'].fillna(0)
    df['impressions_google'] = df['Impressions'].fillna(0)
    df['impressions_open'] = df['Impressions_open'].fillna(0)
    df['ad_requests'] = df['Ad Requests'].fillna(0)

    log("Creating separate rows for GOOGLE and OPEN_BIDDING channels...")

    # Create Google channel rows
    df_google = df.copy()
    df_google['channel_group'] = 'GOOGLE'
    df_google['revenue'] = df_google['revenue_google']
    df_google['impressions'] = df_google['impressions_google']

    # Create Open Bidding channel rows
    df_open = df.copy()
    df_open['channel_group'] = 'OPEN_BIDDING'
    df_open['revenue'] = df_open['revenue_open']
    df_open['impressions'] = df_open['impressions_open']

    # Combine both
    df_combined = pd.concat([df_google, df_open], ignore_index=True)

    log(f"Combined rows: {len(df_combined):,} (double of original)")

    # Group and aggregate
    group_cols = ['timestamp', 'channel_group', 'environment', 'publisher_id', 'site_id', 'geo_cluster']

    log(f"Grouping by: {group_cols}")

    agg_dict = {
        'revenue': 'sum',
        'impressions': 'sum',
        'ad_requests': 'sum',
    }

    df_agg = df_combined.groupby(group_cols, as_index=False).agg(agg_dict)

    # Calculate coverage
    df_agg['bacino'] = df_agg['ad_requests']
    df_agg['coverage'] = df_agg.apply(
        lambda row: safe_divide(row['impressions'], row['bacino']), axis=1
    )

    # Round values
    df_agg['revenue'] = df_agg['revenue'].round(2)
    df_agg['coverage'] = df_agg['coverage'].round(4)
    df_agg['bacino'] = df_agg['bacino'].astype(int)
    df_agg['impressions'] = df_agg['impressions'].astype(int)

    # Select final columns
    final_cols = [
        'timestamp', 'channel_group', 'environment', 'publisher_id', 'site_id',
        'geo_cluster', 'revenue', 'bacino', 'coverage', 'impressions'
    ]
    df_final = df_agg[final_cols]

    log(f"Aggregated to {len(df_final):,} rows")
    log(f"Date range: {df_final['timestamp'].min()} to {df_final['timestamp'].max()}")
    log(f"Publishers: {df_final['publisher_id'].nunique()}")
    log(f"Total revenue: €{df_final['revenue'].sum():,.2f}")

    # Save
    output_path = OUTPUT_DIR / "hourly_aggregated.parquet"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df_final.to_parquet(output_path, index=False, compression='snappy')

    file_size = os.path.getsize(output_path) / 1024 / 1024
    log(f"Saved to: {output_path} ({file_size:.2f} MB)")
    log("✓ HOURLY AGGREGATION COMPLETE\n")

    return True


def aggregate_daily_channel():
    """
    Aggregate daily channel parquet data (156M rows - MUST process in chunks!)
    Output: daily_channel_aggregated.parquet
    """
    log("=" * 80)
    log("TASK 2: AGGREGATING DAILY CHANNEL DATA (156M rows)")
    log("=" * 80)

    if not os.path.exists(DAILY_CHANNEL_PATH):
        log(f"ERROR: Daily channel file not found at {DAILY_CHANNEL_PATH}")
        return False

    log(f"Reading in CHUNKS from: {DAILY_CHANNEL_PATH}")

    # Open parquet file for batch reading
    parquet_file = pq.ParquetFile(DAILY_CHANNEL_PATH)
    log(f"Total rows: {parquet_file.metadata.num_rows:,}")

    batch_size = 500000
    log(f"Processing in batches of {batch_size:,} rows")

    # Accumulate aggregations
    aggregates = {}
    total_processed = 0
    batch_num = 0

    for batch in parquet_file.iter_batches(batch_size=batch_size):
        batch_num += 1
        df_batch = batch.to_pandas()
        total_processed += len(df_batch)

        if batch_num % 10 == 0:
            log(f"  Batch {batch_num}: processed {total_processed:,} rows...")

        # Normalize columns
        df_batch['publisher_id'] = df_batch['Ad unit 1'].apply(normalize_publisher)
        df_batch['site_id'] = df_batch['Ad unit 2']
        df_batch['environment'] = df_batch['Environment'].str.upper()
        df_batch['date'] = pd.to_datetime(df_batch['Date'])
        df_batch['geo_cluster'] = df_batch['Country'].apply(map_country_to_geo_cluster)
        df_batch['channel_group'] = df_batch['Channel'].apply(map_channel_to_channel_group)

        df_batch['revenue'] = df_batch['Revenue'].fillna(0)
        df_batch['impressions'] = df_batch['Impressions'].fillna(0)

        # Group this batch
        group_cols = ['date', 'publisher_id', 'site_id', 'environment', 'geo_cluster', 'channel_group']
        batch_agg = df_batch.groupby(group_cols, as_index=False).agg({
            'revenue': 'sum',
            'impressions': 'sum',
        })

        # Accumulate into main dict
        for _, row in batch_agg.iterrows():
            key = tuple(row[col] for col in group_cols)
            if key not in aggregates:
                aggregates[key] = {'revenue': 0.0, 'impressions': 0}
            aggregates[key]['revenue'] += row['revenue']
            aggregates[key]['impressions'] += row['impressions']

    log(f"Total processed: {total_processed:,} rows")
    log(f"Unique aggregation keys: {len(aggregates):,}")

    # Convert aggregates dict to DataFrame
    log("Converting aggregates to DataFrame...")
    rows = []
    group_cols = ['date', 'publisher_id', 'site_id', 'environment', 'geo_cluster', 'channel_group']

    for key, metrics in aggregates.items():
        row_dict = dict(zip(group_cols, key))
        row_dict['revenue'] = round(metrics['revenue'], 2)
        row_dict['impressions'] = int(metrics['impressions'])
        rows.append(row_dict)

    df_final = pd.DataFrame(rows)

    log(f"Final aggregated rows: {len(df_final):,}")
    log(f"Date range: {df_final['date'].min()} to {df_final['date'].max()}")
    log(f"Total revenue: €{df_final['revenue'].sum():,.2f}")

    # Save
    output_path = OUTPUT_DIR / "daily_channel_aggregated.parquet"
    df_final.to_parquet(output_path, index=False, compression='snappy')

    file_size = os.path.getsize(output_path) / 1024 / 1024
    log(f"Saved to: {output_path} ({file_size:.2f} MB)")
    log("✓ DAILY CHANNEL AGGREGATION COMPLETE\n")

    return True


def aggregate_daily_adrequests():
    """
    Aggregate daily adrequests parquet data (159M rows - MUST process in chunks!)
    Output: daily_adrequests_aggregated.parquet
    """
    log("=" * 80)
    log("TASK 3: AGGREGATING DAILY ADREQUESTS DATA (159M rows)")
    log("=" * 80)

    if not os.path.exists(DAILY_ADREQUESTS_PATH):
        log(f"ERROR: Daily adrequests file not found at {DAILY_ADREQUESTS_PATH}")
        return False

    log(f"Reading in CHUNKS from: {DAILY_ADREQUESTS_PATH}")

    # Open parquet file for batch reading
    parquet_file = pq.ParquetFile(DAILY_ADREQUESTS_PATH)
    log(f"Total rows: {parquet_file.metadata.num_rows:,}")

    batch_size = 500000
    log(f"Processing in batches of {batch_size:,} rows")

    # Accumulate aggregations
    aggregates = {}
    total_processed = 0
    batch_num = 0

    for batch in parquet_file.iter_batches(batch_size=batch_size):
        batch_num += 1
        df_batch = batch.to_pandas()
        total_processed += len(df_batch)

        if batch_num % 10 == 0:
            log(f"  Batch {batch_num}: processed {total_processed:,} rows...")

        # Normalize columns
        df_batch['publisher_id'] = df_batch['Ad unit 1'].apply(normalize_publisher)
        df_batch['site_id'] = df_batch['Ad unit 2']
        df_batch['environment'] = df_batch['Environment'].str.upper()
        df_batch['date'] = pd.to_datetime(df_batch['Date'])
        df_batch['geo_cluster'] = df_batch['Country'].apply(map_country_to_geo_cluster)

        df_batch['revenue'] = df_batch['Revenue'].fillna(0)
        df_batch['impressions'] = df_batch['Impressions'].fillna(0)
        df_batch['ad_requests'] = df_batch['Ad Requests'].fillna(0)

        # Group this batch
        group_cols = ['date', 'publisher_id', 'site_id', 'environment', 'geo_cluster']
        batch_agg = df_batch.groupby(group_cols, as_index=False).agg({
            'revenue': 'sum',
            'impressions': 'sum',
            'ad_requests': 'sum',
        })

        # Accumulate into main dict
        for _, row in batch_agg.iterrows():
            key = tuple(row[col] for col in group_cols)
            if key not in aggregates:
                aggregates[key] = {'revenue': 0.0, 'impressions': 0, 'ad_requests': 0}
            aggregates[key]['revenue'] += row['revenue']
            aggregates[key]['impressions'] += row['impressions']
            aggregates[key]['ad_requests'] += row['ad_requests']

    log(f"Total processed: {total_processed:,} rows")
    log(f"Unique aggregation keys: {len(aggregates):,}")

    # Convert aggregates dict to DataFrame
    log("Converting aggregates to DataFrame...")
    rows = []
    group_cols = ['date', 'publisher_id', 'site_id', 'environment', 'geo_cluster']

    for key, metrics in aggregates.items():
        row_dict = dict(zip(group_cols, key))
        row_dict['revenue'] = round(metrics['revenue'], 2)
        row_dict['impressions'] = int(metrics['impressions'])
        row_dict['bacino'] = int(metrics['ad_requests'])
        row_dict['coverage'] = round(safe_divide(metrics['impressions'], metrics['ad_requests']), 4)
        rows.append(row_dict)

    df_final = pd.DataFrame(rows)

    log(f"Final aggregated rows: {len(df_final):,}")
    log(f"Date range: {df_final['date'].min()} to {df_final['date'].max()}")
    log(f"Total revenue: €{df_final['revenue'].sum():,.2f}")
    log(f"Avg coverage: {df_final['coverage'].mean():.4f}")

    # Save
    output_path = OUTPUT_DIR / "daily_adrequests_aggregated.parquet"
    df_final.to_parquet(output_path, index=False, compression='snappy')

    file_size = os.path.getsize(output_path) / 1024 / 1024
    log(f"Saved to: {output_path} ({file_size:.2f} MB)")
    log("✓ DAILY ADREQUESTS AGGREGATION COMPLETE\n")

    return True


def main():
    """Run all aggregation tasks"""
    log("\n" + "=" * 80)
    log("VALUE NETWORK ALERTING - DATA INTEGRATION")
    log("=" * 80)
    log(f"Start time: {datetime.now()}")
    log(f"Output directory: {OUTPUT_DIR}")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log(f"Output directory ready: {OUTPUT_DIR}\n")

    success = True

    # Task 1: Hourly
    if not aggregate_hourly():
        success = False

    # Task 2: Daily Channel
    if not aggregate_daily_channel():
        success = False

    # Task 3: Daily AdRequests
    if not aggregate_daily_adrequests():
        success = False

    log("=" * 80)
    if success:
        log("✓ ALL AGGREGATION TASKS COMPLETED SUCCESSFULLY")
    else:
        log("✗ SOME AGGREGATION TASKS FAILED")
    log(f"End time: {datetime.now()}")
    log("=" * 80 + "\n")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
