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
- [x] **MONITOR-11** 🆕 (Phase 10.2): `send_daily_digest` time cutoff usa formato canonico naive UTC microseconds (matches Migration 004 D-10.1-01); test asserts cross-format mismatch impossibile; HARD-03 drift detector esteso al digest callsite
- [ ] **MONITOR-12** 🆕 (Phase 10.2 → DEFERRED 2026-04-27): Slack webhook in `config/alerting_rules.yaml` è una URL reale operator-supplied (NON `TEST123`); rotation procedure documentata; legacy URL purgata da git history o R-05 documented decision. **Deferred at checkpoint:human-action via "abort" resume signal** — operator priority pivoted to Vercel dashboard deploy. Re-enters Plan 10.2-04 Task 1 in a future session.
- [x] **MONITOR-13** 🆕 (Phase 10.2): `Retry-After` parsing in `send_meta_alert` bounded (≤60s upper cap); test asserts upstream `Retry-After: 999999` non blocca lo scheduler thread (anti-DoS WR-02)
- [x] **MONITOR-14** 🆕 (Phase 10.2): `_restore` operations atomic (transactional context); test asserts partial-restore mid-failure lascia DB pre-restore state, mai parziale (WR-03)

### API Surface (hybrid PBI parity)

- [x] **API-01** 🆕: Nuovo endpoint `/api/metrics/network-totals?date=...&channel=...` che legge `data/sentinel_db/*.csv` upstream via `pyarrow.csv.read_csv` streaming (bypassa top-50 parquet filter per dashboard PBI-match) — implementa D1 hybrid. _RED scaffold pronto in Plan 11-01 (`scripts/test_network_totals_pbi_parity.py`) — Wave 1 Plan 11-02 chiude._
- [x] **API-02** 🆕: Query param `sell_type` su `/api/publishers/top`, `/api/alerts`, `/api/metrics/revenue-status-24h` (mappa ai channel_group via derivation SCHEMA-04). _RED scaffold pronto in Plan 11-01 (`scripts/test_sell_type_filter.py`) — Wave 1 Plan 11-03 chiude (Phase 11 limita a `/api/publishers/top`; `/api/alerts` differito a Phase 12)._
- [x] **API-03** 🆕: Response alert payload include `baseline_bacino`, `baseline_coverage` calcolati server-side (7w rolling same-weekday) — elimina heuristic frontend. _RED scaffold pronto in Plan 11-01 (`scripts/test_alert_baseline_fields.py`) — Wave 1 Plan 11-02 chiude._

### WIP Reconciliation (56 file)

- [ ] **WIP-01**: Binary-diff `data/vna_alerts.db*` investigato: schema changes locali documentati, migration script creato se necessario, o reset pulito con rationale
- [ ] **WIP-02**: Commit A atomico — design system + i18n infrastructure (10 file: index.css, Card/Button/Badge/Skeleton, Sidebar, main.tsx, lib/utils, .gitignore)
- [x] **WIP-03**: Commit B atomico — traduzione IT→EN contenuti (10 file: DocsPage, PublisherDetailPage, layout labels)
- [x] **WIP-04**: Commit C atomico — backend data correctness (2 file: routes.py YoY rolling 7w + complete-day detection + available_dates; publisher_routes.py bacino dedup fix)
- [ ] **WIP-05**: Commit D atomico — dashboard date navigation + nuovo API contract (8 file: RevenueStatus24h, client.ts, charts, pages con month selector)
- [ ] **WIP-06**: Decisione Commit E Vercel static export — ship come v1.3.1 o shelve con rationale documentato

### Correctness (UI trustworthiness)

- [x] **CORR-01**: Triage baseline server-side — `baseline_bacino` + `baseline_coverage` dal backend (API-03). `TriageSection.tsx:31-32` rimuove heuristic `revenueRatio * 0.95` + `avgCoverage + 0.05`
- [x] **CORR-02**: Alert `revenue_current` reference period esplicito in UI (etichetta "for [timestamp hour UTC]" su metric card)
- [x] **CORR-03** 🆕: Revenue display **gross + net side-by-side** con label "€X gross (net €Y post rev-share 60%)" — decisione D2. Toggle default GROSS (PBI-aligned), NET sempre visibile come subtitle.
- [x] **CORR-04** 🆕: Channel scope badge prominente su `RevenueStatus24h`, `RevenueByChannel`, `KpiCards` → "GOOGLE_ADEX only" dove applicabile
- [x] **CORR-05** 🆕: Reference period + currency + timezone label su ogni metric card (as of [timestamp] UTC, EUR)
- [x] **CORR-06** 🆕: Filter state riflesso in page titles + URL params (PublishersPage migra da `useState` locale a URL, come `useAlertFilters`)
- [x] **CORR-07** 🆕: Diagnostic empty states sui charts (RevenueTrendChart: "No 7-week history. Alert &lt; 7 days old or data not yet aggregated")
- [x] **CORR-08** 🆕: Rimuovere `avgFillRate = simple_average` in `PublishersPage.tsx`, sostituire con weighted by impressions
- [x] **CORR-09** 🆕: i18n keys per `KpiCards.tsx:72-111` (RPM/CTR/Viewability/GrossMargin labels hardcoded inglese attualmente bloccano i18n WIP)
- [x] **CORR-10** 🆕: Error boundaries su chart components (`RevenueTrendChart`, `EnvironmentBarChart`, `GeoBreakdownPieChart`)
- [x] **CORR-11** 🆕: Filter UI derivati da parquet: sell_type_proxy dropdown, geo_cluster, environment drill-down, publisher tier A/B/C, gross/net toggle

### Migration & Cleanup

- [x] **MIGRATE-01** 🆕: Deprecare alert generati pre-2026-02-01 (stale channel naming "GOOGLE", revenue value non allineato al parquet v1.2). Strategia: soft-delete via flag + regenerate dal parquet post-BACKFILL-01
- [ ] **CLEAN-01** 🆕: Valutare `floor_cpm` column: rimuovere dallo schema (dead, sempre NaN) o implementare population da upstream/manual intervention
- [ ] **CLEAN-02** 🆕: Gestione `Mondadori` + `Mondadori_npa` (GDPR non-consent variant) — aggregazione logica in UI o disclosure side-by-side

### Publisher Mapping (Phase 17.1 — gap closure post Marco audit 2026-05-18)

- [x] **MAP-01** 🆕: `ad_unit_1_mapping.xlsx` (Marco-maintained, 432 rows × 9 cols, zero NULLs, 259 unique `publisher` values) copiato in `data/sentinel_db/ad_unit_1_mapping.xlsx` come authoritative truth source per `ad_unit_name → publisher` aggregation
- [x] **MAP-02** 🆕: Loader `_load_ad_unit_mapping()` in backend (data_fetcher_real.py o publisher_routes.py) restituisce `dict[ad_unit_name → publisher]` con caching (LRU o file-mtime watch); zero re-parse per request
- [x] **MAP-03** 🆕: `/api/publishers/top` rewriting `df["publisher_id"]` via mapping PRIMA di ogni `groupby`; mapping miss → fallback al raw `ad_unit_name` (no silent drop)
- [x] **MAP-04** 🆕: Filtro `publisher ∉ {OLD, test}` applicato a Top Publishers prima di top-N (147 OLD + 13 test ad_units esclusi dal ranking)
- [x] **MAP-05** 🆕: Hardcoded `MONDADORI_FAMILY = {Mondadori, Mondadori_npa, Mediamond, Adgage_mondocore}` block rimosso (Phase 17 over-aggregation: Mediamond e Mondocore sono publisher separati)
- [x] **MAP-06** 🆕: `config/sell_type_proxy.yaml` annotato con la definizione PBI di Marco verbatim sopra la chiave `Open_Market` (cross-ref informazionale per parity, NON collassare i 5-bucket UI di Phase 14); TAM deprecation documentata nel commento (AdOps shutdown announce, keep per cristallizzato gen-mar parquet)
- [x] **MAP-07** 🆕: Frontend `PublishersPage.tsx` row click navigation riabilitato (Phase 17 disabilitò righe con `_family` suffix; ora i nomi sono clean publisher → drilldown sempre attivo)
- [x] **MAP-08** 🆕: Drilldown endpoints (`/api/publishers/{id}/weekly-kpis|ecpm-analysis|recurring-patterns|feedback-history|interventions`) accettano clean publisher name (`Vocento`) e fanno reverse-mapping a tutti gli `ad_unit_name` mappati su quel publisher
- [x] **MAP-09** 🆕: JSON snapshot re-export via `scripts/export_api_json.sh` + Vercel re-deploy; verifica live: Top Publishers mostra `Mondadori`, `Vocento`, `Prensa Ibérica`, `Grupo Godó`, `Unidad Editorial` (NO raw `AdGage_*` / NO `_family` suffixes); Mondadori revenue ≈ €1.125k (NOT Phase 17's €1.458k over-aggregated)
- [x] **MAP-10** 🆕: `.planning/phases/17.1-publisher-mapping-correction/17.1-SUMMARY.md` commit-ato con before/after numerici (Mondadori, Mediamond, Mondocore separati; AdGage_* normalizzati; OLD/test esclusi); rationale Marco's email allegato

### Marco Feedback Hotfix (Phase 17.2, email 2026-05-19)

- [x] **HOTFIX-01** 🆕: Tooltip Revenue Impact chart in AlertDetailPage mostra label "Current Revenue" sulla serie current e "Baseline" su quella baseline (oggi mostra "baseline" su entrambe). Test asserts tooltip formatter retorna due distinte stringhe per le due serie. (V3)
- [x] **HOTFIX-02** 🆕: Etichetta "Revenue Trend (7 Weeks)" coerente con dati: scelta Path A (label fix → "Revenue Trend (Last 7 Days)") per Phase 17.2 CONTEXT.md operator decision (i dati di `useAlertTrend` sono 7 daily points dal endpoint `/api/alerts/{id}/trend`); Path B (data reshape a 7w rolling) deferred a backlog. Commit `2159ea1` (V4)
- [x] **HOTFIX-03** 🆕: Disclaimer Top-N reso prominente: aumentare font-weight + opacity + posizionare sopra la tabella (ad oggi `text-xs text-gray-500`). Mantiene il link "Network totals" funzionante. (V5) — completed 2026-05-20 (commit 406862f: `text-xs text-gray-500` → `text-sm text-gray-800` su `<div role="note">` con `border-l-4 border-amber-400 bg-amber-50`; top-N count `<span class="font-semibold">`; link `underline` sempre; rinominato `TOP_N_DISCLAIMER_COPY.linkHref → linkBase` per HOTFIX-06)
- [x] **HOTFIX-04** 🆕: Tab 3 (Top Contributors), 4 (Geo Breakdown), 5 (Environment Split) di AlertDetailPage accessibili: indagare perché Marco li vede "non più accessibili" (probabile error boundary che catcha render failure su payload incompleto o nav state che blocca click). Fix + test che asserts i 3 tab sono navigabili anche con alert payload minimo. (B1) — completed 2026-05-20 (commits `64869b3` diagnose-first DIAGNOSIS.md per-tab classification [Tab 5 = (b) AlertDetailPage:259 short-circuit `Object.keys(env_split).length > 0` when env_split=null; Tabs 3+4 = (d) UX defect via DataTable half-bait fallback]; `a5f09bd` test RED source-grep 3 invariants `scripts/test_alert_detail_tabs_accessibility.py` [no condition predicates on contributors/geo/environment STEPS entries + no `Object.keys(...).length > 0` on env render branch + explicit "No <X> data available" copy in 3 section components]; `dba6c17` ui GREEN — AlertDetailPage:259 guard dropped + `Environment` + `EnvironmentMetrics` type imports + ContributorsSection + GeoBreakdownSection early-return empty-state cards mirroring EnvironmentSplitSection lines 22-37 pattern; 238/238 snapshot alerts confirmed `contributors=[]`, `geo_breakdown=[]`, `environment_split=null`; TS clean — `cd frontend && npx tsc --noEmit` exit 0 zero output; Python regression test exit 0 "All 3 HOTFIX-04 / B1 invariants hold ✓")
- [x] **HOTFIX-05** 🆕: Tab 2 Triage Classification mostra valori reali di `baseline_bacino` e `baseline_coverage` (non 0) sugli alert generati post-API-03 (Phase 11). Fallback graceful con label "n/a" per alert pre-API-03 che non hanno baseline server-side. Test asserts payload v1.3 con baseline_bacino e baseline_coverage > 0 produce display corrispondente. (B2) — completed 2026-05-20 (commits `44560fe` diagnose-first DIAGNOSIS.md [125 lines, FALSIFIED plan's hypothesis (i) "empty env_split dominant" — actual root cause = hypothesis (iii) variant: contract drift on `_current` suffix between `environment_splitter` producer and `TriageSection.tsx` consumer; 238/238 snapshot alerts confirmed populated env_split with non-null top-level baselines]; `40de253` test RED `scripts/test_triage_baseline_payload.py` [grep-based: bacino_current + coverage_current + envSplitMissing + 'n/a' + env_split disclosure copy + backend invariant `_compute_baseline_from_env_split({}) === (None, None)`]; `f0a7303` fix GREEN Path C — TriageSection.tsx reads `(m as { bacino_current?: number }).bacino_current ?? m.bacino ?? 0` and analog for coverage [primary root-cause fix], `envSplitMissing` predicate + `'n/a'` substitution + disclosure copy [defensive Path B leftover for legacy empty-env_split alerts], `amp_drift_detected` scalar sibling filtered out of envEntries [Rule 1 auto-fix — was diluting avgCoverage by 1/4 via 4-entry divisor], backend `_compute_baseline_from_env_split` HOTFIX-05 docstring comment [no behavior change]; Tab 5 EnvironmentSplitSection same-class drift flagged Phase 17.3 candidate, NOT touched in HOTFIX-05 scope; backend payload UNCHANGED → no Plan 06 snapshot re-export risk; `cd frontend && npx tsc --noEmit` exit 0 zero output; `.venv/bin/python scripts/test_triage_baseline_payload.py` exit 0 "All HOTFIX-05 / B2 invariants hold ✓")
- [x] **HOTFIX-06** 🆕: Link "Network totals" in `TopNDisclaimer` passa i filter params correnti (year, month, sell_type, country, tier, environment) al endpoint `/api/metrics/network-totals` via query string. Test asserts URL costruito con tutti i filtri attivi. (D1) — completed 2026-05-20 (commit 6c953c6: `TopNDisclaimerFilters` interface + `composeNetworkTotalsHref` helper con `URLSearchParams` skip-sentinel, PublishersPage forward via explicit destructure `filters={{ year, month, sell_type_proxy, geo_cluster, publisher_tier, environment }}`; backend `/api/metrics/network-totals` contract unchanged — chiavi forward-compatible, FastAPI ignora unknown params, Phase 18 promuoverà a first-class senza UI changes)
- [x] **HOTFIX-07** 🆕: JSON snapshot re-exported (se backend payload cambia per HOTFIX-05) + Vercel re-deployed + W-05 CDN byte-diff PASS + UAT 6/6 operator verifica (un check per ciascun HOTFIX-01..06) + risposta email Marco partita SOLO dopo verifica live. — completed 2026-05-20 (snapshot `352fbd0` 1004 JSON byte-stable [Path C frontend-only → no payload shape change] + initial Vercel deploy `dpl_ERFHbCJzHVgewtoUXRVfpZWjzvgw` 2026-05-20T18:16Z W-05 CDN byte-diff PASS 3/3 first attempt [publishers_top + Prensa Ibérica weekly-kpis multi-word + ALT-20260123-010000-P2] + initial UAT Checks 1-4 PASS / Checks 5+6 FAIL via React error boundary on sibling consumers (EnvironmentSplitSection + EnvironmentBarChart + ContributorsSection + GeoBreakdownSection + GeoBreakdownPieChart) reading old bare-key contract → gap-closure within-phase 7 commits `994ad23` + `4f9f404` + `0a3895c` + `cbb1621` + `eaee9f9` + `74291a1` + `8a3ed45` migrate types interface + 5 sibling components to payload contract `_current`-suffix / `display_name` / `cluster` / `revenue_current` / `delta_eur` / `delta_pct` / `quota_of_drop` keys + filter `amp_drift_detected` scalar + `quota_of_drop` percentage-not-fraction Rule 1 auto-fix [pre-existing `* 100` would have rendered "1057%"/"4487%"] + regression script `scripts/test_alert_sections_payload_contract.py` pinning 5-invariant contract + DEPLOY-LOG.md gap-closure amendment → gap-closure deploy `dpl_5gHyT8DKCSWjKYKrzu2N9PZJZDjh` 2026-05-20T21:57Z W-05 PASS 3/3 first attempt + operator re-UAT 6/6 PASS; rollback tag `pre-17.2-deploy-2026-05-20` on commit `d8527fd`; UAT-LOG.md + 17.2-SUMMARY.md + 17.2-VERIFICATION.md committed atomically per R-06)

### Alert Revenue Calc Audit (Phase 17.3, D2 from Marco's email 2026-05-19)

- [x] **AUDIT-01** 🆕: Diagnosis numerica completa: per ciascuno dei 2 sample alert (ALT-20260322-010000-P2 + ALT-20260320-070000-P2), dimostrato numericamente come il valore Sentinel viene calcolato (path codice file:line + reproduction script byte-match) vs come Marco se lo aspetta (PBI orario). Root cause identificato H6 (NEW): tz-mismatch silent synthetic fallback in BACKTEST mode — `backend/agents/data_fetcher_real.py:585-589` keeps `current_ts` tz-aware while parquet timestamps are tz-naive, pandas comparison silently returns False for every row, fallback to synthetic data_fetcher. H1-H5 (multi-hour window / channel filter / tz wrap / rolling / baseline subtraction) tutti REFUTATI con evidenza numerica. — completed 2026-05-21 (commit `5a02fe4` `.planning/phases/17.3-alert-revenue-calc-audit/17.3-DIAGNOSIS.md` 358 lines)
- [x] **AUDIT-02** 🆕: Regression test `scripts/test_alert_revenue_hourly_window.py` pinning 4 invariants: INV-1 data_source='real_parquet' for GOOGLE_ADEX BACKTEST 2026-03-22 01:00 (RED pre-fix, GREEN post-fix); INV-2 direct parquet net €312.87 / gross €521.44 within expected ranges; INV-3 no silent synthetic for GOOGLE_ADEX 12:00 BACKTEST (RED pre-fix, GREEN post-fix); INV-4 synthetic byte-match to DB sample alerts (DIAGNOSIS evidence preserved). 4/4 GREEN post-fix. No regression on 17.1 (publisher drilldown 9/9 OK), 17.2 (triage baseline + alert sections payload contract OK). — completed 2026-05-21 (commits `01f3f90` test RED + `9a91792` fix GREEN — backend/agents/data_fetcher_real.py +13 lines tz-naive normalization at line 589 region)
- [x] **AUDIT-03** 🆕 (DOWNGRADED): Numerico post-fix revenue_gross coerente con PBI ±2%. **Structural impossibility documented**: (a) Sample 1 GOOGLE_ADEX parquet returns €521 gross vs PBI €662 = 21.3% off due to **top-50 publisher filter** in `daily_aggregated.parquet` (Phase 11 D1 hybrid trade-off — closing requires Phase 18 / `/api/metrics/network-totals` extension at alert-detail layer); (b) Sample 2 HBM has **zero hourly rows** in parquet — `data/sentinel_db/hour_kpi.csv` upstream contains only GOOGLE_ADEX, closing requires v1.4 Athena ingestion expansion. ±2% target not achievable in 17.3 scope. Documentation of path-to-closure delivered in 17.3-DIAGNOSIS.md §"What the parquet (real) data actually says" + 17.3-VERIFICATION.md. Operator email draft to Marco committed in SUMMARY §"Next Phase Readiness". — completed 2026-05-21 (no deploy this phase — DB rows unchanged by code-only fix, snapshot byte-identical → R-04 chirurgico defers deploy to next phase with user-visible delta)

### D2 Closure Tecnica (Phase 17.4, post Phase 17.3 downgrade)

- [x] **D2CLOSE-01** 🆕: Path A endpoint extension — `/api/metrics/network-totals` accepts optional `bypass_top50: bool = False` query param (Pydantic Query). When `bypass_top50=true` AND `channel='GOOGLE_ADEX'`, response uses raw `daily_kpi.csv` aggregation (already the case in Phase 11 baseline). `data_fetcher_real.py` consumes this internally via in-process function call (NOT HTTP) for `channel == 'GOOGLE_ADEX'` BACKTEST mode, setting `data_source='real_csv'`. Sample 1 ALT-20260322-010000-P2 post-Path-A `revenue_current` falls within €655.37–€668.62 (PBI €662 ±1%). Other channels keep parquet path unchanged.
- [x] **D2CLOSE-02** 🆕: Athena connector code-ready — `backend/connectors/athena.py:19` `ALLOWED_CHANNEL_GROUPS` extended from `{GOOGLE, OPEN_BIDDING}` to `{GOOGLE, GOOGLE_ADEX, OPEN_BIDDING, HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC, TAM, DIRECT, DEAL}` (8 values including legacy GOOGLE alias). Fallback graceful when AWS creds missing: `_get_athena_client` returns `None` (existing behavior preserved); when consumed by `data_fetcher_real` Athena branch and `df is None`, log `data_source='synthetic_no_athena'` to surface the missing-creds state distinct from pre-existing `data_source='synthetic'` fallback. Mock-based unit tests cover each of the 6 newly whitelisted channels + missing-creds path. No production AWS credentials committed; runtime activation deferred to Phase 21 v1.4.
- [x] **D2CLOSE-03** 🆕: Backfill split — Migration `006_backfill_split_marking.sql` + apply driver `scripts/apply_migration_006.py` mark the 199 non-GOOGLE_ADEX backfill alerts (`data_source='backfill' AND channel_group != 'GOOGLE_ADEX' AND deprecated=0`) with `deprecated=1` + `deprecation_reason='synthetic-era pre-H6-fix, Phase 21 Athena dependency'`. `data_source` field unchanged (preserves audit trail). Idempotent ledger row guard. Separately, `scripts/rewrite_backfill_google_adex_post_17_4.py` runs in-place SQL UPDATE on the 38 GOOGLE_ADEX backfill alerts (1 CSV-EOF alert deprecated instead of rewritten): reads `data/sentinel_db/hour_kpi.csv` via pyarrow column projection joined with `data/sentinel_db/publisher_mapping.csv`, recomputes `revenue_current` + `revenue_baseline` + `revenue_delta_pct`, flips `data_source` from `'backfill'` to `'real_csv'`. Report file `.planning/phases/17.4-d2-closure-tecnica-post-phase-17-3-downgrade/17.4-BACKFILL-REWRITE-REPORT.md` committed with per-alert `{alert_id, old_revenue, new_revenue, delta_eur, delta_pct}` table. Pre-rewrite snapshot `data/vna_alerts.db.pre-17.4-backfill-rewrite` + git tag `pre-17.4-backfill-rewrite` mandatory. — completed 2026-05-21 (commits `fdc85e1`, `cf87121`)
- [x] **D2CLOSE-04** 🆕: Regression contract — `scripts/test_alert_revenue_pbi_parity.py` (NEW, separate from Phase 17.3's `test_alert_revenue_hourly_window.py` which stays 4/4 GREEN) pins 4 invariants: INV-1 Sample 1 ALT-20260322-010000-P2 GOOGLE_ADEX post-Path-A `revenue_current` ∈ [€655.37, €668.62] (PBI €662 ±1%); INV-2 every GOOGLE_ADEX alert created post-2026-05-21 has `data_source` ∈ {'real_parquet', 'real_csv'} (never 'backfill', 'synthetic', 'synthetic_no_athena'); INV-3 SELECT COUNT(*) FROM alerts WHERE channel_group='GOOGLE_ADEX' AND data_source='real_csv' = 39 post-rewrite; INV-4 SELECT COUNT(*) FROM alerts WHERE channel_group != 'GOOGLE_ADEX' AND data_source='backfill' AND deprecated=1 = 199 post-migration. RED before Path A/migration/rewrite land, GREEN after. Phase 17.4 deploy gates on 4/4 GREEN + live Vercel CDN byte-diff PASS + operator UAT.

### Hardening (regression prevention)

- [x] **HARD-01**: Contract test `tests/contracts/test_parquet_db_ui.py` verifica coerenza cross-layer su 1 alert known-good per ogni canale (7 casi; GOOGLE_ADEX PASS, 6 channels SKIP Phase 21 Athena). — completed 2026-05-21 (commits `4bca5ff` `9d07ac5`)
- [x] **HARD-02**: CI schema drift gate — GitHub Actions fails when `backend/db/models.py` CHECK constraints diverge from migration 001..006-derived expected DB schema. Implementation: `.github/workflows/schema-drift.yml` + `scripts/test_models_sync.py` (`TestComposeChainAgainstModels`). — completed 2026-05-21 (commits `a51e7d2` `91bc1cb`)
- [x] **HARD-03**: Pipeline silent-failure regression — extended `scripts/test_silent_failure_watch.py` with `TestPhase18HardeningRegression` (CSV-EOF boundary + post-cutoff synthetic-class detection + Path A source-grep cross-check). — completed 2026-05-21 (commit `fc82805`)
- [x] **HARD-04** 🆕: PBI parity automation — `scripts/test_alert_revenue_pbi_parity.py` extended with INV-5 (Sample 2 HBM SKIP until Phase 21 v1.4) + INV-6 (Path A guard source-grep). Wired to CI via `.github/workflows/pbi-parity.yml`. INV-1..INV-4 are operator-machine pre-push gates per gitignored-DB constraint. — completed 2026-05-21 (commits `1f0fefe` `efffe6a`)

### Documentation

- [x] **DOC-01** 🆕: `DATA_INTEGRATION.md` extended with `## v1.3 PBI ↔ Sentinel Reproducibility Matrix` (16-row table × 7 channels × metrics with match status + anchors) and `## v1.3 PBI ↔ Sentinel Gap Disclosure` (8 enumerated gap classes with lifecycle status and closing phase). 503 lines. Cross-linked to ROADMAP.md + 17.4-SUMMARY.md. — completed 2026-05-21 (commits `549b89f` `6034fe7`)

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
| MONITOR-12 🆕 | 10.2 | Deferred (2026-04-27, abort signal) |
| MONITOR-13 🆕 | 10.2 | Pending |
| MONITOR-14 🆕 | 10.2 | Done |
| API-01 🆕 | 10.5 | Pending |
| API-02 🆕 | 10.5 | Pending |
| API-03 🆕 | 11 | Pending |
| WIP-02 | 12 | Pending |
| WIP-03 | 12 | Complete |
| WIP-04 | 12 | Complete |
| CORR-01 | 12 | Complete |
| CORR-08 🆕 | 12 | Pending |
| CORR-09 🆕 | 12 | Pending |
| WIP-05 | 12 | Pending |
| CORR-02 | 13 | Complete |
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
| MAP-01 🆕 | 17.1 | Complete |
| MAP-02 🆕 | 17.1 | Complete |
| MAP-03 🆕 | 17.1 | Complete |
| MAP-04 🆕 | 17.1 | Complete |
| MAP-05 🆕 | 17.1 | Complete |
| MAP-06 🆕 | 17.1 | Complete |
| MAP-07 🆕 | 17.1 | Complete |
| MAP-08 🆕 | 17.1 | Complete |
| MAP-09 🆕 | 17.1 | Complete |
| MAP-10 🆕 | 17.1 | Complete |
| HARD-01 | 18 | Complete |
| HARD-02 | 18 | Complete |
| HARD-03 | 18 | Complete |
| HARD-04 🆕 | 18 | Complete |
| DOC-01 🆕 | 18 | Complete |
| HOTFIX-01 🆕 | 17.2 | Complete |
| HOTFIX-02 🆕 | 17.2 | Complete |
| HOTFIX-03 🆕 | 17.2 | Complete |
| HOTFIX-04 🆕 | 17.2 | Complete |
| HOTFIX-05 🆕 | 17.2 | Complete |
| HOTFIX-06 🆕 | 17.2 | Complete |
| HOTFIX-07 🆕 | 17.2 | Complete |
| AUDIT-01 🆕 | 17.3 | Complete |
| AUDIT-02 🆕 | 17.3 | Complete |
| AUDIT-03 🆕 | 17.3 | Complete (Downgraded — structural) |
| D2CLOSE-01 🆕 | 17.4 | Complete |
| D2CLOSE-02 🆕 | 17.4 | Complete |
| D2CLOSE-03 🆕 | 17.4 | Complete |
| D2CLOSE-04 🆕 | 17.4 | Complete |

**Coverage:**
- v1.3 requirements: 58 total (era 54 post Phase 17.3, +4 D2CLOSE-* aggiunti per Phase 17.4 D2 closure tecnica 2026-05-21)
- Mapped to phases: 58 ✓
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
| 17.1 Publisher Mapping Correction | MAP-01, MAP-02, MAP-03, MAP-04, MAP-05, MAP-06, MAP-07, MAP-08, MAP-09, MAP-10 | 10 |
| 17.2 Marco Feedback Hotfix | HOTFIX-01, HOTFIX-02, HOTFIX-03, HOTFIX-04, HOTFIX-05, HOTFIX-06, HOTFIX-07 | 7 |
| 17.3 Alert Revenue Calc Audit | AUDIT-01, AUDIT-02, AUDIT-03 | 3 |
| 17.4 D2 Closure Tecnica | D2CLOSE-01, D2CLOSE-02, D2CLOSE-03, D2CLOSE-04 | 4 |
| 18 Hardening + PBI Contract Tests + Docs | HARD-01, HARD-02, HARD-03, HARD-04, DOC-01 | 5 |
| **Total** | | **49 ✓** |

## v1.1 Archive

v1.1 requirements (shipped 2026-02-21) sono validated e tracciate in `PROJECT.md > Requirements > Validated`. Original v1.1 REQUIREMENTS.md preservato in git history.

---
*Requirements defined: 2026-04-22*
*Last updated: 2026-05-21 — Phase 18 HARD-01..04 + DOC-01 closed; body text refreshed to match implemented deliverables; traceability table Phase column corrected from stale 15 to 18; v1.3 milestone shipped.*
