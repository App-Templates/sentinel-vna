# Data Integration Guide

This guide explains how to integrate real parquet data into the Value Network Alerting platform.

## Overview

The system now supports **real parquet data** with automatic fallback to synthetic data generation. The integration processes large datasets (150M+ rows) efficiently using chunk-based aggregation.

## Data Files

### Source Data

1. **Hourly Data** (4.3M rows, Jan 2024 - Jan 2026)
   - Path: `/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_hourly/data.parquet`
   - Schema: Timestamp, Ad unit 1, Ad unit 2, SubFormat, Environment, Impressions, Revenue, Ad Requests, Impressions_open, Revenue_open

2. **Daily Channel Data** (156M rows, Jan 2024 - Sep 2025)
   - Path: `/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_daily/data_channel.parquet`
   - Schema: Date, Ad unit 1, Ad unit 2, SubFormat, Environment, OperatingSystem, Country, Channel, Impressions, Revenue

3. **Daily AdRequests Data** (159M rows, Jan 2024 - Sep 2025)
   - Path: `/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_daily/data_adrequests.parquet`
   - Schema: Date, Ad unit 1, Ad unit 2, SubFormat, Environment, OperatingSystem, Country, Impressions, Revenue, Ad Requests

### Aggregated Data (Created by Integration)

Located in `data/baseline/`:

1. **hourly_aggregated.parquet**
   - Processed from hourly source data
   - Schema: timestamp, channel_group, environment, publisher_id, site_id, geo_cluster, revenue, bacino, coverage, impressions
   - ~4.3M rows → aggregated to fewer rows
   - Used for: Real-time alerting, baseline calculation

2. **daily_channel_aggregated.parquet**
   - Processed from daily channel source data
   - Schema: date, publisher_id, site_id, environment, geo_cluster, channel_group, revenue, impressions
   - 156M rows → significantly reduced
   - Used for: A2 drift detection (7-day trends)

3. **daily_adrequests_aggregated.parquet**
   - Processed from daily adrequests source data
   - Schema: date, publisher_id, site_id, environment, geo_cluster, revenue, bacino, coverage, impressions
   - 159M rows → significantly reduced
   - Used for: Coverage analysis

## Field Mappings

### Publisher ID
- Source: `Ad unit 1`
- Transformation: Remove "AdGage_" prefix, convert to lowercase
- Examples:
  - "AdGage_Vocento" → "vocento"
  - "Mondadori" → "mondadori"
  - "TheCore" → "thecore"

### Environment
- Source: `Environment`
- Transformation: Convert to uppercase
- Values: WEB, AMP, APP

### Geo Cluster
- Source: `Country`
- Mapping:
  - "Italy" → "ITA"
  - "Spain" → "ES"
  - Everything else → "OTHER"
- Note: Hourly data doesn't have Country, so geo_cluster = 'ALL'

### Channel Group
- Source: `Channel` (in daily data)
- Mapping:
  - "Ad Exchange" → "GOOGLE"
  - Everything else (PubMatic, etc.) → "OPEN_BIDDING"
- Note: Hourly data has separate revenue/impressions columns for each channel

### Metrics
- `Revenue` → Google revenue (in hourly: `Revenue` column)
- `Revenue_open` → Open Bidding revenue (hourly only)
- `Impressions` / `Impressions_open` → Split by channel (hourly)
- `Ad Requests` → `bacino`
- `coverage` = impressions / ad_requests (calculated)

## Setup Instructions

### Step 1: Install Dependencies

Ensure you have the required Python packages:

```bash
pip install pandas pyarrow
```

### Step 2: Run Data Aggregation

This is the **most important step**. It processes the large parquet files and creates optimized aggregated versions:

```bash
cd /Users/admintemp/Downloads/Claude/value-network-alerting
python scripts/aggregate_parquet.py
```

**What this does:**
- Reads hourly data (4.3M rows) - loads fully into memory
- Reads daily channel data (156M rows) - **processes in 500K row chunks**
- Reads daily adrequests data (159M rows) - **processes in 500K row chunks**
- Normalizes publisher names, maps geo clusters, splits channels
- Aggregates to group by relevant dimensions
- Creates 3 parquet files in `data/baseline/`

**Expected output:**
```
[timestamp] ========================================
[timestamp] TASK 1: AGGREGATING HOURLY DATA
[timestamp] ========================================
[timestamp] Reading hourly data from: /Users/admintemp/Downloads/...
[timestamp] Loaded 4,300,000 rows
[timestamp] Aggregated to 150,000 rows
[timestamp] Saved to: data/baseline/hourly_aggregated.parquet (25.3 MB)
[timestamp] ✓ HOURLY AGGREGATION COMPLETE

[timestamp] ========================================
[timestamp] TASK 2: AGGREGATING DAILY CHANNEL DATA (156M rows)
[timestamp] ========================================
[timestamp] Processing in batches of 500,000 rows
[timestamp] Total processed: 156,000,000 rows
[timestamp] Unique aggregation keys: 500,000
[timestamp] Saved to: data/baseline/daily_channel_aggregated.parquet (45.2 MB)
[timestamp] ✓ DAILY CHANNEL AGGREGATION COMPLETE

[timestamp] ========================================
[timestamp] TASK 3: AGGREGATING DAILY ADREQUESTS DATA (159M rows)
[timestamp] ========================================
[timestamp] Processing in batches of 500,000 rows
[timestamp] Total processed: 159,000,000 rows
[timestamp] Saved to: data/baseline/daily_adrequests_aggregated.parquet (38.7 MB)
[timestamp] ✓ DAILY ADREQUESTS AGGREGATION COMPLETE
```

**Performance Note:**
- Daily files are too large to load fully into memory
- Uses PyArrow's `iter_batches()` for memory-efficient processing
- Processes 500K rows at a time
- Takes ~5-15 minutes depending on machine

### Step 3: Seed Historical Alerts (Optional)

Populate the dashboard with real alerts from the last 7 days of data:

```bash
python scripts/seed_alerts_from_parquet.py
```

**What this does:**
- Runs the full anomaly detection pipeline on the last 7 days of hourly data
- Checks every 2 hours for anomalies
- Generates real alerts (A1, A2, A3) based on actual data patterns
- Inserts alerts into SQLite database
- Populates the dashboard with historical context

### Step 4: Verify Integration

Start the backend and verify real data is being used:

```bash
python3 -m uvicorn backend.main:app --port 8000
```

Check the logs for:
```
Data fetcher started (real data mode)
Loaded hourly data: 150,000 rows, date range 2024-01-01 to 2026-01-31
Data fetcher complete (REAL DATA): rev=12500.00, baseline=13200.00, points=7
Rate limiting enabled on API endpoints
```

If you see `data_source: "real_parquet"` in API responses, real data is active.

## How It Works

### Data Fetcher Agent

Located in `backend/agents/data_fetcher.py`:

1. **Real Data Mode** (if parquet files exist):
   - Loads `hourly_aggregated.parquet` into memory (cached)
   - For a given timestamp + channel:
     - **Current metrics**: Query exact hour from parquet
     - **Baseline**: Calculate 7-day same-hour same-weekday average (7 weeks back, sample std dev with Bessel's correction)
     - **Drift** (for A2): Load daily data, compare last 7 days vs previous 7 days
   - Returns full metrics breakdown by publisher, geo, environment
   - Cache TTL: 5 minutes for real data queries
   - Generates A0 alerts for data gaps (missing/empty real data)

2. **Synthetic Fallback Mode** (if parquet files missing):
   - **LIVE mode**: Synthetic data is BLOCKED (raises error, generates A0 alert)
   - **BACKTEST mode**: Synthetic data allowed as fallback
   - Priority chain: Athena → GAM → Parquet → Synthetic (backtest only)
   - Ensures production alerts use only real data

### Backtest Runner

Located in `backend/backtest/runner.py`:

1. **Real Data Mode**:
   - Loads hourly parquet
   - Iterates through date range at 2-hour intervals
   - For each timestamp:
     - Runs full workflow (fetch → detect → triage → insights)
     - Checks alert rules (A1, A2, A3)
     - Generates alerts if thresholds exceeded
   - Returns real backtest results based on actual data patterns

2. **Synthetic Mode** (fallback):
   - Generates random alerts based on configured probabilities
   - Used when parquet files aren't available

## File Structure

```
value-network-alerting/
├── scripts/
│   ├── aggregate_parquet.py          # Main aggregation script
│   └── seed_alerts_from_parquet.py   # Alert seeding script
├── backend/
│   ├── agents/
│   │   ├── data_fetcher.py           # Main data fetcher (auto-switching)
│   │   └── data_fetcher_real.py      # Real parquet data loader
│   └── backtest/
│       ├── runner.py                 # Main backtest runner (auto-switching)
│       └── runner_real.py            # Real data backtest runner
├── data/
│   └── baseline/                     # Created by aggregation script
│       ├── hourly_aggregated.parquet
│       ├── daily_channel_aggregated.parquet
│       └── daily_adrequests_aggregated.parquet
└── DATA_INTEGRATION.md               # This file
```

## Logs

All integration operations log to:
- Console (stdout)
- `/tmp/vna-dataintegration.log`

Check this file for detailed progress during aggregation:
```bash
tail -f /tmp/vna-dataintegration.log
```

## Troubleshooting

### "Hourly parquet not found"

**Problem**: The aggregated parquet files haven't been created yet.

**Solution**: Run `python scripts/aggregate_parquet.py`

### "Memory error during aggregation"

**Problem**: System ran out of memory processing large files.

**Solution**: The script already uses chunk processing. If still failing:
- Reduce `batch_size` in `aggregate_parquet.py` (default: 500000)
- Close other applications to free RAM
- Process on a machine with more memory

### "No data found for timestamp"

**Problem**: Requesting data outside the available date range.

**Solution**:
- Check data range: `python -c "import pandas as pd; df=pd.read_parquet('data/baseline/hourly_aggregated.parquet'); print(df['timestamp'].min(), df['timestamp'].max())"`
- Ensure your requested timestamp falls within this range

### "Falling back to synthetic data"

**Problem**: Real data loader encountered an error.

**Causes**:
- Parquet files not created (run aggregation script)
- Parquet files corrupted (re-run aggregation)
- Import error (check dependencies: `pip install pandas pyarrow`)

**Solution**: Check logs for specific error, re-run aggregation if needed

## Performance Metrics

### Aggregation Script

- **Hourly data** (4.3M rows): ~30 seconds
- **Daily channel** (156M rows): ~5-10 minutes
- **Daily adrequests** (159M rows): ~5-10 minutes
- **Total**: ~15-25 minutes

### Real-time Queries

- **Data fetcher** (single hour): ~10-50ms (cached)
- **Baseline calculation** (7 weeks): ~50-200ms
- **Drift calculation** (14 days): ~100-300ms

### Alert Seeding

- **7 days, 2-hour intervals**: ~2-5 minutes
- **Generates**: ~80-100 checks, 5-15 alerts (depending on data)

## Data Quality

### Validation Checks

The aggregation script performs:
- Publisher name normalization
- Null/NaN handling (converted to 0 or 'unknown')
- Division by zero protection (coverage calculation)
- Data type conversions (int for counts, float for revenue)
- Rounding (revenue: 2 decimals, coverage: 4 decimals)

### Expected Data Patterns

From real data:
- **Revenue range**: €0 - €50,000 per hour per channel
- **Coverage**: 0.30 - 0.95 (30% - 95%)
- **Bacino**: 100K - 5M ad requests per hour
- **Publishers**: ~20 active publishers
- **Channels**: GOOGLE (60-70% revenue), OPEN_BIDDING (30-40%)

## Next Steps

After successful integration:

1. **Test Alerting**: Trigger manual checks via API to verify real data flows through
2. **Run Backtest**: Execute historical backtest to validate detection accuracy
3. **Monitor Dashboard**: Check that alerts show real publisher names and metrics
4. **Tune Thresholds**: Adjust alert thresholds based on real data patterns
5. **Schedule Jobs**: Set up cron jobs for regular data updates

## Support

For issues or questions:
1. Check logs: `/tmp/vna-dataintegration.log`
2. Verify file existence: `ls -lh data/baseline/`
3. Test data loading: `python -c "import pandas as pd; print(pd.read_parquet('data/baseline/hourly_aggregated.parquet').info())"`
