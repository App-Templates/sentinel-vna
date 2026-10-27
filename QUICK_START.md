# Quick Start Guide - Real Data Integration

This guide gets you up and running with real parquet data in 5 minutes.

## Prerequisites

1. Python 3.8+ installed
2. Required packages: `pandas`, `pyarrow`
   ```bash
   pip install pandas pyarrow
   ```

3. Source data files at:
   - `/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_hourly/data.parquet`
   - `/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_daily/data_channel.parquet`
   - `/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_daily/data_adrequests.parquet`

## Option 1: Automated Integration (Recommended)

Run the full integration script:

```bash
cd /Users/admintemp/Downloads/Claude/value-network-alerting
chmod +x scripts/run_full_integration.sh
./scripts/run_full_integration.sh
```

This script will:
1. ✓ Verify source data files exist
2. ✓ Aggregate 315M rows into optimized parquet files (~15-25 min)
3. ✓ Test the integration
4. ✓ Optionally seed historical alerts

## Option 2: Manual Step-by-Step

### Step 1: Verify Data Paths

```bash
cd /Users/admintemp/Downloads/Claude/value-network-alerting
python scripts/verify_data_paths.py
```

Expected output:
```
✓ All source data files found!
```

### Step 2: Run Aggregation

```bash
python scripts/aggregate_parquet.py
```

**This is the key step!** It processes:
- 4.3M hourly rows → `data/baseline/hourly_aggregated.parquet`
- 156M daily channel rows → `data/baseline/daily_channel_aggregated.parquet`
- 159M daily adrequests rows → `data/baseline/daily_adrequests_aggregated.parquet`

Takes ~15-25 minutes. Watch progress:
```bash
tail -f /tmp/vna-dataintegration.log
```

### Step 3: Test Integration

```bash
python scripts/test_integration.py
```

Should show:
```
✓ TEST 1 PASSED: All aggregated files exist
✓ TEST 2 PASSED: All data files loaded successfully
✓ TEST 3 PASSED: Data fetcher working correctly
✓ TEST 4 PASSED: Workflow ran successfully with real data
Total: 4/4 tests passed
```

### Step 4: Seed Alerts (Optional)

```bash
python scripts/seed_alerts_from_parquet.py
```

Populates dashboard with real alerts from last 7 days of data.

## Verify Integration

### Check Files Created

```bash
ls -lh data/baseline/
```

Should show:
```
hourly_aggregated.parquet           (20-30 MB)
daily_channel_aggregated.parquet    (40-50 MB)
daily_adrequests_aggregated.parquet (30-40 MB)
```

### Test Data Loading

```python
import pandas as pd

# Load hourly data
df = pd.read_parquet('data/baseline/hourly_aggregated.parquet')
print(f"Rows: {len(df):,}")
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
print(f"Publishers: {df['publisher_id'].nunique()}")
print(f"Total revenue: €{df['revenue'].sum():,.2f}")
```

### Test API

Start backend:
```bash
python3 -m uvicorn backend.main:app --port 8000
```

In another terminal:
```bash
curl http://localhost:8000/api/health
```

Should show `data_mode: "real_parquet"` if integration successful. The backend now includes rate limiting on all API endpoints for production safety.

## Start Application

### Backend

```bash
python3 -m uvicorn backend.main:app --port 8000
```

Logs should show:
```
Data fetcher started (real data mode)
Loaded hourly data: 150,000 rows, date range 2025-11-01 to 2025-12-31
Rate limiting enabled on API endpoints
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open: http://localhost:5173

## Alert Types

The system now supports 4 alert types:
- **A0**: Data gap (missing or empty real data sources)
- **A1**: Revenue drop (P0/P1/P2 severity based on threshold)
- **A2**: 7-day drift (gradual revenue decline over week)
- **A3**: Near-zero coverage (fill rate issues)

**Note**: In LIVE mode, synthetic data is blocked. A0 alerts are generated if real data sources (Athena/GAM/Parquet) are unavailable.

## Troubleshooting

### "Source data files not found"

**Fix**: Verify files are at the correct paths:
```bash
ls -lh "/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_hourly/"
ls -lh "/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_daily/"
```

### "Memory error during aggregation"

**Fix**: Close other applications, or reduce batch size in `aggregate_parquet.py`:
```python
batch_size = 250000  # Reduce from 500000
```

### "No data found for timestamp"

**Fix**: Check available date range:
```python
import pandas as pd
df = pd.read_parquet('data/baseline/hourly_aggregated.parquet')
print(f"Available: {df['timestamp'].min()} to {df['timestamp'].max()}")
```

### "Falling back to synthetic data"

**Fix**: Run aggregation script:
```bash
python scripts/aggregate_parquet.py
```

## Data Quality Checks

Verify data looks correct:

```python
import pandas as pd

df = pd.read_parquet('data/baseline/hourly_aggregated.parquet')

# Check publisher names (should be normalized: lowercase, no "AdGage_")
print("Publishers:", df['publisher_id'].unique()[:10])
# Expected: ['vocento', 'mondadori', 'thecore', ...]

# Check channels
print("Channels:", df['channel_group'].unique())
# Expected: ['GOOGLE', 'OPEN_BIDDING']

# Check geo clusters
print("Geo clusters:", df['geo_cluster'].unique())
# Expected: ['ALL'] for hourly data

# Check environments
print("Environments:", df['environment'].unique())
# Expected: ['WEB', 'AMP', 'APP']

# Check revenue range (should be reasonable)
print(f"Revenue range: €{df['revenue'].min():.2f} - €{df['revenue'].max():,.2f}")
# Expected: €0 - €50,000 per hour

# Check coverage (should be 0-1)
print(f"Coverage range: {df['coverage'].min():.4f} - {df['coverage'].max():.4f}")
# Expected: 0.30 - 0.95
```

## Performance

### Expected Runtimes

- **Aggregation**: 15-25 minutes (one-time)
- **Alert seeding**: 2-5 minutes (optional, one-time)
- **Data fetcher**: <100ms per request (after aggregation)
- **Workflow**: 200-500ms per check

### Optimization Tips

1. **First run**: Aggregation is slow (processing 315M rows)
2. **Subsequent runs**: Fast (data is cached in memory)
3. **Large datasets**: Already optimized with chunk processing
4. **Memory usage**: ~1-2GB during aggregation, ~500MB runtime

## What's Different with Real Data?

### Before (Synthetic)
- ⚠ Fake publisher names
- ⚠ Deterministic patterns
- ⚠ Perfect data quality
- ⚠ No real anomalies

### After (Real Data)
- ✓ Real publisher names (vocento, mondadori, thecore, etc.)
- ✓ Actual traffic patterns
- ✓ Real anomalies and outliers
- ✓ Historical baselines from actual data
- ✓ Real geo/environment distributions

## Next Steps

After successful integration:

1. **Explore Dashboard**: See real publisher names and metrics
2. **Run Backtest**: `POST /api/backtest/run` to validate detection
3. **Tune Thresholds**: Adjust alert rules based on real data patterns
4. **Schedule Updates**: Set up cron jobs to refresh aggregated data
5. **Monitor Performance**: Track query times and alert accuracy

## Files Created

```
value-network-alerting/
├── data/
│   └── baseline/                     # Created by aggregation
│       ├── hourly_aggregated.parquet
│       ├── daily_channel_aggregated.parquet
│       └── daily_adrequests_aggregated.parquet
├── scripts/
│   ├── aggregate_parquet.py          # Main aggregation script
│   ├── seed_alerts_from_parquet.py   # Alert seeding
│   ├── verify_data_paths.py          # Path verification
│   ├── test_integration.py           # Integration tests
│   └── run_full_integration.sh       # Automated pipeline
├── backend/
│   ├── agents/
│   │   ├── data_fetcher.py           # Auto-switching data fetcher
│   │   └── data_fetcher_real.py      # Real data loader
│   └── backtest/
│       ├── runner.py                 # Auto-switching backtest runner
│       └── runner_real.py            # Real data backtest
├── DATA_INTEGRATION.md               # Detailed integration guide
└── QUICK_START.md                    # This file
```

## Support

For detailed documentation, see: `DATA_INTEGRATION.md`

For issues:
1. Check logs: `tail -f /tmp/vna-dataintegration.log`
2. Run tests: `python scripts/test_integration.py`
3. Verify files: `ls -lh data/baseline/`

## Summary Commands

```bash
# Full automated integration
./scripts/run_full_integration.sh

# Or manual step-by-step
python scripts/verify_data_paths.py           # Verify source files
python scripts/aggregate_parquet.py           # Process data (15-25 min)
python scripts/test_integration.py            # Test integration
python scripts/seed_alerts_from_parquet.py    # Seed alerts (optional)

# Start application
python -m backend.api.server                  # Backend (port 8000)
cd frontend && npm run dev                    # Frontend (port 5173)
```

That's it! You now have real parquet data integrated into the Value Network Alerting platform.
