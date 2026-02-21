# Roadmap: SENTINEL v1.1

## Overview

**BROWNFIELD EVOLUTION** — SENTINEL v1.0 is a fully functional platform with 10 pages, 25+ React components, 11 LangGraph agents, full API layer with auth/rate-limiting, and real data from 1.75M parquet rows. v1.1 does NOT rebuild or refactor anything. Every phase EXTENDS existing functionality: new alert rules add to the A0-A3 system, operator feedback adds to the existing alert detail page, Slack notifications activate the existing notifier agent (which already has Block Kit code), and Athena activates the existing connector (already coded but disabled). Five phases, ordered by business impact: first we close the detection gap for gradual declines (the #1 pain point that costs money daily), then we add missing alert types, then we enable the operator feedback loop, then we activate Slack notifications, and finally we activate live data.

**Existing platform (v1.0 baseline):**
- Backend: FastAPI + SQLite (WAL) + APScheduler + LangGraph (11 agents) + PyArrow/Pandas
- Frontend: React 18 + TypeScript + Vite + Tailwind CSS + TanStack Query + Recharts
- Pages: dashboard, alerts list, alert detail (7-step), publishers, publisher detail, backtest, health, admin, docs
- Alert rules: A0 (data gap), A1 (revenue drop P0/P1/P2), A2 (7-day drift), A3 (near-zero)
- Auth: Google OAuth (@adkaora.com), rate limiting
- Data: 3 parquet files (daily_adrequests 360K, daily_channel 650K, hourly 740K)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Alerting Evoluto** - Extend anomaly_detector agent with drift regression, add yesterday/14d comparisons, calibrate dual thresholds, enable weekend scheduling (completed 2026-02-21)
- [x] **Phase 2: Nuovi Tipi Alert** - Add A5 (margin), A6 (coverage-zero), A7 (pricing-rule) alert rules to existing pipeline (completed 2026-02-21)
- [ ] **Phase 3: Operator Workflow** - Add feedback/assignment UI to existing alert detail page, add intervention tracking with new DB tables
- [ ] **Phase 4: Notifiche Slack** - Activate existing notifier agent with real Slack webhook, add severity-based templates and daily digest
- [ ] **Phase 5: Dati Live e Multi-canale** - Activate existing Athena connector, extend data model for new channels, add CTR/Viewability metrics

## Phase Details

### Phase 1: Alerting Evoluto
**Goal**: Gli operatori vedono in dashboard i cali graduali che oggi sfuggono, con confronti allineati alla pratica operativa (ieri, media 14gg) e alert attivi anche nei weekend
**Depends on**: Nothing (first phase)
**Requirements**: DRIFT-01, DRIFT-02, DRIFT-03, ALRT-04, ALRT-05
**Extends**: anomaly_detector agent (add linear regression + yesterday/14d comparison logic), APScheduler config (add weekend jobs), alerting_rules.yaml (add dual threshold config), alert detail page (show new drift visualizations)
**Success Criteria** (what must be TRUE):
  1. Un calo graduale del 2%/giorno per 14 giorni genera un alert di drift visibile in dashboard con trend line e percentuale cumulativa
  2. L'operatore vede in dashboard il confronto revenue orarie vs stesse ore di ieri, con alert quando la deviazione supera il 30%
  3. L'operatore vede il confronto revenue vs media ultimi 14 giorni, con alert quando le curve divergono significativamente
  4. SENTINEL genera alert anche nel weekend e nei festivi (scheduling ridotto, 2x/giorno)
  5. Le soglie sono calibrate su due livelli: alert operativo (30% deviazione) e alert di attenzione (5-15% deviazione)
**Plans**: 4 plans in 2 waves

Plans:
- [ ] 01-01-PLAN.md — Linear regression drift detection (14-30 day window)
- [ ] 01-02-PLAN.md — Yesterday and 14d moving average comparisons
- [ ] 01-03-PLAN.md — Dual thresholds and weekend scheduling
- [ ] 01-04-PLAN.md — Frontend visualization (drift charts, comparative metrics)

### Phase 2: Nuovi Tipi Alert
**Goal**: SENTINEL rileva i tre pattern operativi critici che oggi non copre: margine sotto soglia, coverage azzerata, pricing rule errate — come nuove regole nel sistema A0-A3 esistente
**Depends on**: Phase 1
**Requirements**: ALRT-01, ALRT-02, ALRT-03
**Extends**: anomaly_detector agent (add A5/A6/A7 rules alongside existing A0-A3), triage_classifier agent (add coverage-zero triage logic), alerting_rules.yaml (add margin/coverage thresholds), alert detail page (add triage-specific views for new alert types)
**Success Criteria** (what must be TRUE):
  1. Quando il margine % di un publisher scende sotto la soglia configurata, l'operatore riceve un alert con dettaglio margine attuale vs soglia
  2. Quando la coverage di un publisher va a zero, il sistema genera un alert con triage dedicato che indica la causa probabile (policy Google, MCM, ads.txt)
  3. Quando coverage cala e contemporaneamente il CPM schizza, il sistema genera un alert "pricing rule errata" con evidenza della correlazione
**Plans**: 4 plans in 3 waves

Plans:
- [ ] 02-01-PLAN.md — A5 margin/eCPM drop alert rule
- [ ] 02-02-PLAN.md — A6 coverage-zero alert with root cause triage
- [ ] 02-03-PLAN.md — A7 pricing-rule alert (coverage↓ + CPM↑ correlation)
- [ ] 02-04-PLAN.md — Frontend visualization for new alert types

### Phase 3: Operator Workflow
**Goal**: Gli operatori possono interagire con gli alert (feedback, assegnazione, interventi manuali) e il sistema accumula conoscenza operativa per publisher
**Depends on**: Phase 1
**Requirements**: FEED-01, FEED-02, FEED-03, FEED-04, INTV-01, INTV-02, INTV-03
**Extends**: alert detail page (add feedback panel, assignment dropdown, intervention form below existing 7-step view), SQLite schema (add feedback, interventions, assignments tables), backend API routes.py (add feedback/intervention endpoints), existing alert list page (add assignment filter)
**Success Criteria** (what must be TRUE):
  1. L'operatore puo confermare un alert come reale o segnalarlo come falso positivo scegliendo tra categorie predefinite, e puo aggiungere un commento testuale
  2. L'operatore puo assegnare un alert a un collega del team, che lo vede nella propria lista
  3. Quando si visualizza un alert, il sistema mostra lo storico dei feedback precedenti sullo stesso publisher/pattern
  4. L'operatore puo registrare un intervento manuale in meno di 1 minuto (data, publisher, tipo, valore prima/dopo, motivo) e collegarlo a un alert
  5. I periodi con interventi manuali registrati vengono annotati/esclusi nella baseline degli alert futuri
**Plans**: 4 plans in 2 waves

Plans:
- [ ] 03-01-PLAN.md — Feedback system (DB schema + backend API for REAL/FALSE_POSITIVE categories, comments, history)
- [ ] 03-02-PLAN.md — Assignment system (DB schema + backend API for alert assignment with email validation)
- [ ] 03-03-PLAN.md — Intervention tracking (DB schema + backend API + baseline exclusion logic)
- [ ] 03-04-PLAN.md — Frontend UI (FeedbackPanel, InterventionPanel, assignment dropdown, filters)

### Phase 4: Notifiche Slack
**Goal**: Gli alert arrivano direttamente su Slack con il livello di dettaglio giusto per la severity, senza che gli operatori debbano controllare la dashboard proattivamente
**Depends on**: Phase 1
**Requirements**: NOTF-01, NOTF-02, NOTF-03
**Extends**: existing notifier agent (already has Slack Block Kit code — activate with real webhook URL and channel config), alerting_rules.yaml (add notification routing config), admin page (add Slack webhook configuration)
**Success Criteria** (what must be TRUE):
  1. Gli alert P0 generano una notifica Slack immediata sul canale dedicato SENTINEL con report completo (contributors, geo, azioni suggerite)
  2. Gli alert P1 e P2 vengono raggruppati in un riepilogo giornaliero inviato su Slack a orario configurabile
  3. Il template della notifica e configurabile per severity (P0=report completo, P2=una riga con link alla dashboard)
**Plans**: 3 plans in 3 waves

Plans:
- [ ] 04-01-PLAN.md — Slack configuration (webhook URL, channel, test connection in admin UI)
- [ ] 04-02-PLAN.md — Severity-based templates and routing (P0 immediate, P1/P2 digest queue)
- [ ] 04-03-PLAN.md — Daily digest scheduler (CronTrigger job + manual trigger endpoint)

### Phase 5: Dati Live e Multi-canale
**Goal**: SENTINEL si connette a dati reali via Athena con refresh orario, monitora tutti i canali di vendita, e usa CTR/Viewability come indicatori predittivi
**Depends on**: Phase 1
**Requirements**: DATA-01, DATA-02, DATA-03
**Extends**: existing Athena connector (already coded but disabled — activate with credentials and schema mapping), data_fetcher agent (extend query logic for new channels and metrics), existing fallback chain (Athena -> GAM -> Parquet already defined), admin page (already has datasource config UI — wire to real Athena settings)
**Success Criteria** (what must be TRUE):
  1. SENTINEL riceve dati aggiornati da Athena ogni ora e li usa per la pipeline di alerting (con fallback a parquet se Athena non disponibile)
  2. L'operatore vede revenue breakdown per tutti i canali: Open Market, diretta, HB&TAM, preferred deal, deal guaranteed
  3. Il sistema monitora CTR e Viewability AdEx e genera alert predittivi quando questi leading indicator calano (anticipando il calo revenue Open Market)
**Plans**: TBD

Plans:
- [ ] 05-01: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6
Note: Phases 2, 3, 4, 5 all depend on Phase 1 but are independent of each other. After Phase 1, they can be executed in any order. Phase 6 depends on all previous phases (reviews documentation after all changes).

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Alerting Evoluto | 0/? | Complete    | 2026-02-21 |
| 2. Nuovi Tipi Alert | 4/4 | Complete    | 2026-02-21 |
| 3. Operator Workflow | 0/? | Not started | - |
| 4. Notifiche Slack | 0/? | Not started | - |
| 5. Dati Live e Multi-canale | 0/? | Not started | - |
| 6. Revisione Documentale | 0/? | Not started | - |

### Phase 6: Revisione Documentale

**Goal:** Tutta la documentazione in-app (tecnica e operativa) riflette accuratamente le nuove regole, soglie, alert types e workflow introdotti nelle fasi 1-5
**Depends on:** Phase 5
**Plans:** 4/4 plans complete

Plans:
- [ ] TBD (run /gsd:plan-phase 6 to break down)
