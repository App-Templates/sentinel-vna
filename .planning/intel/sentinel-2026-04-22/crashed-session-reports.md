# Reports from crashed session (2026-04-22 10:00-11:00)

The morning session (session id `467f64da-e81f-4f1e-9624-3130ecc3d8cb`) crashed at ~11:00 UTC due to OOM (~100GB pressure) caused by `pd.read_csv` su 1.3 GB `daily_kpi.csv` senza column pruning. 4 analyst subagents had been launched. Reports recovered dai subagent jsonl.

**⚠ IMPORTANTE**: Il report "Parquet Consistency Audit" (analyst D) contiene una conclusione errata perché ha auditato `daily_channel_aggregated.parquet` (v1.0 stale) invece di `daily_aggregated.parquet` (v1.2 fresh). Le conclusioni di questo analyst sono rettificate in `v1-2-delivery-audit.md` e `runtime-data-audit.md`.

---

## Analyst 1 — Backend Data Correctness (12:20-12:22)

5 bug specifici con file:line citation.

### 1. Dashboard AdEx Revenue hourly/daily not matching PBI
- **File**: `backend/agents/data_fetcher_real.py:650`, `backend/api/routes.py:188`
- **Root cause**: mapping "Ad Exchange" → `channel_group = "GOOGLE"` collassa sorgente. Split GOOGLE + OPEN_BIDDING raddoppia righe. Se PBI include sell_type/deal_type subset, totali divergono.
- **Fix hint**: verificare row count parquet vs PBI source

### 2. Alert ALT-2026 €25.9k vs PBI Jan 12 €27.2k
- **File**: `backend/agents/data_fetcher_real.py:650`, `backend/db/models.py:85`
- **Root cause**: `revenue_current` = single-hour sum (data_fetcher_real.py:589 `current_ts.replace(minute=0, second=0, microsecond=0)`). Alert ALT fired Jan 13 08:57 → current_ts=08:00 Jan 13, sum single hour only (line 81). PBI "Jan 12 Open Market" è full-day. Mismatch 1 ora vs 1 giorno.
- **Fix hint**: aggregate 24 hours, align sell_type

### 3. Top Publisher Mondadori Feb bacino 133M vs 366M
- **File**: `backend/api/publisher_routes.py:203-210`
- **Root cause**: bacino dedup `groupby(pub, date, env, geo).channel.nunique()` divide by n_channels, assume split bilanciato (falso). No `sell_type` filter (schema non ha sell_type per DATA_INTEGRATION.md:18-23).
- **Fix hint**: add sell_type column + filter line 179

### 4. Alert "Current Revenue" reference period missing
- **File**: `backend/db/models.py:85`, `data_fetcher_real.py:589`
- **Root cause**: revenue_current salvato senza metadata del periodo (single-hour), UI mostra senza label. Users assume full day.
- **Fix hint**: aggiungi `revenue_period_label` field

### 5. Google-labeled alerts trend empty
- **File**: `backend/api/routes.py:188`
- **Root cause**: `df["channel_group"] == channel` filter on "GOOGLE" (legacy alias models.py:42). Se il parquet non ha righe `channel_group="GOOGLE"` per (publisher_id, date), mask vuoto.
- **Fix hint**: debug log filtered rows count, fallback message

## Cross-cutting patterns

- **Timezone**: timestamps round a UTC hour, PBI usa Europe/Rome. No conversion → ±1h drift.
- **Sell type / deal type filtering**: schema v1.0 non ha sell_type (DATA_INTEGRATION.md:19-23). PBI segmenta by sell_type. Non confrontabile.
- **Publisher ID matching**: normalizzazione "AdGage_" prefix/lowercase ma no dedup validation.
- **Bacino dedup**: assume split bilanciato tra canali (falso).

---

## Analyst 2 — Frontend UI Correctness (12:20-12:22)

5 UI issues con file:line + fix proposto.

### 1. "Current Revenue" no reference period
- **File**: `frontend/src/components/alerts/RevenueStatusSection.tsx:33-37`
- **Endpoint**: `/alerts/{alertId}` (AlertDetailPage.tsx:59, client.ts:94-102)
- **Hidden**: revenue_current è per l'ora dell'alert (`alert.timestamp`) ma UI non mostra il contesto temporale. Label "7-week avg" esiste per baseline ma non per current.
- **Fix**: aggiungere subtitle con `new Date(alert.timestamp).toLocaleDateString(...)`

### 2. Revenue Trend 7 Weeks chart empty for Google alerts
- **File**: `frontend/src/components/charts/RevenueTrendChart.tsx:42-47`
- **Endpoint**: `/alerts/{alertId}/trend` (routes.py:171-178)
- **Hidden**: empty state generico "No revenue trend data available". User non sa se è genuine empty, channel filter silently excluding, o API error.
- **Fix**: empty state diagnostico, check backend routes.py:169-219 per channel filter

### 3. Hourly chart GOOGLE_ADEX only, UI hides it
- **Files**: `RevenueStatus24h.tsx:76-228`, `RevenueByChannel.tsx:17-143`, `KpiCards.tsx:12-114`
- **Hidden**: comment `RevenueByChannel:33-34` dice "Hourly data only covers GOOGLE_ADEX — show total until IT delivers multi-channel". UI non ha badge prominente.
- **Fix**: badge "Google AdX only" visibile, non gray text

### 4. Triage Classification UI — client-side baseline estimate
- **File**: `frontend/src/components/alerts/TriageSection.tsx:19-56`
- **Hidden**: lines 29-32
  ```ts
  const revenueRatio = alert.revenue_current ? alert.revenue_baseline / alert.revenue_current : 1
  const baselineBacino = Math.round(totalBacino * (revenueRatio * 0.95))
  const baselineCoverage = Math.min(avgCoverage + 0.05, 0.95)
  ```
  `baselineBacino` e `baselineCoverage` NON sono dal backend — **heuristic client-side**. Non documentato, appare equally authoritative come "Current". PBI ha true baseline → mismatch.
- **Fix**: footnote "baseline estimated from environment split" OR rimuovere + aggiungere `alert.baseline_bacino` al backend

### 5. Top Publisher filter state invisible
- **File**: `frontend/src/pages/PublishersPage.tsx`
- **Endpoint**: `useTopPublishers(year, month?, limit=50)` → `/publishers/top_{year}_{month:02d}` o `/publishers/top_{year}` (client.ts:231-239)
- **Hidden**: selected month/year in `<select>`, ma table title non include suffix "(February 2026)". Nessun `sell_type` visible filter.
- **Fix**: title suffix with active filter state, expose sell_type dropdown

## Systemic UX findings

- **Reference periods** encoded in data ma mai rendered as readable metadata
- **Channel/segment restrictions** in code comments, non prominent UI
- **Client-side calcs** appear equally authoritative as backend data
- **Filter state** in selects ma non in result headers

---

## Analyst 3 — Sentinel vs Power BI Reconciliation (12:53-12:58)

Per-number delta vs PBI.

### T1 — Jan 12 2026 Open Market Reconciliation
PBI ref: 14M impressions, €27.2k revenue

| Source | Revenue | Δ€ | Δ% | Impressions | Δ Impr | Δ% Impr |
|---|---|---|---|---|---|---|
| PowerBI (ref) | €27,200 | — | — | 14,000,000 | — | — |
| Daily (GOOGLE) | €25,638 | -€1,561 | -5.7% | 10,199,508 | -3.8M | -27.1% |
| Daily (GOOGLE+OPEN) | €36,272 | +€9,072 | +33.4% | 13,885,260 | -115k | -0.8% |
| Hourly (GOOGLE_ADEX) | €13,814 | -€13,386 | -49.2% | 17,326,766 | +3.3M | +23.8% |

**Interpretation**: GOOGLE+OPEN_BIDDING matches impressions ±1% but overshoots revenue 33%. GOOGLE alone undershoots. Hourly inverted. Sentinel channel logic differs from PBI "AdEx" definition.

**⚠ Nota**: questa analisi usava parquet v1.0 stale. Con v1.2 (7 channels) i numeri sarebbero diversi — Analyst D (sotto) e questi report sono obsoleti per valutare gap corrente v1.2. Restano validi per capire la logica di divergenza storica.

### T2 — Mondadori Feb 2026 Reconciliation
**Cannot measure — no Feb 2026 data in v1.0 parquet (cutoff 2026-01-22)**. 
*(v1.2 correction: daily_aggregated.parquet HA dati Feb-Mar. Il gap reale è backfill alert, non data staleness.)*

### T3 — Alert ALT-20260113 one-day check
Alert revenue_current €25,927.18 matches Jan 13 GOOGLE daily revenue (**not Jan 12 as user assumed**). Alert è seed-generated batch 2026-02-15 dal `scripts/regenerate_alerts.py` che aggrega per giornata da `daily_channel_aggregated.parquet` (v1.0).

### T4 — YoY sanity
YoY computed on-the-fly da `routes.py:701-739`. Prior year stesso ISO week, avg 7 weekdays, Δ% vs current. Se parquet underreports absolute, YoY ratio resta consistent → masks level error.

## Hot spots (v1.0 context)

1. Feb 2026 data missing (v1.0 parquet cutoff). **Fixed in v1.2** ✓
2. Jan 12 revenue mismatch by channel (PBI "AdEx" definition ambiguity). **Partially fixed in v1.2** (7 channels available, ma PBI mapping needs explicit doc)
3. Hourly-daily inversion (separate pipeline logics). **Partially fixed in v1.2** (unified 18-field schema), ma hourly still single-channel.

---

## Analyst 4 — Internal Parquet Consistency Audit (re-run 2026-04-22 afternoon)

⚠ **Questo analyst ha auditato `daily_channel_aggregated.parquet` (v1.0) credendo fosse il file corrente. Le conclusioni su "3 pipeline disaccoppiate" sono ERRATE per v1.2.** Il runtime usa `daily_aggregated.parquet` (v1.2 fresh).

Correzioni:
- NOT "ETL stopped running" — ETL è one-shot script, ha generato correttamente il parquet v1.2 con max date 2026-03-23
- NOT "mapping lossy" — v1.2 ha tutti e 7 i canali, no collapse
- NOT "sentinel_db ingested but not connected" — sentinel_db È la source dell'ETL v1.2

Report di analyst 4 utile solo come snapshot dei file v1.0 stale (non il runtime).

---

## Recovered conclusions that hold

- **Client-side triage baseline heuristic** (`revenueRatio * 0.95`) è un vero gap (confirmed da Analyst 2 + 3 indipendenti). **P0-D valido.**
- **Reference period mancante su alert UI** (P0-4) — parzialmente fixato in WIP, still incomplete.
- **Sell_type filter mancante** (P0-2) — ancora aperto, ma meno urgente del silent-failure DB bug.
- **Silent failure ipotizzato** — confermato da runtime-data-audit (2590 pipeline_runs, 0 alerts saved since 2026-01-22) → **P0-A schema + P0-B backfill + P0-C monitoring**.
