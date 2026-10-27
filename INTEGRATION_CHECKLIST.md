# Data Integration Checklist

Use this checklist to ensure successful integration of real parquet data.

## Pre-Integration

### ☐ Prerequisites
- [ ] Python 3.8+ installed (`python3 --version`)
- [ ] pip installed (`pip --version`)
- [ ] Git repository cloned
- [ ] Working directory: `/Users/admintemp/Downloads/Claude/value-network-alerting`

### ☐ Dependencies
- [ ] Install required packages: `pip install -r requirements.txt`
- [ ] Verify pandas: `python -c "import pandas; print(pandas.__version__)"`
- [ ] Verify pyarrow: `python -c "import pyarrow; print(pyarrow.__version__)"`

### ☐ Source Data Files
- [ ] Hourly data exists: `/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_hourly/data.parquet`
- [ ] Daily channel data exists: `/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_daily/data_channel.parquet`
- [ ] Daily adrequests data exists: `/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_daily/data_adrequests.parquet`
- [ ] Run verification: `python scripts/verify_data_paths.py`

## Integration Steps

### ☐ Step 1: Data Aggregation (15-25 minutes)
- [ ] Clear log file: `> /tmp/vna-dataintegration.log`
- [ ] Run aggregation: `python scripts/aggregate_parquet.py`
- [ ] Monitor progress: `tail -f /tmp/vna-dataintegration.log` (in another terminal)
- [ ] Wait for completion (~20 minutes)
- [ ] Check for errors in log: `grep ERROR /tmp/vna-dataintegration.log`
- [ ] Verify output files created:
  - [ ] `data/baseline/hourly_aggregated.parquet` exists
  - [ ] `data/baseline/daily_channel_aggregated.parquet` exists
  - [ ] `data/baseline/daily_adrequests_aggregated.parquet` exists
- [ ] Check file sizes: `ls -lh data/baseline/`
  - [ ] hourly_aggregated.parquet: 20-30 MB
  - [ ] daily_channel_aggregated.parquet: 40-50 MB
  - [ ] daily_adrequests_aggregated.parquet: 30-40 MB

### ☐ Step 2: Integration Testing
- [ ] Run integration tests: `python scripts/test_integration.py`
- [ ] Verify Test 1 PASSED (Aggregated Files)
- [ ] Verify Test 2 PASSED (Data Loading)
- [ ] Verify Test 3 PASSED (Data Fetcher)
- [ ] Verify Test 4 PASSED (Full Workflow)
- [ ] All 4/4 tests passed

### ☐ Step 3: Alert Seeding (Optional)
- [ ] Run seeding script: `python scripts/seed_alerts_from_parquet.py`
- [ ] Check for completion message
- [ ] Note number of alerts generated
- [ ] Verify alerts in database (if accessible)

## Post-Integration Verification

### ☐ Data Quality Checks

**Check Publisher Names**:
```python
import pandas as pd
df = pd.read_parquet('data/baseline/hourly_aggregated.parquet')
print("Publishers:", df['publisher_id'].unique()[:10])
```
- [ ] Publisher names are lowercase
- [ ] No "AdGage_" prefix
- [ ] Examples: vocento, mondadori, thecore

**Check Channels**:
```python
print("Channels:", df['channel_group'].unique())
```
- [ ] Contains "GOOGLE"
- [ ] Contains "OPEN_BIDDING"
- [ ] Only 2 channels

**Check Environments**:
```python
print("Environments:", df['environment'].unique())
```
- [ ] Contains "WEB"
- [ ] Contains "AMP"
- [ ] Contains "APP"
- [ ] All uppercase

**Check Date Range**:
```python
print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
```
- [ ] Covers Jan 2024 - Jan 2026 (for hourly data)
- [ ] No missing days

**Check Revenue**:
```python
print(f"Revenue range: €{df['revenue'].min():.2f} - €{df['revenue'].max():,.2f}")
print(f"Total revenue: €{df['revenue'].sum():,.2f}")
```
- [ ] Revenue > 0
- [ ] Revenue < 100,000 per hour (reasonable upper bound)
- [ ] No NaN values

**Check Coverage**:
```python
print(f"Coverage range: {df['coverage'].min():.4f} - {df['coverage'].max():.4f}")
```
- [ ] Coverage between 0 and 1
- [ ] Average coverage ~0.70-0.85

### ☐ Backend Integration

**Test Data Fetcher**:
```python
from backend.agents.data_fetcher_real import _load_hourly_data
df = _load_hourly_data()
print(f"Loaded: {len(df):,} rows")
```
- [ ] Loads without errors
- [ ] Shows row count
- [ ] Cache message on second load

**Test Imports**:
```bash
python -c "from backend.agents.data_fetcher_real import data_fetcher_agent; print('OK')"
python -c "from backend.backtest.runner_real import BacktestRunnerReal; print('OK')"
```
- [ ] data_fetcher_real imports successfully
- [ ] runner_real imports successfully

### ☐ API Testing

**Start Backend**:
```bash
python3 -m uvicorn backend.main:app --port 8000
```
- [ ] Backend starts without errors
- [ ] Logs show "Data fetcher started (real data mode)"
- [ ] Logs show "Loaded hourly data: X rows"
- [ ] Logs show "Rate limiting enabled on API endpoints"

**Test Health Endpoint** (in another terminal):
```bash
curl http://localhost:8000/api/health
```
- [ ] Returns 200 OK
- [ ] Response includes `"status": "healthy"`
- [ ] Check for `data_mode` in response (if available)

**Test Metrics Endpoint**:
```bash
curl "http://localhost:8000/api/metrics?timestamp=2025-11-15T10:00:00Z&channel=GOOGLE"
```
- [ ] Returns 200 OK
- [ ] Response includes real metrics
- [ ] Publisher names are normalized

### ☐ Frontend Integration

**Start Frontend** (if available):
```bash
cd frontend
npm install
npm run dev
```
- [ ] Frontend starts on http://localhost:5173
- [ ] Open in browser
- [ ] Dashboard loads
- [ ] Real publisher names visible (vocento, mondadori, etc.)
- [ ] Alerts show (if seeded)

## Performance Verification

### ☐ Query Performance

**Test Data Fetcher Speed**:
```python
import time
from datetime import datetime
from backend.agents.data_fetcher_real import _load_hourly_data, _get_hourly_metrics

df = _load_hourly_data()
ts = df['timestamp'].iloc[0]

start = time.time()
metrics = _get_hourly_metrics(df, ts, "GOOGLE")
elapsed = (time.time() - start) * 1000
print(f"Query time: {elapsed:.2f}ms")
```
- [ ] First query: <200ms
- [ ] Subsequent queries: <50ms

### ☐ Memory Usage

**Check Memory During Aggregation**:
- [ ] Peak memory < 4GB (use `top` or Activity Monitor)
- [ ] No out-of-memory errors

**Check Memory During Runtime**:
- [ ] Backend process < 1GB after cache loaded

## Troubleshooting

### ☐ If Aggregation Fails

- [ ] Check disk space: `df -h`
- [ ] Check source file permissions: `ls -l "/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/"`
- [ ] Check Python version: `python3 --version` (need 3.8+)
- [ ] Check dependencies: `pip install pandas pyarrow`
- [ ] Check logs: `cat /tmp/vna-dataintegration.log`
- [ ] Reduce batch size in `aggregate_parquet.py` if memory issues

### ☐ If Tests Fail

- [ ] Re-run aggregation: `python scripts/aggregate_parquet.py`
- [ ] Check file permissions: `ls -l data/baseline/`
- [ ] Verify file integrity: `python -c "import pandas as pd; pd.read_parquet('data/baseline/hourly_aggregated.parquet')"`
- [ ] Check Python path: `echo $PYTHONPATH`

### ☐ If Backend Shows Synthetic Data

- [ ] Verify parquet files exist: `ls -lh data/baseline/`
- [ ] Check backend logs for error messages
- [ ] Test import: `python -c "from backend.agents.data_fetcher_real import data_fetcher_agent"`
- [ ] Restart backend: `python -m backend.api.server`

## Rollback Plan

### ☐ If Integration Fails

To rollback to synthetic data:
1. [ ] Rename real data files: `mv data/baseline data/baseline.backup`
2. [ ] Restart backend (will auto-detect missing files)
3. [ ] Backend will use synthetic data
4. [ ] Debug and retry integration

To restore real data:
1. [ ] Rename backup: `mv data/baseline.backup data/baseline`
2. [ ] Restart backend

## Sign-Off

### Integration Complete
- [ ] All aggregation steps completed successfully
- [ ] All tests passing (4/4)
- [ ] Backend running with real data
- [ ] Frontend displaying real publisher names
- [ ] Performance acceptable (<500ms per query)
- [ ] No critical errors in logs

### Documentation Review
- [ ] Read `QUICK_START.md`
- [ ] Read `DATA_INTEGRATION.md`
- [ ] Read `INTEGRATION_SUMMARY.md`
- [ ] Understand data flow and architecture

### Next Steps Planned
- [ ] Schedule regular data refresh (weekly/monthly)
- [ ] Set up monitoring for data quality
- [ ] Plan alert threshold tuning
- [ ] Document operational procedures

---

**Date Completed**: _______________

**Completed By**: _______________

**Notes**:
```
[Add any issues encountered, workarounds, or observations]







```

---

## Quick Commands Reference

```bash
# Pre-integration
python scripts/verify_data_paths.py

# Full automated integration
chmod +x scripts/run_full_integration.sh
./scripts/run_full_integration.sh

# Manual integration
python scripts/aggregate_parquet.py          # 15-25 min
python scripts/test_integration.py           # 30 sec
python scripts/seed_alerts_from_parquet.py   # 2-5 min

# Verification
ls -lh data/baseline/
python scripts/test_integration.py

# Start application
python3 -m uvicorn backend.main:app --port 8000  # Terminal 1
cd frontend && npm run dev                       # Terminal 2 (if available)

# Monitor logs
tail -f /tmp/vna-dataintegration.log

# Test API
curl http://localhost:8000/api/health
```

## Support

If you encounter issues:
1. Check `/tmp/vna-dataintegration.log` for detailed error messages
2. Re-run `python scripts/test_integration.py` to identify failing component
3. Review troubleshooting section above
4. Consult `DATA_INTEGRATION.md` for detailed documentation
