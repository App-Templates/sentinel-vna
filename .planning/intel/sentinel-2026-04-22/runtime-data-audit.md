# Data Freshness & Runtime Reads Audit

**Agent:** Explore subagent (read-only, pyarrow-only, 500 MB budget)
**Date:** 2026-04-22

## Executive summary

**Il platform legge dati FRESCHI (max date 2026-03-23).** Lo "stale" percepito è dovuto a un single-point bug: lo schema `vna_alerts.db` CHECK constraint rifiuta canali v1.2 → ogni INSERT fallisce silenziosamente.

## Full Data Inventory

| Path | Size | mtime | Max Date | Schema | Rows |
|---|---|---|---|---|---|
| `data/baseline/daily_aggregated.parquet` | 196.8 MB | Mar 26 14:54 | **2026-03-23** | 18 cols (v1.2) | 5,047,383 |
| `data/baseline/hourly_aggregated.parquet` | 13 MB | Mar 26 14:54 | **2026-03-23** | 18 cols (v1.2) | 171,700 |
| `data/baseline/v1/daily_channel_aggregated.parquet` | 3.4 MB | Feb 11 20:36 | 2026-01-22 | 7 cols (v1.0) | 650,814 |
| `data/baseline/v1/daily_adrequests_aggregated.parquet` | 4.0 MB | Feb 11 20:38 | 2026-01-22 | 5 cols (v1.0) | — |
| `data/baseline/v1/hourly_aggregated.parquet` | 5.4 MB | Feb 11 20:34 | 2026-01-22 | — | — |
| `data/sentinel_db/daily_kpi.csv` | 1.3 GB | Mar 23 12:11 | **2026-03-23** | 14 cols | — |
| `data/sentinel_db/hour_kpi.csv` | 85 MB | Mar 23 13:03 | **2026-03-23** | 13 cols | — |
| `data/sentinel_db/daily_adrequests.csv` | 474 MB | Mar 23 12:56 | **2026-03-23** | 6 cols | — |
| `data/sentinel_db/hour_adrequests.csv` | 53 MB | Mar 23 12:18 | **2026-03-23** | 6 cols | — |
| `data/vna_alerts.db` | 1.4 MB | Apr 18 14:07 | 2026-01-22 | SQLite | 33 alerts |

## Runtime Reads

**CRITICAL FINDING: Il runtime è wired sui file freschi (v1.2).**

| Component | Parquet File | Date Range |
|---|---|---|
| `backend/agents/data_fetcher_real.py:27-28` | `data/baseline/daily_aggregated.parquet` | 2025-02-16 .. **2026-03-23** |
| — | `data/baseline/hourly_aggregated.parquet` | 2025-12-23 .. **2026-03-23** (line 25) |
| `backend/api/routes.py:80` | `data/baseline/daily_aggregated.parquet` | 2025-02-16 .. **2026-03-23** |
| — | `data/baseline/hourly_aggregated.parquet` (line 79) | 2025-12-23 .. **2026-03-23** |
| `backend/api/publisher_routes.py:20-21` | `data/baseline/daily_aggregated.parquet` | 2025-02-16 .. **2026-03-23** |
| `backend/api/admin_routes.py:55-59` | `data/baseline/daily_aggregated.parquet` | 2025-02-16 .. **2026-03-23** |

**Stale references (v1.0, NOT USED IN PRODUCTION):**
- `scripts/regenerate_alerts.py:26` — legge `daily_channel_aggregated.parquet` (ad-hoc seeding, non pipeline live)
- `scripts/aggregate_parquet.py` — genera v1.0 files (storico/archivio)

## Orphan Datasets

| Path | Status | Purpose |
|---|---|---|
| `data/baseline/v1/*.parquet` (3 files) | ORPHAN | v1.0 schema archive, 12.8 MB |
| `scripts/regenerate_alerts.py` | ORPHAN | One-off alert DB seeding (reads stale v1.0) |
| `scripts/aggregate_parquet.py` | BUILD ARTIFACT | Legacy ETL, not runtime |
| `scripts/etl_csv_to_parquet.py` | BUILD ARTIFACT | v1.2 ETL, not runtime (ran once at commit time) |

## Config / Env

- `datasource_config.json`: `"active_source": "parquet"` (hardcoded path, not dynamic)
- **No .env overrides**: tutti BASE_DIR / DATA_DIR hardcoded
- **No version manifest**: nessun `data/latest` symlink o key `DATASET_VERSION`
- ETL config: `etl_csv_to_parquet.py` explicit `DATA_DIR = ... / "data" / "sentinel_db"` input, `baseline` output

## Alert DB State

| Metric | Value | Implication |
|---|---|---|
| Latest alert timestamp | **2026-01-22T14:39:40** | **STALE — 2 mesi indietro rispetto ai dati** |
| Alert count total | 33 | — |
| Alerts after 2026-01-22 | **0** | Nessun alert generato post v1.0 cutoff |
| DB schema channel_group CHECK | `('GOOGLE', 'OPEN_BIDDING')` | **Hardcoded v1.0; v1.2 ha 7 canali** |
| `pipeline_runs` last 10 days | 2590 recent runs (through 2026-04-22) | **Pipeline esegue ma non salva alert** |

**Root cause della staleness**: schema DB accetta solo 2 valori channel_group (v1.0). Pipeline runs OK (pipeline_runs popolato), ma **alert generation fallisce su CHECK constraint violation** quando incontra canali v1.2 (GOOGLE_ADEX, DEAL, DIRECT, HEADER_BIDDING_*, TAM) → nessun alert salvato.

## v1.2 Dataset Reality

**Freshest dataset**: `data/baseline/daily_aggregated.parquet`
- Max date: **2026-03-23**
- Channels: **7** (DEAL, DIRECT, GOOGLE_ADEX, HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC, OPEN_BIDDING, TAM)
- Publishers: **50** (top-50 from etl_csv_to_parquet.py)
- Schema: 18 columns (v1.2 unified)

**Wired into runtime**: ✓ YES
- `data_fetcher_real.py:25-28`
- `routes.py:79-80`
- `publisher_routes.py:20-21`

**Alert generation**: ✗ BLOCKED
- DB schema incompatibile
- Pipeline fails silently on CHECK violation

## Verdict

**Stefano è parzialmente corretto: la UI alert è stale (last 2026-01-22).** Ma **data infrastructure non è stale**. v1.2 ha deployed fresh data (through 2026-03-23). **Runtime backend correttamente wired**.

**Il bottleneck è lo schema mismatch**: `vna_alerts.channel_group` CHECK accetta solo v1.0 channels. v1.2 pipeline → 7 canali → INSERT fallisce → silent.

**Live UI behavior**:
- Dashboard / publishers pages → leggono parquet fresco (2026-03-23), mostrano numeri aggiornati
- Alerts page → vuota / ferma al 22 gen (nessun nuovo alert salvato)
- Backend anomaly detection logic **esegue** (pipeline_runs lo conferma), ma insert fallisce

**To fix**:
1. Migrate alerts schema → accept v1.2 channels (P0-A)
2. Regenerate alerts for 2026-01-23 onwards (P0-B)
3. Add silent-failure monitoring (P0-C)

## Memory footprint
Peak RSS ~375 MB. Free+Inactive 5.0 GB (ben sopra budget 500 MB).
