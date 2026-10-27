# Roadmap: SENTINEL

## Milestones

- [x] **v1.0 MVP** — Piattaforma base (shipped baseline)
- [x] **v1.1 Alerting Evoluto + Operator Workflow** — Phases 01-06 (shipped 2026-02-21)
- [x] **v1.2 New IT Dataset + Advanced Rules** — non-GSD drift (shipped 2026-03-26; runtime live, silent-failure discovered by intel 2026-04-22)
- [x] **v1.3 Stabilization** — Phases 07-18 (shipped 2026-05-21)
- [ ] **v1.4 Channel Granularity + Athena + Open Market** — Phases 19-21 (anticipated 2026-05-21 to close 100% Marco feedback before reply email; original v1.4 scope ML/mobile/sell_type deferred to v1.4+)

## Overview

**v1.3 STABILIZATION** — Closing a 2-month silent-failure bug (CHECK constraint drift), committing 56 WIP files atomically, and installing structural monitoring that makes silent drift impossible to repeat. Deep audit evening 2026-04-22 expanded scope to include PBI-parity on revenue totals, sell_type proxy derivation, measurable_impressions preservation, UI labeling overhaul, and explicit reproducibility gap disclosure.

**Critical path (Phases 07 → 10):** unblock alerts in production + install silent-failure watchdog. Estimated 1 full day.
**Full milestone (Phases 07 → 18):** 4-5 days to ship v1.3 (expanded from 3-4 days after deep audit).

**4 Key decisions approved by Stefano (2026-04-22 evening):**
- **D1 (hybrid)**: top-50 filter stays in parquet + NEW `/api/metrics/network-totals` endpoint streams upstream CSV for PBI-parity dashboard totals
- **D2 (gross+net side-by-side)**: UI displays "€X gross (net €Y post rev-share 60%)" with default GROSS (PBI-aligned)
- **D3 (parquet backfill)**: Alert regen from current parquet post SCHEMA-01-04 fixes; deprecate pre-2026-02-01 legacy alerts
- **D4 (sell_type proxy)**: derive Open_Market/Header_Bidding/Direct/Deal/Other from channel_group mapping (95% confidence)

**Numeric validation findings (Mondadori Feb 2026):**
- Bacino: already matches PBI 133M within 0.2% ✅
- Revenue total gross: matches PBI €188k within 2.5% ✅
- Fill rate 35.2% PBI requires `measurable_impressions` (dropped by ETL:187 — fix in SCHEMA-03)
- OM revenue €90k PBI vs €50k Sentinel proxy: taxonomy delta, document in DOC-01

## Phases

**Phase Numbering:**
- Integer phases (07-18): v1.3 milestone work
- Decimal phases: reserved for urgent insertions (none currently)

<details>
<summary>v1.1 shipped phases (01-06) — completed 2026-02-21</summary>

- [x] **Phase 01: Alerting Evoluto** — Drift regression + yesterday/14d comparisons + weekend scheduling + dual thresholds
- [x] **Phase 02: Nuovi Tipi Alert** — A5 margin, A6 coverage-zero, A7 pricing-rule
- [x] **Phase 03: Operator Workflow** — Feedback + assignment + intervention tracking
- [x] **Phase 04: Notifiche Slack** — Block Kit templates + daily digest + admin config
- [ ] **Phase 05: Dati Live e Multi-canale** — DEFERRED to v1.4 (Athena activation)
- [x] **Phase 06: Revisione Documentale** — Operational + technical docs refresh

</details>

**v1.3 Stabilization phases (07-18):**

- [x] **Phase 07: DB WIP Investigation** — Read-only gate before any schema work (completed 2026-04-22)
- [x] **Phase 08: Schema Migration + ETL Extensions** — CHECK 7 channels + preserve measurable_impressions + add sell_type_proxy column (completed 2026-04-23)
- [x] **Phase 09: Alert Backfill + Legacy Migration** — Recover 90+ days alerts + deprecate pre-v1.2 stale alerts (completed 2026-04-23)
- [x] **Phase 10: Pipeline Silent-Failure Monitoring** — Health endpoint + meta-alert on runs > 0 ∧ alerts = 0 (completed 2026-04-23)
- [ ] **Phase 10.2: Pipeline Monitoring Security Hardening** — CR-01 send_daily_digest canonical cutoff + HARD-03 extension + Slack webhook rotation + WR-02 Retry-After bound + WR-03 _restore atomicity (MONITOR-11..14)
- [x] **Phase 11: Network Totals Endpoint + Filter API** — `/metrics/network-totals` hybrid + sell_type query param + server-side baseline (API-03) (completed 2026-04-29)
- [x] **Phase 12: WIP Atomic Commits (Foundation + Correctness + Triage Server-Side)** — Commits A/B/C + CORR-01/08/09 in parallel waves (completed 2026-04-30)
- [x] **Phase 13: Dashboard Date Navigation** — Commit D (consumer of Commit C contract) (completed 2026-04-30)
- [x] **Phase 14: UI Labeling + Filter Exposure** — gross/net toggle + channel badges + reference period labels + filter state in URL + derived filters (sell_type_proxy, geo, env, publisher tier) (completed 2026-04-30)
- [x] **Phase 15: UI Resilience** — error boundaries + diagnostic empty states (completed 2026-05-04)
- [x] **Phase 16: Vercel Static Export Decision** — Ship Commit E as v1.3.1 or formally shelve (completed 2026-05-06)
- [x] **Phase 17: Data Cleanup** — floor_cpm dead column + Mondadori/Mondadori_npa aggregation
- [x] **Phase 17.1: Publisher Mapping Correction** — Excel-based authoritative loader (ad_unit_1_mapping.xlsx), fix Mondadori over-aggregation from Phase 17, AdGage_X normalization, exclude OLD/test clusters (completed 2026-05-20)
- [x] **Phase 17.2: Marco Feedback Hotfix** — 6 UI/data bug fix da feedback Marco 2026-05-19 (V3 tooltip "baseline" vs current revenue, V4 "7 Weeks" label vs 7 giorni, V5 disclaimer Top-N prominence, B1 Tab 3/4/5 inaccessibilità, B2 Triage Tab Bacino+Coverage=0, D1 Network totals link ignora filtri). Esclusi: D2 revenue calc audit → Phase 17.3; V1+V2 Alert per Channel granularity → backlog v1.4 (completed 2026-05-20)
- [x] **Phase 17.3: Alert Revenue Calculation Audit** — D2 dalla mail Marco 2026-05-19: root cause identificato H6 (NEW) tz-mismatch silent synthetic fallback in BACKTEST mode; 1-line chirurgico fix in `backend/agents/data_fetcher_real.py` per future alerts; regression test `scripts/test_alert_revenue_hourly_window.py` 4/4 GREEN; AUDIT-03 ±2% PBI match downgraded (structural top-50 filter + missing HBM hourly ingestion); deploy deferred (code-only fix, snapshot byte-identical → R-04 chirurgico) (completed 2026-05-21)
- [x] **Phase 17.4: D2 Closure Tecnica** — chiusura strutturale D2 post Phase 17.3 downgrade: Path A `/api/metrics/network-totals` extension al alert detail layer → Sample 1 GOOGLE_ADEX byte-perfect PBI €662 match; Athena connector unwhitelist HBM/HBP/TAM (code-ready, creds out-of-scope); backfill split — 38 GOOGLE_ADEX rewrite real via CSV direct (1 CSV-EOF deprecated) + 199 altri channel marked deprecated=1 con disclosure; regression test Sample 1 PBI parity invariant (completed 2026-05-21)
- [x] **Phase 18: Hardening + PBI Contract Tests + Docs** — tests/contracts + CI schema gate + DATA_INTEGRATION.md + PBI↔Sentinel gap disclosure (completed 2026-05-21)

## Phase Details

### Phase 07: DB WIP Investigation
**Goal**: Understand 2-month uncommitted DB binary drift before any schema work
**Depends on**: Nothing (first phase of v1.3)
**Requirements**: WIP-01
**Success Criteria**:
  1. Schema dump of WIP `vna_alerts.db` vs `git show HEAD:data/vna_alerts.db` produced and diffed
  2. Decision recorded (preserve / reset / forward-port via migration) with rationale
  3. If preserved, migration script lands in `scripts/migrations/` tracked in git
**Plans**: 1 plan
- [x] 07-01-PLAN.md — Dump WIP+HEAD schemas, diff, cross-check models.py, record decision, conditionally author migration

### Phase 08: Schema Migration + ETL Extensions
**Goal**: Pipeline can insert alerts for all 8 channel_group values declared in `backend/db/models.py` (GOOGLE_ADEX, OPEN_BIDDING, HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC, TAM, DIRECT, DEAL, plus legacy alias GOOGLE) AND all 8 alert_rule values (A0-A3, A5-A8; A4 intentionally skipped); parquet preserves `measurable_impressions`; `sell_type_proxy` derived column added; models.py CHECK matches live DB byte-for-byte
**Depends on**: Phase 07
**Requirements**: SCHEMA-01, SCHEMA-02, SCHEMA-03, SCHEMA-04
**Success Criteria**:
  1. `scripts/migrations/001_expand_channel_groups.sql` applied with backup; INSERT succeeds for each of 8 channels AND 8 alert_rules per models.py; INSERT of invalid channel or `alert_rule='A4'` raises IntegrityError
  2. `backend/db/models.py` CHECK matches live DB byte-for-byte
  3. `etl_csv_to_parquet.py` rebuilt parquet contains `measurable_impressions` + `sell_type_proxy` columns; schema bumped to 20 fields
  4. Regression check: Mondadori Feb fill rate `measurable/bacino` matches PBI 35.2% within 1.5 ppt
**Plans**: 5 plans (2 waves — SCHEMA-01..04)
- [x] 08-01-PLAN.md — Author 001_expand_channel_groups.sql migration + stdlib validation suite (SCHEMA-01)
- [x] 08-02-PLAN.md — Sync models.py CHECK constants + tighten pending_notifications + drift-detector test (SCHEMA-02)
- [x] 08-03-PLAN.md — [BLOCKING] Backup + apply migration to live DB + smoke-test INSERTs (SCHEMA-01/02 apply)
- [x] 08-04-PLAN.md — Preserve measurable_impressions + add sell_type_proxy column; rebuild 20-col parquet (SCHEMA-03/04)
- [x] 08-05-PLAN.md — Mondadori Feb 2026 fill-rate regression vs PBI 35.2% ±1.5 ppt (SCHEMA-03 proof)

### Phase 09: Alert Backfill + Legacy Migration
**Goal**: UI alert list populated 2026-01-23 → parquet_v2_max_date (2026-03-23); legacy pre-v1.2 alerts soft-deprecated. 31-day gap 2026-03-24 → current date disclosed in COVERAGE-GAP.md (v1.3.1 plant-seed).
**Depends on**: Phase 08
**Requirements**: BACKFILL-01, MIGRATE-01
**Success Criteria**:
  1. `scripts/backfill_alerts.py` run for 2026-01-23 → 2026-03-23 writes N > 0 alerts to DB
  2. Alert list UI shows ≥ 1 alert per week 2026-01-23 → parquet_v2_max_date (2026-03-23); see .planning/phases/09-alert-backfill-legacy-migration/COVERAGE-GAP.md for v1.3.1 plant-seed
  3. Pre-2026-02-01 alerts marked `deprecated=TRUE` with `deprecation_reason='v1.0 schema stale'`
**Plans**: TBD

### Phase 10: Pipeline Silent-Failure Monitoring
**Goal**: Silent failure structurally impossible (observable + alertable)
**Depends on**: Phase 09
**Requirements**: MONITOR-01, MONITOR-02, MONITOR-03
**Success Criteria**:
  1. `GET /health/alerts-pipeline` returns live `{last_alert_at, alerts_last_24h, pipeline_runs_last_24h}`
  2. Simulated CHECK violation triggers P0 meta-alert in Slack + logs within one run cycle
  3. `pipeline_runs.alerts_written_count` populated on every run
**Plans**: 3 plans
Plans:
- [x] 10-01-PLAN.md — Migration 003 alerts_written_count + record_pipeline_run wire-up + [BLOCKING] live apply (MONITOR-03)
- [x] 10-02-PLAN.md — GET /api/health/alerts-pipeline endpoint + TestClient smoke suite (MONITOR-01)
- [x] 10-03-PLAN.md — silent_failure_watch module + scheduler integration + Slack P0 meta-alert (MONITOR-02)
**UI hint**: yes

### Phase 10.1: pipeline-monitoring-hotfix-and-hardening (INSERTED)

**Goal:** Fix 5 MAJOR bugs discovered by 5 independent auditors post-Phase-10 so the silent-failure watchdog actually detects real silent failures (no false-positives from BACKTEST contamination, no false-negatives from datetime string-compare edge cases) AND unblock `alerts.created_at` dual-format corruption that makes MAX/dedup logic unreliable project-wide.

**Depends on:** Phase 10
**Requirements**: MONITOR-04, MONITOR-05, MONITOR-06, MONITOR-07, MONITOR-08

**Requirement details** (all new for 10.1):
- **MONITOR-04**: `alerts.created_at` written in ONE canonical format everywhere (notifier + operations + backfill); migration normalizes existing rows; drift test prevents regression
- **MONITOR-05**: Silent-failure watchdog temporal queries immune to datetime string-compare edge cases (strftime or space-separator everywhere) AND filtered to `mode='LIVE'`
- **MONITOR-06**: `find_open_alert` dedup window respects the 6-hour contract across all calendar-day boundaries
- **MONITOR-07**: Slack retry path correctly distinguishes HTTPError vs URLError, honors `Retry-After` on 429, no dead code
- **MONITOR-08**: `alerts_written_count` counter semantics matches INSERT intent (0 on dedup UPDATE path; 1 only on new row insertion)

**Success Criteria:**
1. `GET /api/health/alerts-pipeline` returns `pipeline_runs_last_24h` counting only `mode='LIVE'` rows AND temporal comparison returns bit-identical results across T-format and space-format boundary rows (regression test proves it)
2. Silent-failure watchdog re-enabled via `enabled: true` returns `triggered=False` on current live DB (5 LIVE runs have paired LIVE alerts; the 1442 BACKTEST runs correctly filtered out)
3. `alerts.created_at` has single canonical format in 100% of rows post-migration; `MAX(created_at)` returns the true latest alert regardless of write code-path
4. Unit test proves `find_open_alert` returns None for a 7-hour-old open alert spanning a calendar-day boundary (pre-fix: returns row; post-fix: returns None)
5. Unit test proves Slack 429 response triggers `Retry-After`-honoring retry
6. Final commit re-enables `config/alerting_rules.yaml` `silent_failure_monitor.enabled: true` and verifier confirms live-smoke watchdog returns `triggered=False` against current DB

**Plans:** 8/8 plans complete

Plans:
- [x] 10.1-01-PLAN.md — Pre-phase tag + WAL-safe backup + migration 004 SQL + driver + smoke tests (Wave 1, MONITOR-04 part 1)
- [x] 10.1-02-PLAN.md — Canonicalize created_at writes in notifier.py + operations.py + HARD-03 drift gate (Wave 2, MONITOR-04 part 2)
- [x] 10.1-03-PLAN.md — [BLOCKING] apply migration 004 to live DB (Wave 3, MONITOR-04 CLOSED)
- [x] 10.1-04-PLAN.md — AND mode='LIVE' filter in get_alerts_pipeline_health + temporal regression (Wave 4, MONITOR-05)
- [x] 10.1-05-PLAN.md — find_open_alert boundary-day regression coverage + module-level _tmpdb_with_schema helper for Plan 10.1-07 reuse (Wave 5, MONITOR-06)
- [x] 10.1-06-PLAN.md — Slack retry rewrite: HTTPError/URLError + Retry-After (Wave 5, MONITOR-07)
- [x] 10.1-07-PLAN.md — alerts_written_count counter semantics via db_new_row (Wave 6 — serialized after 10.1-05 to avoid test_operations_idempotency.py write conflict, MONITOR-08)
- [x] 10.1-08-PLAN.md — Re-enable silent_failure_monitor.enabled: true + live smoke (Wave 7, all MONITOR-0{4..8})

**Gap closure context:** Closes gaps surfaced by 5 independent auditors AFTER Phase 10 verification passed 3/3 SC. Verification caught the mechanical firing but not the semantic correctness. Mitigation committed bb34e36 (`silent_failure_monitor.enabled: false`) stops false-positive P0 loop until fixes land. Audit findings:
- Phase 10 REVIEW.md (WR-01..WR-04)
- .planning/phases/10-pipeline-silent-failure-monitoring/audits/auditor1_runtime_report.md (runtime black-box)
- .planning/phases/10-pipeline-silent-failure-monitoring/audits/auditor2_code_report.md (adversarial — found MAJOR-01/02/03)
- .planning/phases/10-pipeline-silent-failure-monitoring/audits/auditor_a_sql_report.md (SQL — found MAJOR-NEW-01, MAJOR-NEW-02, 3 minors)
- .planning/phases/10-pipeline-silent-failure-monitoring/audits/auditor_b_security_report.md (security — deferred to Phase 10.2)
- .planning/phases/10-pipeline-silent-failure-monitoring/audits/auditor_c_integration_report.md (cross-phase — no regressions, E2E on clean DB PASS)

**Scope EXCLUDES (deferred to Phase 10.2 security-hardening):**
- Live DB + 6 backups tracked in git history (.gitignore + filter-repo)
- Slack webhook `TEST123` committed in YAML (verify-if-live then rotate)
- `{e!r}` exception leak in HTTP 503 response body
- `slack_channel_override` URL validation (SSRF surface)
- Rate-limit behind reverse proxy (ProxyHeadersMiddleware)
- `idx_alerts_deprecated` missing from SQL_CREATE_INDEXES
- `BEGIN DEFERRED` isolation on watchdog queries
- `busy_timeout` on apply_migration_003 driver
- Cleanup of `test-run-sc3` smoke-test row in live DB

### Phase 999.1: Investigate LIVE pipeline silent since 2026-03-23

**Status:** Resolved 2026-04-25 — Path A (see 999.1-DECISION.md)
**Goal:** Diagnose WHY LIVE pipeline has produced 0 alerts since 2026-03-23; decide and document remediation path
**Depends on:** Phase 10.1
**Requirements:** MONITOR-09, MONITOR-10
**Plans:** 2/2 plans complete

Plans:
- [x] 999.1-01-PLAN.md — Read-only diagnostic + DIAGNOSIS.md (MONITOR-09)
- [x] 999.1-02-PLAN.md — Operator-signed decision + ROADMAP amendment (MONITOR-10)

Root-cause summary: parquet frozen at 2026-03-23 (Phase 09 COVERAGE-GAP.md); LIVE pipeline produces no_alert against stale tail window. Watchdog Case C firing is semantically correct (per 10.1-VERIFICATION.md overrides[0]). Remediation owned by Phase 11 / v1.3.1 per COVERAGE-GAP.md Option A (Phase 11 cron) / Option B (v1.3.1 one-shot). Path A — Accept + document — selected by operator (stefano) 2026-04-25 with Phase 10.2 readiness secondary answer (i): operator accepts ~17 P0 pages/day on rotated webhook until parquet refresh closes the H1 gap. `phase_10_2_safe: true` in DECISION.md frontmatter; Phase 10.2 unblocked.

### Phase 10.2: Pipeline Monitoring Security Hardening
**Goal**: Close residual hardening debt from Phase 10 + 10.1 audits — fix CR-01 (`send_daily_digest` canonical cutoff bug), rotate the test Slack webhook to a real one, bound `Retry-After` against DoS, and make `_restore` operations atomic. Tight scope; defer remaining 9 audit-deferred items to Phase 10.3 or fold into Phase 18 hardening.
**Depends on**: Phase 10.1, Phase 999.1 (`phase_10_2_safe: true` confirmed in 999.1-DECISION.md)
**Requirements**: MONITOR-11, MONITOR-12, MONITOR-13, MONITOR-14
**Success Criteria**:
  1. `send_daily_digest` time cutoff uses canonical space-separator naive UTC microseconds format (matches Migration 004 D-10.1-01); regression test asserts cross-format query mismatch is impossible. HARD-03 drift detector extended to cover the digest callsite.
  2. Slack webhook in `config/alerting_rules.yaml` is a real, operator-supplied URL (NOT `TEST123`); webhook rotation procedure documented; legacy URL purged from git history (or formally accepted via R-05 documented decision).
  3. `Retry-After` header parsing in `send_meta_alert` is bounded (e.g. ≤ 60s upper cap); regression test asserts a malicious upstream returning `Retry-After: 999999` does not block the scheduler thread.
  4. `_restore` atomicity: SQLite `restore` operations wrapped in transactional context (BEGIN…COMMIT or `Connection.backup()` flush guarantees); regression test asserts partial-restore mid-failure leaves DB at pre-restore state, never partial.
**Out of scope (deferred to 10.3 or Phase 18)**: WR-04/05/06 (10.1 review tail), IN-01..06 (10.1 review info), and the 9 Phase 10 audit security items (gitignore filter-repo for live DB + 6 backups, `{e!r}` exception leak, `slack_channel_override` SSRF, ProxyHeaders middleware, `idx_alerts_deprecated` missing from SQL_CREATE_INDEXES, `BEGIN DEFERRED` isolation on watchdog, `busy_timeout` on apply_migration_003 driver, `test-run-sc3` smoke-row cleanup).
**Plans**: 4 plans
Plans:
- [x] 10.2-01-PLAN.md — send_daily_digest canonical cutoff (CR-01) + HARD-03 drift gate extension (MONITOR-11)
- [x] 10.2-02-PLAN.md — bound Retry-After parsing in send_meta_alert (anti-DoS, MONITOR-13 / WR-02)
- [x] 10.2-03-PLAN.md — atomic _restore across 4 migration drivers (MONITOR-14 / WR-03)
- [ ] 10.2-04-PLAN.md — Slack webhook rotation: YAML→null + env-var ingress + operator R-05 sign-off (MONITOR-12)

### Phase 11: Network Totals Endpoint + Filter API + Server-Side Baseline
**Goal**: PBI-parity dashboard totals via upstream-streaming endpoint; filter API supports sell_type_proxy; alert payload includes server-computed baselines
**Depends on**: Phase 10
**Requirements**: API-01, API-02, API-03
**Success Criteria**:
  1. `GET /api/metrics/network-totals?date=...&channel=GOOGLE_ADEX` returns value matching PBI 2026-01-12 €27.2k gross within 2%
  2. `GET /api/publishers/top?sell_type=Open_Market` filters via channel_group mapping (95% confidence confirmed by config:alerting_rules.yaml:84-91)
  3. Alert payload contains `baseline_bacino` and `baseline_coverage` computed server-side (7w rolling same-weekday), NOT derived client-side
**Plans**: 3 plans (2 waves — Wave 0 Nyquist tests, Wave 1 parallel API-01/API-03 + API-02)
Plans:
- [x] 11-01-nyquist-test-scaffold-PLAN.md — Author 3 RED test scripts (test_network_totals_pbi_parity, test_sell_type_filter, test_alert_baseline_fields) before any implementation (API-01/02/03 Wave 0)
- [x] 11-02-network-totals-and-baseline-PLAN.md — /api/metrics/network-totals endpoint reading raw daily_kpi.csv + AlertDetail.baseline_bacino/baseline_coverage on-the-fly aggregation (API-01 + API-03)
- [x] 11-03-sell-type-filter-PLAN.md — sell_type query param on /api/publishers/top with whitelist + column guard (API-02)

### Phase 12: WIP Atomic Commits + Triage Server-Side
**Goal**: 2-month WIP landed as reviewable atomic commits (Commits A/B/C); TriageSection client-side baseline heuristic removed; CORR-01/08/09 closed in operator UI; RC-(e) closed at the UI layer
**Depends on**: Phase 11 (needs API-03 for baseline fields)
**Requirements**: WIP-02, WIP-03, WIP-04, CORR-01, CORR-08, CORR-09
**Success Criteria**:
  1. `git log` shows 6 atomic commits in this phase: Commit A (WIP-02 i18n keys foundation), Commit B (WIP-03 IT→EN), Commit C (WIP-04 backend correctness), CORR-01 (TriageSection server-side baseline), CORR-08 (PublishersPage weighted avgFillRate + sell_type dropdown), CORR-09 (KpiCards i18n keys)
  2. `TriageSection.tsx` no longer contains `revenueRatio * 0.95` or `avgCoverage + 0.05`; reads `alert.baseline_bacino` / `baseline_coverage`
  3. `KpiCards.tsx` `avgFillRate` uses weighted average; labels i18n-enabled
  4. `git status` post-phase shows only Commit D (WIP-05) + Commit E (WIP-06) files outstanding
**Plans**: 6 plans (3 waves)
Plans:
- [x] 12-01-PLAN.md — Commit A: lib/i18n-keys.ts foundation + frontend/.gitignore .vercel (WIP-02)
- [x] 12-02-PLAN.md — Commit B: IT→EN translation in DocsPage, PublisherDetailPage, PublishersPage tooltips (WIP-03)
- [x] 12-03-PLAN.md — Commit C: backend correctness — bacino dedup + 7w YoY rolling + available_dates + path-based date variant (WIP-04)
- [x] 12-04-PLAN.md — TriageSection server-side baseline + heuristic delete + baseline-missing disclosure (CORR-01 / RC-e UI closure)
- [x] 12-05-PLAN.md — PublishersPage weighted avgFillRate + sell_type dropdown filter (CORR-08 + sell_type UI affordance)
- [x] 12-06-PLAN.md — KpiCards labels via KPI_LABELS from i18n-keys (CORR-09)
**UI hint**: yes

### Phase 13: Dashboard Date Navigation
**Goal**: Operators navigate dashboard by date with YoY 7-week rolling baseline
**Depends on**: Phase 12
**Requirements**: WIP-05
**Success Criteria**:
  1. `RevenueStatus24h` date picker populated from `available_dates`, loads selected day without errors
  2. YoY widget shows 7-week rolling with explicit baseline window label
  3. Commit D atomic: exactly 8 files per WIP split, no scope creep
**Plans**: 2 plans (2 waves — Wave 1 i18n-keys extension prep, Wave 2 Commit D 8-file atomic landing)
Plans:
- [x] 13-01-PLAN.md — Extend frontend/src/lib/i18n-keys.ts with REVENUE_LABELS + KPI_NO_DATA_COPY (Phase 13 prep, Wave 1)
- [x] 13-02-PLAN.md — Cherry-pick WIP `94a48cd` 8 frontend files with i18n downgrade + useTopPublishers hunk exclusion (WIP-05 Commit D, Wave 2)
**UI hint**: yes

### Phase 14: UI Labeling + Filter Exposure
**Goal**: Every metric displayed has full disclosure (scope, period, gross/net, currency, timezone); derived filters exposed
**Depends on**: Phase 13
**Requirements**: CORR-02, CORR-03, CORR-04, CORR-05, CORR-06, CORR-11
**Success Criteria**:
  1. Every metric card shows: reference period (as of [timestamp] UTC), channel scope badge, gross/net label with share %
  2. PublishersPage filter state in URL (year, month, sell_type_proxy, publisher_tier) — shareable
  3. New derived filter UI: sell_type_proxy dropdown, geo_cluster filter, environment drill-down, gross/net toggle, publisher tier A/B/C
**Plans**: TBD
**UI hint**: yes

### Phase 15: UI Resilience
**Goal**: Frontend gracefully handles malformed data or empty states
**Depends on**: Phase 14
**Requirements**: CORR-07, CORR-10
**Success Criteria**:
  1. `RevenueTrendChart`, `EnvironmentBarChart`, `GeoBreakdownPieChart` wrapped in ErrorBoundary
  2. Diagnostic empty states: "No 7w history. Alert &lt; 7d old or data not yet aggregated"
  3. Manual regression: inject malformed payload → UI shows fallback instead of crash
**Plans**: 4 plans (3 waves)
Plans:
- [x] 15-01-PLAN.md — Append CHART_EMPTY_COPY + CHART_ERROR_COPY to i18n-keys.ts (CORR-07 SSoT, Wave 1)
- [x] 15-02-PLAN.md — Create ChartErrorBoundary primitive (CORR-10 infrastructure, Wave 1)
- [x] 15-03-PLAN.md — Wire 3 charts to CHART_EMPTY_COPY + wrap call sites with ChartErrorBoundary (CORR-07 + CORR-10 close, Wave 2)
- [x] 15-04-PLAN.md — Manual regression UAT via prop injection (closes ROADMAP SC #3, Wave 3, has checkpoint:human-verify)
**UI hint**: yes

### Phase 16: Vercel Static Export Decision
**Goal**: Resolve 5-file architectural WIP (Vercel config + static export) — ship or shelve
**Depends on**: Phase 15
**Requirements**: WIP-06
**Success Criteria**:
  1. Decision in PROJECT.md Key Decisions: ship v1.3.1 with migration plan OR shelve with rationale + branch reference
  2. `git status` no longer lists Commit E files as uncommitted on main
  3. Deployment docs consistent with chosen model
**Plans**: 4 plans (4 waves) — phase scope ESTESO 2026-05-04 to include deploy + UAT (CONTEXT.md scope_extension)
Plans:
- [x] 16-01-PLAN.md — Pre-deploy safety + Commit E SHIP decision formalization in PROJECT.md + git tag pre-deploy-v1.3-2026-05-04 + capture current Vercel state (D-16.01, D-16.05, Wave 1)
- [ ] 16-02-PLAN.md — Boot local backend + re-export API JSON snapshot (51+ files) + npm run build + manual network-totals snapshot + kill backend (D-16.02, D-16.03, Wave 2)
- [ ] 16-03-PLAN.md — vercel --prod --yes (R-05 OK gate, checkpoint:human-action) + 7-check operator-driven UAT (checkpoint:human-verify) + atomic deploy-log + UAT-report commit (D-16.04, D-16.06, Wave 3)
- [ ] 16-04-PLAN.md — Phase close: STATE/ROADMAP/REQUIREMENTS update (PATH A — UAT PASS) OR vercel rollback + git reset --hard pre-deploy tag (PATH B — UAT FAIL); D-16.07 honored, D-16.08 boundary respected (Wave 4)

### Phase 17: Data Cleanup
**Goal**: Dead / inconsistent data elements resolved
**Depends on**: Phase 16
**Requirements**: CLEAN-01, CLEAN-02
**Success Criteria**:
  1. `floor_cpm` decision: removed from schema OR populated from source (documented)
  2. `Mondadori` + `Mondadori_npa` handled: aggregated or disclosed with rationale
**Plans**: TBD

### Phase 17.1: Publisher Mapping Correction
**Goal**: Replace Phase 17 hardcoded `MONDADORI_FAMILY` with authoritative Excel-based loader (`ad_unit_1_mapping.xlsx`, Marco-maintained) — fix Mondadori over-aggregation, normalize `AdGage_*` brands, exclude `OLD`/`test` clusters from Top Publishers.
**Type**: gap_closure (parent: Phase 17)
**Depends on**: Phase 17
**Requirements**: MAP-01, MAP-02, MAP-03, MAP-04, MAP-05, MAP-06, MAP-07, MAP-08, MAP-09, MAP-10
**Success Criteria**:
  1. `ad_unit_1_mapping.xlsx` copied to `data/sentinel_db/` and loaded by backend via cached loader (`_load_ad_unit_mapping()`)
  2. `/api/publishers/top` applies mapping BEFORE `groupby` (rewrites `publisher_id` via `ad_unit_name → publisher` dict)
  3. Hardcoded `MONDADORI_FAMILY = {...}` block from Phase 17 removed
  4. Rows with mapped publisher ∈ {`OLD`, `test`} filtered out of Top Publishers responses
  5. Drilldown endpoints (`/api/publishers/{id}/weekly-kpis|ecpm-analysis|recurring-patterns|feedback-history|interventions`) accept clean publisher name (e.g. `Vocento`) and reverse-lookup all `ad_unit_name` mapped to it
  6. Frontend `PublishersPage.tsx` re-enables row click navigation (no more `_family` suffix guard)
  7. `config/sell_type_proxy.yaml` Open_Market mapping verified against Marco's list (`GOOGLE_ADEX`, `OPEN_BIDDING`, `HEADER_BIDDING_MAGNITE`, `HEADER_BIDDING_PUBMATIC`, `TAM`) — TAM deprecation documented
  8. JSON snapshot re-exported via `scripts/export_api_json.sh` and Vercel re-deployed; Top Publishers live shows clean PBI-style names (no raw `AdGage_*` / no `_family` suffixes); Mondadori revenue ≈ €1.125k (not Phase 17's over-aggregated €1.458k)
**Out of scope (defer to Phase 18)**: daily cron for mapping refresh, contract tests pinning mapping invariants, `DATA_INTEGRATION.md` update, interstitial ad_request fallback chain audit, live data attach (v1.4 Athena).
**Source of truth**: `.planning/phases/17.1-publisher-mapping-correction/17.1-CONTEXT.md` (Marco audit response 2026-05-18 verbatim).
**Plans**: 5 plans (5 waves — Plan 02 split into 02a + 02b per plan-checker iter-1 W-02)
- [x] 17.1-01-PLAN.md — Mapping foundation: xlsx ingestion + `_load_ad_unit_mapping()` cached loader + sell_type_proxy.yaml annotation block (MAP-01, MAP-02, MAP-06) — completed 2026-05-19
- [x] 17.1-02a-PLAN.md — Publisher mapping application (parquet path): get_top_publishers mapping + EXCLUDED_PUBLISHER_CLUSTERS + Phase 17 block removed (MAP-03, MAP-04, MAP-05) — completed 2026-05-19
- [x] 17.1-02b-PLAN.md — Drilldown reverse-mapping: `_resolve_publisher_ad_units` + 3 parquet endpoints + 2 SQL IN-clause endpoints (MAP-08, B-01 5/5 closure) — completed 2026-05-19
- [x] 17.1-03-PLAN.md — Frontend row click re-enable: PublishersPage.tsx `_family` guard removed + encodeURIComponent (MAP-07) — completed 2026-05-19
- [x] 17.1-04-PLAN.md — Snapshot regen + Vercel deploy + W-05 CDN byte-diff + 8/8 UAT + SUMMARY + governance (MAP-09, MAP-10) — completed 2026-05-20 (gap-closure deploy for multi-word publisher bug shipped within same phase: commits 98d1ddc + 190636c + b626f20)

### Phase 17.2: Marco Feedback Hotfix
**Goal**: Risolvere 6 bug UI/dati segnalati da Marco Manduca (email 2026-05-19) come pre-condizione per rispondere a Marco senza errori live. Tutto deve essere live e verificato prima dell'invio email.
**Type**: hotfix (parent: v1.3 milestone, post Phase 17.1)
**Depends on**: Phase 17.1 (publisher mapping live)
**Requirements**: HOTFIX-01..HOTFIX-07 (HOTFIX-01..06 = fix; HOTFIX-07 = deploy+UAT)
**Success Criteria**:
  1. **V3** Tooltip Revenue Impact chart mostra "current revenue" su current series (non "baseline" su entrambe)
  2. **V4** Etichetta "Revenue Trend (7 Weeks)" coerente con i dati mostrati: o cambiare label a "7 Days" o cambiare query a 7 settimane reali (decisione in plan)
  3. **V5** Disclaimer Top-35 reso prominente (ad oggi `text-xs text-gray-500`, da elevare a body weight)
  4. **B1** Tab 3 (Top Contributors), 4 (Geo Breakdown), 5 (Environment Split) di AlertDetailPage accessibili e renderizzano contenuto valido (no error boundary, no empty silente)
  5. **B2** Tab 2 Triage Classification mostra valori reali di `baseline_bacino` e `baseline_coverage` (non 0) per alert con API-03 payload; fallback graceful per alert pre-Phase 11
  6. **D1** Link "Network totals" in `TopNDisclaimer` passa i filter params correnti (year, month, sell_type, country, tier, environment) via query string al endpoint `/api/metrics/network-totals`
  7. JSON snapshot re-exported + Vercel re-deployed + W-05 CDN byte-diff PASS + UAT 6/6 operator verifica
**Out of scope (defer/separate)**:
  - **D2** revenue calc audit (2 alert sample) → Phase 17.3 dedicata (serve indagine parquet marzo)
  - **V1+V2** Alert per Channel granularity (Demand: Diretta/Deal/Open) → backlog v1.4 (refactor architetturale, non hotfix)
**Source of truth**: `.planning/intel/marco-2026-05-19/EMAIL-MARCO-FEEDBACK.md` (copia mail verbatim allegata a CONTEXT)
**Plans**: 6 plans (2 waves)
Plans:
- [x] 17.2-01-PLAN.md — Tooltip discriminant in RevenueTrendChart (HOTFIX-01 / V3)
- [x] 17.2-02-PLAN.md — Chart heading 7 Weeks → Last 7 Days (HOTFIX-02 / V4) — completed 2026-05-20 (commit 2159ea1)
- [x] 17.2-03-PLAN.md — TopNDisclaimer prominence + filter passthrough (HOTFIX-03 / V5 + HOTFIX-06 / D1) — completed 2026-05-20 (commits 406862f V5 + 6c953c6 D1)
- [x] 17.2-04-PLAN.md — AlertDetail Tabs 3/4/5 always-accessible + empty-state cards (HOTFIX-04 / B1) — completed 2026-05-20 (commits `64869b3` diagnose-first DIAGNOSIS.md per-tab classification + `a5f09bd` test RED source-grep 3 invariants + `dba6c17` ui GREEN AlertDetailPage:259 guard dropped + Environment/EnvironmentMetrics type imports + ContributorsSection + GeoBreakdownSection early-return empty-state cards mirroring EnvironmentSplitSection lines 22-37 pattern; 238/238 snapshot alerts confirmed empty payload; TS clean)
- [x] 17.2-05-PLAN.md — Triage Bacino+Coverage Path C: read _current suffix + 'n/a' + disclosure on empty env_split (HOTFIX-05 / B2) — completed 2026-05-20 (commits `44560fe` diagnose-first DIAGNOSIS.md [FALSIFIED plan's hypothesis (i) — 100% of 238 snapshot alerts have populated env_split, real root cause = hypothesis (iii) variant contract drift on _current suffix] + `40de253` test RED grep-based 4 frontend + 1 backend invariants + `f0a7303` fix GREEN — TriageSection reads `bacino_current` / `coverage_current` [primary root-cause] + `envSplitMissing` + 'n/a' + disclosure copy [defensive Path B leftover] + `amp_drift_detected` filtered out of envEntries [Rule 1 auto-fix] + backend HOTFIX-05 comment block [no behavior change]; Tab 5 same-class drift flagged Phase 17.3 candidate; backend payload UNCHANGED → no snapshot re-export risk for Plan 06; TS clean)
- [x] 17.2-06-PLAN.md — Snapshot regen + Vercel deploy + 6/6 UAT + governance (HOTFIX-07) — completed 2026-05-20 (snapshot `352fbd0` 1004 JSON byte-stable + initial deploy `85842a9` dpl_ERFHbCJzHVgewtoUXRVfpZWjzvgw W-05 PASS 3/3 + Wave-1 UAT Checks 1-4 PASS / Checks 5+6 FAIL via React error boundary on sibling consumers reading old bare-key contract → gap-closure within-phase 7 commits `994ad23..8a3ed45` migrate types + EnvironmentSplitSection + ContributorsSection + GeoBreakdownSection + GeoBreakdownPieChart to payload contract fields + `quota_of_drop` percentage-not-fraction Rule 1 auto-fix + regression test pinning 5 invariants → gap-closure deploy dpl_5gHyT8DKCSWjKYKrzu2N9PZJZDjh W-05 PASS 3/3 + operator re-UAT 6/6 PASS; rollback tag `pre-17.2-deploy-2026-05-20` on `d8527fd`; HOTFIX-07 closed)

### Phase 17.3: Alert Revenue Calculation Audit
**Goal**: Spiegare e documentare la discrepanza alert revenue gross segnalata da Marco (D2 mail 2026-05-19). Sample: ALT-20260322-010000-P2 → Sentinel €736, PBI €662 (01:00) o €1.166 (00:00); ALT-20260320-070000-P2 → Sentinel €1.185, PBI €688 (07:00). Ipotesi iniziale: finestra di aggregazione errata (multi-hour) o channel filter mismatch.
**Type**: audit + fix (parent: v1.3 milestone)
**Depends on**: Phase 17.2 (UI bug fix prima dell'audit numerico)
**Requirements**: AUDIT-01..AUDIT-03
**Success Criteria**:
  1. ✓ Per ciascuno dei 2 sample alert, dimostrato numericamente come il valore Sentinel viene calcolato (path codice + reproduction Python byte-match a €736.01 e €1185.04) vs come Marco se lo aspetta (orario singolo PBI)
  2. ✓ Root cause documentata (H6 NEW: tz-mismatch silent synthetic fallback) + fix landed (backend/agents/data_fetcher_real.py +13 lines tz-naive normalization)
  3. ✗→DOWNGRADED Re-run pipeline su parquet marzo per i 2 alert: revenue gross post-fix coerente con PBI ±2% — **structurally unmeetable**: GOOGLE_ADEX parquet returns €521 gross (21% off PBI €662 due to top-50 filter Phase 11 D1); HBM has no hourly source (hour_kpi.csv only GOOGLE_ADEX). Documented path-to-closure: Phase 18 / v1.4 Athena.
  4. ✓ Regression test in `scripts/test_alert_revenue_hourly_window.py` 4/4 GREEN post-fix
**Out of scope (decision at phase close)**:
  - Backfill rewrite di ~2160 alerts pre-fix (operator decides; rischio invalida Marco's reference baseline)
  - Vercel deploy (DEFERRED — code-only fix, snapshot byte-identical, no user-visible delta → R-04 chirurgico)
  - Closure del top-50 filter (Phase 18 — `/api/metrics/network-totals` extension al alert-detail layer)
  - HBM/HBP/TAM hourly ingestion (v1.4 Athena territory)
**Source of truth**: PDF email Marco 2026-05-19 + screenshot tabelle BigQuery PBI allegate.
**Plans**: Single autonomous execution (no formal sub-plans)
- [x] DIAGNOSIS (`5a02fe4`) — 358 lines, H1-H5 refuted with evidence, H6 NEW confirmed via synthetic byte-match
- [x] RED test (`01f3f90`) — 4 invariants, 2 RED pre-fix
- [x] GREEN fix (`9a91792`) — backend/agents/data_fetcher_real.py +13 lines, 4/4 invariants GREEN
- [x] Phase close (this commit) — SUMMARY + VERIFICATION + STATE/ROADMAP/REQUIREMENTS

### Phase 17.4: D2 Closure Tecnica (post Phase 17.3 downgrade)
**Goal**: Chiudere strutturalmente la D2 audit di Marco (mail 2026-05-19) per i 2 sample alert. Sample 1 GOOGLE_ADEX deve raggiungere byte-perfect PBI €662; Sample 2 HBM richiede ingestion futura (Phase 21 v1.4) — qui prepariamo code-path Athena pronto + isoliamo backfill synthetic-era dei channel non rebuildabili oggi.
**Type**: closure (parent: Phase 17.3 AUDIT-03 downgrade)
**Depends on**: Phase 17.3
**Requirements**: D2CLOSE-01, D2CLOSE-02, D2CLOSE-03, D2CLOSE-04 (new — define in REQUIREMENTS.md plan stage)
**Success Criteria**:
  1. **Sample 1 byte-perfect**: alert detail layer per GOOGLE_ADEX legge `/api/metrics/network-totals` (no top-50 filter) invece di parquet aggregato → ricostruzione Sample 1 timestamp 2026-03-22 01:00 A2 entro ±1% di PBI €662 gross (regression test inchiodato).
  2. **Athena code-ready**: `backend/connectors/athena.py:19` ALLOWED_CHANNEL_GROUPS estesa a HBM/HBP/TAM/DIRECT/DEAL; connector ritorna gracefully `None` se creds assenti (no crash, fallback synthetic flagged `data_source='synthetic_no_athena'`); test dedicato per ogni nuovo channel whitelisted.
  3. **Backfill split**: 39 alert GOOGLE_ADEX `data_source='backfill'` (2026-01-23 → 2026-03-23) ri-eseguiti via CSV direct read → `data_source='real_csv'`; 199 alert HBM/HBP/TAM/DIRECT/DEAL/OPEN_BIDDING/GOOGLE marked `deprecated=1` con `deprecation_reason='synthetic-era pre-H6-fix, Phase 21 Athena dependency'`; snapshot pre-rewrite tagged `pre-17.4-backfill-rewrite-2026-05-XX`.
  4. **Regression contract**: nuovo invariant in `scripts/test_alert_revenue_hourly_window.py` o file dedicato: Sample 1 alert post-fix == PBI €662 ±1%; nessun alert GOOGLE_ADEX post-2026-05-21 ha `data_source` ∈ {'backfill','synthetic',...} (solo 'real_parquet'/'real_csv').
**Out of scope (defer)**:
  - Sample 2 HBM byte-perfect chiusura — Phase 21 v1.4 (Athena live + credenziali)
  - V1 Channel granularity refactor — Phase 19 v1.4
  - V2 Open Market distribution study — Phase 20 v1.4
  - Email Marco Manduca SHIPPED — gate finale post Phase 21 v1.4 (9/9 punti chiusi)
**Source of truth**: 17.3-DIAGNOSIS.md + Marco mail 2026-05-19 + audit tecnico+strategico 2026-05-21 (memory `project_sentinel_*`).
**Plans**: 5 plans (4 waves)
- [x] 17.4-01-PLAN.md — RED regression contract scaffold `scripts/test_alert_revenue_pbi_parity.py` (D2CLOSE-04 RED) — Wave 1
- [x] 17.4-02-PLAN.md — Path A endpoint extension (`/api/metrics/network-totals` + `bypass_top50` param + `_compute_network_totals_for_channel` helper) + `data_fetcher_real` wiring for GOOGLE_ADEX BACKTEST → `data_source='real_csv'` (D2CLOSE-01) — Wave 2
- [x] 17.4-03-PLAN.md — Athena connector unwhitelist (ALLOWED_CHANNEL_GROUPS 2→8) + `synthetic_no_athena` provenance tag + 5 mock tests (D2CLOSE-02) — Wave 2 (file overlap with 02 promotes to Wave 3 at runtime per dep-graph rules)
- [x] 17.4-04-PLAN.md — Migration 006 (199 deprecated marking) + apply driver + rewrite script (38 GOOGLE_ADEX backfill→real_csv + 1 CSV-EOF deprecated) + report markdown (D2CLOSE-03) — Wave 3, **BLOCKING** R-05 gate on live DB
- [x] 17.4-05-PLAN.md — Snapshot re-export + `vercel --prod` (R-05 gate, pre-authorized) + W-05 byte-diff 3/3 PASS + UAT 4/4 PASS + SUMMARY/VERIFICATION + STATE/ROADMAP/REQUIREMENTS close (D2CLOSE-04 GREEN side) — Wave 4 — **COMPLETE** 2026-05-21

### Phase 18: Hardening + PBI Contract Tests + Docs
**Goal**: Regression impossible on silent-failure class; PBI match assertions automated; lineage documented
**Depends on**: Phase 17.4
**Requirements**: HARD-01, HARD-02, HARD-03, HARD-04, DOC-01
**Success Criteria**:
  1. `tests/contracts/test_parquet_db_ui.py` covers 1 known-good alert per channel (7 cases) + 1 PBI-match assertion per known metric
  2. GitHub Actions fails when `backend/db/models.py` CHECK diverges from migration-derived expected DB schema
  3. `DATA_INTEGRATION.md` updated to v1.2 schema + PBI↔Sentinel reproducibility matrix + gap disclosure (OM taxonomy, eCPM/RPM denominator, hourly YoY synthetic, fill rate measurable, Phase 17.4 D2 closure path) + reference a v1.4 (Phase 19/20/21) per V1/V2/HBM
**Plans**: 5 plans (2 waves — Wave 1 18-01/02/03/04 fully parallel; Wave 2 18-05 close)
- [x] 18-01-PLAN.md — HARD-01 tests/contracts/test_parquet_db_ui.py 7-channel parametrized parquet↔DB↔UI contract (Wave 1)
- [x] 18-02-PLAN.md — HARD-02 .github/workflows/schema-drift.yml + extended scripts/test_models_sync.py with Migration 006 + chain-against-models (Wave 1)
- [x] 18-03-PLAN.md — HARD-03 + HARD-04 .github/workflows/pbi-parity.yml + extended pbi-parity test (Sample 2 SKIP + Path A guard) + extended silent-failure regression (CSV-EOF + post-cutoff synthetic) (Wave 1)
- [x] 18-04-PLAN.md — DOC-01 DATA_INTEGRATION.md v1.3 PBI ↔ Sentinel Reproducibility Matrix + 8-gap disclosure (Wave 1)
- [x] 18-05-PLAN.md — Phase close: SUMMARY + VERIFICATION + STATE/ROADMAP/REQUIREMENTS governance (Wave 2)

## v1.4 Milestone (anticipated — scope expansion 2026-05-21)

v1.4 originalmente "Athena Live + ML-tuned thresholds + Mobile + Sell_type schema" (vedi PROJECT.md "Out of Scope" v1.3). Anticipato per chiudere 100% feedback Marco Manduca prima dell'email risposta. Scope minimo v1.4 per Marco email:
- **Phase 19**: V1 Channel Granularity Refactor (Diretta/Deal/Open Market come entità separate) — risolve falsi positivi shift inter-channel. Richiede design meeting Iolanda.
- **Phase 20**: V2 Open Market Distribution Study + UI breakdown — visualizza % revenue per intra-Open Market channel.
- **Phase 21**: Athena HBM/HBP/TAM full ingestion — chiude Sample 2 D2 byte-perfect (€688 PBI). Eredita code-ready connector da Phase 17.4.
- **Phase 22+**: scope v1.4 originale (ML, mobile, ecc.) — defer post-Marco-email.

Email Marco Manduca SHIPPED solo dopo Phase 21 close (9/9 punti Marco chiusi).

## Progress

**Execution Order:**
Sequential: 07 → 08 → 09 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17 → 18

**Critical path to unblock production alerting:** 07 → 08 → 09 → 10 (target: 1 full day)
**Parallel opportunity Phase 12:** Commit A, B, C, CORR-01/08/09 independent (different files); parallel waves during planning.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 01. Alerting Evoluto (v1.1) | — | Complete | 2026-02-21 |
| 02. Nuovi Tipi Alert (v1.1) | 4/4 | Complete | 2026-02-21 |
| 03. Operator Workflow (v1.1) | — | Complete | 2026-02-21 |
| 04. Notifiche Slack (v1.1) | — | Complete | 2026-02-21 |
| 05. Dati Live e Multi-canale (v1.1) | — | Deferred to v1.4 | - |
| 06. Revisione Documentale (v1.1) | — | Complete | 2026-02-21 |
| 07. DB WIP Investigation | 1/1 | Complete    | 2026-04-22 |
| 08. Schema Migration + ETL Extensions | 5/5 | Complete   | 2026-04-23 |
| 09. Alert Backfill + Legacy Migration | 3/3 | Complete    | 2026-04-23 |
| 10. Pipeline Silent-Failure Monitoring | 3/3 | Complete    | 2026-04-23 |
| 11. Network Totals + Filter API + Baseline | 3/3 | Complete    | 2026-04-29 |
| 12. WIP Atomic Commits + Triage Server-Side | 6/6 | Complete    | 2026-04-30 |
| 13. Dashboard Date Navigation | 2/2 | Complete    | 2026-04-30 |
| 14. UI Labeling + Filter Exposure | 5/5 | Complete   | 2026-04-30 |
| 15. UI Resilience | 4/4 | Complete    | 2026-05-04 |
| 16. Vercel Static Export Decision | 1/4 | Complete    | 2026-05-06 |
| 17. Data Cleanup | 1/1 | Complete    | 2026-05-07 |
| 17.1. Publisher Mapping Correction | 5/5 | Complete    | 2026-05-20 |
| 17.2. Marco Feedback Hotfix | 6/6 | Complete    | 2026-05-20 |
| 17.3. Alert Revenue Calc Audit | 1/1 | Complete    | 2026-05-21 |
| 17.4. D2 Closure Tecnica | 5/5 | Complete   | 2026-05-21 |
| 18. Hardening + PBI Contract Tests + Docs | 5/5 | Complete   | 2026-05-21 |
| 19. (v1.4) V1 Channel Granularity Refactor | 0/TBD | Not started | - |
| 20. (v1.4) V2 Open Market Distribution Study | 0/TBD | Not started | - |
| 21. (v1.4) Athena HBM/HBP/TAM Full Ingestion | 0/TBD | Not started | - |

---

## Backlog

### Phase 999.2: notifier `_save_to_db` dedup regression — `find_open_alert` window (BACKLOG)

**Goal:** [Captured for future planning] Fix pre-existing Phase 10.1 regression: `_save_to_db` returns `(True, True)` on 2nd consecutive call with same channel+rule instead of `(True, False)` (dedup-UPDATE path). `find_open_alert()` doesn't detect the row INSERTed by the previous call.
**Requirements:** TBD (likely revives MONITOR-08 counter semantics + MONITOR-04/MAJOR-NEW-02 boundary)
**Plans:** 5/5 plans complete

**Discovery context (2026-04-29 Phase 11 regression gate):**
- Failing test: `scripts/test_operations_idempotency.py::TestNotifierSaveToDbCanonicalFormat::test_save_to_db_returns_is_new_signal`
- Verified pre-existing at base `4b7f661` (pre-Phase-11) — Phase 11 innocent (only added API surface, no shared code mutation)
- Impact: `alerts_written_count` (MONITOR-08) may double-count INSERTs as "new" in burst scenarios; dedup-UPDATE path appears unreachable when first INSERT precedes second call within same `find_open_alert` time window
- Likely root cause: `find_open_alert` time-window query OR canonical timestamp comparison drift in `backend/db/operations.py`

**Investigation seed:**
- Read `backend/db/operations.find_open_alert` and recent dedup-window logic (Phase 10.1 commits: `c7c2a7b`, `fe02601`, `3ac9543`, `6ac3c8b`)
- Run failing test against multiple DB states; instrument with logging
- Cross-check `test_save_to_db_update_writes_canonical` (PASSES) vs `test_save_to_db_returns_is_new_signal` (FAILS) — both call `_save_to_db`, but the passing one pre-seeds via `create_alert()` directly while the failing one relies on first `_save_to_db` to write the row

**Suggested target:** Phase 11.1 (decimal hotfix) OR fold into Phase 18 hardening sweep.

Plans:
- [ ] TBD (promote with /gsd-review-backlog when ready)
