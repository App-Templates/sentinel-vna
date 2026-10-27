# SENTINEL — Value Network Alerting Platform

## What This Is

Piattaforma di monitoraggio e alerting per la rete pubblicitaria Adkaora. SENTINEL analizza le revenue orarie dei publisher (50 top), rileva anomalie (cali improvvisi, drift graduali, near-zero, data gap, margine sotto soglia, coverage-zero, pricing rule errate, leading-indicator drop, cross-channel shift), classifica le cause e notifica il team operativo. Destinata al team TAM&Yield (5-10 persone) per il monitoraggio su 7 canali di vendita (GOOGLE_ADEX, OPEN_BIDDING, DEAL, DIRECT, TAM, HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC).

## Core Value

**Trovare gli alert in tempo quasi reale comunicando tempestivamente solo ciò che è davvero importante** — eliminando i falsi positivi e rendendo visibili i cali graduali che oggi nessuno nota finché il danno non è fatto.

## Current Milestone: v1.3 Stabilization

**Goal:** Portare SENTINEL a production-grade 10/10 chiudendo il silent-failure bug del pipeline alert (CHECK constraint drift), committando atomicamente 2 mesi di WIP pendente, rimuovendo heuristic client-side non documentate, e installando monitoring che previene future silent failures.

**Target features:**
- Schema migration `vna_alerts.channel_group` per accettare i 7 canali v1.2 + backfill 90 giorni di alert persi
- Pipeline silent-failure monitoring (meta-alert su `pipeline_runs > 0 AND alerts_written = 0`)
- WIP reconciliation in 4 atomic commit (design+i18n, traduzione IT→EN, backend correctness, dashboard date-nav)
- DB WIP binary-diff investigation + migration script tracciato in git
- Triage baseline server-side (rimuove heuristic `revenueRatio * 0.95` dal frontend)
- Decisione Vercel static export (ship o shelve Commit E)
- Hardening: contract test parquet↔DB↔UI, data lineage doc aggiornata a v1.2, CI gate CHECK constraint drift

## Requirements

### Validated

<!-- Funzionalità shippate e confermate funzionanti -->

**v1.0 — Piattaforma base:**
- ✓ Pipeline LangGraph 11 agenti (orchestrator → notifier) — v1.0
- ✓ Alert A1 revenue drop con severity P0/P1/P2 — v1.0
- ✓ Alert A2 drift 7 giorni — v1.0 (migliorato in v1.1)
- ✓ Alert A3 near-zero revenue/coverage — v1.0
- ✓ Alert A0 data gap detection — v1.0
- ✓ Triage classification (TRAFFIC/COVERAGE/MIXED/REVENUE_ONLY) — v1.0
- ✓ Contributor analysis per-publisher — v1.0
- ✓ Geo breakdown (ITA/ES/OTHER) — v1.0
- ✓ Environment split (WEB/AMP/APP) — v1.0
- ✓ Insight generation (template-based) — v1.0
- ✓ Dashboard alert list con filtri — v1.0
- ✓ Alert detail 7-step view — v1.0
- ✓ Top 35 publisher per revenue con country — v1.0
- ✓ Publisher weekly KPI charts con annotazioni stagionali — v1.0
- ✓ eCPM optimization windows — v1.0
- ✓ Backtest storico — v1.0
- ✓ Health page — v1.0
- ✓ Admin page datasource config — v1.0
- ✓ Google OAuth (dominio @adkaora.com) — v1.0
- ✓ Rate limiting API — v1.0
- ✓ Deduplicazione alert LIVE mode — v1.0.1
- ✓ Graph singleton (compile-once) — v1.0.1
- ✓ Real data fetcher (parquet, non sintetico) — v1.0.1

**v1.1 — Alerting Evoluto + Operator Workflow (GSD milestone 2026-02-21):**
- ✓ Drift detection regressione lineare 14-30gg — v1.1 Phase 01
- ✓ Confronto revenue vs giorno precedente (stesse ore) con soglia 30% — v1.1 Phase 01
- ✓ Confronto revenue vs media 14 giorni — v1.1 Phase 01
- ✓ Alert attivi weekend/festivi (scheduling ridotto 2x/giorno 10/18 UTC) — v1.1 Phase 01
- ✓ Soglie doppie (P2-WATCH per attenzione -15% vs operativa -30%) — v1.1 Phase 01
- ✓ Frontend drift visualization + comparative metrics — v1.1 Phase 01
- ✓ Alert A5 margine / eCPM drop — v1.1 Phase 02
- ✓ Alert A6 coverage-zero con triage dedicato (policy Google/MCM/ads.txt/technical) — v1.1 Phase 02
- ✓ Alert A7 pricing-rule (coverage↓ + CPM↑ correlation) — v1.1 Phase 02
- ✓ Frontend panels per A5/A6/A7 — v1.1 Phase 02
- ✓ Feedback system (6 categorie REAL/FALSE_POSITIVE, commenti, storico per publisher) — v1.1 Phase 03
- ✓ Assignment system (email @adkaora.com, UNIQUE constraint) — v1.1 Phase 03
- ✓ Intervention tracking (form <1min, junction table, baseline exclusion) — v1.1 Phase 03
- ✓ Frontend FeedbackPanel + InterventionPanel + assignment dropdown — v1.1 Phase 03
- ✓ Slack webhook configuration (admin UI, 3 endpoints GET/PUT/TEST) — v1.1 Phase 04
- ✓ Slack templates severity-based (P0 full, P1 medium, P2 compact) + pending_notifications — v1.1 Phase 04
- ✓ Daily digest scheduler (CronTrigger + manual trigger) — v1.1 Phase 04
- ✓ Revisione documentale completa operational + technical docs — v1.1 Phase 06

**v1.2 — New IT Dataset + Advanced Rules (drift commit, non-GSD, 2026-03-26):**
- ✓ ETL sentinel_db CSV → parquet via `scripts/etl_csv_to_parquet.py` (18-field v2 schema) — v1.2
- ✓ Dataset 7 canali (GOOGLE_ADEX, OPEN_BIDDING, DEAL, DIRECT, TAM, HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC) — v1.2
- ✓ Top 50 publishers by revenue_gross (86.8% revenue coverage) — v1.2
- ✓ Alert A8 gross-margin (threshold 25%, P1, baseline 7w) — v1.2
- ✓ Leading indicators CTR/viewability (P2-WATCH, -15% threshold) — v1.2
- ✓ Cross-channel detection (DIRECT↑ vs Open Market↓ pattern) — v1.2
- ✓ Revenue share 60/40 default + per-publisher overrides config — v1.2
- ✓ Fresh data through 2026-03-23 (daily + hourly parquets) — v1.2
- ✓ Runtime read paths wired a `daily_aggregated.parquet` — v1.2

**v1.3 — Stabilization (in-flight):**
- ✓ 60 giorni di alert backfilled in DB (2026-01-23 → 2026-03-23, parquet_v2_max_date) via `scripts/backfill_alerts.py` — 238 fresh alerts across 8 canali, HH-offset alert_id disambiguation — **Validated in Phase 09: alert-backfill-legacy-migration** (31-day gap 2026-03-24 → today disclosed in COVERAGE-GAP.md, v1.3.1 plant-seed)
- ✓ 200 legacy pre-v1.2 alerts soft-deprecated via `deprecated + deprecation_reason` columns (migration 002, belt-and-suspenders filter, D-14 canonical reason string) — **Validated in Phase 09: alert-backfill-legacy-migration**
- ✓ API `/api/alerts` default-hides deprecated alerts; `?include_deprecated=true` opt-in; Pydantic `deprecated: bool` field exposed — **Validated in Phase 09: alert-backfill-legacy-migration**

### Active

<!-- Milestone v1.3 Stabilization — requisiti correnti -->

**Silent-failure fix:**
- [ ] Schema `vna_alerts.channel_group` CHECK constraint espanso ai 7 canali v1.2 con migration script tracciato in git
<!-- [moved to Validated] 60 giorni backfilled in Phase 09; 31-day gap 2026-03-24 → today disclosed in COVERAGE-GAP.md as v1.3.1 plant-seed -->

- [ ] Pipeline silent-failure monitoring: health endpoint `/health/alerts-pipeline` + meta-alert quando `pipeline_runs_last_24h > 0 AND alerts_last_24h == 0`

**WIP cleanup:**
- [ ] Investigazione `vna_alerts.db` binary WIP (2 mesi non tracciati) — preserva, reset o ricrea con script
- [ ] 56 file WIP committati in 4 atomic commits (design+i18n, traduzione, backend correctness, dashboard date-nav)
- [ ] Decisione Commit E Vercel static export (ship v1.3.1 o shelve)

**Correctness:**
- [ ] Triage baseline calcolato server-side (rimuove `revenueRatio * 0.95` heuristic in `TriageSection.tsx`)
- [ ] Reference period esplicito su alert metrics UI (`revenue_current` mostra intervallo temporale)

**Hardening:**
- [ ] Contract test parquet ↔ DB ↔ UI (regressione schema impossibile)
- [ ] Data lineage doc aggiornata: `DATA_INTEGRATION.md` riflette v1.2 schema 18-field
- [ ] CI gate: CHECK constraint drift detection (compare `backend/db/models.py` con DB live)

### Out of Scope

- Esecuzione diretta azioni su GAM dalla piattaforma — troppo rischioso, serve validazione umana
- Integrazione GAM change history via API — complessità alta, form manuale sufficiente
- Benchmark competitor/mercato — dati non disponibili
- App mobile — dashboard web responsive sufficiente
- Athena live connection (Phase 5 v1.1) — **deferito a v1.4**, parquet pipeline attuale copre need
- Dati traffico page views/sessioni — dipendenza da Analytics, valutazione v1.4+
- Adattamento soglie automatico ML basato su feedback — v1.4+, serve massa critica di feedback prima
- Sell_type filter in schema — non confermato come blocker v1.3, deferito valutazione
- Hourly 7-channel — limite sorgente `hour_kpi.csv` (solo GOOGLE_ADEX); richiede nuova sorgente dati

## Context

**Team:** TAM&Yield guidato da Vito Sena (Head). 5-10 operatori tra account manager e yield specialists.

**Workflow attuale:** Check manuale ogni 3-4 ore durante il giorno, 2x/giorno weekend. Confronto visivo su GAM tra revenue orarie vs ieri e vs media 14gg. Diagnosi manuale per formato, company, environment.

**Stato piattaforma (2026-04-22):**
- v1.1 shippata per intero via GSD milestone (2026-02-21)
- v1.2 shippata fuori workflow GSD (2026-03-26) — drift da correggere ma codice funzionante in runtime
- **Silent-failure scoperto**: CHECK constraint stale blocca tutti gli alert insert dal 2026-01-22 (2590 pipeline_runs eseguiti, 0 alert salvati)
- UI mostra dati parquet freschi (2026-03-23) ma alert list ferma al 22 gennaio
- 56 file WIP uncommitted (2 mesi di drift, mix design/i18n/correctness/deployment)

**Pain point principale:** I cali graduali (es. 2%/giorno) non vengono notati finché il danno cumulativo non è significativo. Ora aggravato dal silent-failure che ha interrotto completamente l'alerting per 2+ mesi.

**Interventi manuali:** Quotidiani su pricing rules, floor CPM, demand partners. Tracciati su GAM (change history) ma non usati proattivamente. Il team è disposto a loggarli su SENTINEL se il form è rapido (< 1 min).

**Falsi positivi:** Campagne dirette publisher (sottraggono traffico all'Open Market), interventi pianificati, stagionalità, problemi tecnici noti. Generano rumore negli alert.

**KPI prioritari:** 1. RPM, 2. Coverage, 3. eCPM, 4. CTR

**Dati Athena:** Non attivato. Piattaforma usa sentinel_db CSV → parquet ETL (refresh manuale, schedulazione automatica da definire in v1.4).

**Publisher critici:** Top 50 per revenue (v1.2 filtered). Coverage ~86.8% revenue totale.

## Constraints

- **Infrastruttura:** SQLite single-writer (accettabile per 5-10 utenti), parquet come source primaria (Athena deferito)
- **Team:** 5-10 utenti, nessun accesso differenziato (tutti vedono tutto)
- **Dati:** sentinel_db CSVs (1.3 GB daily_kpi, 474 MB daily_adrequests) via ETL one-shot → parquet 197 MB
- **Operativo:** Form interventi < 1 min, notifiche solo per ciò che è importante
- **Budget:** Nessun vincolo esplicito, LLM optional (fallback statistico sempre attivo)
- **Deployment:** Vercel (static + serverless frontend) — decisione architetturale in sospeso (Commit E WIP)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Drift detection con regressione lineare 14-30gg | 2%/giorno non rilevato da A2 attuale (7gg, -8%) | ✓ Good — v1.1 shipped |
| Form interventi manuali (non integrazione GAM API) | GAM API complessa, form < 1min accettato dal team | ✓ Good — v1.1 shipped |
| Soglie doppie (30% operativo + 5-15% attenzione) | Allineare con pratica ops senza perdere granularità | ✓ Good — v1.1 shipped |
| Slack come canale primario notifiche | Team già su Slack, canale dedicato creato | ✓ Good — v1.1 shipped |
| RPM come KPI primario (non solo revenue) | Il team ragiona in RPM, non revenue assoluta | ✓ Good — v1.1 shipped |
| CTR/Viewability come leading indicator | Quando calano su AdEx, revenue Open Market cala dopo | ✓ Good — v1.2 shipped |
| Top 50 publishers filter in ETL | Pareto 80/20, ~86.8% revenue coverage, riduce parquet size | ✓ Good — v1.2 shipped |
| 18-field unified schema (daily+hourly) | Evita divergenze tra pipeline, supporta tutti gli alert types | ⚠️ Revisit — hourly single-channel limit |
| Schema migration via script tracciato in git | Mai più silent drift (incident 2026-01-22 → 2026-04-22 silent failure) | — Pending (v1.3) |
| Triage baseline server-side (no client heuristic) | UI non deve "inventare" numeri non esistenti nel DB | — Pending (v1.3) |
| Pipeline monitoring meta-alert | Silent failure per 2 mesi = no observability | — Pending (v1.3) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-23 — v1.3 Phase 10 (Pipeline Silent-Failure Monitoring) complete: MONITOR-01/02/03 closed. `GET /api/health/alerts-pipeline` live (1.9ms), silent_failure_watch scheduled at 60min intervals, `pipeline_runs.alerts_written_count` populated on every run. Live smoke: watchdog returns `triggered=True` on current DB state (pipeline_runs_last_24h=1446 ∧ alerts_last_24h=0 — the exact 2-month silent-failure pattern the phase was designed to catch). Verification 3/3 SC passed; code review 0 Critical / 4 Warning / 6 Info (advisory, WR-01 Slack 429 deferred). Critical path 07→10 for v1.3 complete — production alerts now have structural monitoring. Phases 07, 08, 09 also complete earlier in milestone.*

*Last updated: 2026-04-24 — v1.3 Phase 10.1 (Pipeline Monitoring Hotfix & Hardening) complete: MONITOR-04/05/06/07/08 closed across 8 plans / 7 waves. Migration 004 applied in-place (438 alerts canonicalized to space-sep naive UTC microseconds). Write paths unified, HARD-03 drift gate live. Watchdog query filters mode='LIVE' (runs dropped from 1447 → 1 in smoke). send_meta_alert retry rewritten (HTTPError/URLError distinguished, Retry-After honored, 4xx non-retriable). Counter semantics now uses db_new_row signal. Final flip: silent_failure_monitor.enabled=true. Post-fix watchdog smoke returned Case C (real silent failure, last LIVE alert 2026-03-23) — operator authorized re-enable; watchdog now reports genuine state. Verification 6/6 must-haves passed; code review 1 Critical / 6 Warning / 6 Info (CR-01 send_daily_digest aware-T cutoff on canonical space-sep column — same bug class as MAJOR-NEW-01 in an out-of-scope sibling callsite, routed to Phase 10.2). Backlog 999.1 filed: investigate LIVE pipeline silence root cause before 10.2 webhook rotation.*

*Last updated: 2026-04-25 — v1.3 Phase 999.1 (Investigate LIVE pipeline silent since 2026-03-23) complete: MONITOR-09/10 closed across 2 plans / 2 waves. Read-only diagnostic `scripts/diagnose_live_silence_999_1.py` (663 lines, mode=ro URI + grep-enforced no DML) ran zero-mutation against live DB (shasum byte-identical pre/post). Diagnosis: H1 HIGH confidence — parquet `max_date=2026-03-23` ≡ `MAX(alerts.created_at)`, LIVE pipeline correctly emits `no_alert` against stale tail window. H2 MEDIUM — legacy 2-channel scheduler (now dead) + `pipeline_runs.channel_group` has no SQL CHECK (`mondadori` lowercase passed through, Phase 10.1-08 smoke marker); routed to Phase 10.2+ hardening. Watchdog Case C firing semantically correct (10.1-VERIFICATION.md overrides[0] `'C — flip'` quoted verbatim). Operator (stefano) selected Path A — Accept + document; zero code/config change, ROADMAP §Backlog→§Phase Details promotion, `phase_10_2_safe: true` (operator accepts ~17 P0 pages/day until Phase 11 ETL refresh). H1 remediation owned by Phase 11/v1.3.1 per COVERAGE-GAP.md Option A/B. Verification 16/16 passed; code review 0 Critical / 2 Warning / 5 Info (WR-01 `--json` flag silent-bypass + WR-02 asymmetric import try/except — both diagnostic-script ergonomics, deferred). Phase 10.2 unblocked.*
