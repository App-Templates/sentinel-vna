# Roadmap: SENTINEL

## Milestones

- [x] **v1.0 MVP** — Piattaforma base (shipped baseline)
- [x] **v1.1 Alerting Evoluto + Operator Workflow** — Phases 01-06 (shipped 2026-02-21)
- [x] **v1.2 New IT Dataset + Advanced Rules** — non-GSD drift (shipped 2026-03-26; runtime live, silent-failure discovered by intel 2026-04-22)
- [ ] **v1.3 Stabilization** — Phases 07-18 (in progress, started 2026-04-22, expanded evening same day post deep audit)

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
- [ ] **Phase 11: Network Totals Endpoint + Filter API** — `/metrics/network-totals` hybrid + sell_type query param + server-side baseline (API-03)
- [ ] **Phase 12: WIP Atomic Commits (Foundation + Correctness + Triage Server-Side)** — Commits A/B/C + CORR-01/08/09 in parallel waves
- [ ] **Phase 13: Dashboard Date Navigation** — Commit D (consumer of Commit C contract)
- [ ] **Phase 14: UI Labeling + Filter Exposure** — gross/net toggle + channel badges + reference period labels + filter state in URL + derived filters (sell_type_proxy, geo, env, publisher tier)
- [ ] **Phase 15: UI Resilience** — error boundaries + diagnostic empty states
- [ ] **Phase 16: Vercel Static Export Decision** — Ship Commit E as v1.3.1 or formally shelve
- [ ] **Phase 17: Data Cleanup** — floor_cpm dead column + Mondadori/Mondadori_npa aggregation
- [ ] **Phase 18: Hardening + PBI Contract Tests + Docs** — tests/contracts + CI schema gate + DATA_INTEGRATION.md + PBI↔Sentinel gap disclosure

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
- [ ] 10.2-01-PLAN.md — send_daily_digest canonical cutoff (CR-01) + HARD-03 drift gate extension (MONITOR-11)
- [ ] 10.2-02-PLAN.md — bound Retry-After parsing in send_meta_alert (anti-DoS, MONITOR-13 / WR-02)
- [ ] 10.2-03-PLAN.md — atomic _restore across 4 migration drivers (MONITOR-14 / WR-03)
- [ ] 10.2-04-PLAN.md — Slack webhook rotation: YAML→null + env-var ingress + operator R-05 sign-off (MONITOR-12)

### Phase 11: Network Totals Endpoint + Filter API + Server-Side Baseline
**Goal**: PBI-parity dashboard totals via upstream-streaming endpoint; filter API supports sell_type_proxy; alert payload includes server-computed baselines
**Depends on**: Phase 10
**Requirements**: API-01, API-02, API-03
**Success Criteria**:
  1. `GET /api/metrics/network-totals?date=...&channel=GOOGLE_ADEX` returns value matching PBI 2026-01-12 €27.2k gross within 2%
  2. `GET /api/publishers/top?sell_type=Open_Market` filters via channel_group mapping (95% confidence confirmed by config:alerting_rules.yaml:84-91)
  3. Alert payload contains `baseline_bacino` and `baseline_coverage` computed server-side (7w rolling same-weekday), NOT derived client-side
**Plans**: TBD

### Phase 12: WIP Atomic Commits + Triage Server-Side
**Goal**: 2-month WIP landed as reviewable atomic commits; TriageSection heuristic removed
**Depends on**: Phase 11 (needs API-03 for baseline fields)
**Requirements**: WIP-02, WIP-03, WIP-04, CORR-01, CORR-08, CORR-09
**Success Criteria**:
  1. `git log` shows 3 atomic commits (A design+i18n, B IT→EN, C backend correctness) + CORR-01/08/09 landed
  2. `TriageSection.tsx` no longer contains `revenueRatio * 0.95` or `avgCoverage + 0.05`; reads `alert.baseline_bacino` / `baseline_coverage`
  3. `KpiCards.tsx` `avgFillRate` uses weighted average; labels i18n-enabled
  4. `git status` post-phase shows only Commit D (WIP-05) + Commit E (WIP-06) files outstanding
**Plans**: TBD
**UI hint**: yes

### Phase 13: Dashboard Date Navigation
**Goal**: Operators navigate dashboard by date with YoY 7-week rolling baseline
**Depends on**: Phase 12
**Requirements**: WIP-05
**Success Criteria**:
  1. `RevenueStatus24h` date picker populated from `available_dates`, loads selected day without errors
  2. YoY widget shows 7-week rolling with explicit baseline window label
  3. Commit D atomic: exactly 8 files per WIP split, no scope creep
**Plans**: TBD
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
**Plans**: TBD
**UI hint**: yes

### Phase 16: Vercel Static Export Decision
**Goal**: Resolve 5-file architectural WIP (Vercel config + static export) — ship or shelve
**Depends on**: Phase 15
**Requirements**: WIP-06
**Success Criteria**:
  1. Decision in PROJECT.md Key Decisions: ship v1.3.1 with migration plan OR shelve with rationale + branch reference
  2. `git status` no longer lists Commit E files as uncommitted on main
  3. Deployment docs consistent with chosen model
**Plans**: TBD

### Phase 17: Data Cleanup
**Goal**: Dead / inconsistent data elements resolved
**Depends on**: Phase 16
**Requirements**: CLEAN-01, CLEAN-02
**Success Criteria**:
  1. `floor_cpm` decision: removed from schema OR populated from source (documented)
  2. `Mondadori` + `Mondadori_npa` handled: aggregated or disclosed with rationale
**Plans**: TBD

### Phase 18: Hardening + PBI Contract Tests + Docs
**Goal**: Regression impossible on silent-failure class; PBI match assertions automated; lineage documented
**Depends on**: Phase 17
**Requirements**: HARD-01, HARD-02, HARD-03, HARD-04, DOC-01
**Success Criteria**:
  1. `tests/contracts/test_parquet_db_ui.py` covers 1 known-good alert per channel (7 cases) + 1 PBI-match assertion per known metric
  2. GitHub Actions fails when `backend/db/models.py` CHECK diverges from migration-derived expected DB schema
  3. `DATA_INTEGRATION.md` updated to v1.2 schema + PBI↔Sentinel reproducibility matrix + gap disclosure (OM taxonomy, eCPM/RPM denominator, hourly YoY synthetic, fill rate measurable)
**Plans**: TBD

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
| 11. Network Totals + Filter API + Baseline | 0/TBD | Not started | - |
| 12. WIP Atomic Commits + Triage Server-Side | 0/TBD | Not started | - |
| 13. Dashboard Date Navigation | 0/TBD | Not started | - |
| 14. UI Labeling + Filter Exposure | 0/TBD | Not started | - |
| 15. UI Resilience | 0/TBD | Not started | - |
| 16. Vercel Static Export Decision | 0/TBD | Not started | - |
| 17. Data Cleanup | 0/TBD | Not started | - |
| 18. Hardening + PBI Contract Tests + Docs | 0/TBD | Not started | - |

---

## Backlog

_(empty — Phase 999.1 promoted to §Phase Details on 2026-04-25 per 999.1-DECISION.md Path A)_
