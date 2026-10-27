# Requirements: SENTINEL

**Defined:** 2026-04-22 (milestone v1.3 Stabilization)
**Core Value:** Trovare gli alert in tempo quasi reale comunicando solo ciò che è davvero importante

## v1.3 Requirements (Current Milestone — updated after deep audit 2026-04-22 evening)

Requirements for production-grade 10/10 release. Updates riflettono 4 decisioni (D1-D4) approvate da Stefano + findings dei 3 deep agent + micro-query numerica Mondadori Feb.

### Schema & Silent-Failure Fix

- [x] **SCHEMA-01**: Schema `vna_alerts.channel_group` CHECK constraint accetta i 7 canali v1.2 (GOOGLE, OPEN_BIDDING, GOOGLE_ADEX, DEAL, DIRECT, TAM, HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC) via migration script tracciato in `scripts/migrations/`
- [x] **SCHEMA-02**: `backend/db/models.py` CHECK constraint sincronizzato con lo schema DB live (no drift possibile)
- [x] **SCHEMA-03** 🆕: ETL conserva `measurable_impressions` (remove from drop list `etl_csv_to_parquet.py:187`). Abilita fill rate PBI-match (35.2% = `measurable_impressions / bacino`)
- [x] **SCHEMA-04** 🆕: Aggiungere colonna `sell_type_proxy` a daily_aggregated.parquet via mapping `channel_group → {Open_Market, Header_Bidding, Direct, Deal, Other}` (confidence 95%, confermato da `alerting_rules.yaml:84-91`)
- [x] **BACKFILL-01**: Re-run pipeline genera alert per range 2026-01-23 → oggi (90+ giorni alert recuperati) da parquet ricostruito (decisione D3 = parquet attuale post-SCHEMA fixes)
- [x] **MONITOR-01**: Endpoint `/health/alerts-pipeline` espone `{last_alert_at, alerts_last_24h, pipeline_runs_last_24h}`
- [x] **MONITOR-02**: Meta-alert interno su `pipeline_runs_last_24h > 0 AND alerts_last_24h == 0` (P0 critical, Slack + log)
- [x] **MONITOR-03**: Campo `alerts_written_count` aggiunto a `pipeline_runs` per observability
- [x] **MONITOR-04** 🆕 (Phase 10.1): `alerts.created_at` written in UN UNICO formato canonico (notifier + operations + backfill); migration normalizza 438 righe esistenti; drift test impedisce regressione
- [x] **MONITOR-05** 🆕 (Phase 10.1): Watchdog temporal queries immune a datetime string-compare edge cases (strftime o space-separator ovunque) AND filtered `mode='LIVE'` su pipeline_runs
- [x] **MONITOR-06** 🆕 (Phase 10.1): `find_open_alert` dedup window 6h rispettata su tutti i calendar-day boundaries (stessa fix di MONITOR-05 applicata al dedup path)
- [x] **MONITOR-07** 🆕 (Phase 10.1): Slack retry path distingue HTTPError vs URLError, onora `Retry-After` su 429, zero dead code
- [x] **MONITOR-08** 🆕 (Phase 10.1): `alerts_written_count` counter semantics allineato a INSERT intent (0 su dedup UPDATE path; 1 solo su nuova riga)
- [x] **MONITOR-09** 🆕 (Phase 999.1): Script diagnostico read-only + `999.1-DIAGNOSIS.md` che documenta root-cause della silenzio LIVE dal 2026-03-23 con ipotesi H1/H2/H3 rankate ed evidenze
- [x] **MONITOR-10** 🆕 (Phase 999.1): Decisione remediation operator-signed (`999.1-DECISION.md`: Path A/B-1/B-2/C) + promozione ROADMAP §Backlog→§Phases + config toggle condizionale (solo Path B) gated da checkpoint
- [ ] **MONITOR-11** 🆕 (Phase 10.2): `send_daily_digest` time cutoff usa formato canonico naive UTC microseconds (matches Migration 004 D-10.1-01); test asserts cross-format mismatch impossibile; HARD-03 drift detector esteso al digest callsite
- [ ] **MONITOR-12** 🆕 (Phase 10.2): Slack webhook in `config/alerting_rules.yaml` è una URL reale operator-supplied (NON `TEST123`); rotation procedure documentata; legacy URL purgata da git history o R-05 documented decision
- [ ] **MONITOR-13** 🆕 (Phase 10.2): `Retry-After` parsing in `send_meta_alert` bounded (≤60s upper cap); test asserts upstream `Retry-After: 999999` non blocca lo scheduler thread (anti-DoS WR-02)
- [ ] **MONITOR-14** 🆕 (Phase 10.2): `_restore` operations atomic (transactional context); test asserts partial-restore mid-failure lascia DB pre-restore state, mai parziale (WR-03)

### API Surface (hybrid PBI parity)

- [ ] **API-01** 🆕: Nuovo endpoint `/api/metrics/network-totals?date=...&channel=...` che legge `data/sentinel_db/*.csv` upstream via `pyarrow.csv.read_csv` streaming (bypassa top-50 parquet filter per dashboard PBI-match) — implementa D1 hybrid
- [ ] **API-02** 🆕: Query param `sell_type` su `/api/publishers/top`, `/api/alerts`, `/api/metrics/revenue-status-24h` (mappa ai channel_group via derivation SCHEMA-04)
- [ ] **API-03** 🆕: Response alert payload include `baseline_bacino`, `baseline_coverage` calcolati server-side (7w rolling same-weekday) — elimina heuristic frontend

### WIP Reconciliation (56 file)

- [ ] **WIP-01**: Binary-diff `data/vna_alerts.db*` investigato: schema changes locali documentati, migration script creato se necessario, o reset pulito con rationale
- [ ] **WIP-02**: Commit A atomico — design system + i18n infrastructure (10 file: index.css, Card/Button/Badge/Skeleton, Sidebar, main.tsx, lib/utils, .gitignore)
- [ ] **WIP-03**: Commit B atomico — traduzione IT→EN contenuti (10 file: DocsPage, PublisherDetailPage, layout labels)
- [ ] **WIP-04**: Commit C atomico — backend data correctness (2 file: routes.py YoY rolling 7w + complete-day detection + available_dates; publisher_routes.py bacino dedup fix)
- [ ] **WIP-05**: Commit D atomico — dashboard date navigation + nuovo API contract (8 file: RevenueStatus24h, client.ts, charts, pages con month selector)
- [ ] **WIP-06**: Decisione Commit E Vercel static export — ship come v1.3.1 o shelve con rationale documentato

### Correctness (UI trustworthiness)

- [ ] **CORR-01**: Triage baseline server-side — `baseline_bacino` + `baseline_coverage` dal backend (API-03). `TriageSection.tsx:31-32` rimuove heuristic `revenueRatio * 0.95` + `avgCoverage + 0.05`
- [ ] **CORR-02**: Alert `revenue_current` reference period esplicito in UI (etichetta "for [timestamp hour UTC]" su metric card)
- [ ] **CORR-03** 🆕: Revenue display **gross + net side-by-side** con label "€X gross (net €Y post rev-share 60%)" — decisione D2. Toggle default GROSS (PBI-aligned), NET sempre visibile come subtitle.
- [ ] **CORR-04** 🆕: Channel scope badge prominente su `RevenueStatus24h`, `RevenueByChannel`, `KpiCards` → "GOOGLE_ADEX only" dove applicabile
- [ ] **CORR-05** 🆕: Reference period + currency + timezone label su ogni metric card (as of [timestamp] UTC, EUR)
- [ ] **CORR-06** 🆕: Filter state riflesso in page titles + URL params (PublishersPage migra da `useState` locale a URL, come `useAlertFilters`)
- [ ] **CORR-07** 🆕: Diagnostic empty states sui charts (RevenueTrendChart: "No 7-week history. Alert &lt; 7 days old or data not yet aggregated")
- [ ] **CORR-08** 🆕: Rimuovere `avgFillRate = simple_average` in `PublishersPage.tsx`, sostituire con weighted by impressions
- [ ] **CORR-09** 🆕: i18n keys per `KpiCards.tsx:72-111` (RPM/CTR/Viewability/GrossMargin labels hardcoded inglese attualmente bloccano i18n WIP)
- [ ] **CORR-10** 🆕: Error boundaries su chart components (`RevenueTrendChart`, `EnvironmentBarChart`, `GeoBreakdownPieChart`)
- [ ] **CORR-11** 🆕: Filter UI derivati da parquet: sell_type_proxy dropdown, geo_cluster, environment drill-down, publisher tier A/B/C, gross/net toggle

### Migration & Cleanup

- [x] **MIGRATE-01** 🆕: Deprecare alert generati pre-2026-02-01 (stale channel naming "GOOGLE", revenue value non allineato al parquet v1.2). Strategia: soft-delete via flag + regenerate dal parquet post-BACKFILL-01
- [ ] **CLEAN-01** 🆕: Valutare `floor_cpm` column: rimuovere dallo schema (dead, sempre NaN) o implementare population da upstream/manual intervention
- [ ] **CLEAN-02** 🆕: Gestione `Mondadori` + `Mondadori_npa` (GDPR non-consent variant) — aggregazione logica in UI o disclosure side-by-side

### Hardening (regression prevention)

- [ ] **HARD-01**: Contract test `tests/contracts/test_parquet_db_ui.py` verifica coerenza cross-layer su 1 alert known-good per ogni canale (7 casi)
- [ ] **HARD-02**: `DATA_INTEGRATION.md` aggiornato a v1.2 schema 18-field + ETL pipeline `etl_csv_to_parquet.py` + PBI↔Sentinel reproducibility matrix
- [ ] **HARD-03**: CI gate GitHub Actions: fallisce se `backend/db/models.py` CHECK constraint diverge dal DB schema live
- [ ] **HARD-04** 🆕: VALID contract tests — validazione numerica PBI match per ogni metric (Mondadori Feb bacino ≤ 0.5%, Jan 12 GOOGLE_ADEX gross ≤ 2%, network total gross ≤ 2%)

### Documentation

- [ ] **DOC-01** 🆕: Aggiornamento `DATA_INTEGRATION.md` con sezione "PBI↔Sentinel Gap Disclosure":
  - OM revenue taxonomy delta (PBI include ~€40k di DIRECT in OM che Sentinel classifica separatamente)
  - eCPM/RPM denominator differences
  - Hourly YoY synthetic vs measured
  - Fill rate requires measurable_impressions (resolved via SCHEMA-03)
  - device_format / deal_type subclassification unresolvable

## v1.4+ Requirements (Deferred)

### Athena Live Connection
- **ATHENA-01/02/03**: Connector + hourly refresh + fallback chain

### Multi-Channel Hourly
- **HOURLY-01**: Estendere sorgente hourly oltre GOOGLE_ADEX (richiede nuova ingestion)

### Intelligence Layer
- **INTEL-01**: Soglie dinamiche per stagionalità
- **INTEL-02**: Auto-suggerimento falso positivo da feedback storico
- **INTEL-03**: Suggerimenti d'azione pattern-based
- **INTEL-04**: Publisher tiering automatico

### Data & Operations
- **OPS-01**: ETL scheduler automatico (cron/systemd + health check)
- **OPS-02**: `sell_type` REALE in schema (se upstream lo rende disponibile) — per ora v1.3 usa proxy SCHEMA-04
- **OPS-03**: Publisher ID normalization + dedup (mondadori vs Mondadori vs AdGage_Mondadori)
- **OPS-04**: Timezone Europe/Rome optional (attualmente UTC-only disclosed)

## Out of Scope v1.3

| Feature | Reason |
|---------|--------|
| Esecuzione azioni dirette su GAM | Troppo rischioso |
| GAM change history API | Complessità alta |
| Benchmark competitor | Dati non disponibili |
| App mobile | Web responsive sufficient |
| Page views / Analytics | v1.4+ |
| ML soglie dinamiche | v1.4+ |
| Real-time streaming | Refresh periodico sufficient |
| `sell_type` reale upstream | Sostituito da sell_type_proxy (SCHEMA-04) |
| Hourly 7-channel | Limite sorgente `hour_kpi.csv` |
| Rebuild parquet senza top-50 filter | Sostituito da hybrid `/network-totals` endpoint (API-01) — decisione D1 |
| OM revenue exact PBI-match | Taxonomy delta strutturale, documentato in DOC-01 |
| `measurable_impressions` custom computation | Resolved by SCHEMA-03 (stop dropping in ETL) |

## Traceability

Updated 2026-04-22 after deep audit findings.

| Requirement | Phase | Status |
|-------------|-------|--------|
| WIP-01 | 07 | Pending |
| SCHEMA-01 | 08 | Complete |
| SCHEMA-02 | 08 | Complete |
| SCHEMA-03 🆕 | 08.5 | Pending |
| SCHEMA-04 🆕 | 08.5 | Pending |
| BACKFILL-01 | 09 | Complete |
| MIGRATE-01 🆕 | 09 | Complete |
| MONITOR-01 | 10 | Complete |
| MONITOR-02 | 10 | Complete |
| MONITOR-03 | 10 | Complete |
| MONITOR-04 🆕 | 10.1 | Pending |
| MONITOR-05 🆕 | 10.1 | Pending |
| MONITOR-06 🆕 | 10.1 | Pending |
| MONITOR-07 🆕 | 10.1 | Pending |
| MONITOR-08 🆕 | 10.1 | Pending |
| MONITOR-09 🆕 | 999.1 | Pending |
| MONITOR-10 🆕 | 999.1 | Pending |
| MONITOR-11 🆕 | 10.2 | Pending |
| MONITOR-12 🆕 | 10.2 | Pending |
| MONITOR-13 🆕 | 10.2 | Pending |
| MONITOR-14 🆕 | 10.2 | Pending |
| API-01 🆕 | 10.5 | Pending |
| API-02 🆕 | 10.5 | Pending |
| API-03 🆕 | 11 | Pending |
| WIP-02 | 11 | Pending |
| WIP-03 | 11 | Pending |
| WIP-04 | 11 | Pending |
| CORR-01 | 11 | Pending |
| CORR-08 🆕 | 11 | Pending |
| CORR-09 🆕 | 11 | Pending |
| WIP-05 | 12 | Pending |
| CORR-02 | 13 | Pending |
| CORR-03 🆕 | 13 | Pending |
| CORR-04 🆕 | 13 | Pending |
| CORR-05 🆕 | 13 | Pending |
| CORR-06 🆕 | 13 | Pending |
| CORR-11 🆕 | 13 | Pending |
| CORR-07 🆕 | 13.5 | Pending |
| CORR-10 🆕 | 13.5 | Pending |
| WIP-06 | 14 | Pending |
| CLEAN-01 🆕 | 14.5 | Pending |
| CLEAN-02 🆕 | 14.5 | Pending |
| HARD-01 | 15 | Pending |
| HARD-02 | 15 | Pending |
| HARD-03 | 15 | Pending |
| HARD-04 🆕 | 15 | Pending |
| DOC-01 🆕 | 15 | Pending |

**Coverage:**
- v1.3 requirements: 41 total (era 17, +24 dopo deep audit + 999.1 promotion + 10.2 hardening)
- Mapped to phases: 41 ✓
- Unmapped: 0 ✓

**Phase-to-requirements reverse index:**

| Phase | Requirements | Count |
|-------|--------------|-------|
| 07 DB WIP Investigation | WIP-01 | 1 |
| 08 Schema Migration (channel_group) | SCHEMA-01, SCHEMA-02 | 2 |
| 08.5 Schema Extensions (measurable + sell_type proxy) | SCHEMA-03, SCHEMA-04 | 2 |
| 09 Alert Backfill + Legacy Migration | BACKFILL-01, MIGRATE-01 | 2 |
| 10 Pipeline Monitoring | MONITOR-01, MONITOR-02, MONITOR-03 | 3 |
| 999.1 Investigate LIVE pipeline silent since 2026-03-23 | MONITOR-09, MONITOR-10 | 2 |
| 10.2 Pipeline Monitoring Security Hardening | MONITOR-11, MONITOR-12, MONITOR-13, MONITOR-14 | 4 |
| 10.5 Network Totals Endpoint + Filter API | API-01, API-02 | 2 |
| 11 WIP Atomic Commits + Triage Server-Side | WIP-02, WIP-03, WIP-04, CORR-01, CORR-08, CORR-09, API-03 | 7 |
| 12 Dashboard Date Navigation | WIP-05 | 1 |
| 13 UI Labeling + Filter Exposure | CORR-02, CORR-03, CORR-04, CORR-05, CORR-06, CORR-11 | 6 |
| 13.5 UI Resilience (empty states + error boundaries) | CORR-07, CORR-10 | 2 |
| 14 Vercel Static Export Decision | WIP-06 | 1 |
| 14.5 Data Cleanup | CLEAN-01, CLEAN-02 | 2 |
| 15 Hardening + PBI Contract Tests + Docs | HARD-01, HARD-02, HARD-03, HARD-04, DOC-01 | 5 |
| **Total** | | **35 ✓** |

## v1.1 Archive

v1.1 requirements (shipped 2026-02-21) sono validated e tracciate in `PROJECT.md > Requirements > Validated`. Original v1.1 REQUIREMENTS.md preservato in git history.

---
*Requirements defined: 2026-04-22*
*Last updated: 2026-04-22 evening — post deep audit expansion (17 → 35 requirements), D1-D4 decisioni approvate*
