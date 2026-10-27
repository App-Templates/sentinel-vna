# Scripts Directory

This directory contains data integration and utility scripts for the Value Network Alerting platform.

## Scripts Overview

### 1. `aggregate_parquet.py` ⭐ **MAIN SCRIPT**
**Purpose**: Process raw parquet data (315M rows) into optimized aggregated files

**Usage**:
```bash
python scripts/aggregate_parquet.py
```

**What it does**:
- Reads 3 source parquet files (hourly, daily channel, daily adrequests)
- Processes large files in 500K row chunks (memory-efficient)
- Normalizes publisher names, maps geo clusters and channels
- Aggregates by relevant dimensions (hour/day, publisher, channel, geo, environment)
- Creates 3 optimized parquet files in `data/baseline/`

**Runtime**: ~15-25 minutes (one-time)

**Output**:
- `data/baseline/hourly_aggregated.parquet` (~25 MB)
- `data/baseline/daily_channel_aggregated.parquet` (~45 MB)
- `data/baseline/daily_adrequests_aggregated.parquet` (~38 MB)

**Logs**: `/tmp/vna-dataintegration.log`

---

### 2. `seed_alerts_from_parquet.py`
**Purpose**: Populate database with real historical alerts

**Usage**:
```bash
python scripts/seed_alerts_from_parquet.py
```

**What it does**:
- Loads last 7 days of hourly aggregated data
- Runs full anomaly detection workflow every 2 hours
- Generates real alerts (A0, A1, A2, A3) based on actual patterns
- Inserts alerts into SQLite database

**Runtime**: ~2-5 minutes

**Prerequisites**: Must run `aggregate_parquet.py` first

---

### 3. `verify_data_paths.py`
**Purpose**: Verify source data files exist before aggregation

**Usage**:
```bash
python scripts/verify_data_paths.py
```

**What it does**:
- Checks if 3 source parquet files exist
- Shows file sizes and metadata (if pyarrow installed)
- Checks if aggregated files already exist
- Provides next steps guidance

**Runtime**: <1 second

**Use case**: Run before aggregation to ensure source files are accessible

---

### 4. `test_integration.py`
**Purpose**: End-to-end integration testing

**Usage**:
```bash
python scripts/test_integration.py
```

**What it does**:
- **Test 1**: Verify aggregated files exist
- **Test 2**: Load data and verify structure
- **Test 3**: Test data fetcher agent
- **Test 4**: Run full workflow with real data

**Runtime**: ~10-30 seconds

**Use case**: Run after aggregation to validate integration

---

### 5. `run_full_integration.sh` 🚀 **AUTOMATED PIPELINE**
**Purpose**: One-command complete integration

**Usage**:
```bash
chmod +x scripts/run_full_integration.sh
./scripts/run_full_integration.sh
```

**What it does**:
1. Verifies source data paths
2. Prompts for confirmation
3. Runs aggregation (~20 min)
4. Runs integration tests
5. Optionally seeds alerts

**Runtime**: ~20-35 minutes (full pipeline)

**Use case**: First-time setup or complete re-integration

---

## Quick Start

### Option 1: Automated (Recommended)
```bash
./scripts/run_full_integration.sh
```

### Option 2: Manual
```bash
# Step 1: Verify
python scripts/verify_data_paths.py

# Step 2: Aggregate
python scripts/aggregate_parquet.py

# Step 3: Test
python scripts/test_integration.py

# Step 4: Seed (optional)
python scripts/seed_alerts_from_parquet.py
```

## File Dependencies

```
Source Data (external)
    ↓
verify_data_paths.py → (checks existence)
    ↓
aggregate_parquet.py → Creates data/baseline/*.parquet
    ↓
test_integration.py → Validates integration
    ↓
seed_alerts_from_parquet.py → Populates database
```

## Requirements

**Python Packages**:
```bash
pip install pandas pyarrow
```

**Source Files** (must exist):
- `/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_hourly/data.parquet`
- `/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_daily/data_channel.parquet`
- `/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_daily/data_adrequests.parquet`

## Logs

All scripts log to:
- **Console**: Real-time progress
- **File**: `/tmp/vna-dataintegration.log`

View logs:
```bash
# Watch in real-time
tail -f /tmp/vna-dataintegration.log

# Search for errors
grep ERROR /tmp/vna-dataintegration.log

# View aggregation progress
grep "Batch" /tmp/vna-dataintegration.log
```

## Troubleshooting

### "Source data files not found"
**Solution**: Verify files exist at the correct paths
```bash
ls -lh "/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_hourly/"
ls -lh "/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_daily/"
```

### "Memory error during aggregation"
**Solution**: Close other applications or reduce batch_size in `aggregate_parquet.py`:
```python
batch_size = 250000  # Reduce from 500000
```

### "Tests failing"
**Solution**: Re-run aggregation and check logs
```bash
python scripts/aggregate_parquet.py
cat /tmp/vna-dataintegration.log | grep ERROR
```

### "Permission denied" for .sh script
**Solution**: Make executable
```bash
chmod +x scripts/run_full_integration.sh
```

## Expected Output

### Aggregation Success
```
[timestamp] ========================================================================
[timestamp] TASK 1: AGGREGATING HOURLY DATA
[timestamp] ========================================================================
[timestamp] Loaded 4,300,000 rows
[timestamp] Aggregated to 150,000 rows
[timestamp] Saved to: data/baseline/hourly_aggregated.parquet (25.3 MB)
[timestamp] ✓ HOURLY AGGREGATION COMPLETE

[timestamp] ========================================================================
[timestamp] TASK 2: AGGREGATING DAILY CHANNEL DATA (156M rows)
[timestamp] ========================================================================
[timestamp] Processing in batches of 500,000 rows
[timestamp]   Batch 10: processed 5,000,000 rows...
[timestamp]   Batch 20: processed 10,000,000 rows...
...
[timestamp] Total processed: 156,000,000 rows
[timestamp] Saved to: data/baseline/daily_channel_aggregated.parquet (45.2 MB)
[timestamp] ✓ DAILY CHANNEL AGGREGATION COMPLETE

[timestamp] ========================================================================
[timestamp] TASK 3: AGGREGATING DAILY ADREQUESTS DATA (159M rows)
[timestamp] ========================================================================
[timestamp] Processing in batches of 500,000 rows
[timestamp] Total processed: 159,000,000 rows
[timestamp] Saved to: data/baseline/daily_adrequests_aggregated.parquet (38.7 MB)
[timestamp] ✓ DAILY ADREQUESTS AGGREGATION COMPLETE

[timestamp] ✓ ALL AGGREGATION TASKS COMPLETED SUCCESSFULLY
```

### Test Success
```
✓ TEST 1 PASSED: All aggregated files exist
✓ TEST 2 PASSED: All data files loaded successfully
✓ TEST 3 PASSED: Data fetcher working correctly
✓ TEST 4 PASSED: Workflow ran successfully with real data

Total: 4/4 tests passed
```

## Performance

| Script | Input Size | Runtime | Output |
|--------|------------|---------|--------|
| verify_data_paths.py | - | <1s | Console output |
| aggregate_parquet.py | 315M rows | 15-25 min | 3 parquet files (~108 MB) |
| test_integration.py | 1.1M rows | 10-30s | Test results |
| seed_alerts_from_parquet.py | 7 days | 2-5 min | SQLite records |
| run_full_integration.sh | Full pipeline | 20-35 min | All of the above |

## Data Flow

```
External Source Files (17 GB)
    ↓
aggregate_parquet.py
    ↓ [chunk processing]
Aggregated Files (108 MB)
    ↓
    ├─→ test_integration.py (validates)
    ├─→ seed_alerts_from_parquet.py (populates DB)
    └─→ Backend (real-time queries)
```

## Best Practices

1. **First Time Setup**:
   - Use `run_full_integration.sh` for guided setup
   - Watch logs: `tail -f /tmp/vna-dataintegration.log`
   - Verify tests pass before using in production

2. **Regular Updates**:
   - Re-run `aggregate_parquet.py` when source data updates
   - No need to re-run tests if source schema unchanged
   - Consider incremental updates for production

3. **Development**:
   - Use `verify_data_paths.py` to check setup
   - Use `test_integration.py` to validate changes
   - Keep aggregated files backed up

4. **Troubleshooting**:
   - Always check `/tmp/vna-dataintegration.log` first
   - Re-run failing script with verbose logging
   - Test individual components with test_integration.py

## Documentation

For detailed information:
- **Quick Start**: `../QUICK_START.md`
- **Integration Guide**: `../DATA_INTEGRATION.md`
- **Summary**: `../INTEGRATION_SUMMARY.md`
- **Checklist**: `../INTEGRATION_CHECKLIST.md`

## Support

For issues:
1. Check logs: `cat /tmp/vna-dataintegration.log`
2. Verify files: `ls -lh data/baseline/`
3. Test components: `python scripts/test_integration.py`
4. Review documentation in `../DATA_INTEGRATION.md`
