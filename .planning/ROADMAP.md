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

- [ ] **Phase 1: Alerting Evoluto** - Extend anomaly_detector agent with drift regression, add yesterday/14d comparisons, calibrate dual thresholds, enable weekend scheduling
- [ ] **Phase 2: Nuovi Tipi Alert** - Add A5 (margin), A6 (coverage-zero), A7 (pricing-rule) alert rules to existing pipeline
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
**Plans**: TBD

Plans:
- [ ] 01-01: TBD
- [ ] 01-02: TBD

### Phase 2: Nuovi Tipi Alert
**Goal**: SENTINEL rileva i tre pattern operativi critici che oggi non copre: margine sotto soglia, coverage azzerata, pricing rule errate — come nuove regole nel sistema A0-A3 esistente
**Depends on**: Phase 1
**Requirements**: ALRT-01, ALRT-02, ALRT-03
**Extends**: anomaly_detector agent (add A5/A6/A7 rules alongside existing A0-A3), triage_classifier agent (add coverage-zero triage logic), alerting_rules.yaml (add margin/coverage thresholds), alert detail page (add triage-specific views for new alert types)
**Success Criteria** (what must be TRUE):
  1. Quando il margine % di un publisher scende sotto la soglia configurata, l'operatore riceve un alert con dettaglio margine attuale vs soglia
  2. Quando la coverage di un publisher va a zero, il sistema genera un alert con triage dedicato che indica la causa probabile (policy Google, MCM, ads.txt)
  3. Quando coverage cala e contemporaneamente il CPM schizza, il sistema genera un alert "pricing rule errata" con evidenza della correlazione
**Plans**: TBD

Plans:
- [ ] 02-01: TBD

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
**Plans**: TBD

Plans:
- [ ] 03-01: TBD
- [ ] 03-02: TBD

### Phase 4: Notifiche Slack
**Goal**: Gli alert arrivano direttamente su Slack con il livello di dettaglio giusto per la severity, senza che gli operatori debbano controllare la dashboard proattivamente
**Depends on**: Phase 1
**Requirements**: NOTF-01, NOTF-02, NOTF-03
**Extends**: existing notifier agent (already has Slack Block Kit code — activate with real webhook URL and channel config), alerting_rules.yaml (add notification routing config), admin page (add Slack webhook configuration)
**Success Criteria** (what must be TRUE):
  1. Gli alert P0 generano una notifica Slack immediata sul canale dedicato SENTINEL con report completo (contributors, geo, azioni suggerite)
  2. Gli alert P1 e P2 vengono raggruppati in un riepilogo giornaliero inviato su Slack a orario configurabile
  3. Il template della notifica e configurabile per severity (P0=report completo, P2=una riga con link alla dashboard)
**Plans**: TBD

Plans:
- [ ] 04-01: TBD

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
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5
Note: Phases 2, 3, 4, 5 all depend on Phase 1 but are independent of each other. After Phase 1, they can be executed in any order.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Alerting Evoluto | 0/? | Not started | - |
| 2. Nuovi Tipi Alert | 0/? | Not started | - |
| 3. Operator Workflow | 0/? | Not started | - |
| 4. Notifiche Slack | 0/? | Not started | - |
| 5. Dati Live e Multi-canale | 0/? | Not started | - |
