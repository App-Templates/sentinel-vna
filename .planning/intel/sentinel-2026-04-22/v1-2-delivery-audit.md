# v1.2 Delivery Audit

**Agent:** Explore subagent (read-only, pyarrow-only, 500 MB budget)
**Date:** 2026-04-22
**Commit audited:** `7de84ab feat(v1.2): new IT dataset, 7 channels, 50 publishers, A8 margin alert, leading indicators`

## Executive summary

**v1.2 è STATO shippato**. Le conclusioni dell'analista precedente ("v1.2 non è wired") erano errate — aveva auditato `daily_channel_aggregated.parquet` (v1.0 stale) invece di `daily_aggregated.parquet` (v1.2 fresh).

## What v1.2 committed

### Backend anomaly detection
- `backend/agents/anomaly_detector.py`:
  - `_detect_gross_margin_alert()` (70 lines, A8 rule)
  - `_detect_leading_indicators()` (80 lines, CTR/viewability P2-WATCH)
  - `_detect_cross_channel()` (80 lines, DIRECT↑ vs Open Market↓ pattern)

### ETL
- **Nuovo script**: `scripts/etl_csv_to_parquet.py` (338 lines)
  - Input: 6 CSVs da `data/sentinel_db/` (daily_kpi, daily_adrequests, hour_kpi, hour_adrequests, publisher_mapping, country_mapping)
  - Output: 2 parquet v2 con 18-field schema
  - Logic: top 50 publishers by revenue_gross, 60/40 revenue share default
  - Compute: revenue_gross, ecpm, rpm, ctr, viewability, gross_margin_pct, floor_cpm

### Data files (generated at commit time)
- `data/baseline/daily_aggregated.parquet`: 197 MB, 5,047,383 rows, **7 canali**, range 2025-02-16 → **2026-03-23**
  - Channel distribution (sample): GOOGLE_ADEX 120k rows, HEADER_BIDDING_MAGNITE 60k, DIRECT 46k, OPEN_BIDDING 44k, TAM 34k, HEADER_BIDDING_PUBMATIC 13k, DEAL 10k
- `data/baseline/hourly_aggregated.parquet`: 13 MB, 171,700 rows, **GOOGLE_ADEX only**, range 2025-12-23 → **2026-03-23**
- `data/baseline/v1/*`: backup pre-v1.2 (3 files, 12.8 MB, orphan)

### Config
- `config/revenue_share.yaml` (nuovo): 60/40 default + placeholder per-publisher overrides
- `config/alerting_rules.yaml` espanso:
  - `gross_margin_alert`: enabled, 25% threshold, P1, baseline 7 weeks
  - `leading_indicator`: enabled, [ctr, viewability], -15% threshold, P2-WATCH
  - `cross_channel_detection`: enabled
  - `top_publishers`: 50 entries (Mondadori, Mediamond, AdGage_Vocento, …, EdAlliance)
  - Channel list aggiornato: GOOGLE_ADEX, HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC, TAM, DIRECT, DEAL + legacy GOOGLE, OPEN_BIDDING

### Backend wiring
- `backend/agents/data_fetcher_real.py`: paths a `daily_aggregated.parquet` + 9 nuove metriche in `_get_hourly_metrics()`
- `backend/agents/contributor_analyzer.py`: rpm/ctr/viewability per publisher
- `backend/agents/triage_classifier.py`: A8 handling
- `backend/db/models.py`: A8 enum + DB constraint
- `backend/api/routes.py` + `publisher_routes.py`: 7-channel-aware filtering

### Frontend
- 7 nuovi componenti (ChannelBreakdownSection, LeadingIndicatorPanel, ChannelFilter, KpiCards, RevenueByChannel, etc.)
- Alert/Publisher detail pages enriched
- Docs expanded

## 7-Channel Wiring: Status

### On-disk parquet
- `daily_aggregated.parquet`: ✓ 7 canali presenti + 18 campi v1.2 completi
- `hourly_aggregated.parquet`: solo GOOGLE_ADEX (limite sorgente `hour_kpi.csv`, non del codice)

### Scripts
- `scripts/aggregate_parquet.py`: **STALE**, v1.0 2-channel (GOOGLE + OPEN_BIDDING), legge da dataset esterno Value Network — **NON è il pipeline attivo**
- `scripts/etl_csv_to_parquet.py`: ✓ v1.2 pipeline attivo, produce 7-channel daily + 1-channel hourly

### Backend read paths
- `data_fetcher_real.py:27-28`: ✓ punta a `daily_aggregated.parquet`
- `routes.py:80`: ✓ `DAILY_PARQUET = daily_aggregated.parquet`
- `publisher_routes.py:20-21`: ✓ entrambi i file reindirizzati a `daily_aggregated.parquet`
- Filter logic: ✓ `df["channel_group"] == channel` con lista 7 canali

### Gap
- **Hourly single-channel**: limite della sorgente dati (hour_kpi.csv ha solo GOOGLE_ADEX), non abbandono del progetto. Il commit message prometteva "7-channel ETL" per daily, che È delivered. Doc gap su hourly.
- **Legacy script (aggregate_parquet.py)**: non è stato rimosso, può confondere chi fa audit superficiale.

## A8 + 50 publishers + leading indicators

### A8 Gross Margin Alert
- ✓ Code: `anomaly_detector.py:586-639`
- ✓ Config: `alerting_rules.yaml` enabled, 25% threshold, P1
- ✓ DB: `models.py:30` enum + line 184 CHECK
- ✓ Data: `gross_margin_pct` computed in parquet (formula `(revenue_gross - revenue) / revenue_gross * 100`)

### 50 publishers
- ✓ `config/alerting_rules.yaml` lines 155+: 50 entries
- ✓ Selection: `etl_csv_to_parquet.py:83` top 50 by total `revenue_gross`
- ✓ Revenue coverage: ~86.8% (Pareto 80/20)

### Leading indicators
- ✓ Code: `anomaly_detector.py:641-707`
- ✓ Wiring: called at line 990, stored in state line 992
- ✓ Config: `alerting_rules.yaml:76-83`
- ✓ Data: parquet has `ctr` and `viewability` columns

## Runtime Dataset Selection

- **No dynamic config key** (no env var `DATASET_VERSION` o simile)
- Paths hardcoded in `data_fetcher_real.py:25-28` (BASE_DIR / "data" / "baseline" / ...)
- No `data/latest` symlink / manifest

Runtime reads (confirmed):
- Daily/channel: `data/baseline/daily_aggregated.parquet`
- Hourly: `data/baseline/hourly_aggregated.parquet`

## Verdict

**v1.2 was: FULLY SHIPPED (daily) + PARTIALLY LIMITED (hourly by source)**

Gap tra intent e reality:
- **Principale**: hourly è single-channel per limite sorgente, non per codice. Doc da aggiornare.
- **Secondario**: `aggregate_parquet.py` stale lasciato nel repo (confuse audit).
- **Terzo**: nessun monitoring sul successo del pipeline (bug correlato: CHECK constraint drift, separate doc).

## Memory footprint
- Peak RSS: ~3 MB (streaming parquet reads con pyarrow predicate pushdown)
- Files loaded: nessuno (solo schema + metadata)
- Files streamed: daily_aggregated.parquet (5M rows via filters), hourly schema check
