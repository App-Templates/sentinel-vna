# Phase 11: Network Totals Endpoint + Filter API + Server-Side Baseline — Research

**Researched:** 2026-04-28
**Domain:** FastAPI endpoint design, pyarrow CSV streaming, parquet filter pushdown, alert schema extension
**Confidence:** HIGH (tutto verificato su codice e dati live, zero assunzioni training)

---

## Project Constraints (from CLAUDE.md)

- **R-13:** qualità 10/10 production-grade obbligatoria — zero quick-and-dirty
- **R-05:** nessun deploy, push o azione su stato condiviso senza OK esplicito Stefano
- **R-04:** chirurgico — ogni step con rollback verificabile, dry-run prima di live
- **R-03:** ogni cambiamento logico = 1 commit atomico, rollback indipendente
- **Anti-pattern PROIBITI:** No `git stash` su `data/vna_alerts.db*`, no Path A (refresh JSON), no confondere `[x]` con "live"
- **Sentinel = value-network-alerting**, non sentinel-spot

---

## 1. Phase Summary

Phase 11 introduce tre nuovi endpoint FastAPI che indirizzano le root cause RC-(a) e RC-(e) identificate dall'audit triplo del 2026-04-28. L'endpoint `GET /api/metrics/network-totals` bypassa il filtro top-50 del parquet leggendo direttamente `data/sentinel_db/daily_kpi.csv` via `pyarrow.csv` per restituire totali PBI-comparabili. Il query param `sell_type` su `/api/publishers/top` applica il mapping `channel_group → sell_type_proxy` già presente in parquet (SCHEMA-04, Phase 08). Il payload degli alert viene esteso con due campi flat `baseline_bacino` e `baseline_coverage` — già calcolati server-side e presenti in `environment_split_json`, ma non esposti come campi top-level, costringendo il frontend a reinventarli con euristica.

**Raccomandazione primaria:** Implementare nell'ordine API-01 → API-02 → API-03, perché API-01 è il più critico per la PBI-parity e API-03 sblocca Phase 12 (TriageSection.tsx rimozione euristica).

---

## 2. Truth-Source Alignment

### RC-(e): client-side heuristics in TriageSection.tsx

[VERIFIED: `frontend/src/components/alerts/TriageSection.tsx:29-32`]

```typescript
const revenueRatio = alert.revenue_current ? alert.revenue_baseline / alert.revenue_current : 1
const baselineBacino = Math.round(totalBacino * (revenueRatio * 0.95))   // INVENTATO
const baselineCoverage = Math.min(avgCoverage + 0.05, 0.95)              // INVENTATO
```

Entrambi i valori non provengono dal DB. La soluzione (API-03) espone `baseline_bacino` e `baseline_coverage` come campi top-level in `AlertDetail`. I valori ESISTONO GIA' in `environment_split_json` per ogni alert (verificato su ALT-20260123-010000-P2: `bacino_baseline`, `coverage_baseline` per ogni environment). API-03 è un'addizione di schema + logica di aggregazione server-side — non richiede nuovo calcolo da zero.

### RC-(c): NET vs GROSS revenue senza label

[VERIFIED: `AUDIT-A-NUMBERS-FORENSICS.md:Bug2`]

`/api/publishers/top` espone `total_revenue` (NET, post 60% rev-share) senza label. La colonna `revenue_gross` è nel parquet ma NON nel response JSON (linee 274-292 di `publisher_routes.py`). RC-(c) è territorio principalmente di Phase 13 (CORR-03 gross+net side-by-side), ma API-01 deve SEMPRE restituire `revenue_gross` come campo primario per la PBI-parity (il gap €27.2k vs €25.9k è esattamente questo: PBI mostra gross, Sentinel mostra net).

### Mapping email Vito → Phase 11

| Lamentela email | Root Cause | API Phase 11 |
|----------------|------------|--------------|
| #1 Dashboard hourly Revenue AdEx | RC-(a) top-50 | API-01 network-totals bypassa top-50 |
| #2 10M impressioni vs 14M PBI | RC-(a) + RC-(e) | API-01 (upstream); API-03 (triage baseline) |
| #3 €25.9k vs €27.2k gross Jan 12 | RC-(a) top-50 + gross/net | API-01 restituisce `revenue_gross` da raw CSV |
| #4b fill rate | RC-(e) bacino baseline inventato | API-03 `baseline_coverage` server-side |

---

## 3. Existing Code Map

| File | Ruolo | Rilevanza Phase 11 |
|------|-------|-------------------|
| `backend/api/routes.py` | Router principale, prefix `/api` | API-01 va qui (nuovo endpoint sotto `/metrics`) |
| `backend/api/publisher_routes.py` | Router `/api/publishers`, in-memory cache parquet | API-02 estende `/top` con `sell_type` query param |
| `backend/api/schemas.py` | Pydantic models request/response | API-03 aggiunge `baseline_bacino` e `baseline_coverage` a `AlertDetail` |
| `backend/main.py` | FastAPI app, registra tutti i router | Nessuna modifica (router già inclusi) |
| `data/baseline/daily_aggregated.parquet` | Parquet v1.2 top-50, 20 col, max_date=2026-03-23 | Fonte per API-02 (ha `sell_type_proxy`) |
| `data/sentinel_db/daily_kpi.csv` | Raw upstream CSV, TUTTI i publisher, nessun filtro | Fonte per API-01 (bypassa top-50) |
| `data/sentinel_db/daily_adrequests.csv` | Ad requests upstream, nessun channel_group | Non usato direttamente da API-01 (kpi.csv sufficiente) |
| `config/sell_type_proxy.yaml` | Mapping `channel_group → sell_type_proxy`, SSOT | Utilizzato da API-02 per tradurre il param `sell_type` |
| `config/alerting_rules.yaml:84-91` | `cross_channel_detection.channels_open_market` | Riferimento di design (NON il mapping principale — vedi §7) |
| `frontend/src/components/alerts/TriageSection.tsx:29-32` | Euristica `revenueRatio*0.95` + `avgCoverage+0.05` | Da eliminare in Phase 12 dopo API-03 |
| `backend/db/models.py` | Schema DB, CHECK constraints | API-03 richiede migration DB (nuovi campi alerts) |
| `scripts/etl_csv_to_parquet.py` | ETL che produce il parquet con `sell_type_proxy` | Nessuna modifica in Phase 11 |

---

## 4. API-01 Design: `/api/metrics/network-totals`

### Problema verificato

[VERIFIED: `data/sentinel_db/daily_kpi.csv` vs `data/baseline/daily_aggregated.parquet` — test Bash live]

Per Jan 12 2026, GOOGLE_ADEX:
- **Raw CSV (tutti i publisher):** `revenue_gross = €27,245.63`, `impressions = 14,009,820`
- **Parquet top-50:** `revenue_gross = €23,024.16`, `impressions = 11,491,192`
- **Gap dovuto a filtro top-50:** ~15.5% revenue, ~18% impressioni
- **PBI:** `€27.2k` gross Open Market (Jan 12) — corrisponde al raw CSV GOOGLE_ADEX

L'endpoint DEVE leggere `daily_kpi.csv` direttamente per PBI-parity. Il parquet top-50 NON è sufficiente.

### Signature endpoint

```
GET /api/metrics/network-totals?date=YYYY-MM-DD&channel=CHANNEL_GROUP
```

Query params:
- `date` (required): data in formato `YYYY-MM-DD`
- `channel` (required): uno tra `GOOGLE_ADEX`, `OPEN_BIDDING`, `GOOGLE_ADEX+OPEN_BIDDING` (Open_Market), ecc. Alternativa: accettare `sell_type=Open_Market` e applicare la mapping.

### Logica di calcolo

```python
# Pseudocodice — da implementare in routes.py

@router.get("/metrics/network-totals")
def network_totals(date: str, channel: str, sell_type: Optional[str] = None):
    # 1. Leggi daily_kpi.csv con pyarrow.csv.read_csv (streaming, projection pushdown)
    #    Filtra: date == target_date AND channel_group IN [channels]
    # 2. Aggrega: revenue_gross.sum(), impressions.sum(), bacino (da daily_adrequests.csv join se serve)
    # 3. Applica revenue_share se serve net (opzionale per ora, gross è primario per PBI)
    # 4. Restituisce: {date, channel, revenue_gross, revenue_net, impressions, ...}
```

### Strategia di lettura CSV (R-13 compliance)

[VERIFIED: `scripts/etl_csv_to_parquet.py:169-178` — pattern chunked read esistente nel progetto]

Il progetto usa già `pd.read_csv(..., chunksize=500_000)` per leggere i CSV da 6.2M righe. Per API-01 usare `pyarrow.csv.read_csv` con `ConvertOptions` e `ReadOptions` per column projection (solo `date`, `channel_group`, `revenue_gross`, `impressions`) — più efficiente, no full materialization.

```python
import pyarrow.csv as pa_csv
import pyarrow.compute as pc

def _read_kpi_for_date_channel(target_date: str, channels: list[str]) -> pa.Table:
    """Stream daily_kpi.csv con column projection. Ritorna solo le colonne necessarie."""
    convert_opts = pa_csv.ConvertOptions(
        column_types={
            "revenue_gross": pa.float64(),
            "impressions": pa.int64(),
            "measurable_impressions": pa.int64(),
        }
    )
    read_opts = pa_csv.ReadOptions(block_size=64 * 1024 * 1024)  # 64MB blocks
    tbl = pa_csv.read_csv(
        KPI_CSV_PATH,
        read_options=read_opts,
        convert_options=convert_opts,
    )
    # Filtra per date e channel
    mask = pc.and_(
        pc.equal(tbl["date"], target_date),
        pc.is_in(tbl["channel_group"], pa.array(channels))
    )
    return tbl.filter(mask)
```

**ATTENZIONE:** daily_kpi.csv = ~6.2M righe, ~500MB stimati. Il caricamento completo + filtro è accettabile per un endpoint a bassa frequenza (dashboard load). Cache in-memory (pattern già usato in `routes.py` con `_hourly_cache`) può essere aggiunta in Wave 2 se i test mostrano latenza >2s.

### Success Criterion verificato

[VERIFIED via test Bash live]: Raw CSV Jan 12 GOOGLE_ADEX = €27,245.63 gross
- PBI target = €27,200 (approssimato dall'email)
- Delta: (27245.63 - 27200) / 27200 × 100 = **+0.17%** → dentro il 2% richiesto ✅

Il criterio "2%" è soddisfatto leggendo `daily_kpi.csv` raw senza filtro top-50.

### Nota sull'interpretazione "upstream-streaming"

[ASSUMED da ROADMAP.md wording "upstream-streaming endpoint"] — Il termine non indica HTTP streaming (chunked response), bensì "legge dal CSV upstream (raw, pre-ETL)" invece del parquet derivato. Conferma: REQUIREMENTS.md API-01 dice "reads `data/sentinel_db/*.csv` upstream via `pyarrow.csv.read_csv` streaming". L'endpoint ritorna una risposta JSON normale (non SSE/chunked HTTP).

---

## 5. API-02 Design: sell_type query param su `/api/publishers/top`

### Verifica claim "95% confidence confirmed by config:alerting_rules.yaml:84-91"

[VERIFIED: `config/alerting_rules.yaml:84-91`]

```yaml
cross_channel_detection:
  enabled: true
  direct_increase_threshold_pct: 20
  open_market_drop_threshold_pct: -10
  channels_open_market:
  - GOOGLE_ADEX
  - OPEN_BIDDING
  channel_direct: DIRECT
```

**Questo blocco NON è il mapping sell_type_proxy.** Definisce solo "Open Market" per il cross-channel detection alert. Il mapping canonico è in `config/sell_type_proxy.yaml`.

[VERIFIED: `config/sell_type_proxy.yaml`]

```yaml
Open_Market:
  - GOOGLE_ADEX
  - OPEN_BIDDING
  - GOOGLE          # legacy alias
Header_Bidding:
  - HEADER_BIDDING_MAGNITE
  - HEADER_BIDDING_PUBMATIC
Direct:
  - DIRECT
Deal:
  - DEAL
Other:
  - TAM
```

Il ROADMAP afferma "95% confidence confirmed by config:alerting_rules.yaml:84-91". Questa formulazione è **PARZIALMENTE IMPRECISA**: la confidence del 95% si riferisce alla decisione D4 (Phase 08) che il mapping `channel_group → sell_type_proxy` cattura il 95% dei casi reali. Il file canonico è `sell_type_proxy.yaml`, non `alerting_rules.yaml:84-91`. La linea :84-91 è un subset (solo Open_Market vs Direct). Il planner deve usare `sell_type_proxy.yaml` come SSOT.

[VERIFIED: `data/baseline/daily_aggregated.parquet`] — La colonna `sell_type_proxy` è già presente con 5 valori:
`['Deal', 'Direct', 'Header_Bidding', 'Open_Market', 'Other']`

### Implementazione API-02

```python
# In publisher_routes.py — estendere get_top_publishers:

@router.get("/top")
def get_top_publishers(
    request: Request,
    limit: int = Query(35, ge=1, le=200),
    year: int = Query(2025),
    sell_type: Optional[str] = Query(None),  # NUOVO: Open_Market|Header_Bidding|Direct|Deal|Other
):
    df = _load_adrequests()
    df_year = df[df["date"].dt.year == year]
    
    # API-02: filtro sell_type_proxy
    if sell_type is not None:
        valid_sell_types = ["Open_Market", "Header_Bidding", "Direct", "Deal", "Other"]
        if sell_type not in valid_sell_types:
            raise HTTPException(400, f"sell_type must be one of {valid_sell_types}")
        if "sell_type_proxy" in df_year.columns:
            df_year = df_year[df_year["sell_type_proxy"] == sell_type]
        else:
            raise HTTPException(503, "sell_type_proxy column not available in parquet")
    # ... resto invariato
```

**Nota importante per API-02:** Il campo `sell_type_proxy` è già presente nel parquet (verificato) — nessuna migrazione ETL necessaria. Il filtro è una singola riga di pandas. La risposta deve includere `sell_type_filter` nel payload per la trasparenza UI.

### Impatto su altri endpoint

Per API-02 completo (REQUIREMENTS.md): il param `sell_type` va aggiunto anche a:
- `/api/alerts` (via `get_alerts` in `operations.py` — richiede colonna `sell_type_proxy` nella tabella alerts, che NON esiste; **in Phase 11 si limita a `/api/publishers/top`** dove il parquet ha già il campo)
- `/api/metrics/revenue-status-24h` (parquet hourly ha solo `Open_Market` sell_type_proxy; aggiungibile ma triviale)

**Phase 11 scope raccomandato per API-02:** solo `/api/publishers/top` + API-01. Gli altri endpoint con `sell_type` vanno in Phase 12 (triage server-side).

---

## 6. API-03 Design: baseline_bacino e baseline_coverage server-side

### Scoperta critica

[VERIFIED: `data/vna_alerts.db` SQL query live]

Il campo `environment_split_json` negli alert già contiene `bacino_baseline` e `coverage_baseline` per ogni environment:

```json
{
  "WEB": {
    "bacino_current": 95318,
    "bacino_baseline": 95534,
    "coverage_current": 0.7584,
    "coverage_baseline": 0.8201
  },
  "AMP": { ... }
}
```

**Il calcolo server-side GIA' ESISTE** — i valori sono generati da `backend/agents/data_fetcher_real.py` al momento della creazione dell'alert. Il problema è che questi valori restano sepolti nel JSON blob e il frontend (`TriageSection.tsx:20-32`) li ignora, ricalcolando euristica propria.

**API-03 = aggiungere 2 campi top-level all'`AlertDetail` schema, popolati aggregando `environment_split_json`.**

### Schema migration richiesta (DB)

```sql
-- Migration 005 — Phase 11 API-03
-- Aggiunge baseline_bacino e baseline_coverage come colonne top-level
ALTER TABLE alerts ADD COLUMN baseline_bacino INTEGER;
ALTER TABLE alerts ADD COLUMN baseline_coverage REAL;
```

Per alert esistenti (238 non-deprecated): i valori possono essere backfillati leggendo `environment_split_json` in un migration script (`scripts/apply_migration_005.py`).

Formula di aggregazione (da `TriageSection.tsx:20-26` — logica valida, solo la baseline è sbagliata):

```python
def _compute_baseline_from_env_split(environment_split_json: str) -> tuple[int, float]:
    """
    Aggrega bacino_baseline e coverage_baseline da environment_split_json.
    Restituisce (total_bacino_baseline, avg_coverage_baseline).
    """
    env = json.loads(environment_split_json) if environment_split_json else {}
    env_entries = {k: v for k, v in env.items() if isinstance(v, dict)}
    
    total_bacino = sum(v.get("bacino_baseline", 0) for v in env_entries.values())
    coverages = [v.get("coverage_baseline", 0) for v in env_entries.values() 
                 if v.get("coverage_baseline") is not None]
    avg_coverage = sum(coverages) / len(coverages) if coverages else 0.0
    
    return total_bacino, avg_coverage
```

**Esempio verificato** (ALT-20260123-010000-P2, GOOGLE_ADEX):
- `bacino_baseline` aggregato = 171,503
- `coverage_baseline` avg = 0.8161

Vs euristica frontend:
- `baselineBacino = totalBacino * (revenueRatio * 0.95)` = 168,552 * (0.XXX * 0.95) = valore inventato
- `baselineCoverage = avgCoverage + 0.05` = 0.7358 + 0.05 = 0.7858 (vs reale 0.8161: off di 3.7pp)

### Pydantic schema extension

```python
# backend/api/schemas.py — AlertDetail aggiunta

class AlertDetail(BaseModel):
    # ... campi esistenti ...
    baseline_bacino: Optional[int] = None       # NUOVO — API-03 Phase 11
    baseline_coverage: Optional[float] = None   # NUOVO — API-03 Phase 11
```

**Nota:** `Optional` perché alert legacy (deprecated=1) potrebbero avere JSON blob vuoto; nessun crash per backward compat.

### Dove viene scritto il valore

Due opzioni:

**Opzione A (raccomandata — zero migrazione dati per alert futuri):** Calcola al volo in `get_alert_by_id()` in `operations.py` leggendo `environment_split_json` e aggregando on-the-fly. Nessuna colonna DB aggiuntiva.

**Opzione B (persistenza):** Migration 005 aggiunge colonne, backfill su 238 alert, `run_pipeline()` scrive i valori al momento della creazione alert.

**Raccomandazione:** Opzione A per Phase 11 (zero DB migration, zero rischio di rollback complesso). Opzione B in Phase 18 (hardening) se i contract test richiedono query SQL.

---

## 7. Channel / sell_type / Baseline Reference Data

### Mapping sell_type_proxy (SSOT verificato)

[VERIFIED: `config/sell_type_proxy.yaml` — letto verbatim]

| sell_type_proxy | channel_group values |
|----------------|---------------------|
| `Open_Market` | GOOGLE_ADEX, OPEN_BIDDING, GOOGLE (legacy) |
| `Header_Bidding` | HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC |
| `Direct` | DIRECT |
| `Deal` | DEAL |
| `Other` | TAM |

**Nota sull'alias GOOGLE:** GOOGLE (legacy pre-v1.2) è mappato a Open_Market. Nel parquet corrente non esiste più (solo GOOGLE_ADEX), ma il mapping lo gestisce per retrocompat.

**Nota sul claim ROADMAP "alerting_rules.yaml:84-91":** Le righe 84-91 di `alerting_rules.yaml` definiscono `channels_open_market: [GOOGLE_ADEX, OPEN_BIDDING]` e `channel_direct: DIRECT` per il cross-channel detection alert — NON per il sell_type_proxy API. Il mapping completo per API-02 viene da `sell_type_proxy.yaml`. Il claim nel ROADMAP è fuorviante ma la confidence del 95% rimane valida (la D4 decision è fondata su entrambi i file).

### Colonne parquet verificate

[VERIFIED: schema pyarrow live]

```
daily_aggregated.parquet (20 colonne):
date, publisher_id, channel_group, sell_type_proxy, environment, geo_cluster,
revenue, revenue_gross, impressions, measurable_impressions, viewable_impressions,
bacino, clicks, floor_cpm, coverage, ecpm, rpm, ctr, viewability, gross_margin_pct
```

Max date parquet: **2026-03-23** (congelato — nessuna ETL refresh da allora).

### 7w rolling same-weekday baseline

[VERIFIED: `backend/api/routes.py:619-768` — logica `revenue_status_24h`]

La logica 7w rolling same-weekday ESISTE GIA' per l'endpoint hourly:

```python
# routes.py:625-659
for week_offset in range(1, 8):
    bl_date = target_date - timedelta(weeks=week_offset)
    bl_rev = rev_lookup.get((bl_date, hour), 0.0)
    if bl_rev > 0:
        baseline_values.append(bl_rev)
baseline = sum(baseline_values) / len(baseline_values) if baseline_values else 0.0
```

Per API-03, il calcolo è equivalente ma su dati daily (già fatto in `data_fetcher_real.py` durante la generazione degli alert). La formula di aggregazione per `environment_split_json` è già in `backend/agents/data_fetcher_real.py:142-260`.

### Valori chiave verificati

[VERIFIED: query live su parquet e CSV]

| Valore | Source | Verificato |
|--------|--------|-----------|
| Jan 12 GOOGLE_ADEX rev_gross (raw CSV) | €27,245.63 | ✅ |
| Jan 12 GOOGLE_ADEX rev_gross (parquet top-50) | €23,024.16 | ✅ |
| Jan 12 Open_Market rev_gross (parquet top-50) | €24,025.54 | ✅ |
| PBI target Jan 12 (email Vito) | ~€27,200 | Verbatim email |
| Gap top-50 vs raw | -15.5% revenue | ✅ calcolato |
| sell_type_proxy values | 5 distinti in parquet | ✅ |
| baseline_bacino in env_split_json | presente per tutti gli alert non-deprecated | ✅ |
| Max date parquet | 2026-03-23 | ✅ |

---

## 8. Open Questions (RESOLVED)

1. **Scope di `sell_type` param per API-02** — REQUIREMENTS.md dice `sell_type` va su `/api/alerts`, `/api/publishers/top` E `/api/metrics/revenue-status-24h`. La tabella `alerts` nel DB NON ha colonna `sell_type_proxy` — aggiungerla richiederebbe Migration 006 + backfill su tutti gli alert. Raccomandazione: Phase 11 limita API-02 a `/api/publishers/top` (parquet già pronto); `/api/alerts` con sell_type sposta in Phase 12.
   - **Stefano decide: API-02 solo su `/top` o anche su `/api/alerts` in Phase 11?**
   - **RESOLVED:** Phase 11 limits API-02 to `/api/publishers/top` per plan 11-03. `/api/alerts` sell_type filter deferred to Phase 12 (requires Migration 006 + alerts column).

2. **Cache per API-01 (daily_kpi.csv)** — Il CSV è ~6.2M righe, caricamento stimato 2-5 secondi. Accettabile per uso dashboard (bassa frequenza)? O serve cache in-memory analogamente a `_hourly_cache`?
   - **Stefano decide: accetti latenza ~3s per API-01, o serve cache on-boot?**
   - **RESOLVED:** cache layer added in plan 11-02 Task 2 to mitigate ~3s CSV read latency.

3. **`baseline_bacino` / `baseline_coverage` come colonne DB o on-the-fly?** — Opzione A (on-the-fly in `get_alert_by_id`) è zero-migration e backward compat. Opzione B (nuove colonne DB + backfill) è più robusta per contract tests. Phase 11 recommendation = Opzione A; Phase 18 HARD-04 può aggiungere la persistenza.
   - **Raccomandazione: Opzione A per Phase 11. Stefano ha preferenze diverse?**
   - **RESOLVED:** Opzione A chosen (on-the-fly aggregation of environment_split_json in get_alert handler). No DB migration in Phase 11. Migration 005 deferred to Phase 18 if HARD-04 contract tests demand persistence.

4. **Mondadori+Mondadori_npa aggregation per publisher filter** — `GET /api/publishers/top?sell_type=Open_Market` filtrerà i publisher per sell_type MA mostrerà ancora `Mondadori` e `Mondadori_npa` come publisher separati (RC-b). L'aggregazione `publisher_family` è Phase 12/17. Il planner deve esplicitare questo limite in PLAN.md per non creare aspettative false.
   - **DEFERRED:** to Phase 12/17 (RC-b in SYNTHESIS). Out of Phase 11 scope.

5. **`revenue_share.yaml` — verifica applicazione per API-01** — API-01 legge raw `revenue_gross` dal CSV. Il rev-share (60%) NON deve essere applicato sul gross (sarebbe doppio). La colonna `revenue` (NET) nel parquet è già post-rev-share. API-01 deve esporre GROSS primario, con NET opzionale calcolato moltiplicando per il rev-share del publisher.
   - **Aperto:** verificare se `revenue_share.yaml` contiene lookup per publisher per permettere calcolo NET opzionale.
   - **RESOLVED:** API-01 endpoint exposes both revenue_gross and revenue_net (optional); dashboard label changes deferred to Phase 13 (RC-c).

---

## 9. Risk Register (R-04 Chirurgico Checkpoints)

| # | Rischio | Probabilità | Impatto | Mitigation |
|---|---------|------------|---------|------------|
| R1 | CSV da 6.2M righe OOM o timeout su endpoint API-01 | MEDIUM | HIGH | pyarrow column projection + filtro prima di materializzare; no `pd.read_csv` senza chunks |
| R2 | Migration DB (colonne o schema) corrotta su `vna_alerts.db` | LOW | HIGH | Snapshot `.bak` pre-migration come da R-04 + precedente Phase 09/10 |
| R3 | Cache stale in `_adrequests_cache` non aggiornata dopo filtro `sell_type` | MEDIUM | MEDIUM | Per API-02 il filtro avviene DOPO il load cached — no invalidazione necessaria; documenta che il param è stateless |
| R4 | `environment_split_json` vuoto/malformato su alert legacy → panic in aggregazione `baseline_bacino` | MEDIUM | LOW | `json.loads` in try/except; `Optional[int]` nel schema Pydantic; `None` come fallback |
| R5 | `sell_type_proxy` colonna mancante in parquet (se ETL viene re-runno senza SCHEMA-04) | LOW | HIGH | Aggiungere guard check `if "sell_type_proxy" in df.columns` con HTTP 503 diagnostico |
| R6 | Euristica frontend (`revenueRatio*0.95`) rimane in TriageSection.tsx | CERTAIN (Phase 12) | MEDIUM | Phase 11 espone i campi; Phase 12 rimuove l'euristica — non tentare entrambi nello stesso commit |
| R7 | `daily_kpi.csv` non disponibile in environment di deploy (Vercel static) | HIGH | CRITICAL | API-01 è backend-only; il CSV NON è deployabile su Vercel (gitignored, 2GB). Il backend serve l'endpoint; frontend lo consuma via fetch. Verificare che il deploy Vercel abbia backend accessibile. |

**Checkpoint R-04 obbligatori:**
1. Pre-phase tag `v1.3-pre-phase-11` + `.bak` snapshot del DB prima di qualsiasi migration
2. Dry-run API-01 in locale con assertion PBI-parity prima del commit
3. Unit test API-02 con fixture parquet prima di qualsiasi modifica a `publisher_routes.py`
4. Commit atomico separato per ogni API (API-01, API-02, API-03) + test associato

---

## 10. Validation Architecture (Nyquist Checkpoints)

> `workflow.nyquist_validation` non presente in `.planning/config.json` → trattato come ENABLED.

### Test Framework

| Proprietà | Valore |
|-----------|--------|
| Framework | pytest (confermato da `scripts/test_*.py` esistenti) + `unittest` (alcuni test usano `unittest.TestCase`) |
| Config file | Nessun `pytest.ini` o `pyproject.toml` nella root — i test sono in `scripts/` con invocazione diretta |
| Quick run | `.venv/bin/python scripts/test_network_totals_endpoint.py` |
| Full suite | `.venv/bin/python -m pytest scripts/ -v --ignore=.venv` |
| TestClient | `from fastapi.testclient import TestClient` (pattern da `scripts/test_health_alerts_pipeline.py`) |

### Phase 11 Requirements → Test Map

| Req ID | Comportamento da verificare | Tipo test | Comando automatizzato | File esiste? |
|--------|---------------------------|-----------|----------------------|--------------|
| API-01 | `GET /network-totals?date=2026-01-12&channel=GOOGLE_ADEX` ritorna `revenue_gross` entro 2% da €27,200 | integration | `.venv/bin/python scripts/test_network_totals_pbi_parity.py` | ❌ Wave 0 |
| API-01 | Endpoint restituisce 400 su date mancante o formato errato | unit | stessa suite | ❌ Wave 0 |
| API-01 | Endpoint restituisce 404 su date fuori range parquet | unit | stessa suite | ❌ Wave 0 |
| API-02 | `GET /api/publishers/top?sell_type=Open_Market` ritorna solo publisher con Open_Market rows | integration | `.venv/bin/python scripts/test_sell_type_filter.py` | ❌ Wave 0 |
| API-02 | Param `sell_type` invalido → HTTP 400 con messaggio descrittivo | unit | stessa suite | ❌ Wave 0 |
| API-02 | `sell_type_proxy` column guard → HTTP 503 se colonna assente | unit | stessa suite | ❌ Wave 0 |
| API-03 | `GET /api/alerts/{alert_id}` ritorna `baseline_bacino` e `baseline_coverage` non-None per alert non-deprecated | integration | `.venv/bin/python scripts/test_alert_baseline_fields.py` | ❌ Wave 0 |
| API-03 | `baseline_coverage` server-side ≠ `avgCoverage + 0.05` (euristica eliminata) | regression | stessa suite | ❌ Wave 0 |
| API-03 | Alert deprecated → `baseline_bacino=None`, `baseline_coverage=None` (no panic) | unit | stessa suite | ❌ Wave 0 |

### Sampling Rate

- **Per commit:** test specifico del componente modificato (es. `test_network_totals_pbi_parity.py` dopo ogni modifica a routes.py)
- **Per wave:** full suite `scripts/test_*.py` (escludendo quelli che richiedono DB live migration)
- **Phase gate:** `test_network_totals_pbi_parity.py` green + `test_sell_type_filter.py` green + `test_alert_baseline_fields.py` green prima di `/gsd-verify-work`

### Wave 0 Gaps (da creare PRIMA dell'implementazione)

- [ ] `scripts/test_network_totals_pbi_parity.py` — PBI-parity assertion €27.2k ±2%, include fixture con subset CSV Jan 12
- [ ] `scripts/test_sell_type_filter.py` — verifica filtro sell_type su `/api/publishers/top`; usa parquet fixture
- [ ] `scripts/test_alert_baseline_fields.py` — verifica `baseline_bacino`/`baseline_coverage` in AlertDetail response; usa in-memory SQLite fixture

**Pattern fixture esistente da seguire:** `scripts/test_mondadori_fill_rate_regression.py` usa `pyarrow.parquet` con column projection per test veloci senza caricare tutto il parquet. `scripts/test_health_alerts_pipeline.py` usa `TestClient(app)` per endpoint integration test.

---

## 11. Assumptions Log

| # | Claim | Sezione | Rischio se sbagliato |
|---|-------|---------|----------------------|
| A1 | Il termine "upstream-streaming" in ROADMAP.md = lettura CSV raw, non HTTP streaming | §4 | Basso — confermato da testo REQUIREMENTS.md API-01 |
| A2 | daily_kpi.csv è aggiornato allo stesso max_date del parquet (2026-03-23) | §4 | Medio — se CSV è più vecchio, API-01 ha dati meno recenti del parquet |
| A3 | `revenue_share.yaml` contiene il fattore 0.60 per permettere calcolo NET opzionale in API-01 | §8 open question 5 | Basso — NET è opzionale, GROSS è primario |
| A4 | L'ambiente Vercel ha accesso al backend FastAPI per API-01 (CSV non deployabile su static) | §9 R7 | ALTO — se il deploy è pure static senza backend, API-01 è inaccessibile dalla dashboard |

---

## 12. References (file:line citations)

| File | Righe | Contenuto |
|------|-------|-----------|
| `backend/api/routes.py` | 1-82 | FastAPI router setup, pattern esistente endpoint metrics |
| `backend/api/routes.py` | 609-728 | `revenue_status_24h` — pattern 7w rolling baseline hourly |
| `backend/api/publisher_routes.py` | 168-288 | `get_top_publishers` — target per API-02 |
| `backend/api/schemas.py` | 64-89 | `AlertDetail` — target per API-03 estensione |
| `backend/agents/data_fetcher_real.py` | 142-260 | `_get_hourly_metrics` — logica baseline per alert (fonte `environment_split_json`) |
| `frontend/src/components/alerts/TriageSection.tsx` | 29-32 | Euristica `revenueRatio*0.95` + `avgCoverage+0.05` da eliminare in Phase 12 |
| `config/sell_type_proxy.yaml` | 29-45 | Mapping canonical channel_group → sell_type_proxy (SSOT per API-02) |
| `config/alerting_rules.yaml` | 84-91 | `cross_channel_detection` — NON il mapping sell_type (solo Open_Market vs Direct per alert) |
| `data/sentinel_db/daily_kpi.csv` | (CSV) | Raw upstream, colonne: date, ad_unit_id_1, channel_group, revenue_gross, impressions |
| `data/baseline/daily_aggregated.parquet` | (parquet) | 20 colonne, top-50, max_date=2026-03-23, ha `sell_type_proxy` |
| `scripts/etl_csv_to_parquet.py` | 169-178 | Pattern chunked read CSV (da adattare per API-01 con pyarrow) |
| `scripts/test_mondadori_fill_rate_regression.py` | 1-60 | Pattern pyarrow column projection per test veloci |
| `.planning/intel/sentinel-2026-04-28/AUDIT-A-NUMBERS-FORENSICS.md` | Bug1-Bug4 | Verified code paths per ogni numero dell'email |
| `.planning/intel/sentinel-2026-04-28/SYNTHESIS.md` | RC-(a), RC-(e) | Root causes indirizzate da Phase 11 |

---

## Security Domain

> `security_enforcement` non esplicitamente configurato → trattato come ENABLED.

### Applicable ASVS Categories

| ASVS Category | Applicabile | Controllo standard |
|---------------|-------------|-------------------|
| V2 Authentication | Sì (tutti gli endpoint usano `require_auth`) | `backend/api/auth.py::require_auth` già applicato via `Depends` in `main.py` |
| V5 Input Validation | Sì | Pydantic `Query(..., pattern=...)` per `date`, enum check per `sell_type`, `Optional[str]` con validation |
| V6 Cryptography | No | Nessun dato crittografato in questi endpoint |
| V3 Session Management | No | Gestito da middleware esistente, nessuna modifica |

### Threat Patterns per questo stack

| Pattern | STRIDE | Mitigazione standard |
|---------|--------|---------------------|
| Path traversal su CSV path | Tampering | Usare costanti `Path()` hardcoded, mai interpolazione da query param |
| OOM via date range molto ampio in API-01 | DoS | Limitare `date` a singolo giorno (no range), pyarrow column projection |
| Injection via `sell_type` param | Tampering | Whitelist enum esplicita: `["Open_Market", "Header_Bidding", "Direct", "Deal", "Other"]` |
| `json.loads` panic su `environment_split_json` corrotto | Denial | try/except + fallback `None` |

---

## Sources

### Primary (HIGH confidence — verificato con tool)
- `data/sentinel_db/daily_kpi.csv` — query live Jan 12 GOOGLE_ADEX revenue_gross = €27,245.63
- `data/baseline/daily_aggregated.parquet` — schema e valori verificati (pyarrow read live)
- `config/sell_type_proxy.yaml` — mapping canonico verificato
- `config/alerting_rules.yaml` — linee 84-91 lette verbatim
- `backend/api/routes.py` — pattern endpoint esistenti letti
- `backend/api/publisher_routes.py` — logica `get_top_publishers` letta
- `backend/api/schemas.py` — schema `AlertDetail` letto
- `frontend/src/components/alerts/TriageSection.tsx:29-32` — euristica letta verbatim
- `data/vna_alerts.db` — `environment_split_json` verificato live (bacino_baseline, coverage_baseline presenti)
- `.planning/STELLA-POLARE.md`, `EMAIL-VITO-2026-04-22.md`, `SYNTHESIS.md`, `AUDIT-A-NUMBERS-FORENSICS.md` — truth sources canonici letti

### Secondary (MEDIUM confidence)
- REQUIREMENTS.md API-01/02/03 — specifica requisiti letta
- ROADMAP.md Phase 11 — success criteria letti

### Tertiary (LOW confidence)
- Nessuno

---

## Metadata

**Confidence breakdown:**
- API-01 design (CSV streaming, PBI-parity): HIGH — verificato numericamente con query live
- API-02 design (sell_type filter): HIGH — colonna `sell_type_proxy` verificata in parquet, mapping in YAML verificato
- API-03 design (baseline fields): HIGH — `bacino_baseline`/`coverage_baseline` verificati in DB live
- Claim "alerting_rules.yaml:84-91" per sell_type: MEDIUM — le righe esistono ma non sono il SSOT del mapping; SSOT è `sell_type_proxy.yaml`

**Research date:** 2026-04-28
**Valid until:** 2026-05-28 (stable stack)
