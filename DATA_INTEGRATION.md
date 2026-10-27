# Data Integration Guide

This guide explains how to integrate real parquet data into the Value Network Alerting platform.

## Overview

The system now supports **real parquet data** with automatic fallback to synthetic data generation. The integration processes large datasets (150M+ rows) efficiently using chunk-based aggregation.

## Data Files

### Source Data

> **Path note:** The absolute paths below are on Stefano's operator machine
> (`/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/...`).
> Substitute your own local path to the raw parquet datasets. The aggregation
> script currently reads the operator path directly — when porting to another
> machine, parameterize via env var (suggested `VNA_DATASET_ROOT`) or edit
> `scripts/aggregate_parquet.py` accordingly.

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

---

## v1.3 PBI ↔ Sentinel Reproducibility Matrix

This matrix is the canonical lineage map for v1.3. Each row pairs a PBI metric × channel combination with its Sentinel source path and current match status. Phase 17.4 (`.planning/phases/17.4-d2-closure-tecnica-post-phase-17-3-downgrade/17.4-SUMMARY.md`) anchors Sample 1 byte-perfect; remaining rows close in Phase 19/20/21 v1.4 (`.planning/ROADMAP.md` §"v1.4 Milestone"). Authoritative requirement traceability: `.planning/REQUIREMENTS.md`.

**Column definitions:**

- **PBI source** — the upstream PBI / BigQuery field or report that produces the value Marco and the AdKaora team see in their dashboards.
- **Sentinel source** — the file, endpoint, or computed field that Sentinel reads for the same metric. Includes the code path where relevant.
- **Match status** — one of four states: `byte-perfect` (difference < ±1%, verified in code), `±X%` (within acceptable v1.3 tolerance), `structural gap` (no source data in Sentinel for this channel/metric today), or `pending v1.4` (code-ready but waiting on infrastructure, e.g. Athena credentials).
- **Closing phase** — the GSD phase that closed (✓) or will close the gap. Links point to `.planning/ROADMAP.md` for navigation.

| Metric | Channel | PBI source | Sentinel source | Match status | Closing phase |
|--------|---------|------------|-----------------|--------------|---------------|
| revenue_gross (hourly) | GOOGLE_ADEX | BigQuery `revenue_gross` for GOOGLE_ADEX channel + timestamp | `/api/metrics/network-totals?bypass_top50=true` reading `data/sentinel_db/hour_kpi.csv` via Path A | byte-perfect (€662.67 vs €662 PBI, ±1%) | [Phase 17.4](.planning/ROADMAP.md) ✓ |
| revenue_gross (hourly) | HEADER_BIDDING_MAGNITE | BigQuery `revenue_gross` for HBM channel + timestamp | currently synthetic (`data_source='synthetic_no_athena'`); future = Athena hourly extract | structural gap — no hourly source in `hour_kpi.csv` for HBM | [Phase 21 v1.4](.planning/ROADMAP.md) (pending) |
| revenue_gross (hourly) | HEADER_BIDDING_PUBMATIC | BigQuery `revenue_gross` for HBP channel + timestamp | currently synthetic; future = Athena | structural gap — same as HBM | [Phase 21 v1.4](.planning/ROADMAP.md) (pending) |
| revenue_gross (hourly) | TAM | BigQuery `revenue_gross` for TAM channel + timestamp | currently synthetic; future = Athena | structural gap (TAM deprecated upstream — `config/sell_type_proxy.yaml` annotated Phase 17.1) | [Phase 21 v1.4](.planning/ROADMAP.md) (pending) |
| revenue_gross (hourly) | DIRECT | BigQuery `revenue_gross` for Direct channel + timestamp | currently synthetic; future = Athena | structural gap | [Phase 21 v1.4](.planning/ROADMAP.md) (pending) |
| revenue_gross (hourly) | DEAL | BigQuery `revenue_gross` for Deal channel + timestamp | currently synthetic; future = Athena | structural gap | [Phase 21 v1.4](.planning/ROADMAP.md) (pending) |
| revenue_gross (hourly) | OPEN_BIDDING | BigQuery `revenue_gross` for OPEN_BIDDING channel + timestamp | currently synthetic; future = Athena | structural gap | [Phase 21 v1.4](.planning/ROADMAP.md) (pending) |
| revenue_gross (daily) | network total | BigQuery daily revenue sum across all 7 channels | `/api/metrics/network-totals?date=...` reading `data/sentinel_db/daily_kpi.csv` (Phase 11 hybrid) | ±0.17% (verified Phase 11 + Phase 17.4 RECONCILIATION) | [Phase 11](.planning/ROADMAP.md) ✓ |
| revenue_gross (daily, Mondadori Feb 2026) | network total | PBI €188k gross | aggregated parquet via `/api/metrics/revenue-status-24h` | ±2.5% (acceptable v1.3 band) | [Phase 11](.planning/ROADMAP.md) ✓ |
| impressions | GOOGLE_ADEX | BigQuery `impressions` for GOOGLE_ADEX | parquet column `impressions` in `hourly_aggregated.parquet` | byte-perfect for Sample 1 hour | [Phase 17.4](.planning/ROADMAP.md) ✓ |
| impressions | HBM/HBP/TAM/DIRECT/DEAL/OPEN_BIDDING | BigQuery `impressions` per channel | currently synthetic; future = Athena | structural gap | [Phase 21 v1.4](.planning/ROADMAP.md) (pending) |
| measurable_impressions | all channels | BigQuery `measurable_impressions` | parquet column `measurable_impressions` (preserved in ETL since Phase 08 SCHEMA-03 — was dropped pre-v1.3) | byte-perfect where parquet source aligned | [Phase 08](.planning/ROADMAP.md) ✓ |
| fill_rate (Mondadori Feb 2026) | network | PBI 35.2% = `measurable_impressions / bacino` | computed client-side from preserved `measurable_impressions` + `bacino` | within 1.5 ppt (per Phase 08 SCHEMA-03 regression test) | [Phase 08](.planning/ROADMAP.md) ✓ |
| fill_rate (per channel) | GOOGLE_ADEX | BigQuery `fill_rate` for GOOGLE_ADEX | derived client-side from parquet `measurable_impressions` + `bacino` per channel slice | within 1.5 ppt | [Phase 08](.planning/ROADMAP.md) ✓ |
| eCPM (per channel) | all channels | BigQuery `revenue / impressions × 1000` (denominator definition: gross or net depending on PBI report) | derived client-side; denominator definition documented in Gap Disclosure §eCPM/RPM | denominator difference flagged | [Phase 18](.planning/ROADMAP.md) (this phase — documented) |
| OM revenue (Mondadori Feb 2026) | OPEN_BIDDING + DIRECT subset reclassified as OM by PBI | PBI €90k OM revenue includes ~€40k Sentinel-classified DIRECT | parquet `channel_group ∈ {Open_Market}` per `config/sell_type_proxy.yaml` derivation | taxonomy delta (Sentinel €50k vs PBI €90k = expected, documented) | [Phase 17.1](.planning/ROADMAP.md) ✓ documented; resolution = N/A (intentional taxonomy difference) |

### Anchor: Sample 1 (GOOGLE_ADEX 2026-03-22 01:00)

- **PBI value:** €662.00 (BigQuery hourly snapshot, attached to Marco email 2026-05-19)
- **Sentinel value:** €662.67 (Phase 17.4 post-Path-A rewrite, live on CDN)
- **Tolerance:** ±1% → band `[€655.37, €669.30]` (€662.67 is inside; ratio 1.0010)
- **Data path (Sentinel):** `data/sentinel_db/hour_kpi.csv` → `_compute_network_totals_for_channel(channel='GOOGLE_ADEX', date='2026-03-22', hour=1, bypass_top50=True)` in `backend/api/routes.py` (via in-process call from `backend/agents/data_fetcher_real.py` GOOGLE_ADEX BACKTEST branch — see [Phase 17.4](.planning/phases/17.4-d2-closure-tecnica-post-phase-17-3-downgrade/17.4-SUMMARY.md) §"Plan 02")
- **alert_id:** `ALT-20260322-010000-P2`
- **DB row:** `data_source='real_csv'`, `revenue_current=662.67`, `deprecated=0`
- **Regression contract:** `scripts/test_alert_revenue_pbi_parity.py` INV-1 (Phase 17.4 D2CLOSE-04) + Phase 18 18-01 contract test `tests/contracts/test_parquet_db_ui.py` (HARD-01) parametrized GOOGLE_ADEX case
- **Closing phase:** Phase 17.4 (D2 Closure Tecnica) — shipped 2026-05-21

### Anchor: Sample 2 (HEADER_BIDDING_MAGNITE 2026-03-20 07:00)

- **PBI value:** €688.00 (BigQuery hourly snapshot, attached to Marco email 2026-05-19)
- **Sentinel value (current):** synthetic — `data_source='synthetic'` pre-Phase-17.4; post Phase 17.4 the alert is `deprecated=1` with reason `synthetic-era pre-H6-fix, Phase 21 Athena dependency` (Migration 006)
- **Tolerance:** ±1% → band `[€681.12, €694.88]` (will apply when Phase 21 lands real_athena value)
- **Data path (target, Phase 21 v1.4):** Athena hourly extract via `backend/connectors/athena.py` (code-ready post Phase 17.4 D2CLOSE-02 — `ALLOWED_CHANNEL_GROUPS` extended to include HEADER_BIDDING_MAGNITE; awaits production AWS credentials)
- **alert_id:** `ALT-20260320-070000-P2`
- **Regression contract:** `scripts/test_alert_revenue_pbi_parity.py` INV-5 (Phase 18 HARD-04, currently SKIP; will GREEN automatically when Phase 21 lands)
- **Closing phase:** Phase 21 v1.4 (Athena HBM/HBP/TAM Full Ingestion) — pending

---

## v1.3 PBI ↔ Sentinel Gap Disclosure

Eight known gap classes are documented below per CONTEXT.md D-12 (`.planning/phases/18-hardening-pbi-contract-tests-docs/18-CONTEXT.md`). Each entry maps the gap to the phase that closed it (or will close it). Authoritative requirement IDs in `.planning/REQUIREMENTS.md`; phase order in `.planning/ROADMAP.md`.

### Gap 1 — OM (Open Market) revenue taxonomy delta

PBI's "Open Market" classification includes ~€40k of revenue that Sentinel classifies as `DIRECT` per `config/sell_type_proxy.yaml`. This is an intentional taxonomy difference, not a measurement error. PBI groups by deal-vs-no-deal at the auction layer; Sentinel groups by `channel_group` at the ETL layer. The Sentinel `OPEN_BIDDING` channel maps only to exchange-traded inventory; `DIRECT` covers reserved placements that PBI may classify inside Open Market depending on the report view.

- **Closing phase:** Phase 17.1 (Publisher Mapping Correction) — documented via `config/sell_type_proxy.yaml` annotation block + Marco's email verbatim cross-reference (MAP-06)
- **Impact:** Mondadori Feb 2026 OM revenue: Sentinel €50k vs PBI €90k (~44% delta). Reconciles when Sentinel applies PBI's auction-layer reclassification — not in v1.3 scope.
- **Reference:** `.planning/REQUIREMENTS.md` §MAP-06 + `.planning/phases/17.1-publisher-mapping-correction/17.1-SUMMARY.md`

### Gap 2 — eCPM / RPM denominator definitions

eCPM = revenue / impressions × 1000. PBI sometimes reports gross-revenue / impressions, sometimes net-revenue (post rev-share 60%) / impressions, depending on the report. Sentinel exposes both via the gross/net toggle (CORR-03, shipped Phase 14). For per-report PBI parity, use the denominator that matches the specific PBI dashboard being compared. The `REV_SHARE_FACTOR=0.6` constant in `backend/api/routes.py` governs net-revenue derivation. RPM (Revenue Per Mille) may additionally differ from eCPM depending on whether PBI uses requests or filled impressions in the denominator — this is a PBI report-level choice, not a Sentinel implementation gap.

Sentinel's eCPM display formula: `eCPM_gross = revenue_current / impressions_current * 1000` (gross default). Net: `eCPM_net = revenue_current * REV_SHARE_FACTOR / impressions_current * 1000`. Both are client-side computations using the same underlying revenue and impressions fields.

- **Closing phase:** Phase 18 (this phase) — documented here; no code change required
- **Impact:** Side-by-side gross + net display (CORR-03) lets the operator pick the denominator at view time; no PBI parity failure attributable to denominator definition alone.
- **Reference:** `.planning/REQUIREMENTS.md` §CORR-03 + Phase 14 SUMMARY

### Gap 3 — Hourly YoY synthetic vs measured (Phase 17.3 H6 root cause + Phase 17.4 forward fix)

Pre-Phase-17.3, BACKTEST mode in `backend/agents/data_fetcher_real.py` had a tz-mismatch bug: `current_ts` was tz-aware while parquet timestamps were tz-naive; pandas comparison silently returned False; fallback to synthetic data fired without warning. Both Sample 1 and Sample 2 of Marco's audit ran into this. Phase 17.3 landed the +13-line fix (H6 root cause); Phase 17.4 closed Sample 1 byte-perfect via Path A (`/api/metrics/network-totals` extension with `bypass_top50=True`), Sample 2 awaits Phase 21 Athena ingestion. Migration 006 marks all pre-fix synthetic-era alerts with `deprecated=1`.

- **Closing phase (root cause):** Phase 17.3 (Alert Revenue Calc Audit) — shipped 2026-05-21
- **Closing phase (Sample 1 forward fix):** Phase 17.4 (D2 Closure Tecnica) — shipped 2026-05-21
- **Closing phase (Sample 2 + remaining channels):** Phase 21 v1.4 (pending)
- **Impact:** Pre-fix synthetic alerts (~200 total) marked `deprecated=1` with reason `synthetic-era pre-H6-fix` via Migration 006 (Phase 17.4 D2CLOSE-03).
- **Reference:** `.planning/REQUIREMENTS.md` §AUDIT-01/02/03 + §D2CLOSE-01..04 + Phase 17.3 + 17.4 SUMMARYs

### Gap 4 — Fill rate denominator (measurable_impressions)

PBI fill_rate = `measurable_impressions / bacino` (35.2% for Mondadori Feb 2026). Pre-v1.3, `etl_csv_to_parquet.py:187` dropped `measurable_impressions` from the parquet schema on the assumption it was redundant with `impressions`. This assumption was incorrect: `measurable_impressions` tracks viewability-qualifying inventory (a filtered subset of total impressions), and `bacino` represents total ad requests. The fill rate ratio `measurable_impressions / bacino` is the standard programmatic fill metric, distinct from `impressions / bacino` (coverage). Phase 08 SCHEMA-03 restored the column; fill rate now within 1.5 ppt of PBI.

The column `measurable_impressions` is a first-class schema field validated in `backend/db/models.py` CHECK constraints and covered by the HARD-01 contract tests (Phase 18 18-01).

- **Closing phase:** Phase 08 (Schema Migration + ETL Extensions) — shipped 2026-04-23
- **Impact:** Fill rate matches PBI 35.2% within 1.5 ppt (verified by `scripts/test_mondadori_fill_rate_regression.py`).
- **Reference:** `.planning/REQUIREMENTS.md` §SCHEMA-03 + Phase 08 SUMMARY

### Gap 5 — Top-50 publisher filter (Phase 17.4 Path A resolution)

`daily_aggregated.parquet` applies a top-50-by-revenue publisher filter at the ETL layer (Phase 11 D1 hybrid). For PBI-parity at the alert-detail layer this caused 21% under-reporting on Sample 1 (€521 vs PBI €662). Phase 17.4 Path A reads `hour_kpi.csv` directly via `_compute_network_totals_for_channel` (`bypass_top50=True`), yielding byte-perfect €662.67 for GOOGLE_ADEX. The Path A branch is gated GOOGLE_ADEX-only by design — defense-in-depth via Phase 18 18-03 INV-6 source-grep regression that asserts no other channel inadvertently enables Path A.

- **Closing phase:** Phase 17.4 (D2 Closure Tecnica) — shipped 2026-05-21
- **Impact:** Sample 1 byte-perfect; daily network totals continue to use top-50-filtered parquet for dashboard performance (acceptable v1.3 trade-off, documented in Phase 11 D1).
- **Reference:** `.planning/REQUIREMENTS.md` §D2CLOSE-01 + Phase 17.4 SUMMARY §"Plan 02" + Phase 18 plan 18-03 (INV-6 guard)

### Gap 6 — 200 synthetic-era deprecated alerts (Phase 17.4 backfill split)

Phase 09 backfilled 238 alerts pre-v1.3. Post Phase 17.3 H6 fix, 38 GOOGLE_ADEX backfill alerts were rewritten to `data_source='real_csv'` (Phase 17.4 `scripts/rewrite_backfill_google_adex_post_17_4.py`). 1 GOOGLE_ADEX alert (`ALT-20260323-010000-P1`, 2026-03-23 01:00) was 1h beyond `hour_kpi.csv` EOF and was deprecated instead of rewritten. 199 non-GOOGLE_ADEX backfill alerts were marked `deprecated=1` with reason `synthetic-era pre-H6-fix, Phase 21 Athena dependency` (Migration 006). Total deprecated: 200.

- **Closing phase:** Phase 17.4 (D2 Closure Tecnica) — shipped 2026-05-21
- **Impact:** 38 GOOGLE_ADEX alerts now real_csv; 200 alerts deprecated with audit trail preserved (data_source unchanged on the 199 non-GOOGLE_ADEX rows to preserve forensic trail). Rewrite decision for the 199 deprecated alerts owned by Phase 21 v1.4 + operator R-05 sign-off.
- **Reference:** `.planning/REQUIREMENTS.md` §D2CLOSE-03 + Phase 17.4 BACKFILL-REWRITE-REPORT.md + Migration 006

### Gap 7 — Phase 21 v1.4 Athena pending (HBM, HBP, TAM, DIRECT, DEAL, OPEN_BIDDING + 199 deprecated rewrite candidate)

6 of the 7 channels have no hourly source in `data/sentinel_db/hour_kpi.csv` (which is GOOGLE_ADEX-only per the upstream CSV export pipeline). Their hourly revenue values are currently synthetic (post-Phase-17.4 alerts are tagged `data_source='synthetic_no_athena'`). Phase 17.4 D2CLOSE-02 made the Athena connector code-ready: `ALLOWED_CHANNEL_GROUPS` in `backend/connectors/athena.py` was extended from 2 to 8 channels (GOOGLE_ADEX, OPEN_BIDDING, HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC, TAM, DIRECT, DEAL, and the legacy GOOGLE alias). Activation awaits production AWS credentials provisioned in Phase 21 v1.4.

Once Phase 21 ships, `scripts/test_alert_revenue_pbi_parity.py` INV-5 (HBM Sample 2 case, currently `@pytest.mark.skip`) will un-skip automatically — it is already written to assert €688.00 ±1% band `[€681.12, €694.88]`. The 199 deprecated alerts will be rewrite candidates (operator R-05 sign-off required for the rewrite; deprecation state is safe to preserve indefinitely).

- **Pending phase:** Phase 21 v1.4 (Athena HBM/HBP/TAM Full Ingestion)
- **Impact:** Sample 2 HBM byte-perfect closure pending. 6 channels remain synthetic in BACKTEST mode. Email Marco reply gated on Phase 21 close (9/9 of Marco's audit points resolved).
- **Reference:** `.planning/REQUIREMENTS.md` §D2CLOSE-02 + `.planning/ROADMAP.md` §"v1.4 Milestone" Phase 21 + Phase 17.4 SUMMARY §"Plan 03"

### Gap 8 — V1 Channel granularity (Diretta / Deal / Open Market as separate UI entities)

Marco's V1 audit point: Sentinel currently displays `OPEN_BIDDING`, `DIRECT`, `DEAL` etc. as separate alerts but the UI grouping does not expose Diretta/Deal/Open Market as first-class entities for filter and drill-down at the Demand level. Within the Open Market bucket, channel shifts (e.g. Equative migrating from AdEx to Demand Manager) generate false positives. Phase 19 v1.4 will refactor the channel granularity model (design meeting with Iolanda required before scoping).

- **Pending phase:** Phase 19 v1.4 (V1 Channel Granularity Refactor)
- **Impact:** Marco audit V1 point unresolved until Phase 19. Email Marco reply gated.
- **Reference:** `.planning/ROADMAP.md` §"v1.4 Milestone" Phase 19 + Marco email 2026-05-19 V1 point

### v1.4 milestone dependency summary

Gaps 7 and 8 (Athena + channel granularity) are v1.4 scope. Their resolution is required to close all 9 points in Marco's 2026-05-19 audit email and unblock the formal reply. The dependency chain is:

1. **Phase 19** — V1 channel granularity refactor (design + implementation, Iolanda sign-off required)
2. **Phase 20** — V2 Open Market distribution study (UI breakdown for shift analysis)
3. **Phase 21** — Athena HBM/HBP/TAM activation (production AWS credentials + 199 alert rewrite decision)
4. **Email Marco** — 9/9 audit points confirmed resolved, formal reply drafted and sent

Until Phase 21 ships, `scripts/test_alert_revenue_pbi_parity.py` carries Sample 2 as a pinned-skip (`@pytest.mark.skip`) that self-activates when Athena credentials are available.

### Update protocol

When a new gap is discovered or a pending gap closes:

1. Append a new H3 subsection here following the same structure (description / closing phase / impact / reference).
2. Update the corresponding row in the "v1.3 PBI ↔ Sentinel Reproducibility Matrix" section above.
3. Update `.planning/REQUIREMENTS.md` traceability.
4. Reference the new entry from the closing phase's SUMMARY.md.

**Gap lifecycle:**

- **Open** — gap discovered, root cause documented, no fix yet. Add subsection immediately upon discovery so the gap is visible in the lineage record.
- **In-progress** — fix scoped in a planned phase, closing phase listed as "pending". The Reproducibility Matrix row shows `structural gap` or `pending v1.4`.
- **Closed** — fix shipped, match status updated to `byte-perfect` or `±X%`, closing phase marked with ✓. The gap subsection is never deleted — it remains as an audit trail with the closing phase and ship date.

**Who updates this file:** Any GSD executor plan that closes a gap must include `DATA_INTEGRATION.md` in its `files_modified` list and update both the corresponding matrix row and the gap subsection within the same atomic commit. Phase SUMMARY.md files cross-reference this document per D-13.

This file is the lineage record for v1.3 closure and the foundation document for the Marco audit reply (gated Phase 21 close per `.planning/ROADMAP.md`).
