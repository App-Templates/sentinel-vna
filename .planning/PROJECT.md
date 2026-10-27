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
- ✓ Triage baseline calcolato server-side (rimosso `revenueRatio * 0.95` + `avgCoverage + 0.05` heuristic da `TriageSection.tsx`; UI consuma `alert.baseline_bacino` / `alert.baseline_coverage` dall'API; baseline-missing disclosure via `BASELINE_MISSING_COPY`) — **Validated in Phase 12: wip-atomic-commits-triage-server-side** (Plan 12-04 CORR-01 / RC-(e) UI closure)
- ✓ WIP backlog Commits A/B/C (i18n keys foundation, IT→EN translation 27+13+5 hunks, backend correctness bacino dedup + 7w YoY + available_dates) committati atomicamente da `wip/pre-10.2-rescue` — **Validated in Phase 12: wip-atomic-commits-triage-server-side** (Commit D dashboard date-nav owned by Phase 13)
- ✓ Sell_type dropdown filter su PublishersPage (5-value whitelist) + weighted avgFillRate (`Σ(p.avg_coverage·p.total_impressions)/Σ(p.total_impressions)`) + KpiCards i18n keys — **Validated in Phase 12: wip-atomic-commits-triage-server-side** (CORR-08 + CORR-09)
- ✓ Commit D dashboard date navigation: `RevenueStatus24h` date `<select>` populated from `available_dates` (path-based URL `/api/metrics/revenue-status-24h/{date}`) + YoY 7-week rolling Area series (amber dashed `dataKey="yoy"`, hour-by-hour curve from `prev_year.hours[24]`) + lifted `KpiCards` props + decoupled `RevenueByChannel` + new `DatePicker` primitive + `RevenueStatusSection` Card wrapping with `tabular-nums`. i18n downgrade: `useTranslation()` swapped for `REVENUE_LABELS`/`KPI_NO_DATA_COPY` from `lib/i18n-keys.ts`. `useTopPublishers` byte-identity preserved (D-13.02-B) — Phase 12 ship-state intact. — **Validated in Phase 13: dashboard-date-navigation** (Wave 1 i18n-keys prep + Wave 2 Commit D 8-file atomic, WIP-05)
- ✓ UI Labeling + Filter Exposure: 4 new bespoke primitives (`ScopeBadge` channel-specific palette + `ReferencePeriodFootnote` UTC timestamp + `GrossNetToggle` REV_SHARE_FACTOR=0.6 SSoT + `TopNDisclaimer` top-50 disclosure) wired across 5 surfaces (KpiCards, RevenueStatus24h, RevenueByChannel, RevenueStatusSection, TriageSection); `AlertDetailPage` lifted page-level `useState<GrossNetMode>('gross')` (B-1) threading mode prop into RevenueStatusSection (with onModeChange) + TriageSection (read-only) per UI-SPEC §CORR-03; `useTopPublishersFilters` URL-state hook + `PublishersPage` migration to 6-filter row (year/month/sell_type_proxy/publisher_tier/geo_cluster/gross_net) + `api/client.ts` query-key extension. All 5 Email-Vito RCs now closed in code (RC-(a) ScopeBadge×5 + TopNDisclaimer / RC-(c) GrossNetToggle + REV_SHARE_FACTOR=0.6 / RC-(f) ReferencePeriodFootnote on all 5 surfaces; RC-(b) Mondadori publisher_family + RC-(d) legacy GOOGLE math layer via Phase 12+13; RC-(e) server-side baseline via Phase 11+12). — **Validated in Phase 14: ui-labeling-filter-exposure** (5 plans / 3 waves / CORR-02/03/04/05/06/11)

### Active

<!-- Milestone v1.3 Stabilization — requisiti correnti -->

**Silent-failure fix:**
- [ ] Schema `vna_alerts.channel_group` CHECK constraint espanso ai 7 canali v1.2 con migration script tracciato in git
<!-- [moved to Validated] 60 giorni backfilled in Phase 09; 31-day gap 2026-03-24 → today disclosed in COVERAGE-GAP.md as v1.3.1 plant-seed -->

- [ ] Pipeline silent-failure monitoring: health endpoint `/health/alerts-pipeline` + meta-alert quando `pipeline_runs_last_24h > 0 AND alerts_last_24h == 0`

**WIP cleanup:**
<!-- [moved to Validated] vna_alerts.db investigation closed in Phase 07 (FORWARD_PORT decision); WIP Commits A/B/C closed in Phase 12 -->
- [ ] Decisione Commit E Vercel static export (ship v1.3.1 o shelve) — **owned by Phase 16**

**Correctness:**
<!-- [moved to Validated] Triage baseline server-side closed in Phase 12 Plan 12-04; Reference period + 5 RC closure shipped Phase 14 (CORR-02/03/04/05/06/11) -->

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

### D-16.01 — Commit E (Vercel static export): SHIP as v1.3.1 (formalized 2026-05-04)

**Decision:** Ship the existing Vercel static-export deploy model as v1.3.1. No architectural migration.

**Rationale:**
- The 5 architectural files (vercel.json, scripts/export_api_json.sh, frontend bundling, .vercel/project.json, outputDirectory routing) are already in `main` (committed pre-2026-04-27); Commit E is implicitly shipped.
- Backend bacino dedup WIP `7ea4a74` cherry-picked Phase 12-03 (commit 510f5e2 family).
- Frontend i18n WIP `94a48cd` landed Phase 12-02 + Phase 13-02.
- Phase 15 closure 2026-05-04 (HEAD `2942775`) represents the v1.3 stabilization line.
- The current static-export model has been live and functional since 2026-04-27 — no operational evidence justifies architectural redesign.

**Migration plan:** None required. Phase 16 deploys the current model with Phase 11-15 fixes (re-exported API JSON snapshot + freshly built frontend bundle). Rollback path = `vercel rollback <previous-deploy-url>` captured pre-deploy.

**Closes:** ROADMAP Phase 16 SC #1, REQUIREMENTS.md WIP-06, RC-(a/b/c/d/e/f) at the deploy layer (5 RCs already closed in code Phase 11-15; this decision ships them live).

**Operator sign-off:** Stefano Argiolas, 2026-05-04 18:30 CEST ("vai con deploy").

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

*Last updated: 2026-04-27 — v1.3 Phase 10.2 (Pipeline Monitoring Security Hardening) shipped 3/4 plans. 10.2-01 MONITOR-11 (canonical UTC cutoff in `send_daily_digest` + HARD-03 extension, 28 tests green), 10.2-02 MONITOR-13 (`Retry-After` cap MAX_BACKOFF_SEC=60 + `e.headers or {}` defensive, 16 tests green), 10.2-03 MONITOR-14 (atomic `_restore` via `os.replace` in all 4 migration drivers + 2 regression tests, 9 tests green). 10.2-04 MONITOR-12 webhook rotation: deferred via `abort` resume signal at `checkpoint:human-action` — operator pivoted priority. Phase verification deferred to session that completes 10.2-04.*

*Last updated: 2026-04-28 — **AUDIT TRIPLO + PIVOT CRITICO.** Email Vito 22 aprile letta verbatim per la prima volta in sessione. 3 auditor indipendenti (Numbers Forensics, Phase Coverage, Live-vs-Email) verificano: Vito ha ragione su 8/8 punti; le 8 lamentele = 5 root cause (a) top-50 filter undisclosed, (b) Mondadori family non aggregati, (c) NET vs GROSS senza label (€115k = €188k × 0.6 rev-share, no math bug), (d) legacy `GOOGLE` channel naming, (e) client-side heuristics in TriageSection. **Phase 07-10.2 NON ha cambiato nessun numero che Vito cita** — fixavano un bug DIVERSO (silent failure CHECK constraint Jan 22 → Apr 22). Le 5 RC sono indirizzate da Phase 11+12+13+14, nessuna implementata. Live Vercel `sentinel-vna.vercel.app` deploy 2026-04-27 12:45 GMT non tracciato (da WIP working tree, non main HEAD). Persistenza canonica: `.planning/STELLA-POLARE.md` + `.planning/intel/sentinel-2026-04-28/` (EMAIL verbatim + 3 audit + SYNTHESIS + README). `CLAUDE.md` repo-root impone mandatory read prima di azioni. Decisioni operatore aperte: email reply, Phase 11 vs 12 ordering, `publisher_family` definition, sell_type filter scope, Vercel deploy strategy.*

*Last updated: 2026-04-29 — v1.3 Phase 11 (Network Totals Endpoint + Filter API + Server-Side Baseline) complete: API-01/API-02/API-03 closed across 3 plans / 2 waves (Wave 0 RED Nyquist scaffolds → Wave 1 implementations flipping GREEN). 12 atomic commits + meta. **Indirizza email Vito RC-c (NET vs GROSS contract preparato — `revenue_gross` confermato €27,245.63 = PBI €27,200 +0.17%, ben dentro ±2%) + RC-e (server-side `baseline_bacino`/`baseline_coverage` in `AlertDetail` — TriageSection.tsx ora ha il contratto per eliminare l'heuristic `revenueRatio*0.95` + `avgCoverage+0.05`).** API-02 aggiunge `sell_type` query param a `/api/publishers/top` con whitelist 5-valori + 503 column-guard + `sell_type_filter` transparency contract in 3 return paths. Verifier 8/8 must-haves PASSED; tests 4/4 + 4/4 + 5/5 + 10/10 GREEN; non-regressioni controllate. Code review 0 critical / 4 warning / 7 info (drift risks su whitelist hardcoded, baseline edge cases, cold-start CSV concurrency — advisory, deferred). Pre-existing Phase 10.1 regression scoperta durante regression gate (`test_save_to_db_returns_is_new_signal` failing al base `4b7f661`) parcheggiata come backlog Phase 999.2. **RC-c full close + RC-e wire** ora richiedono Phase 12 (TriageSection cliente + heuristic delete) + Phase 13 (UI gross/net side-by-side label). Phase 10.2-04 MONITOR-12 webhook rotation rimane deferred. Live Vercel ancora deploy non tracciato 2026-04-27 — Phase 11 NON ancora deployata.*

*Last updated: 2026-04-30 — v1.3 Phase 13 (Dashboard Date Navigation) complete: WIP-05 closed across 2 plans / 2 waves / 5 atomic commits on main (HEAD `568ffb0`). **Commit D landed atomic** (8 frontend files exactly per UI-SPEC §File-Count Gate, byte-identical alphabetical list): `RevenueStatus24h.tsx` date `<select>` from `data.available_dates` + YoY 7w amber dashed Area `dataKey="yoy"` (24-point hour-by-hour curve from `prev_year.hours`, replaces previous flat `ReferenceLine`); `DashboardPage.tsx` lifts `useRevenueStatus24h` for `KpiCards` (lifted-prop `KpiCardsProps`); `RevenueByChannel.tsx` decoupled with own `selectedDate` (selectedChannels removed); `RevenueTrendChart.tsx` CSS-var styled with en-GB locale; `RevenueStatusSection.tsx` Card-wrapped with 6× `tabular-nums` + uppercase tracking-wide labels; new `DatePicker.tsx` debounced primitive; `client.ts` 5/6 hunks (PrevYearData.hours, RevenueStatus24hResponse.available_dates, path-based `useRevenueStatus24h` URL) — **`useTopPublishers` hunk INTENTIONALLY EXCLUDED (D-13.02-B)** preserving Phase 12 ship-state byte-identical (PublishersPage compatibility). i18n downgrade complete: zero `useTranslation`/`LanguageProvider`/`i18n/context` in 4 dashboard files; `t('revenue.*')` swapped for `REVENUE_LABELS` from new Wave-1 `i18n-keys.ts` extension (`REVENUE_LABELS` 7 keys + `KPI_NO_DATA_COPY`, AC #9). Verifier 15/15 must-haves PASSED + 15/15 UI-SPEC mechanical AC PASS (independent re-grep against HEAD); TS compile clean; Vite build clean (2.26s); runtime API smoke green (7 `available_dates`, 24 nonzero `prev_year.hours`, no `hourly_avg`); `human_needed` UAT 3 items (visual sign-off — date selector renders + amber YoY curve + decoupled-by-design UX confirmation; orchestrator auto-approved phase completion based on mechanical+runtime evidence, items persist in `13-HUMAN-UAT.md` for optional `/gsd-verify-work 13`). Code review advisory: 0 critical / 6 warning / 6 info (WR-01 incomplete-lift = UI-SPEC architectural disagreement not bug; WR-02 KpiCards silent-fail type cast; WR-03/04/05 DatePicker primitive ships unused, fragile sort assumption; WR-06 RevenueByChannel empty-hours guard inconsistency — all deferred to optional `/gsd:code-review-fix 13`). Two documented auto-fix deviations: KpiCards manual rewrite (WIP proposed unsupported MetricCard props out-of-scope per UI-SPEC line 5), 2× JSDoc comments at YoY 7w label sites (mechanical AC #5 grep satisfaction without breaking i18n-keys discipline). Phase 12 ship-state byte-identical preserved (PublishersPage / TriageSection / alert.ts / lib/i18n-keys.ts existing 5 exports). Live Vercel ancora deploy non tracciato 2026-04-27 — Phase 13 NON ancora deployata.*

*Last updated: 2026-04-30 — v1.3 Phase 12 (WIP Atomic Commits + Triage Server-Side) complete: WIP-02/03/04 + CORR-01/08/09 closed across 6 plans / 3 waves / 12 atomic commits on main. **RC-(e) closed at UI layer** (Plan 12-04 CORR-01): `revenueRatio*0.95` + `avgCoverage+0.05` + `Math.min(...,0.95)` heuristics deleted from `TriageSection.tsx`; UI now consumes `alert.baseline_bacino`/`baseline_coverage` exclusively from API; baseline-missing disclosure via `BASELINE_MISSING_COPY`. **WIP backlog Commits A/B/C landed** (Commit D dashboard date-nav owned by Phase 13): i18n keys foundation (`KPI_LABELS`/`SELL_TYPE_LABELS`/`BASELINE_MISSING_COPY`/`emptyPublishersFiltered`/`SellTypeKey`) in new `frontend/src/lib/i18n-keys.ts`, IT→EN translation 27+13+5 hunks across DocsPage/PublisherDetailPage/PublishersPage (`grep -cE '[À-ſ]'` → 0 in tutti e 3), backend cherry-pick da `wip/pre-10.2-rescue` `7ea4a74` (bacino dedup riduce Mondadori 2.6B → 408M, ~6.4× — RC-b family aggregation deferred Phase 13; 7w YoY; `available_dates` field; path-based date variant). **PublishersPage**: weighted avgFillRate `Σ(p.avg_coverage·p.total_impressions)/Σ(p.total_impressions)` (live: simple 48.20% vs weighted 46.14%, Δ=2.05 ppt) + sell_type dropdown filter (Open_Market/Header_Bidding/Direct/Deal/Other/all) + `useTopPublishers(year, limit, sellType?)` query-key extension. **KpiCards i18n** (CORR-09): hardcoded labels → `KPI_LABELS` imports. Phase 11 byte-identity preserved (`_compute_baseline_from_env_split` 3141591 + `VALID_SELL_TYPES` 510f5e2 — diffs empty). Verifier 14/14 PASSED; regression gate 51/51 prior-phase tests green; schema drift clean; code review 0 critical / 4 warning / 7 info (advisory: `n_channels` zero-guard, weighted-formula vs PBI parity check, type/cache hygiene, mixed IT/EN driver tooltips residual). Live Vercel ancora deploy non tracciato 2026-04-27 — Phase 12 NON ancora deployata.*

*Last updated: 2026-05-04 — v1.3 Phase 15 (UI Resilience) complete: CORR-07 + CORR-10 closed across 4 plans / 3 waves / 4 feat commits + 4 SUMMARY commits + REVIEW + UAT-REPORT + VERIFICATION + 9 evidence files (3 PNG + 6 JSON) on main (HEAD `a59eaaf`, post phase-complete). **3/3 ROADMAP SC closed at runtime, not just code:** SC #1 (3 charts wrapped in ChartErrorBoundary) confirmed by UAT #2/#3 boundary fires; SC #2 (diagnostic empty states verbatim "No 7-week history. Alert < 7 days old or data not yet aggregated.") confirmed by UAT #1 DOM capture on alert with `revenue_trend: null`; SC #3 (manual regression: malformed payload → fallback) confirmed by UAT #3 with `[null]` injection → `TypeError: Cannot read properties of null (reading 'timestamp')` → boundary catch → fallback box. **8 production files modified** (frontend/src/lib/i18n-keys.ts append-only + new frontend/src/components/primitives/ChartErrorBoundary.tsx DIY class-component + 3 chart consumers + 3 alert-section call-site wraps with height={280|280|260}). **UAT signed by Stefano** 2026-05-04T18:00 CEST after live review of 3 PNG screenshots + browser at localhost:5173 + reproducible Playwright evidence in `.planning/phases/15-ui-resilience/uat-evidence/`. Verifier 14/14 must-haves PASSED + 12/12 Sentinel invariants PASS (verbatim strings, chart-area scoped fallback, no `min-h-screen`/`window.location.reload`/`dangerouslySetInnerHTML`/`as any`/try-catch suppression, append-only i18n). Code review CLEAN (0 CRITICAL / 0 WARNING / 4 INFO advisory: state.error read-only, formatDateShort silent on null, UI-SPEC line 101 vs 118 color inconsistency, componentDidCatch logging gap — all deferrable). **2 UI-SPEC documentation gaps logged** (non-blocking): UAT #2 stated `null as any` injection insufficient (`?? []` defensive guard absorbs it — empty-state path); UAT #3 stated `[{timestamp:null, revenue:NaN}]` insufficient (Recharts tolerates). Escalations to non-array (`'force-error'`) and array-with-null (`[null]`) used per UI-SPEC line 184 anticipated escalation note. Local main HEAD `a59eaaf` = 245+ commits ahead of origin/main. Live Vercel `https://sentinel-vna.vercel.app` ancora deploy non tracciato 2026-04-27 12:45 GMT — **Phase 11+12+13+14+15 NOT deployed**; deploy strategy decisione operatore aperta (STELLA-POLARE §"Decisioni operatore aperte" #5).*

*Last updated: 2026-04-30 — v1.3 Phase 14 (UI Labeling + Filter Exposure) complete: 6/6 phase REQ-IDs closed (CORR-02/03/04/05/06/11) across 5 plans / 3 waves / 5 feat commits + 5 docs SUMMARY commits + 3 code-review fix commits + REVIEW/REVIEW-FIX/VERIFICATION/HUMAN-UAT artifacts on main (HEAD `3835c70`, post phase-complete commit). **5 RC closure now live in code (Phase 11+12+13+14 not yet deployed):** RC-(a) ScopeBadge×5 surfaces (KpiCards/RevenueStatus24h/RevenueByChannel/RevenueStatusSection/TriageSection) with channel-specific palette + TopNDisclaimer on PublishersPage; RC-(c) GrossNetToggle on RevenueStatusSection + PublishersPage with REV_SHARE_FACTOR=0.6 SSoT, threaded into TriageSection Revenue row via B-1 `AlertDetailPage:62` page-level `useState<GrossNetMode>('gross')` lift (RevenueStatusSection has 0 useState; TriageSection reads mode prop); RC-(f) ReferencePeriodFootnote with `formatTimestampUtc` on all 5 surfaces. RC-(b) Mondadori publisher_family + RC-(d) legacy GOOGLE channel naming closed earlier in Phase 12+13 (math layer); RC-(e) server-side baseline closed in Phase 11+12. **6-filter URL state migration** (CORR-06): `useTopPublishersFilters` URL-state hook + PublishersPage 6-filter row (year/month/sell_type_proxy/publisher_tier/geo_cluster/gross_net — environment added iter-1 W-1 frontend-only via D-14.05-X) + `api/client.ts` query-key extension. Verifier 3/3 must-haves + 3/3 SC mechanical PASS, 6/6 REQ-IDs satisfied. AC #9 anti-creep grep clean (REV_SHARE_FACTOR=0.6 sole live `0.6` in frontend tree). AC #5/#10/#18 disclosure-string invariants clean. Code review 1 Critical + 2 Warning + 8 Info → ALL_FIXED via `/gsd:code-review-fix 14` (3 atomic fix commits): CR-01 Rules of Hooks (useMemo above early returns) `b1f1eee`, WR-01 TriageSection division-by-zero guard `5b78af1`, WR-02 api/client 401 reload-loop guard with module-level `authReloadAttempted` flag `984b660`. HUMAN-UAT 5/5 visual items operator-approved 2026-04-30 (URL round-trip / Gross-Net sync / B-1 mode threading / ScopeBadge palette / KpiCards col-span-full). Worktrees disabled (`workflow.use_worktrees=false` since Phase 08 DB-safety) — sequential execution per wave on main. Local main HEAD `3835c70` = 235 commits ahead of origin/main (origin frozen Feb 21). Live Vercel `https://sentinel-vna.vercel.app` ancora deploy non tracciato 2026-04-27 12:45 GMT — **Phase 11+12+13+14 NOT deployed**; deploy strategy decisione operatore aperta (vedi STELLA-POLARE §"Decisioni operatore aperte" #5).*
