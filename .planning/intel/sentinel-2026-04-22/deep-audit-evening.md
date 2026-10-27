# Deep Audit Evening — 2026-04-22

**Trigger**: Stefano ha richiesto analisi profonda (prior round bollato come shallow: 2-3 min per agent).
**3 agents paralleli**, budget 500 MB RSS, read-only, durata 3-7 min ciascuno.
**Constraint**: "procedete con il parquet che c'è, non mettete in mezzo altri dati".

---

## SMOKING GUN #1 — Top-50 publisher filter (Agent 1)

`scripts/etl_csv_to_parquet.py:70-85` chiama `find_top50_publishers()` e filtra **sia `daily_kpi.csv` che `daily_adrequests.csv`** ai top 50 publisher per revenue.

**Evidenza numerica** (2026-01-12 GOOGLE_ADEX):
- Upstream `daily_kpi.csv` ALL publishers: **€27,245.63 gross** (matcha PBI)
- Parquet top-50 only: **€23,024.16 gross** (−15.5%)
- Dashboard displayed (NET, post 60/40 share): **~€13,814**

Il gap PBI €27.2k vs Dashboard €13.8k = 49% è la **somma di 2 layer**:
1. Top-50 filter: −15%
2. Net vs Gross display: −40%

## SMOKING GUN #2 — sell_type proxy DERIVABILE (Agent 2)

Agent 2 ha trovato mapping validato da `config/alerting_rules.yaml:84-91`:

```
Open_Market    = {GOOGLE_ADEX, OPEN_BIDDING}
Header_Bidding = {HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC}
Direct         = {DIRECT}
Deal           = {DEAL}
Other          = {TAM}
```

**Zero dependency upstream**. Derivabile in runtime o aggiungibile come colonna parquet.

## SMOKING GUN #3 — `measurable_impressions` droppato (validazione live)

`etl_csv_to_parquet.py:187` droppa `measurable_impressions` (presente upstream in `daily_kpi.csv`). Senza questa colonna la UI **NON PUÒ** computare la fill rate allineata a PBI (35.2%, che sta tra `imp/bacino 41.75%` e `viewable/bacino 31.42%`).

## SMOKING GUN #4 — Bacino dedup GIÀ corretto

**Sorpresa positiva**: il dedup in `backend/api/publisher_routes.py:203-206` funziona. Prior analisi che riportava "Mondadori 296M vs PBI 133M" era ERRATA (dedup non applicato).

Numeri live verificati:
```
Mondadori Feb 2026, dedup bacino:
  All channels:        133,242,026  ← matcha PBI 133M (+0.2%)
  OM proxy (G_ADEX+OB): 133,573,005  ← matcha (+0.4%)
  GOOGLE_ADEX only:    133,642,311  ← matcha (+0.5%)
```

Il fatto che tutti e tre matchino è logico: bacino upstream è **channel-agnostic** (no channel_group in `daily_adrequests.csv`), replicato per canale nel join.

## Altri finding Agent 1 (deep)

- ✅ `channel_gorup` typo è fixed da ETL:231 (`df.rename({"channel_gorup": "channel_group"})`)
- ✅ Revenue share 0.60 uniforme, zero per-publisher override (`config/revenue_share.yaml`)
- ✅ Hourly CSV sum == Daily CSV sum per GOOGLE_ADEX 2026-01-12 = €27,245 (consistency upstream ok)
- ⚠ Mondadori è DUE publisher_id: `Mondadori` (17,022 rows) + `Mondadori_npa` (2,764 rows) — GDPR non-consent variant. Da considerare in UI.
- ⚠ `floor_cpm` column sempre NaN (allocated in schema, never populated) — dead column
- ⚠ `webview` → `WEB` environment mapping perde fidelity (agent:ETL:176)
- ⚠ `publisher_mapping.csv` ha 431 publishers ma parquet ne ha solo 49-50 (top-50 filter)

## Altri finding Agent 2 (pipeline trace)

- `daily_kpi.csv` columns: `row_id, date, ad_unit_id_1, environment, country_criteria_id, channel_group, revenue_gross, impressions, measurable_impressions, viewable_impressions, clicks, ctr, viewability, ecpm` (14 cols)
- `daily_adrequests.csv` columns: `row_id, date, ad_unit_id_1, environment, country_criteria_id, ad_requests` (6 cols, **NO channel_group**)
- `hour_kpi.csv` columns: con typo `channel_gorup` → fixed ETL:231
- `hour_adrequests.csv` columns: **NO country_criteria_id** → hourly parquet ha `geo_cluster = "ALL"` hardcoded ETL:251 → geo breakdown impossibile in hourly
- Viewability values > 1.0 (>100%) osservati in `hour_adrequests.csv` → errore misurazione upstream

### PBI↔Sentinel reproducibility matrix (Agent 2 Part F)

Fully reproducible (9): revenue gross/net, coverage, eCPM, RPM, CTR, viewability, margin, geo, env
Approximable (1): sell_type via channel_group proxy (95% confidence)
Unreproducible (2): device_format, deal_type subclassification

## Altri finding Agent 3 (UI deep)

### 🔴 Invented values in frontend

- `TriageSection.tsx:31-32`: `baselineBacino = Math.round(totalBacino * (revenueRatio * 0.95))` + `baselineCoverage = Math.min(avgCoverage + 0.05, 0.95)` — magic constants 0.95/0.05, NON dal backend. P0 trust-breaker.
- `TriageSection.tsx:46,53`: 2 delta% che dipendono dai baseline inventati (cascade failure)

### 🔴 UI scope non dichiarato

- `RevenueStatus24h.tsx`: mostra solo GOOGLE_ADEX ma non lo dice all'utente
- `KpiCards.tsx`: label hardcoded in inglese, bloccano i18n WIP
- `PublishersPage.tsx`: `avgFillRate = simple average`, non weighted — misleading
- `ContributorsSection`: top-3 derived client-side invece che backend

### 🟢 5 filtri derivabili con SOLO parquet attuale (niente upstream)

1. Open Market proxy (channel_group IN G_ADEX+OB)
2. Gross/Net revenue toggle (dati già nei campi revenue + revenue_gross)
3. Geo cluster filter (5 valori già presenti)
4. Environment drill-down (già in alert.environment_split)
5. Publisher tier (A/B/C via cumulative bacino sorting client-side)

### ✅ Quello che già funziona bene

- Alert filters in URL (useAlertFilters hook): shareable, persistent
- Response caching con React Query: 30s auto-refresh
- Skeleton loading states
- i18n structure (44 keys, en.ts + it.ts)

## Numeric validation — Mondadori Feb 2026

Eseguita inline dopo confirm Stefano D1=(D) hybrid:

```
                        bacino       fill    rev_gross   rev_net   eCPM g  RPM g
ALL channels:      133,242,026    41.75%   €192,651   €115,591   €3.46   €1.45
Viewable/bacino:                   31.42%
OM proxy (G_A+OB): 133,573,005    17.95%   €41,786    €25,072    €1.74   €0.31
GOOGLE_ADEX only:  133,642,311    16.48%   €39,444    €23,666    €1.79   €0.30

PBI reference:     133,000,000    35.2%    €90,000 OM / €188,000 total   €1.51   €0.51
```

### Interpretazione

1. **Bacino** ✅ matcha PBI esattamente
2. **Revenue gross TOTAL** ✅ matcha (€192 vs €188, +2.5%)
3. **Fill rate 35.2%** 🔴 sta tra imp/bacino (41.75%) e viewable/bacino (31.42%) → molto probabilmente è `measurable_impressions / bacino` che la ETL droppa
4. **OM Revenue €90k** 🔴 nessuna combinazione channel arriva a €90k (max €50k includendo G_A+OB+HB+TAM) → **taxonomy delta** tra sistemi: PBI include probabilmente parte di DIRECT in OM
5. **eCPM/RPM gross** 🔴 differenze grosse (nostro €3.46 vs PBI €1.51; nostro €1.45 vs PBI €0.51) → denominatori diversi

## Consequenze per v1.3 roadmap

### Nuove requirements aggiunte

- **SCHEMA-03**: Conservare `measurable_impressions` in ETL (rimuovere dalla drop list ETL:187) — abilita fill rate PBI-match
- **SCHEMA-04**: Aggiungere `sell_type_proxy` come colonna parquet (derivato da channel_group via mapping Agent 2)
- **API-01**: Endpoint `/metrics/network-totals` che legge upstream CSV via pyarrow streaming (bypassa top-50 filter, matcha PBI totals)
- **API-02**: Query param `?sell_type=...` su `/publishers/top` e `/alerts`
- **CORR-03**: Gross/Net revenue display side-by-side + label esplicita
- **CORR-04**: Channel scope badge (`RevenueStatus24h`, `RevenueByChannel`, `KpiCards`)
- **CORR-05**: Reference period label su ogni metric card
- **CORR-06**: Filter state in page titles + URL params for Publishers page
- **CORR-07**: Diagnostic empty states (RevenueTrendChart, altri charts)
- **CORR-08**: Rimuovere client-side heuristic TriageSection (consumare `baseline_bacino`, `baseline_coverage` dal backend)
- **CORR-09**: i18n keys mancanti in `KpiCards.tsx:72-111` (bloccano translation WIP)
- **CORR-10**: Error boundaries su chart components (RevenueTrendChart, EnvironmentBarChart, GeoBreakdownPieChart)
- **DOC-01**: Documentare in `DATA_INTEGRATION.md` i gap strutturali PBI↔Sentinel (OM revenue taxonomy, eCPM/RPM denominator differences)
- **CLEAN-01**: Rimuovere `floor_cpm` da schema (dead column) o popolare da upstream
- **CLEAN-02**: Gestire `Mondadori` + `Mondadori_npa` in UI (aggregazione logica o disclosure)

### Decisioni 10/10 (confermate da Stefano)

- **D1 = (D) hybrid**: mantieni top-50 parquet + endpoint `/network-totals` upstream-based (API-01)
- **D2 = (c) Gross+Net side-by-side** con label "gross (net €X post rev-share 60%)"
- **D3 = backfill da parquet attuale** (top-50, post D1 hybrid)
- **D4 = SÌ sell_type proxy** via channel_group mapping

## Memory + effort stimato

- Agent 1: 5.2 min, 38 tool calls, peak 250 MB
- Agent 2: 4.4 min, 28 tool calls, <500 MB
- Agent 3: 2.8 min, 39 tool calls, <50 MB
- Total: 12.4 min, ~105 tool calls, tutti read-only, zero OOM risk

Effort v1.3 aggiornato: ~40-50h (era 35-40h) per nuove CORR + SCHEMA-03/04 + API-01/02.
