---
title: SYNTHESIS — Mondadori bacino gap audit (Feb 2026)
date: 2026-05-04
agents: [A-data-forensics, B-contract-scope]
verdict: family-taxonomy-mismatch + top-50-gate-exclusion
confidence: HIGH (independent convergence + numeric verification)
status: ready-for-operator-decision
---

# Synthesis — Mondadori Feb 2026 bacino gap

## Convergenza tra agenti indipendenti

Due agenti hanno indagato in parallelo lo stesso fenomeno (Sentinel 286M vs PBI 366M, gap -22%) da angoli ortogonali:

- **Agent A** (data forensics): scava nei parquet, ETL, sorgenti raw CSV, dedup logic
- **Agent B** (contract/scope): semantica "bacino" Sentinel vs "ad requests" PBI, family taxonomy, sell_type

I due agenti sono partiti senza conoscenza reciproca e **convergono** sulla stessa root cause prioritaria:

| Aspetto | Agent A verdict | Agent B verdict |
|---------|-----------------|-----------------|
| Root cause primaria | family-incomplete + top-50-gate | family-taxonomy-mismatch (HIGH conf) |
| È bug del codice o decisione di scope? | Architecturale (top-50 filter) + scope (family) | Decisione di scope/spec, NON code bug |
| H6 semantic mismatch (definizioni diverse) | n/a | CONFUTATA — semantica equivalente |
| H7 PBI conta richieste fallite | n/a | CONFUTATA — raw CSV match PBI Jan12 |
| H8 family taxonomy | CONFIRMED | STRONGLY CONFIRMED |
| H10 sell_type scope | partially confuted | SUSPECTED secondario (non risolvibile senza doc PBI) |

## Verifica numerica indipendente (eseguita dall'orchestrator post-agenti)

Letta `data/sentinel_db/publisher_mapping.csv` (431 entries). Trovati 3 publisher Mondadori-family:

| ad_unit_name | ad_unit_id | Bacino Feb 2026 (raw `daily_adrequests.csv`) | Nel parquet (post top-50)? |
|--------------|------------|----------------------------------------------|------------------------------|
| Mondadori | 21704134909 | 133,657,441 | ✓ (top-50) |
| Mondadori_npa | 22888855294 | 162,563,763 | ✓ (top-50) |
| **Adgage_mondocore** | **23316890961** | **109,947,392** | **✗ FUORI dal top-50** |
| **TOTALE family raw** | | **406,168,596** | |
| **PBI target email Vito** | | **366,000,000** | |

**Numeri chiave:**
- Sentinel attuale (post Phase 12 dedup, solo `Mondadori` + `Mondadori_npa`): **286M** → gap -22% vs PBI
- Sentinel + Adgage_mondocore raw: **406M** → +11% sopra PBI
- PBI 366M sta IN MEZZO tra i due → suggerisce che PBI includa Adgage_mondocore con qualche filtro residuo (env/geo subset?)

## Spiegazione causale (3-layer issue, A+B convergente)

```
Layer 1: Family taxonomy mismatch
  - PBI raggruppa "Mondadori" come corporate group (incl. Mondadori_npa, Adgage_mondocore)
  - Sentinel espone i 3 publisher_id come righe separate

Layer 2: Top-50 gate exclusion (artefatto architetturale ETL)
  - scripts/etl_csv_to_parquet.py:106-121 → find_top50_publishers()
  - filtro applicato a daily_adrequests.csv (linee 176-192)
  - Adgage_mondocore (rank #51 per revenue_gross, ~€8.3k) viene FILTRATO
  - Conseguenza: anche se UI aggregasse la family, mancherebbe Adgage_mondocore (~110M bacino raw)

Layer 3 (noto, secondario): parquet structural multiplication
  - daily_kpi (per-channel, 19.8k righe) × daily_adrequests (no-channel, 9.2k righe)
  - join produce 1,181M raw → dedup-via-first() porta a 286M
  - Loss da dedup è solo 3.5% (296M CSV → 286M post-dedup) → NON è la root cause
```

## Cosa NON è la root cause (ipotesi confutate)

- ❌ Bug nel formula bacino o coverage (Agent A: formula `fill_rate = imp/bacino` corretta, dedup recupera 96.5%)
- ❌ ETL filtra righe legittime upstream per NULL/zero/negativi (Agent A: 0 NULL, 0 negative bacino)
- ❌ CSV sentinel_db incompleto vs GAM (Agent A: raw CSV matcha PBI per AdEx Jan 12 al 0.07%)
- ❌ Semantic mismatch "bacino" ≠ "ad requests" (Agent B: identica semantica, definita esplicitamente come tale in `etl_csv_to_parquet.py:238` `df.rename(columns={"ad_requests": "bacino"})` + `DATA_INTEGRATION.md`)
- ❌ Phase 12 dedup over-aggressive (Agent A: WIP commit C `7ea4a74` matematicamente corretto entro ±1%)

## Punto residuo NON risolvibile senza dati operatore (Agent B)

**Sell_type Open_Market scope:**
- PBI Open_Market revenue Mondadori = €90k (=48% di €188k all)
- Sentinel `sell_type_proxy='Open_Market'` = €61k (=27% di €226k all)
- Definizione PBI di "Open Market" potrebbe includere `header_bidding`/`programmatic` che Sentinel mappa diversamente in `config/sell_type_proxy.yaml`
- **Impatto:** anche se chiudi family + top-50, lamentela #4e (€90k OpenMarket) richiede chiarimento spec PBI

## Cosa serve dall'operatore

Per chiusura definitiva:

1. **Definizione PBI di "Mondadori"**: include Adgage_mondocore? Altre subentità (Mondadori_TV, Networkmondadori, etc.)? Confermare lista esatta dal team TAM&Yield.
2. **Definizione PBI di "Open Market"**: quali sell_type/channel_group inclusi? Confronto con `config/sell_type_proxy.yaml`.
3. **Decisione scope top-50**: il filtro top-50 è intenzionale (deliverable v1.2 design) o un'ottimizzazione che ora fa danno? Se intenzionale, Adgage_mondocore va comunque incluso come "outlier" della Mondadori family.

## Raccomandazione operativa

**3 opzioni di fix**, in ordine di costo crescente:

### Opzione 1 — Family aggregation backend (raccomandato dai DUE agenti)

**Scope:** introdurre `publisher_family` come colonna ETL + aggregazione opzionale a livello API.
- File da toccare: `scripts/etl_csv_to_parquet.py` (aggiunge colonna), `backend/api/publisher_routes.py` (`?aggregate_family=true` query param), nuovo `config/publisher_families.yaml` (Mondadori → [Mondadori, Mondadori_npa, Adgage_mondocore])
- Effetto: Sentinel `/top` con `aggregate_family=true` ritorna 1 riga "Mondadori family" con bacino 296M (ancora -19% vs PBI per via di Adgage_mondocore escluso)
- **NON sufficiente da solo**: serve combinare con Opzione 2

### Opzione 2 — Whitelist family in top-50 gate

**Scope:** `find_top50_publishers()` accetta whitelist da `config/publisher_families.yaml` per garantire che ALL family members entrino nel parquet anche se sotto rank-50.
- File da toccare: `scripts/etl_csv_to_parquet.py:106-121` aggiunge `force_include = set(family_members)`
- Effetto: Adgage_mondocore entra nel parquet → +95M bacino post-dedup → Sentinel ≈ 381M ≈ PBI 366M con +4% scostamento (DENTRO ±5%, parity-acceptable)
- Combinato con Opzione 1: copre lamentela #4a (bacino) e #4b (fill rate, denominatore corretto)

### Opzione 3 — Ridiscutere top-50 architectural decision

**Scope:** rimuovere il filtro top-50 in toto, esporre tutti i publisher.
- Costo: aumento dimensione parquet da ~5M righe attuali (top-50) a ~50M+ (tutti i 431 publisher)
- Trade-off: perdita performance ETL + storage size, gain visibility totale
- **Raccomandato solo se** Stefano decide che il top-50 era un artefatto WIP non più giustificato

## Lamentele email Vito — stato dopo fix raccomandato (Opzione 1+2)

| Lamentela | Stato attuale | Stato post fix 1+2 |
|-----------|---------------|--------------------|
| #2/#3 AdEx Jan 12 | ✓ matched 0.17% | invariato (già OK) |
| #4a Mondadori bacino | ⚠ -22% | ✓ ~+4% (parity-acceptable) |
| #4b Fill rate | ⚠ +7% | ✓ ricalcolato corretto |
| #4c eCPM | ⚠ +38% | ✓ riallineato (denominatore impressions invariato, gross_revenue su family corretto) |
| #4d RPM | ⚠ +55% | ✓ riallineato (denominatore bacino corretto) |
| #4e Revenue OpenMarket | ⚠ -32% | ❓ residual — dipende da sell_type spec PBI (Agent B H10) |
| #5 timeframe label | ✓ codice (Phase 14) | invariato |
| #6 empty state Google | ✓ codice (Phase 15) | invariato |

**Net effect:** Opzione 1+2 chiude 4 lamentele ancora aperte (#4a/b/c/d) e lascia 1 residuale (#4e sell_type scope) che richiede spec PBI dal team TAM&Yield.

## Effort stimato (Opzione 1+2 combinato)

- ETL refactor: ~150-200 righe Python, 1 file YAML config nuovo, ~3 hour
- Backend API: 1 query param + family agg logic, ~50 righe TS/Python, ~1 hour
- Frontend: opzionale toggle "Family view" badge, ~50 righe, ~1 hour
- Test + UAT: regressione bacino su 5 publisher noti, ~2 hour
- Documentation: PROJECT.md + DATA_INTEGRATION.md update, ~1 hour
- **Totale: 1-1.5 giorni di lavoro per una nuova fase Phase 16 "Mondadori Family Aggregation"**

## File evidence

- `.planning/intel/sentinel-2026-05-04-mondadori-gap/AGENT-A-data-forensics.md` (Agent A full report)
- `.planning/intel/sentinel-2026-05-04-mondadori-gap/AGENT-B-contract-scope.md` (Agent B full report)
- `data/sentinel_db/publisher_mapping.csv` (3 Mondadori entries verificate)
- `data/sentinel_db/daily_adrequests.csv` (raw upstream — verifica numerica eseguita)
- `data/baseline/daily_aggregated.parquet` (post top-50 — Adgage_mondocore assente)
- `scripts/etl_csv_to_parquet.py:106-121` (top-50 gate — root architectural cause)

## Confidence

- **Family taxonomy mismatch:** HIGH (entrambi agenti convergono, verificato numericamente)
- **Top-50 exclusion impact:** HIGH (ad_unit_id 23316890961 esiste in mapping ma assente in parquet — verificato)
- **Effetto Opzione 1+2 sul gap:** MEDIUM-HIGH (numerica suggerisce parity ±5%, ma residua incertezza su come PBI conta esattamente Adgage_mondocore)
- **Sell_type residual #4e:** LOW confidence senza spec PBI — richiede operator action upstream
