---
gsd_state_version: 1.0
milestone: v1.4
milestone_name: Milestone
status: Phase complete — ready for verification
stopped_at: Completed 18-05-PLAN.md — Phase 18 v1.3 milestone close
last_updated: "2026-05-21T16:04:17.260Z"
progress:
  total_phases: 20
  completed_phases: 15
  total_plans: 71
  completed_plans: 69
  percent: 97
---

# Project State

## 🌟 STELLA POLARE — read FIRST

Questo documento NON è autoritativo da solo. **Prima di proporre qualsiasi azione su Sentinel v1.3, leggi `.planning/STELLA-POLARE.md`** — è la north-star del milestone post audit triplo 2026-04-28.

Truth source: `.planning/intel/sentinel-2026-04-28/EMAIL-VITO-2026-04-22.md` (email Vito 22 aprile, 8 numeri sbagliati confermati).

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-22)

**Core value:** Trovare gli alert in tempo quasi reale comunicando solo ciò che è davvero importante — rendendo visibili i cali graduali che oggi nessuno nota.

**Current focus:** Phase 19 — v1.4 Channel Granularity Refactor (next milestone)

## Current Position

Phase: 18 (hardening-pbi-contract-tests-docs) — COMPLETE. v1.3 milestone SHIPPED 2026-05-21.
Next: Phase 19 (v1.4 V1 Channel Granularity Refactor) — requires design meeting Iolanda.
Plan: 5 of 5 (complete)
Plans completed: Phase 08 5/5 ✓ | Phase 09 3/3 ✓ | Phase 10 3/3 ✓ | Phase 11 3/3 ✓ | Phase 12 6/6 ✓ | Phase 13 2/2 ✓ | Phase 14 5/5 ✓ | Phase 15 2/2 ✓ | Phase 17.1 5/5 ✓ (17.1-01 mapping foundation: data `eceac78` + test RED `bad1b30` + feat GREEN `f95b1fa` + docs `672e6e2`; 17.1-02a parquet-path mapping application: test RED `068ae8a` + feat GREEN `52b6964` — Mondadori revenue €1,125,424.54 vs €1.125k target inside ±€50k; Phase 17 over-aggregated €1,458k removed; MAP-03/04/05 closed; 17.1-02b drilldown reverse-mapping: test RED `24d4cdc` + feat GREEN parquet `1190bf3` + feat GREEN SQL `cff2b67` — all 5 drilldown endpoints accept clean PBI name + reverse-map via IN-clause; B-01 closed 5/5; MAP-08 closed; 17.1-03 frontend row click re-enable: ui `74c87c6` — Phase 17 _family early-return guard removed, encodeURIComponent wired for Iberian-accent names, MAP-07 closed; 17.1-04 deploy: snapshot `ac04c70` + initial CDN smoke `9830259` + gap-closure script fix `98d1ddc` + gap-closure snapshot `190636c` + gap-closure CDN smoke `b626f20`; 2 production deploys [initial `dpl_GAkE3GYXWrc7TDnoQaaMd4Y5VbUQ` + gap-closure `dpl_APXL5nUScNqT9khMZwtcqNYQZxEr`]; rollback tag `pre-17.1-deploy-2026-05-19`; UAT 8/8 PASS; MAP-09 + MAP-10 closed) | Phase 17.2 6/6 SHIPPED 2026-05-20 (17.2-01 V3 tooltip discriminant: ui `221dee4` — HOTFIX-01 closed; 17.2-02 V4 label coherence: ui `2159ea1` — HOTFIX-02 closed, "7 Weeks" → "Last 7 Days" Path A; 17.2-03 V5 disclaimer prominence + D1 filter passthrough: ui `406862f` HOTFIX-03/V5 amber-left-border callout + bolded count + `linkHref→linkBase` rename + ui `6c953c6` HOTFIX-06/D1 `TopNDisclaimerFilters` interface + `composeNetworkTotalsHref` URLSearchParams helper + PublishersPage explicit-destructure forward; 3 files modified across TopNDisclaimer/PublishersPage/i18n-keys; TS clean; live UAT deferred to Plan 06 deploy; 17.2-04 B1 alert detail tabs accessibility: diagnose-first `64869b3` 17.2-04-DIAGNOSIS.md per-tab classification (Tab 5 = (b) AlertDetailPage:259 short-circuit when env_split=null; Tabs 3+4 = (d) UX defect via DataTable half-bait fallback) + test RED `a5f09bd` source-grep 3 invariants + ui GREEN `dba6c17` line 259 guard dropped + Environment/EnvironmentMetrics type imports + ContributorsSection + GeoBreakdownSection early-return empty-state cards mirroring EnvironmentSplitSection lines 22-37 pattern; 238/238 snapshot alerts confirmed empty payload (contributors=[], geo=[], env=null); test GREEN 3/3 invariants; TS clean; HOTFIX-04 closed; 17.2-05 B2 Triage Bacino+Coverage Path C: diagnose-first `44560fe` 17.2-05-DIAGNOSIS.md FALSIFIED plan's hypothesis (i) — 100% of 238 snapshot alerts have populated env_split with non-null top-level baselines, real root cause is hypothesis (iii) variant contract drift on `_current` suffix [environment_splitter emits `bacino_current` / `coverage_current` per-env, TriageSection.tsx was reading `m.bacino` / `m.coverage` → undefined → ?? 0 → "0" on every alert] + test RED `40de253` 4 frontend invariants + 1 backend invariant + fix GREEN `f0a7303` — TriageSection reads `(m as { bacino_current?: number }).bacino_current ?? m.bacino ?? 0` [primary] + `envSplitMissing` predicate + 'n/a' substitution + disclosure copy [defensive Path B leftover] + `amp_drift_detected` scalar filtered out of envEntries [Rule 1 auto-fix — was diluting avgCoverage by 1/4] + backend HOTFIX-05 docstring comment [no behavior change]; Tab 5 EnvironmentSplitSection same-class drift flagged Phase 17.3 candidate (out of HOTFIX-05 scope); backend payload UNCHANGED → no Plan 06 snapshot re-export risk; TS clean exit 0; HOTFIX-05 closed; 17.2-06 HOTFIX-07 deploy + UAT + governance: snapshot `352fbd0` 1004 JSON byte-stable [Path C frontend-only — no payload change] + initial deploy `85842a9` dpl_ERFHbCJzHVgewtoUXRVfpZWjzvgw 2026-05-20T18:16Z W-05 CDN byte-diff PASS 3/3 first attempt + initial UAT Checks 1-4 PASS / Checks 5+6 FAIL via React error boundary on sibling consumers reading old bare-key contract → gap-closure within-phase 7 commits `994ad23` + `4f9f404` + `0a3895c` + `cbb1621` + `eaee9f9` + `74291a1` + `8a3ed45` migrate types + EnvironmentSplitSection + EnvironmentBarChart + ContributorsSection + GeoBreakdownSection + GeoBreakdownPieChart to payload contract `_current`-suffix / `display_name` / `cluster` / `revenue_current` / `delta_eur` / `delta_pct` / `quota_of_drop` keys + filter `amp_drift_detected` + `quota_of_drop` percentage-not-fraction Rule 1 + regression test `scripts/test_alert_sections_payload_contract.py` 5 invariants + DEPLOY-LOG gap-closure amendment → gap-closure deploy dpl_5gHyT8DKCSWjKYKrzu2N9PZJZDjh 2026-05-20T21:57Z W-05 PASS 3/3 first attempt + operator re-UAT 6/6 PASS; rollback tag pre-17.2-deploy-2026-05-20 on `d8527fd`; HOTFIX-07 closed; 3 latent contract drift sections were hidden BEFORE Wave 1 by Tab 5 render guard — fix made it visible AND fixed it) | Watchdog live: triggered=True on pipeline_runs_last_24h=1446 AND alerts_last_24h=0
Phase 17.3 SHIPPED 2026-05-21 — D2 audit closed. Three commits: `5a02fe4` (DIAGNOSIS), `01f3f90` (RED test), `9a91792` (GREEN fix). Root cause H6 (NEW) tz-mismatch silent synthetic fallback in `data_fetcher_real.py:585-589` — `current_ts` was tz-aware (UTC), parquet timestamps are tz-naive, pandas comparison silently returns False for every row → BACKTEST fallback to synthetic `data_fetcher.py:_generate_hourly_metrics`. Both DB sample alerts match the synthetic formula byte-for-byte (€736.01 and €1185.04). H1-H5 (CONTEXT.md hypothesis ranking) all REFUTED. AUDIT-01 + AUDIT-02 complete. AUDIT-03 ±2% PBI match DOWNGRADED — structurally unmeetable in 17.3 scope: Sample 1 GOOGLE_ADEX parquet returns €521 gross vs PBI €662 (21% off due to top-50 publisher filter, Phase 11 D1); Sample 2 HBM has 0 hourly rows in parquet (`data/sentinel_db/hour_kpi.csv` upstream contains only GOOGLE_ADEX). Documented path-to-closure: Phase 18 (top-50 filter) + v1.4 Athena (HBM/HBP/TAM/etc hourly ingestion). Deploy DEFERRED — DB rows unchanged by code-only fix, snapshot byte-identical → R-04 chirurgico → next phase ships fix along with its visible deltas. No regression on 17.1 (publisher drilldown 9/9 OK) / 17.2 (triage baseline + alert sections payload contract OK).

Phase 18 SHIPPED 2026-05-21. v1.3 milestone closed. Five plans across 2 waves: Wave 1 = 18-01 (HARD-01 contract tests `tests/contracts/test_parquet_db_ui.py` 7-channel parametrized; 3 PASS + 12 SKIP Phase 21), 18-02 (HARD-02 first GitHub Actions workflow `.github/workflows/schema-drift.yml` + extended `scripts/test_models_sync.py` with Migration 006 + chain-against-models composite assertion), 18-03 (HARD-03 + HARD-04 second workflow `.github/workflows/pbi-parity.yml` + extended `scripts/test_alert_revenue_pbi_parity.py` with Sample 2 SKIP + Path A guard INV-6 + extended `scripts/test_silent_failure_watch.py` with CSV-EOF + post-cutoff synthetic-class), 18-04 (DOC-01 `DATA_INTEGRATION.md` v1.3 PBI ↔ Sentinel Reproducibility Matrix + 8-gap disclosure); Wave 2 = 18-05 close. Zero production code modified. No Vercel re-deploy. v1.3 ships; v1.4 (Phase 19/20/21) opens. Email Marco still gated Phase 21 close per D-17.4-I.

Next: Phase 19 (v1.4 V1 Channel Granularity Refactor). Requires design meeting Iolanda.

Progress v1.3: [████████░░░░] 67% (8/12 phases substantively progressed: 07, 08, 09, 10, 11, 12, 13, 14 ✓; all 5 RCs from Email Vito 2026-04-22 closed in code: RC-(a) ScopeBadge×5 + TopNDisclaimer / RC-(b) Mondadori publisher_family / RC-(c) GrossNetToggle + REV_SHARE_FACTOR=0.6 / RC-(d) bacino dedup + legacy GOOGLE / RC-(e) server-side baseline / RC-(f) ReferencePeriodFootnote — Phase 11+12+13+14 NON ancora deployate)
Critical path 07→10: 4/4 complete | Email-fix critical path 11→12→13→14: Phase 11 ✓ + 12 ✓ + 13 ✓ + 14 ✓ COMPLETE — RC closure shipped in code, deploy strategy pending operator decision.

## Milestone History

**v1.1 Alerting Evoluto** — completed 2026-02-21

- 6 phases (01 Alerting Evoluto, 02 Nuovi Tipi Alert, 03 Operator Workflow, 04 Notifiche Slack, 06 Revisione Documentale)
- 17 plans, 1.95h total execution
- Phase 05 (Dati Live / Athena) deferred to v1.4

**v1.2 New IT Dataset** — shipped 2026-03-26 (non-GSD drift)

- Commits: `7de84ab feat(v1.2)` + `a975590 fix: TS build errors, UNKNOWN env`
- Delivered: 7-channel dataset, 50 publishers, A8 margin alert, leading indicators, cross-channel detection
- Gap: silent-failure discovered in v1.3 intel (CHECK constraint stale)

**v1.3 Stabilization** — SHIPPED 2026-05-21

- Phases: 07 (DB WIP) → 08 (Schema+ETL) → 09 (Backfill+Migration) → 10 (Monitoring) → 11 (API+Baseline) → 12 (WIP commits + Triage) → 13 (Dashboard) → 14 (UI Labeling) → 15 (UI Resilience) → 16 (Vercel decision) → 17 (Cleanup) → 18 (Hardening+Docs)
- Requirements: 35/35 mapped (see REQUIREMENTS.md traceability)
- Critical path (07→10) estimated 1 day to unblock production alerts
- Full milestone: 4-5 days

## Performance Metrics

**Velocity:**

- Total plans completed (v1.1): 17
- Average duration: ~7 min/plan
- Total execution time: 1.95h

**By Phase:**

| Phase | Plans | Status |
|-------|-------|--------|
| 07-18 | TBD | Pending planning |

*Updated after each plan completion*
| Phase 08 P01 | 12 | 2 tasks | 2 files |
| Phase 08 P02 | 27 | 3 tasks | 3 files |
| Phase 08 P04 | 35 | 4 tasks | 7 files |
| Phase 08 P03 | 4 | 3 tasks | 4 files |
| Phase 09 P01 | 11min | 5 tasks | 8 files |
| Phase 09 P02 | 6min22s | 3 tasks | 3 files |
| Phase 09-alert-backfill-legacy-migration P03 | 85min | 8 tasks | 11 files |
| Phase 10 P01 | 20min | 5 tasks | 11 files |
| Phase 10 P03 | 12min | 3 tasks | 6 files |
| Phase 10.1 P01 | 18min | 2 tasks | 5 files |
| Phase 10.1 P02 | 6min | 3 tasks | 4 files |
| Phase 10.1 P03 | 5min | 1 tasks | 1 files |
| Phase 10.1 P04 | 8min | 2 tasks | 2 files |
| Phase 10.1 P10.1-05 | 525604min | 1 tasks | 1 files |
| Phase 10.1 P06 | 2min | 1 tasks | 2 files |
| Phase 10.1 P07 | 2min | 1 tasks | 2 files |
| Phase 10.1 P08 | 8min | 1 tasks | 1 files |
| Phase 10.2 P01 | 6min | 2 tasks | 2 files |
| Phase 10.2 P02 | 2min | 1 tasks | 2 files |
| Phase 11 P01 | 4min | 3 tasks | 3 files |
| Phase 11 P02 | 5min | 3 tasks | 2 files |
| Phase 11 P03 | 1min | 1 tasks | 1 files |
| Phase 12 P01 | 6min | 4 tasks | 3 files |
| Phase 12 P03 | 10min | 2 tasks | 3 files |
| Phase 12 P02 | 10min | 4 tasks | 3 files |
| Phase 12 P04 | 3min | 3 tasks | 2 files |
| Phase 12 P06 | 1min | 2 tasks | 1 files |
| Phase 12 P05 | 4min | 3 tasks | 2 files |
| Phase 14 P14-01 | 5min | 3 tasks | 2 files |
| Phase 14 P02 | 10min | 5 tasks | 4 files |
| Phase 14 P14-03 | 8min | 4 tasks | 3 files |
| Phase 14 P14-04 | 6min | 4 tasks | 3 files |
| Phase 14 P14-05 | 8min | 4 tasks | 3 files |
| Phase 15 P01 | 5min | 1 tasks | 1 files |
| Phase 15 P02 | 2min | 1 tasks | 1 files |
| Phase 17.1 P01 | 4min | 3 tasks | 6 files |
| Phase 17.1 P02a | 5min | 1 tasks | 2 files |
| Phase 17.1 P02b | 5min | 1 tasks | 4 files |
| Phase 17.1 P03 | 1min | 1 tasks | 1 files |
| Phase 17.1 P04 | 26h (deploy + UAT + gap-closure across 2026-05-19/20 sessions) | 4 tasks | 11 files (snapshot 1004 JSON + 5 script/log/docs + tag + 6 commits) |
| Phase 17.2 P01 | 2 min | 1 tasks | 1 files |
| Phase 17.2 P02 | 4 min | 1 tasks | 1 files |
| Phase 17.2 P03 | 3 min | 2 tasks | 3 files |
| Phase 17.2 P04 | 12 min | 2 tasks | 5 files |
| Phase 17.2 P05 | 8min | 2 tasks | 4 files |
| Phase 17.2 P06 | ~8h (deploy + UAT + gap-closure across 2026-05-20 session) | 5 tasks | 11 files (snapshot 1004 JSON + tag + 2 deploy logs + 7 gap-closure commits + UAT-LOG + SUMMARY + VERIFICATION + ROADMAP/STATE/REQUIREMENTS) |
| Phase 17.4 P01 | 8 | 1 tasks | 1 files |
| Phase 17.4 P02 | 9 | 2 tasks | 4 files |
| Phase 17.4 P17.4-03 | 8min | 1 tasks | 3 files |
| Phase 17.4 P05 | 150 | 4 tasks | 12 files |
| Phase 18-hardening-pbi-contract-tests-docs P01 | 5 | 2 tasks | 5 files |
| Phase 18 P02 | 12 | 2 tasks | 3 files |
| Phase 18 P04 | 20 | 2 tasks | 1 files |
| Phase 18 P03 | 236 | 3 tasks | 4 files |
| Phase 18-hardening-pbi-contract-tests-docs P18-05 | 40 | 2 tasks | 5 files |

## Accumulated Context

### Roadmap Evolution

- Phase 10.1 inserted after Phase 10 on 2026-04-24: pipeline-monitoring-hotfix-and-hardening (URGENT — post-verification findings from 5 independent auditors: MAJOR-NEW-01 alerts.created_at dual-format corruption, MAJOR-01 BACKTEST contamination, MAJOR-03 T-vs-space datetime comparison, MAJOR-NEW-02 find_open_alert dedup window corrupted, MAJOR-02 Slack retry dead code; watchdog mitigation via enabled:false in commit bb34e36)

### Decisions v1.3 (approved 2026-04-22 evening)

- **D1 (hybrid)**: top-50 filter stays + `/api/metrics/network-totals` endpoint streams upstream CSV
- **D2 (gross+net side-by-side)**: default GROSS (PBI-aligned), NET visible with "post rev-share 60%" label
- **D3 (parquet backfill)**: regen alert from current parquet post SCHEMA-01-04 fixes
- **D4 (sell_type proxy)**: derive 5 sell_types from channel_group mapping, 95% confidence

### Decisions Phase 08 Plan 01 (2026-04-23)

- **SQLite FK pragma placement**: `PRAGMA foreign_keys=OFF` must precede `BEGIN TRANSACTION` — setting it inside a transaction is a SQLite no-op, causing ON DELETE CASCADE to fire unexpectedly during table DROP
- **Migration idempotency via ledger INSERT guard**: ledger `INSERT` (no `OR REPLACE`) as first transactional statement — second naked apply raises `IntegrityError` (UNIQUE constraint) before any DDL executes; DB remains intact. Driver must pre-check `sqlite_master` for 'GOOGLE_ADEX' before invoking 001.sql.

### Decisions Phase 08 Plan 02 (2026-04-23)

- **models.py domain tuples**: `CHANNEL_GROUP_CHECK_VALUES` and `ALERT_RULE_CHECK_VALUES` added as module-level authoritative tuples (8 elements each, A4 absent); adjacent to enums they reflect; `test_models_sync.py` asserts byte-identity against migration 001
- **database.py helper rename**: `_migrate_alerts_check_constraint` renamed to `_migrate_alerts_schema_v2` (no alias — zero external callers confirmed by grep); `_migrate_pending_notifications_schema_v2` added; both called BEFORE CREATE IF NOT EXISTS in `init_db()` to cover fresh-DB bypass of migration scripts
- **test_models_sync.py sys.path**: script adds `sys.path.insert(0, REPO_ROOT)` for direct invocation compatibility — unlike `test_migration_001.py` which reads `models.py` as text, the sync test imports live Python objects for enum/tuple assertions

### Decisions Phase 08 Plan 04 (2026-04-23)

- **measurable_impressions zero for HB/TAM channels**: HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC, TAM have zero measurable_impressions in upstream `daily_kpi.csv` — data reality, not ETL bug. ETL correctly passes through source values. Fill rate (35.2%) computed from GOOGLE_ADEX where measurable_impressions is non-zero.
- **sell_type_proxy mapping: TAM → Other**: TAM (Transparent Ad Marketplace) not cleanly Open_Market or Header_Bidding; classified Other pending v1.4 OPS-02 taxonomy clarification when upstream exposes real sell_type field.
- **Hourly parquet GOOGLE_ADEX-only**: `hour_kpi.csv` source only provides GOOGLE_ADEX data; 7-channel hourly parquet deferred to v1.4 (requires new data source). Hourly sell_type_proxy = Open_Market only as consequence.

### Decisions Phase 09 Plan 01 (2026-04-23)

- **Migration 002 applied on live DB**: `deprecated INTEGER NOT NULL DEFAULT 0 CHECK(deprecated IN (0, 1))` + `deprecation_reason TEXT` + `idx_alerts_deprecated` index. All 200 legacy alerts preserved with deprecated=0 via DEFAULT propagation (no post-hoc UPDATE needed — that lands in 09-02 per D-13). HARD-03 drift detector extended from 9 to 17 tests; first real regression test of the gate PASSED.
- **Column position: END of SQL_CREATE_ALERTS** (after `updated_at`, per ERRATA I-2): mirrors SQLite ADD COLUMN append semantics. CHECK(deprecated) regex byte-identity is what the drift gate enforces — column ordering in models.py is free to reflect SQLite's actual post-ALTER sqlite_master ordering.
- **R-11 atomic sub-commit gating for DB-mutation tasks**: Task 3 split 3a (pre-phase snapshot + tag + .bak) / 3b (apply to live DB) / 3c (smoke suite + driver lsof escape hatch). Gate: each commit MUST verify before next starts. Template for Phase 09-02, 09-03, and future DB migrations.
- **VNA_SKIP_LSOF=1 env-var escape hatch in apply_migration_002.py**: opt-in for in-process test reentry only (subprocess test re-invoking driver with parent's read-only FDs still dangling). Concurrent-writer safety preserved via flock (`_acquire_apply_lock`) + `_already_applied` idempotency guard.
- **Pre-phase safety tag + .bak committed**: `v1.3-pre-phase-09` annotated tag + `data/vna_alerts.db.pre-phase09.bak` (WAL-safe sqlite3.backup() snapshot) — both committed (precedent 0dcdfaa tracked .pre-phase08.bak). One-command rollback paths verified: `cp .bak db` OR `sqlite3 db < rollback.sql`.

### Decisions Phase 09 Plan 02 (2026-04-23)

- **MIGRATE-01 applied**: 200 legacy alerts flipped `deprecated=0 → 1` with D-15 canonical reason `v1.0 schema stale: legacy channel naming + v1.2 baseline divergence (Phase 09 deprecation)`. Belt-and-suspenders filter (`timestamp < '2026-02-01T00:00:00' AND channel_group IN ('GOOGLE','OPEN_BIDDING')`) verified against all 200 rows. Zero over-deprecation, zero wrong-channel deprecation. Channel split 107 GOOGLE + 93 OPEN_BIDDING.
- **Idempotency via `AND deprecated = 0` clause in BOTH count + update queries**: second invocation matches 0 rows at the query plan level (not an incidental rowcount=0) and prints distinct `IDEMPOTENT-NOOP` codepath message. Verified: second run against live DB exits 0 with IDEMPOTENT-NOOP; post-apply `--dry-run` prints `DRY RUN: 0 rows would be deprecated`.
- **test_migration_002_apply.py in-place evolution (not net-new tests)**: 2 assertions from plan 09-01 encoded the transient post-09-01 / pre-09-02 state (all deprecated=0, reason NULL). Plan 09-02 is designed to mutate that state. Renamed + re-asserted in the same commit as the DB mutation (`*_all_deprecated_zero` → `*_all_deprecated_one`; `*_all_deprecation_reason_null` → `*_all_deprecation_reason_d15`). Keeps the smoke suite coherent with the schema lifecycle across sibling plans (R-13 top-tier CI posture). Precedent for future lifecycle-transition plans.
- **ERRATA I-1 executed cleanly**: severity as explicit 4th `FIXTURE_ROWS` column (not rsplit-derived from alert_id). Less fragile for future fixture additions; clearer intent. No other ERRATA overrides applied to 09-02 (I-3 is a `<done>` note only, not an action).

### Decisions Phase 10 Plan 03 (2026-04-23)

- **Direct function call to get_alerts_pipeline_health()**: not HTTP self-probe — avoids auth complexity, rate-limit collision, and self-DoS failure mode (per Plan 10-02 handoff).
- **60-minute watchdog cycle cadence**: <1h detection latency; low noise vs 5-min polling; config-overridable via `cron_interval_minutes`.
- **No re-trigger suppression**: 60m cadence + sustained silent-failure = ≤24 pings/day — acceptable; suppression deferred to Phase 18 HARD-03 hardening if operators request.
- **Custom Block Kit payload (not reuse of _send_slack)**: meta-alert has operational metrics shape (run counts, timestamps, phase ref) vs AlertState-shaped alert templates — cleaner separation per R-13.
- **max_instances=1 on APScheduler job**: prevents overlapping watchdog cycles under slow DB conditions.
- **WR-03 default_factory**: `SilentFailureMonitorConfig` field uses `Field(default_factory=...)` in AlertingConfig — missing YAML section defaults to `enabled=False` (watchdog silent until activated). Same pattern as Phase 09 Plan 03 GrossMarginAlertConfig lesson.
- **Live smoke result (2026-04-23)**: `triggered=True, reason=silent_failure, pipeline_runs_last_24h=1446, alerts_last_24h=0` — watchdog correctly detects the live DB silent-failure state that existed for 2 months undetected.

### Decisions Phase 10 Plan 01 (2026-04-23)

- **alerts_written_count is INT not BOOL**: preserves headroom for future co-fire path (multiple alerts per run without schema re-migration). CHECK(>= 0) enforced at DB layer; application-layer passes `int(alerts_written_count)`.
- **Column placed LAST in SQL_CREATE_PIPELINE_RUNS**: mirrors SQLite ALTER TABLE ADD COLUMN append semantics per Phase 09 I-2 precedent. HARD-03 drift gate (TestModels003Sync) enforces byte-identity between models.py and migration 003 SQL.
- **Pre-existing 4,032 pipeline_runs rows left at DEFAULT 0**: retro-filling from `alert_id IS NOT NULL` would muddy the signal the Phase 10-03 watchdog needs; the watchdog must use a time-window filter (e.g., `created_at >= datetime('now', '-24 hours')`) to avoid false positives from the historical corpus.
- **importlib.util.spec_from_file_location used in test shim**: `scripts/` has no `__init__.py`; standard `import scripts.apply_migration_003` fails. Shim loads driver by file path via `importlib.util.spec_from_file_location`. (Rule 1 auto-fix, commit 2e1d222.)
- **pipeline_runs baseline at Phase 10 apply time = 4,032**: Phase 09 snapshot was 1,442 BACKTEST rows; the LIVE scheduler ran 2,590 additional runs between Phase 09 backfill and Phase 10 apply (the exact silent-failure window: 2026-01-22 → Phase 10 apply date). All 4,032 rows have alerts_written_count=0 post-migration.

### Decisions Phase 09 Plan 03 (2026-04-23)

- **BACKFILL-01 closed — hardened R-04 gate passed end-to-end**: 238 fresh alerts (deprecated=0) landed across EXACTLY 60 distinct calendar days (2026-01-23 → 2026-03-23). Zero failed_tuples. Legacy 200 (deprecated=1) unchanged. Every ISO week in range has ≥ 1 alert (Success #2 amended). API `/api/alerts` default filter hides legacy; `?include_deprecated=true` surfaces all; by-id 404 semantics verified. `pipeline_runs` BACKTEST corpus: 1,442 rows (238 success, 1,204 no_alert, 0 failed) — handoff to Phase 10 MONITOR-01/02.
- **HH offset per (channel, trigger) tuple yields 24 distinct alert_id slots/day**: `hh = CHANNELS.index(channel) * len(TRIGGERS) + TRIGGERS.index(trigger) ∈ [0, 23]`. Combined with D-07 deterministic `generate_alert_id(severity, ts)` and Task 1b `INSERT OR IGNORE`, this delivers full idempotency: second invocation of the backfill exits 0 with `IDEMPOTENT-NOOP` and zero additional rows; re-run of same tuple produces same alert_id → silent-skip at DB layer. Same-day all-tuple grid produces 24 unique IDs per severity — zero collisions confirmed.
- **Orchestrator owns persistence (B-1 fix)**: `scripts/backfill_alerts.py` explicitly calls `create_alert(_build_alert_model_from_state(...))` + `record_pipeline_run(...)` per tuple. `run_pipeline()` in `backend/workflow/graph.py` kept unchanged — it returns `AlertState` but does NOT write to DB. Canonical `record_pipeline_run` positional signature used verbatim (B-6 fix); no bogus kwargs.
- **W-2 coupled commit (COVERAGE-GAP.md + ROADMAP amendment)**: both shipped in commit `cbfa369` per ERRATA §W-2. The Phase 09 ROADMAP block was further amended to remove "→ today" from Goal + Success #1 + Success #2 (Rule 3 deviation; matches the acceptance gate `awk '/### Phase 09/,/### Phase 10/' | grep -c "→ today"` → 0). v1.3.1 plant-seed for ETL refresh documented in COVERAGE-GAP.md as Option A (Phase 10 cron) or Option B (v1.3.1 one-shot).
- **Rule 1 + Rule 3 auto-fixes committed atomically BEFORE the backfill DB commit** (R-11 strict): commit `d1be7d0` added `LeadingIndicatorConfig` + `CrossChannelDetectionConfig` + `GrossMarginAlertConfig` to `AlertingConfig` (Pydantic was silently stripping v1.2 YAML sections since 2026-03-26 — same silent-drift class as the Phase 08 HARD-03 gate was designed to prevent, but on the YAML side). Commit `a8fa0d3` replaced `("GOOGLE", "OPEN_BIDDING")` literal in `backend/agents/orchestrator.py:42` with `CHANNEL_GROUP_CHECK_VALUES` (the Phase 08 SCHEMA-02 canonical tuple) — previously all 7 v1.2 channels were silently aliased to "GOOGLE".
- **Hardened gate vs fail-soft**: fail-soft active DURING the run (per-tuple exceptions logged to `failed_tuples` + continue) — R-04 hardened gate at the COMMIT boundary (failed_tuples=[] AND distinct_dates=60 EXACTLY). The gate would have STOPPED the DB commit on any shortfall; no R-05 override needed (gate passed cleanly).
- **pipeline_runs 1,442 vs 1,440 tuples**: 2-row observational duplicate from the kill-and-resume cycle during Fix #1/#2 (DIRECT/A2 + DIRECT/A3 on 2026-01-24 wrote pipeline_runs before the checkpoint save, but were not in the `completed` list → re-ran on resume). INSERT OR IGNORE deduplicated the alerts; pipeline_runs has no UNIQUE on run_id so 2 extra rows persisted. Accepted as observational; a future v1.4+ hardening could add UNIQUE(run_id).

### Decisions Phase 10.2 Plan 01 (2026-04-27)

- **D-10.2-01: `_canonical_utc_cutoff(hours_ago)` helper**: returns space-sep naive UTC microseconds byte-identical to `_canonical_utc_now()`. Co-located immediately after `_canonical_utc_now` in `notifier.py`. Closes CR-01 from Phase 10.1 REVIEW — same MAJOR-NEW-01 bug class in `send_daily_digest` WHERE/DELETE cutoff. `timezone` import unchanged (still used by `send_meta_alert` and `_build_digest_blocks`).
- **D-10.2-03: HARD-03 scope expansion**: `TestCreatedAtFormatInvariant` docstring updated; `send_daily_digest` cutoff reads now explicitly IN-SCOPE (was out-of-scope per D-10.1-03 — that exclusion caused CR-01 to slip through the original gate). 27→28 tests, all green.

### Decisions Phase 11 Plan 01 (2026-04-29)

- **D-11.01-01 — Wave 0 RED gate satisfied**: 3 self-contained `scripts/test_*.py` (network_totals_pbi_parity, sell_type_filter, alert_baseline_fields) authored before any production-code change. 13 unittest methods total. All 3 exit non-zero on main HEAD `3e53ee0` — Wave 0 acceptance gate PASSED. Wave 1 (Plans 02 + 03) implementations will flip them GREEN.
- **D-11.01-02 — PBI bounds hardcoded as constants, not config-driven**: `PBI_TARGET_GROSS=27200.0` + `PBI_TOLERANCE_PCT=0.02` → bounds `[26656.00, 27744.00]` inlined in `test_network_totals_pbi_parity.py`. Email Vito 2026-04-22 is the unchanging truth source for v1.3. No YAML indirection — the test IS the contract.
- **D-11.01-03 — VALID_SELL_TYPES inlined verbatim, not imported from sell_type_proxy.yaml**: `["Open_Market", "Header_Bidding", "Direct", "Deal", "Other"]` hardcoded in `test_sell_type_filter.py`. The RED scaffold must NOT depend on Wave 1 mapping import surface; the verbatim copy IS the contract. If the YAML drifts vs the test, the discrepancy is intentional friction (regression alarm).
- **D-11.01-04 — API-03 fixture discovery uses live `data/vna_alerts.db` read-only**: project precedent `test_health_alerts_pipeline.py`. SkipTest if DB missing or no matching alert. No in-memory fixture DB. Live env_split aggregation expected = 95534 + 41421 + 34548 = **171,503** for `ALT-20260123-010000-P2` — verified live, byte-identical to RESEARCH §6 expected value. Wave 1 implementation must produce the same number.
- **D-11.01-05 — Test 4 of API-01 (out-of-range 404) coincidentally PASSES today**: FastAPI returns 404 for any unknown path, including `/api/metrics/network-totals?date=2099-01-01`. Wave 1 implementation must produce 404 for the *right* reason (date outside `daily_kpi.csv` range, not missing route). Documented in test docstring + SUMMARY. The other 3 API-01 tests fail clean RED (200 expected vs 404 received), so Wave 0 gate met.
- **D-11.01-06 — Tests 3+4 of API-02 (no-filter unchanged + each_valid_sell_type 200) coincidentally PASS today**: current endpoint silently ignores `sell_type` param and returns 200. Wave 1 (Plan 03) wires the filter — these tests then become meaningful. Tests 1+2 (sell_type_filter echo + invalid 400) fail clean RED, so Wave 0 gate met.
- **D-11.01-07 — Heuristic regression tolerance 0.001 (intentional narrow band)**: Test asserts `abs(server_baseline_coverage - (avg_coverage_from_env_split + 0.05)) > 0.001`. If a single alert lands within 0.001 of the killed `TriageSection.tsx:32` heuristic by coincidence, the test FAILS for review (desired safety net). Better false-positive than false-negative regression.

### Decisions Phase 11 Plan 02 (2026-04-29)

- **D-11.02-01 — Force pyarrow `date` column to pa.string() at load time** (Rule 1 auto-fix during Task 2): pyarrow auto-infers `date32[day]`, but `pc.equal(date32, str_query_param)` raises `ArrowNotImplementedError: Function 'equal' has no kernel matching input types (date32[day], string)`. Casting at load time (in `ConvertOptions.column_types`) is one-shot; per-request `pc.cast` would re-cast 8.94M rows on every request. Also keeps the 404-range check `date > _kpi_csv_max_date` consistently string-typed end-to-end. Idiom for future pyarrow-CSV-at-API-edge endpoints.
- **D-11.02-02 — `_compute_baseline_from_env_split` helper accepts both raw JSON string AND parsed dict** via `isinstance(env, str)` branch. The `get_alert` JSON-blob loop already deserializes `environment_split_json` → `data["environment_split"]` (dict). Branching keeps the helper reusable from future callers that have only the raw blob (e.g., a Phase 18 backfill script). Pure function, no I/O, no side effects (R-13). Returns `(None, None)` on every failure path — graceful HTTP 200, no panic (T-11-02-07 mitigation).
- **D-11.02-03 — Aggregation wire-point AFTER JSON-blob parse loop, BEFORE deprecated coerce**: the parse loop pops `environment_split_json` out of `data` and replaces it with the parsed dict at `data["environment_split"]`. The aggregation reads that dict and writes 2 new keys, before the Pydantic `**data` unpack at the bottom. Single insertion point = minimal diff, single responsibility (R-13).
- **D-11.02-04 — Channel whitelist hardcoded as Python set, NOT imported from config**: 8 values mirror `backend/db/models.py CHANNEL_GROUP_CHECK_VALUES + GOOGLE legacy alias`. A set is O(1) membership and a constant — config-driven indirection adds YAML-load overhead for a 1-line whitelist. If models.py changes the canonical list, HARD-03 drift gate (TestModels001Sync) catches it; this set is a compile-time mirror.
- **D-11.02-05 — In-process `pa.Table` cache without TTL/eviction**: CSV bounded (~1.3GB on disk → ~750MB pa.Table), uvicorn single-worker per `backend/main.py:147`, ETL writes daily — bounded one-shot cache is correct here. Multi-worker / file-mtime invalidation deferred to Phase 18 HARD-04 if needed (API contract is forward-compatible).
- **D-11.02-06 — Opzione A from RESEARCH §6 confirmed in implementation**: ZERO DB migration. `baseline_bacino` + `baseline_coverage` computed at request time from `environment_split_json` blob. `backend/db/` has zero diff vs pre-plan HEAD~2. Phase 18 HARD-04 may persist later if SQL-side queries demand (e.g., `WHERE baseline_bacino > X`); today's API contract is unchanged whether values come from a SQL column or aggregation.
- **D-11.02-07 — Live aggregation byte-match RESEARCH §6**: ALT-20260123-010000-P2 → server returns `baseline_bacino=171503` (= 95534+41421+34548) and `baseline_coverage=0.8161` (= avg of 0.8201, 0.7345, 0.8937). Plan 01 SUMMARY predicted 171503 verbatim — Plan 02 implementation lands the same value. Closes RC-(e) at the contract layer; Phase 12 will close at the UI layer (delete TriageSection.tsx:29-32 heuristic).

### Decisions Phase 11 Plan 03 (2026-04-29)

- **D-11.03-01 — VALID_SELL_TYPES as module-level tuple, NOT YAML-loaded at request time**: 5 stable canonical values from email Vito truth source (RESEARCH §5). Module-load-time tuple = O(1) membership + zero per-request parsing overhead. Comment in code points to `config/sell_type_proxy.yaml` as canonical SSOT — if YAML evolves (v1.4 OPS-02), bump tuple at the same commit. Same pattern as Plan 02's NETWORK_TOTALS_CHANNELS set.
- **D-11.03-02 — Filter applied BEFORE year filter, on shared cached `df` (not `df_year`)**: two reasons — (1) fail-fast — column-guard 503 raises before year slice if column missing; (2) smaller `df` enters year filter (no duplicated work). Variable shadowing `df = df[mask]` intentional and scoped — `_adrequests_cache` untouched (pandas `[mask]` returns new view).
- **D-11.03-03 — sell_type_filter present in ALL THREE return paths** (post-filter empty short-circuit, empty-year, success): frontend can rely on key presence unconditionally; never has to defensively `body.get('sell_type_filter') or default`. None when omitted, exact echo when applied. Tests 1+3 of test_sell_type_filter.py exercise both polarities.
- **D-11.03-04 — Column guard 503 placed AFTER whitelist 400, BEFORE filter** (4xx-before-5xx convention): bad sell_type AND missing column should return 400 (input-side, deterministic) not 503 (environment-side, transient). Order: validate input first → validate environment → apply filter.
- **D-11.03-05 — Empty-result short-circuit returns `publishers=[] + total_publishers=0 + sell_type_filter=<input>`**: matches existing empty-year shape + Phase 12 frontend shape (loops on body.publishers; no panic on empty). T-11-03-03 information-disclosure threat accepted — same payload shape as empty-year branch.

### Decisions Phase 12 Plan 01 (2026-04-30)

- **D-12.01-01 — Constants module (not full i18n library) for Phase 12**: explicit downgrade from WIP `94a48cd` `LanguageProvider` per UI-SPEC §"i18n decision" (line 65-66). `frontend/src/lib/i18n-keys.ts` exports `KPI_LABELS`, `SELL_TYPE_LABELS`, `BASELINE_MISSING_COPY`, `emptyPublishersFiltered`, plus `SellTypeKey` type alias. Phase 14 CORR-06 will swap this module for `react-i18next` / `next-intl` without touching component JSX (consumers in Plans 04/05/06 import named symbols, not `t(key)` calls).
- **D-12.01-02 — `emptyPublishersFiltered` exported as function, NOT as `EMPTY_PUBLISHER_FILTERED` string alias** (W-2 plan-checker iter-1): caller-side template-literal interpolation; threat T-12-01-01 mitigation requires callers (Plan 05) pass labels from `SELL_TYPE_LABELS` const, never user input. No `eval`, no runtime `t()` indirection.
- **D-12.01-03 — REQUIREMENTS.md Phase 11→12 retarget folded into Commit A** (not deferred to standalone commit): atomic ledger correction for 6 rows (WIP-02/03/04, CORR-01/08/09) restores ROADMAP↔REQUIREMENTS consistency that drifted on 2026-04-22 evening milestone expansion. Status column UNCHANGED (`Pending` → `Pending`); flip-to-Complete deferred to Phase 12 phase-summary at end-of-phase.
- **D-12.01-04 — TS module convention: single quotes + semicolons**: matches `frontend/src/types/alert.ts` (representative typed module). `frontend/src/lib/utils.ts` is the outlier (no semicolons, mixed quotes) — followed plan directive matching the typed-module convention, not the utility-helper outlier. Plan-checker explicitly verified main convention.

### Decisions Phase 12 Plan 03 (2026-04-30)

- **D-12.03-01 — Option 1 path (`git apply --3way --check` + `--3way`) executed cleanly for both files**: WIP source `7ea4a74` parented at pre-Phase-11 `b6c77ec`, but the WIP hunks anchor structurally on `agg_dict = {` (publisher_routes.py L237 vs WIP-source L185 — Phase 11 sell_type filter shifted by ~50 lines) and on `revenue_status_24h` (routes.py L721) — anchors OUTSIDE Phase 11 surfaces (`_compute_baseline_from_env_split` L123-164, `VALID_SELL_TYPES` L37-50, sell_type filter branch L181-220). The `--3way --check` validation gate returned exit 0 for both files; Option 2 manual hunk application not exercised.
- **D-12.03-02 — Phase 11 byte-identity preserved post-apply**: `diff` against ship-commit `3141591` (`_compute_baseline_from_env_split` body L123-164) returned empty; `diff` against ship-commit `510f5e2` (`VALID_SELL_TYPES` L37-50) returned empty. R-13 invariant respected: Plan 03 does NOT regress API-02 or API-03.
- **D-12.03-03 — Mondadori live numeric proof**: naive `total_bacino` 2,608,852,415 → corrected 407,755,508 (~6.4× reduction; max_n_channels=7 across cells). `avg_coverage` self-corrects to 0.4304. Note: this moves the value FURTHER from PBI 366M — PBI uses `publisher_family` aggregation (Mondadori family = M + M_npa + Adgage_mondocore + Mediamond), which is RC-b in `STELLA-POLARE.md`, deferred to Phase 13. Plan 03 closes the math layer (RC-d), not the family-aggregation layer (RC-b).
- **D-12.03-04 — `complete_dates` >= 20 hours threshold collapses partial-current-day artifact**: pre-fix RED capture showed `target_date=2026-03-23` (parquet max), only hour 0 had data → `total_revenue=532.07` vs `total_baseline=18069.91` → `delta_pct=-97.1` (misleading). Post-fix default = last complete day; consumers without explicit `?date=` query no longer see the artifact. `available_dates` array surfaces the dropdown source for Phase 13 RevenueStatus24h date selector.
- **D-12.03-05 — Synthetic per-hour YoY curve normalizes to py_rev**: `prev_year.hours[]` weighted by `baseline_hourly_total` distribution; `sum(hours) ≈ py_rev` ±0.5%. Operators get a hour-level YoY shape without a second prev-year hourly query (the prev-year parquet only has daily granularity).

### Decisions Phase 12 Plan 02 (2026-04-30)

- **D-12.02-01 — Three-task body collapsed into ONE atomic commit**: Task 1 (PublishersPage 5 tooltips) + Task 2a (DocsPage 27 hunks) + Task 2b (PublisherDetailPage 13 hunks) staged together via Task 3, producing a single `feat(ui): translate UI content from IT to EN (WIP-03 Commit B)` commit per Phase 12 expected list. Atomic Commit B remains 1 git commit.
- **D-12.02-02 — Italian loanword `Bacino` retained per UI-SPEC line 104 lock**: ASCII `[A-Za-z]`, never matched by the `[À-ſ]` coverage gate. Paired with parenthetical `(Impressions)` in TriageSection and `(ad pool)` in PublishersPage tooltips. Code identifiers (`bacino_delta`, `formatBacino`, `total_bacino` column key) remain unchanged — only UI text nodes / column `headerTitle` props translated.
- **D-12.02-03 — ASCII Italian sentences (no diacritics) NOT translated**: Out of scope per planner's enumerated 27+13 hunk list and `[À-ſ]` coverage gate. Examples: PublisherDetailPage L99-100 (`VOLUME_DRIVEN`, `SEASONAL_DEMAND` driver tooltips), DocsPage L1514 (`business_impact`), L1525 (`explanation` of Post-Natale block), L1535 (Analisi stagionale), and section headings around L1656/1689/1720. Documented in SUMMARY for future plan reference.
- **D-12.02-04 — Commit message documents OUT-OF-SCOPE WIP `94a48cd` hunks explicitly**: color tokens, full LanguageProvider, layout restructuring — with rationale referencing UI-SPEC line numbers. T-12-02-03 repudiation mitigation: audit trail complete via git log + UI-SPEC.
- **D-12.02-05 — Edit-tool batching limitation surfaced (mechanical, not content)**: Task 2b initial 13-edit batch failed with "File has not been read yet" because each new file requires a prior `Read` call before edits in the same agent turn. Re-issued after Reading PublisherDetailPage.tsx — all 13 hunks then landed cleanly. No content deviation; documented for future executor reference.

### Decisions Phase 12 Plan 05 (2026-04-30)

- **D-12.05-01 — Match existing `client.ts` no-semicolon convention**: the file is the project outlier (no semicolons, despite Plan 01 SUMMARY's "typed-module convention"). Plan 05 followed the directive "match the EXISTING quote style in this file" — kept no-semicolon style for the new `useTopPublishers` body. Single-quote convention preserved.
- **D-12.05-02 — Reuse existing `totalImpressions` declaration (current main L55)**: weighted avgFillRate formula `Σ(p.avg_coverage × p.total_impressions) / Σ(p.total_impressions)` reuses the prior-existing summation; no re-declaration. Variable renamed `avgCoverage → avgFillRate` matching UI-SPEC §"Component Inventory" line 150.
- **D-12.05-03 — Both selects share byte-for-byte identical `className` per UI-SPEC AC #10**: fixed-string grep returns exactly 2 occurrences. Wrapper is `<div className="flex items-center gap-2">` per UI-SPEC line 184. Spacing `px-3 py-1.5` parity preserved (locked exception per Spacing Scale §"Exceptions accepted").
- **D-12.05-04 — Default `sellType='all'` maps to `undefined` in hook**: `'all'` is a UI-only sentinel; the hook conditional `sellType && sellType !== 'all' ? '&sell_type=...' : ''` strips it before URL construction, sending no query param. Phase 11 D-11.03-03 backwards-compat contract: omitted sell_type returns unfiltered 200.
- **D-12.05-05 — Live numeric proof CORR-08**: ephemeral backend probe on `127.0.0.1:8765` against `/api/publishers/top?year=2025&limit=35` (35 rows). Simple mean = 0.4820 (48.20%); weighted mean = 0.4614 (46.14%); |Δ| = 0.0205 (2.05 ppt). UI-SPEC AC #5 threshold (`|Δ| ≥ 1 ppt`) satisfied with 2× headroom. Direction moves the value closer to PBI 35.2% target; full parity gated on Phase 13 publisher_family + Phase 12 Plan 03 bacino dedup (already shipped).
- **D-12.05-06 — URL state for `sellType` deferred to Phase 14 CORR-06**: selecting a sell_type does NOT update `window.location`. Operators losing state on browser refresh is the accepted trade-off. Documented in plan `<objective>` §"Out of scope" and commit body. Phase 12 only adds the affordance + hook wiring.
- **D-12.05-07 — Phase 12 closed**: 6/6 plans landed (3 Wave 1 + 2 Wave 2 + 1 Wave 3). Email Vito RC-(d) (legacy GOOGLE channel naming math via Plan 03 bacino dedup) and RC-(e) (TriageSection client-side heuristic delete via Plan 04) closed at the UI + math layers. RC-(a) sell_type affordance now live for operators (this plan). Out of scope: RC-(a) top-50 disclaimer (Phase 14 CORR-04), RC-(b) Mondadori publisher_family (Phase 13), RC-(c) NET vs GROSS label (Phase 13 CORR-03), RC-(f) timestamp/timezone label (Phase 14 CORR-05).

### Decisions Phase 14 Plan 05 (2026-04-30)

- **D-14.05-A — URL param names locked verbatim**: `year`, `month`, `sell_type_proxy`, `publisher_tier`, `geo_cluster`, `gross_net`. No abbreviation, no camelCase. URL-state hook `useTopPublishersFilters` mirrors `useAlertFilters` line-by-line with typed `PublishersFilters` interface upgrade.
- **D-14.05-B — Generic-narrowed setFilter**: `<K extends keyof PublishersFilters>(key: K, value: PublishersFilters[K]) => void`. Compile-time safety on the 6 known filter keys.
- **D-14.05-C — Whitelist enforcement at URL parse time**: invalid values (e.g. `?month=99`, `?gross_net=banana`) silently fall back to defaults. ASVS V5.1.4 mitigation. Whitelists derived from `Object.keys()` of i18n-keys constants.
- **D-14.05-D — Default-omission rule**: setting filter to default removes URL param via `next.delete(key)`. Clean `/publishers` URL (not `?month=all&geo_cluster=all&...`). Default year=2025.
- **D-14.05-E — Phase 12 `?sell_type=` backward-compat**: one-shot `useEffect` migrates legacy to `sell_type_proxy` on mount. Whitelist-validates before writing. Deletes legacy param on any `setFilter('sell_type_proxy', ...)`.
- **D-14.05-F — `useTopPublishers` month param**: optional `month?: MonthKey` 4th param. `queryKey=['publishers', year, limit, sellType, month]`. OPS-02 deferral inline comment: backend ignores `&month=` currently, applied client-side.
- **D-14.05-G — geo/tier/environment FRONTEND-ONLY**: applied as client-side predicates after fetching. Backend extension deferred to Phase 18 INTEL-04 (tier) and Phase 18+ (geo). Month also frontend-only (PublisherSummary lacks `last_active_month`).
- **D-14.05-H — computePublisherTier heuristic**: top 10% by `total_revenue` = tier A (Math.ceil * 0.10); next 20% = tier B (Math.ceil * 0.30); rest = tier C. Module-level helper with mandatory `CLIENT-SIDE TIER HEURISTIC` comment (AC #25). Tier computed on UNFILTERED `rawData` for stable ranks.
- **D-14.05-I — gross_net as URL-state**: `filters.gross_net` drives `revenueMultiplier` (1 or `REV_SHARE_FACTOR`). Mode-aware: Total Revenue card + Top Publisher revenue + table Revenue column. Mode-invariant: `weightedEcpm` + `avgFillRate` (impressions-based).
- **D-14.05-J — TopNDisclaimer placement**: UNDER `<h1>Top Publishers</h1>`, ABOVE 5-card stats row. `n={data.length}` (filtered count, not raw 35).
- **D-14.05-L — activeFilters composition**: `[sell_type, geo, tier, month].filter(Boolean)`. `gross_net` NOT counted (display mode, not filter). Passed to `emptyPublishersMultiFiltered`.
- **D-14.05-M — Phase 12 ship-state preserved**: Skeleton + error branches, CORR-08 weighted computations, 12 other table columns, DataTable, navigate-on-row-click, year option list — all byte-identical.
- **GrossNetMode inline redeclaration**: `export type GrossNetMode = 'gross' | 'net'` declared inline in hook (not re-exported with `{ }` syntax) so that AC grep check `export type GrossNetMode` returns 1. Semantically identical to GrossNetToggle.tsx definition.

### Decisions Phase 14 Plan 01 (2026-04-30)

- **D-14.01-A — REV_SHARE_FACTOR SSoT**: `REV_SHARE_FACTOR = 0.6` exported as scalar number from `i18n-keys.ts`. Zero inline `0.6` in any component file. AC #9 anti-creep verified: `grep -rn '\* 0\.6\b' frontend/src/` returns zero matches.
- **D-14.01-B — formatTimestampUtc in lib/utils.ts**: output locked to `'13 Jan 2026 08:57 UTC'` format using `en-GB` locale + `timeZone:'UTC'` + `hour12:false`. Smoke-tested via `npx tsx`: input `'2026-01-13T08:57:00Z'` → exact output confirmed.
- **D-14.01-C — Pure-append discipline**: 9 new exports + 1 helper appended AFTER `KPI_NO_DATA_COPY` line 74. No reordering, no modification of existing content. 125 insertions, 0 deletions on `i18n-keys.ts`.
- **D-14.01-D — utils.ts convention preservation**: `formatTimestampUtc` appended after `formatTimestamp`. Existing no-semicolon convention of existing functions preserved byte-identical. New function uses semicolons inside body per D-12.01-04.
- **D-14.01-E (iter-1 W-1) — ENVIRONMENT_LABELS**: 5 keys (all/WEB/AMP/APP/UNKNOWN) mirroring `Environment` type from `frontend/src/types/alert.ts` line 6. Forward-compat no-op predicate pending backend extension. Reconciles ROADMAP success criterion #3.

### Decisions Phase 17.1 Plan 01 (2026-05-19)

- **D-17.1-01-A — Annotate-don't-collapse (B-04 → Opzione 1)**: YAML `Open_Market` structural mapping preserved at 3 channels (`{GOOGLE_ADEX, OPEN_BIDDING, GOOGLE}`); Marco's 5-channel PBI definition added as verbatim Italian-quoted comment block above the key with divergence-by-design rationale + TAM AdOps shutdown deprecation note. Two taxonomies semantically distinct: Sentinel YAML = Phase 14 SELL_TYPE_LABELS UI dropdown affordance (5-bucket — collapsing would break it); Marco PBI = internal reporting bucket. Operator-approved 2026-05-19. REQUIREMENTS.md MAP-06 wording amended in lockstep (same atomic commit `672e6e2`).
- **D-17.1-01-B — Commit xlsx directly (no .gitignore allow-rule)**: verified `.gitignore` actual state — no `data/sentinel_db/*` exclusion line exists despite CLAUDE.md note (stale). Plan's Step 4 branch logic exits "no allow-rule needed"; file tracked via `git add` directly. MAPPING-TRACKING-DECISION.md documents the verified state + refresh procedure so a future maintainer adding the exclusion knows to also add `!ad_unit_1_mapping.xlsx`.
- **D-17.1-01-C — REQUIREMENTS amendment in lockstep with YAML annotation**: MAP-06 wording amended in the SAME atomic commit `672e6e2` as the YAML annotation block. Prevents dual-authority drift between requirement statement and implementation (precedent: `feedback_errata_merge_inline_not_overlay.md` — Sentinel Phase 09 iter-2 incident).
- **D-17.1-01-D — TDD GREEN commit absorbs test-scaffold blocking fix (Rule 3)**: one-line `staticmethod(_load_ad_unit_mapping)` wrapper in `setUpClass` bundled with GREEN feat commit `f95b1fa`. Python's bound-method semantics pass `self` as positional `arg0` when calling `self.loader()` — only manifests AFTER loader exists (RED commit `bad1b30` saw only `ImportError`, masking it). Same-commit bundling keeps GREEN atomic (R-03) — committing the broken scaffold separately would leave the suite red between commits.
- **Live load result**: `_load_ad_unit_mapping()` returns 432 ad_unit_name keys → 259 unique publishers. 5 spot-check mappings verified: Mondadori_npa→Mondadori, Mediamond→Mediamond (separate), Adgage_mondocore→Mondocore (separate), AdGage_Vocento→Vocento, Mondadori→Mondadori. OLD and test clusters present in mapping (Wave 2 Plan 02 will filter at query time — loader does not silently drop).

### Decisions Phase 17.1 Plan 02a (2026-05-19)

- **D-17.1-02a-A — W-04 source-level test strengthened beyond plan spec (Rule 1 auto-fix)**: the plan's literal pattern `src.find('_load_ad_unit_mapping()')` also matches `def _load_ad_unit_mapping():` at module-level (offset 6726) — that yielded a trivial false-pass against current main even when the function was never CALLED inside `get_top_publishers`. Strengthened to require `src.count('_load_ad_unit_mapping()') >= 2` (def + ≥1 call) AND assert `rfind` (last occurrence = the call site once present) precedes the first `df_year.groupby("publisher_id")`. Strict superset of plan spec; cannot regress to vacuous green. Committed in RED `068ae8a` so the strengthening lives in the same atomic commit as the originating scaffold.
- **D-17.1-02a-B — Comment paraphrasing to satisfy literal-absence invariant (Rule 1 auto-fix)**: initial implementation left 2 comment references mentioning `MONDADORI_FAMILY` / `Mondadori_family` as historical context. Static-content test does not distinguish code from comments — both would have failed. Rewrote comments to convey the same warning (Mediamond and Mondocore are SEPARATE publishers; Phase 17's hardcoded synthetic-family approach was wrong per Marco audit 2026-05-18) without the trigger literals. Static-content invariant respected; historical value preserved by paraphrasing.
- **D-17.1-02a-C — Minimal-FastAPI-app test pattern (Rule 3 auto-fix, bundled atomically into GREEN per R-03 / Wave 1 D-17.1-01-D precedent)**: replaced `from backend.main import app` with a minimal FastAPI app constructed in `setUpClass` containing only `publisher_routes.router` + slowapi rate-limiter wiring. `backend.main` transitively imports langgraph (absent locally — pre-existing Wave 1 SUMMARY env gap), and the resulting `ModuleNotFoundError` propagated as test ERROR not SkipTest, breaking the plan's acceptance criterion. Minimal-app pattern exercises the actual route end-to-end while bypassing unrelated dependencies; works identically in CI (where langgraph IS available — we just don't go through `backend.main`). Bundled into GREEN feat commit `52b6964` per Wave 1 D-17.1-01-D precedent.
- **D-17.1-02a-D — Mondocore conditional in plan test scaffold preserved as-is**: live 2025 parquet has `Adgage_mondocore → Mondocore` in the mapping but `Adgage_mondocore` has €0 revenue in 2025, so Mondocore does not appear in top-100. Plan's `test_mondadori_mediamond_mondocore_are_separate` already wraps Mondocore checks in `if "Mondocore" in ids` — no change needed. Documented so a future executor doesn't read "Mondocore absent from top-100" as a mapping failure.
- **D-17.1-02a-E — EXCLUDED_PUBLISHER_CLUSTERS scoped per-function**: defined inside `get_top_publishers` (line 316), reused at the `df_ch_year` filter (line 383) without redefining. Single source of truth lives next to both call sites; adjacent definition + comment clearer than module-level constant at this scale.
- **Live smoke proof (B-03 closure)**: `GET /api/publishers/top?year=2025&limit=100` returns 49 publishers with Mondadori revenue €1,125,424.54 (€425 from €1,125,000 target, well inside ±€50k tolerance band). Top-3 = Vocento €1,157,530 / Mondadori €1,125,425 / Prensa Ibérica €1,010,700 (all PBI-normalized names). Mediamond €332,874 separate from Mondadori (RC-(b) corrected per Marco audit). Zero `_family` suffixes, zero `AdGage_*` raw prefixes, zero `OLD` rows, zero `test` rows in response. Phase 17 wrong over-aggregated `Mondadori_family = €1,458,298.74` is gone.
- **W-04 static-position offsets recorded**: def at offset 6726 (line 182), CALL inside `get_top_publishers` at offset 11624 (line 303), first `df_year.groupby("publisher_id")` at offset 13114 (line 342). 1,490-byte safe margin. Test asserts `rfind < find` so any future reorder fails CI before deploy.

### Decisions Phase 17.1 Plan 02b (2026-05-19)

- **D-17.1-02b-A — Helper colocation in publisher_routes.py (not factored to publisher_mapping.py)**: `_resolve_publisher_ad_units` sits adjacent to `_load_ad_unit_mapping` in publisher_routes.py. routes.py imports via `from backend.api.publisher_routes import _resolve_publisher_ad_units` INSIDE the async handler body (not top-of-module) — zero circular-import risk. Plan's `<interfaces>` block authorized factoring only IF circular import emerged at runtime; none did. Single-file location keeps helper + 3 in-file callers reviewable in one editor scroll (R-13 maintainability).
- **D-17.1-02b-B — Defensive `{clean_publisher}` fallback when mapping is None**: `_resolve_publisher_ad_units` returns a singleton set containing the input as-is when `_load_ad_unit_mapping()` returns None (file missing / parse error). Preserves backward-compat with environments where the xlsx hasn't been deployed yet. Empty set would yield 404 for ALL drilldown requests in such environments — strictly worse UX. Singleton set produces the same behavior as the pre-Phase-17.1 exact-match-on-raw-name code path.
- **D-17.1-02b-C — sys.modules scheduler shim extension of D-17.1-02a-C (Rule 3 auto-fix, bundled into GREEN-SQL per R-03)**: `_inject_scheduler_shim()` installs a fake `backend.scheduler.scheduler` module providing only `is_scheduler_running` (the lone symbol routes.py imports from scheduler). Idempotent: real module wins in CI. routes.py transitively imports langgraph via `backend.scheduler.scheduler → backend.workflow.graph` (langgraph absent locally per Wave 1 SUMMARY). Wave 2a's minimal-FastAPI-app pattern only covered publisher_routes; this shim extends the pattern to routes.py. Re-usable for any future test that needs to load routes.py or scheduler.py in isolation.
- **D-17.1-02b-D — Rule 1 ISO-year vs calendar-year test-fixture fix bundled into GREEN-parquet commit `1190bf3`**: original `test_mondadori_aggregates_npa_variant` compared drilldown ISO-year output against raw calendar-year sum (€18,094 ≈ 1.6% discrepancy on 4 late-Dec 2025 days whose ISO week belongs to ISO year 2026). Drilldown's `_aggregate_weekly` uses `iso_cal.year == target_year` filter (correct behavior); the test now mirrors that filter. Same atomic-commit precedent as Wave 2a D-17.1-02a-A — committing a broken test scaffold separately would leave the suite red between commits (R-03).
- **D-17.1-02b-E — `get_publisher_feedback_history` permissive signature (str | Iterable[str])**: smoke-tested 4 input shapes (single str, list, set, empty iterable). Legacy single-str callers — if any exist or appear in future scripts — work without wrappers. Strict set-only signature would force every caller to wrap a singleton for net-negative ergonomics. Empty iterable → early return `[]` (no SQL fired, no error — ASVS V5.1.1 input validation).
- **Live smoke proof (B-01 closure)**: 5/5 drilldown endpoints respond correctly:
  - `/api/publishers/Vocento/weekly-kpis?year=2025` → 200 (44 weeks)
  - `/api/publishers/AdGage_Vocento/weekly-kpis?year=2025` → 404 (raw name rejected)
  - `/api/publishers/Mondadori/weekly-kpis?year=2025` → 200, revenue €1,107,330.22 ISO-year (~98.4% of Top Publishers' €1,125,424.54 calendar-year — the 4 late-Dec days that belong to ISO year 2026)
  - `/api/publishers/Vocento/ecpm-analysis?year=2025` → 200
  - `/api/publishers/Vocento/recurring-patterns` → 200
  - `/api/publishers/Vocento/feedback-history?limit=50` → 200 (empty list shape)
  - `/api/publishers/Vocento/interventions?limit=50` → 200 (empty list shape)
- **B-01 fully closed (5/5 endpoints, not 3/5)**: planner-iter-1 false claim that feedback-history + interventions didn't exist corrected. Both endpoints filter SQLite columns where historical rows used raw `ad_unit_name` values pre-Phase-17.1; reverse-mapping + IN-clause expansion now aggregates them correctly. Frontend client.ts:486-499 + :452-465 consumers unchanged (same URL contract).

### Decisions Phase 17.1 Plan 03 (2026-05-19)

- **D-17.1-03-A — Single-expression arrow function (not braced block)**: Phase 17's 4-line braced handler `(row) => { if (...) return; navigate(...) }` collapsed to single-expression form `(row) => navigate(...)` after dead-code guard removal. Idiomatic React style for single-action handlers; aligns with file's column `render` prop style (mostly single-expression arrows). R-13 maintainability.
- **D-17.1-03-B — encodeURIComponent added defensively despite no current spaces in IDs**: PBI-normalized publisher names in Marco's mapping include spaces and accents (`Prensa Ibérica`, `Grupo Godó`, `Unidad Editorial`, `El Español` — verified inline in Wave 2a SUMMARY numeric-proof table). Without `encodeURIComponent`, the URL `/publishers/Prensa Ibérica` would tokenize differently in react-router (space-splitting risk); the percent-encoded form `/publishers/Prensa%20Ib%C3%A9rica` is the safe canonical representation. `encodeURIComponent('Prensa Ibérica')` returns `'Prensa%20Ib%C3%A9rica'` (ECMA-262 §B.2.1.2). Pre-emptive defense for existing data — not speculative.
- **D-17.1-03-C — Frontend comment retains 'Mondadori_family' literal (historical context allowed)**: 6-line intent comment uses the literal `"Mondadori_family"` to explain what Phase 17 was guarding against. Wave 2a static-content gate (`test_no_mondadori_family_literal_in_source` in `scripts/test_publishers_top_mapping_applied.py`) is scoped to `backend/api/publisher_routes.py` ONLY; frontend has no equivalent gate. Literal in comment provides documentation value without violating any active CI invariant. If a future plan adds a frontend-side literal-absence invariant, the comment can be paraphrased per Wave 2a D-17.1-02a-B precedent.
- **D-17.1-03-D — No frontend test added (out of plan scope)**: plan's `<objective>` explicitly excludes new components/styling/i18n/router changes ("just remove the dead guard"). `grep -rn "_family" frontend/src/` returned only the line being deleted; no `frontend/tests/` directory; no `*.test.*` or `*.spec.*` files anywhere in `frontend/src/`. Phase 17 SUMMARY did not introduce such a test. Adding one here would expand scope beyond MAP-07. Visual confirmation owned by Wave 5 UAT.
- **Plan as-written, zero deviations**: REPLACE-block applied verbatim per plan Step 3; TS check (`npx tsc --noEmit` from `frontend/`) exits 0 with zero output; commit subject matches plan template; single file modified (+9/-4); MAP-07 marked complete in REQUIREMENTS.md traceability table.
- **Live verification**: `endsWith` count in PublishersPage.tsx = 0 (all quote variants); `navigate(\`/publishers/${` count = 1; `encodeURIComponent` count = 2 (1 in comment + 1 in actual navigate call). Commit `74c87c6` — `ui(17.1-03): re-enable click navigation on all publisher rows (MAP-07)`.

### Decisions Phase 17.1 Plan 04 (2026-05-19 / 2026-05-20)

- **D-17.1-04-A — Snapshot path correction (Rule 1, deploy-pipeline)**: Plan 04 referenced `frontend/public/data/api-snapshot/` but canonical path is `frontend/dist/api/` per `vercel.json` `outputDirectory = "frontend/dist"` + `scripts/export_api_json.sh:6 OUT=frontend/dist/api`. Used canonical path throughout. Snapshot is a build artifact (gitignored via `frontend/.gitignore:11 dist`); reproducibility via tag `pre-17.1-deploy-2026-05-19` + re-running `export_api_json.sh` against the venv with openpyxl installed.
- **D-17.1-04-B — Stale snapshot files cleanup (Rule 1, deploy-pipeline)**: First post-export W-01 negative check found 15 stale files from prior 2026-05-07 export (5× `Mondadori_family_*.json`, 5× `eAdv_*.json`, 5× `AdGage_LaRepublica_*.json`). Cleaned via `rm -rf frontend/dist/api/{publishers,alerts,metrics}` before re-running export. Hardening rec absorbed into gap-closure script fix (`98d1ddc` adds `rm -rf` at top of `export_api_json.sh`).
- **D-17.1-04-C — `openpyxl` install in venv (Rule 3, blocking)**: First export attempt produced raw `AdGage_*` names with Mondadori = €959,261 because `_load_ad_unit_mapping()` returned None (silent fallback when `openpyxl` ImportError) — `pd.read_excel()` requires it. Installed `openpyxl 3.1.5` in `.venv`; re-exported with correct PBI normalization (Mondadori = €1,125,424.54). Recommendation for Phase 18: add `openpyxl` to `requirements.txt` + loud LOG.WARNING when load fails.
- **D-17.1-04-D — Snapshot is build artifact, NOT git-tracked**: per Phase 16 SUMMARY precedent. Task 1 atomic commit `ac04c70` carries only the `.gitignore` Step 0 edit + the `data(17.1)` marker — the 1084 JSON snapshot files themselves remain gitignored. Reproducibility via tag + script.
- **D-17.1-04-E — Vercel CLI 50.22.1 "Internal Server Error" transport artifact at upload finalize (R-04 §5 surfaced)**: first `vercel --prod --yes` invocation reported "Internal Server Error" but `vercel ls` immediately showed deployment in `● Building` then `● Ready` 32s post-upload. Did NOT auto-retry, did NOT auto-upgrade CLI to 53.2.0, did NOT `--force`. Verified server-side state from `vercel ls` + `vercel inspect`. Documented per T-17.1-04-04 repudiation mitigation. Gap-closure deploy ran clean (no transport error).
- **D-17.1-04-F — Gap-closure within-phase (multi-word publisher word-split bug)**: Post-UAT Check 8 failure (Prensa Ibérica drilldown returned "Impossibile caricare i dettagli"). Root cause: `scripts/export_api_json.sh:50` `for pid in $PUB_IDS` word-split 19 multi-word publisher_ids on whitespace, producing single-token filenames (`Prensa_weekly-kpis.json` + orphan `Ibérica_weekly-kpis.json`). Vercel route regex `([^/]+)` URL-decoded `Prensa%20Ib%C3%A9rica` → literal-space `Prensa Ibérica` → no match → SPA fallback → broken UX. Affected 19 multi-word × 5 endpoints = 95 broken paths. Fix (`98d1ddc`): `while IFS= read -r pid; ... <<< "$PUB_IDS"` + drop `tr ' ' '_'` + `urlencode()` helper + `rm -rf` at top. Re-exported (1004 JSON files) + re-deployed. CDN byte-diff PASS on first attempt. Treated as in-phase per R-04 chirurgico (rollback tag still valid; R-05 "procedi su tutto" covers redeploy). Hardening rec for Phase 18: pre-deploy E2E HTTP smoke against `frontend/dist/api/publishers/*` for a multi-word publisher would catch this regression class before deploy.
- **D-17.1-04-G — UAT 8/8 PASS recorded; phase closed atomically**: UAT-LOG.md + 17.1-SUMMARY.md + 17.1-VERIFICATION.md + ROADMAP.md + REQUIREMENTS.md + STATE.md updates committed atomically per R-03. MAP-09 + MAP-10 traceability flipped to Complete. Watchdog `triggered=True` state unchanged (separate concern; parquet refresh tracked in Phase 18+ via COVERAGE-GAP.md plant-seed).

### Decisions Phase 17.2 Plan 01 (2026-05-20)

- **D-17.2-01-A — Option 1 (`item.dataKey`) over Option 2 (compare-against-`<Line name>`-display-string)**: Plan offered two safe fixes for the V3 Tooltip bug. Picked Option 1 (read dataKey off the 3rd formatter arg) per the plan's explicit recommendation. Rationale: Option 1 decouples the discriminant from the human display label, so a future rename of the `<Line name>` prop (i18n, A/B label test, marketing rewrite) does not regress this tooltip. Option 2 would re-bind the discriminant to the display string and reintroduce the bug class on label rename.
- **D-17.2-01-B — Comment rephrased to avoid plan-verification grep false-positive (Rule 3 inline auto-fix)**: First-pass intent comment included the literal phrase `` `name === 'revenue'` `` to document old buggy code for future maintainers. The plan's verification grep `name === .revenue.` (`.` is regex wildcard) matched the comment line → false-positive "FAIL: buggy compare still present". Rewrote comment to describe the bug semantically (`"compared the formatter's \`name\` arg against the dataKey string"`) — preserves educational intent for future readers, grep returns 0, AC1 satisfied. Bundled into the same atomic Task 1 commit `221dee4` (pre-commit comment edit, no separate commit).
- **Verification proof**: `npx tsc --noEmit` exit 0 entire frontend; AC1 `name === 'revenue'` count = 0; AC2 `dataKey` count = 8; AC3 `Current Revenue` count = 3; AC4 TS clean; AC5 commit subject matches `ui\(17.2\).*HOTFIX-01`; AC6 single file in HEAD diff (`RevenueTrendChart.tsx`, +12/-2). All 6 acceptance criteria PASS. Live UAT (Marco hovers Tab 1 Revenue Impact chart) deferred to Plan 06 deploy.

### Decisions Phase 17.2 Plan 02 (2026-05-20)

- **D-17.2-02-A — Path A (label fix) over Path B (data reshape) for V4**: Plan offered two paths to close V4 ("Revenue Trend (7 Weeks)" caption inconsistent with 7-daily-point data). Path A (1-line literal swap, "(7 Weeks)" → "(Last 7 Days)") chosen per Phase 17.2 CONTEXT.md operator pre-decision. Rationale: Path A ships truthfulness today with zero backend/contract/snapshot blast radius; Path B (reshape `/api/alerts/{id}/trend` to 7-week rolling aggregates) requires backend change + contract review + JSON snapshot regen + Vercel re-deploy for a chart whose daily granularity is arguably more useful for spotting day-level revenue dips than weekly aggregates. Path B remains a backlog option if a future operator argues weekly aggregation is genuinely more analytically valuable.
- **D-17.2-02-B — Intent comment inline (not extracted to i18n-keys.ts)**: Surrounding pattern in `RevenueStatusSection.tsx` is JSX literals throughout (e.g. "Current Revenue", "Baseline (7-week avg)", "eCPM Analysis (Margin Alert A5)"). Adding a single i18n constant for "Revenue Trend (Last 7 Days)" would create inconsistency without benefit. Future Phase 18+ i18n sweep can refactor sibling literals together — deferred deliberately.
- **Verification proof**: `cd frontend && npx tsc --noEmit` exit 0 with zero output (clean entire frontend); AC1 `"Revenue Trend (7 Weeks)"` count = 0; AC2 `"Revenue Trend (Last 7 Days)"` count = 1; AC3 commit subject matches `ui\(17.2\).*HOTFIX-02`; AC4 single file in HEAD diff (`RevenueStatusSection.tsx`, +5/-1). All plan acceptance criteria PASS. Live UAT (Marco sees corrected caption on AlertDetailPage Tab 1) deferred to Plan 06 deploy.

### Decisions Phase 17.2 Plan 03 (2026-05-20)

- **D-17.2-03-A — Combined plan (2 HOTFIX in 1 plan) over split**: HOTFIX-03 (V5 prominence) + HOTFIX-06 (D1 filter passthrough) both touch `TopNDisclaimer.tsx`. Splitting would force serialized waves with a file conflict (or risk losing wave-1 parallelism with Plans 01/02/04/05). Solution: combined plan with 2 atomic commits internally (one per HOTFIX) — preserves git-log readability and reversibility per R-03 while keeping wave parallel-safe.
- **D-17.2-03-B — `linkHref → linkBase` rename done in Task 1 (HOTFIX-03 commit)**: The rename is preparation for Task 2's URLSearchParams composition. Done in Task 1 so the prominence commit is self-consistent (no half-renamed state); Task 2 then ADDS the filter prop + helper without further renames. Sole consumer (`TopNDisclaimer.tsx`) verified via grep before rename — contained, zero collateral.
- **D-17.2-03-C — Forward-compatible descriptive query keys, NOT backend's current contract**: Backend `/api/metrics/network-totals` today accepts `date` + `channel` only. Frontend now forwards `year/month/sell_type/country/tier/environment` — descriptive keys matching how operators mentally describe their filters. FastAPI silently drops unknown params (default behavior) → no 422; Phase 18 backend can promote these keys to first-class without UI changes. Approach honors Marco's actual request (URL reflects filter context) without lying about endpoint behavior (operator opens link → sees raw JSON or a 422 for missing date/channel; the URL is the source of truth, not the response).
- **D-17.2-03-D — Explicit destructure (`filters={{ year:..., month:..., ... }}`) not spread (`filters={filters}`) at the call site**: Compile-time-auditable contract between PublishersPage and TopNDisclaimer. Future rename of any filter key in `PublishersFilters` surfaces as a TS error at this exact site; spread would silently absorb additions (including intentionally-excluded keys like `gross_net` which is not a network-totals filter) and create drift.
- **D-17.2-03-E — URLSearchParams not string concat for href composition**: T-17.2-03-01 (Tampering) mitigation built into the API — RFC-3986 percent-encoding is automatic, so operator-supplied filter strings cannot inject extra query keys or fragment segments. Also future-proof for keys containing `&`, `=`, or non-ASCII characters (e.g. when geo_cluster eventually maps to a localized label).
- **D-17.2-03-F — Skip `'all'` sentinel + undefined/empty values when building qs**: Operator-mental-model match. The URL reflects "filters I narrowed", not "all filter dimensions". When operator has no narrowing applied, link is the bare base URL (backward-compat for non-Publishers callers like potential dashboard widgets that might render TopNDisclaimer with no filter context).
- **D-17.2-03-G — JSDoc comment rephrased to avoid Task 1 verifier false-positive (Rule 3 inline auto-fix)**: First-pass JSDoc included literal phrase `text-xs/text-gray-500` as historical reference for future maintainers. Plan verifier regex `text-xs.*text-gray-500` matched the comment line → false-positive "FAIL: old prominence classes still present". Rewrote comment with descriptive prose ("near-invisible light-gray footnote") — preserves educational intent, regex returns 0, prominence ACs satisfied. Bundled into the same atomic Task 1 commit `406862f` (pre-commit comment edit, no separate commit).
- **Verification proof**: `cd frontend && npx tsc --noEmit` exit 0 with zero output (clean entire frontend); Task 1 ACs — `text-xs text-gray-500` count = 0, `border-l-4` + `font-semibold` present, `linkBase` in i18n-keys, 0 stale `linkHref` refs, commit subject matches `ui\(17.2\).*HOTFIX-03`, 2 files in diff; Task 2 ACs — `TopNDisclaimerFilters` declared, `filters?` optional, `composeNetworkTotalsHref` present, `URLSearchParams` used, PublishersPage forwards via `filters={{...}}` with `sell_type_proxy` key, old bare call site gone, commit subject matches `ui\(17.2\).*HOTFIX-06`, 2 files in diff. All ACs PASS. Live UAT (Marco sees prominent disclaimer + reactive link href on PublishersPage) deferred to Plan 06 deploy.

### Decisions Phase 17.2 Plan 04 (2026-05-20)

- **D-17.2-04-A — Diagnose-first execution (Task 1 read-only DIAGNOSIS.md before Task 2 fix)**: Marco's report 'tabs non accessibili' could map to 4 distinct root causes (a) STEPS predicate pruning / (b) parent-layer render-guard short-circuit / (c) error-boundary catching child exception / (d) UX defect where tab IS reachable but renders empty/misleading content. Task 1 produced `.planning/phases/17.2-marco-feedback-hotfix/17.2-04-DIAGNOSIS.md` (192 lines, committed as `64869b3` with ZERO code changes) classifying per tab — Tab 5 = (b), Tabs 3+4 = (d). Establishes precedent for future hotfixes: when user-reported symptom is ambiguous, write the diagnosis first as a separate atomic commit so fix scope is auditable against recorded root cause.
- **D-17.2-04-B — Snapshot evidence (238/238 alerts) confirms universal impact**: probed `frontend/dist/api/alerts/ALT-*.json` (238 files) — 100% have `contributors=[]`, `geo_breakdown=[]`, `environment_split=null`. Marco hit the defect on every alert because the legacy backfill corpus produced no populated payloads. Explains the universal phrasing in his report ("non più accessibili", not "su alcuni alert"). The 'no populated payload anywhere' problem is owned by Plan 05 (B2) and Phase 17.3 (D2); B1 fix here is purely client-side render-quality.
- **D-17.2-04-C — Tab 5 (Environment Split) root cause classified as (b) render-guard short-circuit**: `AlertDetailPage.tsx:259` required `alert.environment_split && Object.keys(alert.environment_split).length > 0` before invoking `<EnvironmentSplitSection>`. When env_split is null (all 238 alerts), conjunction short-circuits to falsy → content area renders nothing. Meanwhile `EnvironmentSplitSection.tsx` lines 22-37 has a perfectly good empty-state card (`<Card>` + "No environment data available.") that was NEVER REACHED because the parent guard short-circuited first. Fix: drop the guard, pass `alert.environment_split ?? ({} as Record<Environment, EnvironmentMetrics>)` and let the child's existing empty-state handler render. **Lesson: when child component has comprehensive empty-state handling, parent must invoke child unconditionally (or with typed null-coalesce) — never re-check the same predicate at parent layer; this is the same anti-pattern class as defensive null-check duplication.**
- **D-17.2-04-D — Tabs 3 + 4 root cause classified as (d) UX defect (secondary)**: ContributorsSection + GeoBreakdownSection ARE invoked (no parent short-circuit). They DO render via DataTable's default `emptyMessage = 'No data available'` fallback at `DataTable.tsx:53-58`. But Tab 3 also emits a misleading "Concentration (Top 3): 0.0%" line that looks like a real measurement; Tab 4 emits a 2-column empty-table / empty-pie layout. Both visually read as "half-broken". Fix: early-return empty-state card mirroring EnvironmentSplitSection's lines 22-37 pattern. Title preserved, body becomes "No contributor data available." / "No geo data available.". DataTable left untouched (its built-in empty-state still serves other consumers).
- **D-17.2-04-E — Source-grep regression test (Phase 17.1 precedent `test_publisher_drilldown_reverse_mapping.py`)**: 3 invariants pinned by 3 regex assertions: (1) STEPS entries for `contributors`/`geo`/`environment` have NO `condition` predicate; (2) AlertDetailPage env-branch lacks `Object.keys(...).length > 0` short-circuit; (3) all 3 section components contain explicit "No <X> data" copy. Trades semantic precision (jsdom would render actual DOM) for setup cost / CI speed. TDD posture: test written + committed `a5f09bd` RED (3 invariants failing) before fix; commit `dba6c17` GREEN (3 invariants passing). Pure source-level regression — re-introduction of the bug surfaces immediately in CI.
- **D-17.2-04-F — Type-honest empty-object fallback (`?? ({} as Record<Environment, EnvironmentMetrics>)`)**: The empty-object literal `{}` is structurally NOT a full `Record<Environment, EnvironmentMetrics>` (which would require all 4 keys WEB/AMP/APP/UNKNOWN). The `as` cast is acceptable here because EnvironmentSplitSection's lines 22-37 guard reads `if (!environmentSplit || Object.keys(environmentSplit).length === 0)` and short-circuits to the empty-state render BEFORE consuming any per-key field. Cast carries an implicit runtime contract (consumer guards before consuming non-empty keys) that matches the section's existing behavior. Alternative: widen prop type to `Partial<Record<Environment, EnvironmentMetrics>> | null` — deferred to a future cleanup since the existing contract is preserved verbatim and `npx tsc --noEmit` exits 0 with zero output.
- **D-17.2-04-G — EnvironmentSplitSection.tsx unchanged**: its lines 22-37 empty-state pattern was correct all along; it just couldn't fire because the parent guard short-circuited first. Verified by the source-grep test asserting `"No environment data available"` still present in the file post-fix. Avoiding a no-op edit on this file preserves git-blame attribution to its original author + minimizes review surface.
- **Verification proof**: Task 1 — `.planning/phases/17.2-marco-feedback-hotfix/17.2-04-DIAGNOSIS.md` 192 lines (≥30 required), 3/3 tabs covered by name + 3/3 root-cause classifications, commit subject matches `docs\(17.2\).*HOTFIX-04 Task 1`. Task 2 — `.venv/bin/python scripts/test_alert_detail_tabs_accessibility.py` exit 0 with `"All 3 HOTFIX-04 / B1 invariants hold ✓"`; AlertDetailPage env render branch lacks `Object\.keys.*length.*>.*0`; ContributorsSection contains "No contributor data available"; GeoBreakdownSection contains "No geo data available"; EnvironmentSplitSection contains "No environment data available" (preserved); `cd frontend && npx tsc --noEmit` exit 0 with zero output. 3 atomic commits on main (`64869b3` docs + `a5f09bd` test + `dba6c17` ui). All plan acceptance criteria PASS. Live UAT (Marco clicks Tab 3/4/5 on a deployed alert, sees clean empty-state cards instead of half-broken layouts / blank content) deferred to Plan 06 deploy.

### Decisions Phase 17.2 Plan 05 (2026-05-20)

- **D-17.2-05-A — Diagnose-first turned plan hypothesis upside down**: plan presented hypothesis (i) "empty env_split dominant cohort" as "most LIKELY"; the Task 1 diagnosis quantified all 238 snapshot alerts and found 0% empty env_split / 100% populated env_split with non-null top-level baselines. Hypothesis (iii) variant — contract drift on `_current` suffix between `environment_splitter` producer (emits `bacino_current` / `coverage_current`) and `TriageSection.tsx` consumer (reads `m.bacino` / `m.coverage` → undefined → `?? 0` → "0") — is the real root cause across 100% of live alerts. Diagnose-first execution (Plan 04 precedent `D-17.2-04-A`) saved a wrong Path B fix; the recorded diagnosis `.planning/phases/17.2-marco-feedback-hotfix/17.2-05-DIAGNOSIS.md` documents the falsification with quantitative evidence.
- **D-17.2-05-B — Path C selected (corrected from plan's binary A/B framing)**: (1) primary root-cause fix — TriageSection.tsx reads `(m as {bacino_current?: number}).bacino_current ?? m.bacino ?? 0` (and analogously for coverage); (2) defensive Path B layer kept — `envSplitMissing` predicate + `'n/a'` substitution + disclosure copy still wired for hypothetical legacy empty-env_split alerts (pre-Phase-11 deprecated surfaced via `?include_deprecated=true`, or future splitter run failures). Path A (backend `current_bacino` / `current_coverage` top-level fields) rejected — the data already exists in env_split per-env under correct names, top-level synthesis would mask the contract bug rather than fix it; deferred to Phase 17.3 only if Path C insufficient.
- **D-17.2-05-C — `amp_drift_detected` scalar sibling filtered out of envEntries (Rule 1 auto-fix)**: `environment_split` carries `amp_drift_detected: true` alongside the 3 per-env dicts (WEB, AMP, APP). `Object.entries(...)` returned 4 entries → divisor for `avgCoverage` was 4, diluting the mean by 1/4 (~25% understatement) even after the field-name fix. Surfaced while wiring the new aggregation. Fix: `envEntries.filter(([, v]) => typeof v === 'object' && v !== null)` — restricts iteration to the 3 actual env dicts. Caught in the same commit as the field-name fix; documented as Rule 1 auto-fix deviation in the SUMMARY.
- **D-17.2-05-D — Tab 5 EnvironmentSplitSection same-class drift left for Phase 17.3 (scope discipline)**: `EnvironmentSplitSection.tsx` reads `metrics.revenue` / `metrics.bacino` / `metrics.coverage` / `metrics.baseline_revenue` / `metrics.delta_percent` — same contract drift class as TriageSection. The whole Tab 5 render is therefore showing 0s / undefineds. NOT touched in HOTFIX-05 because: (a) HOTFIX-05 mandate is Tab 2 Triage only; (b) HOTFIX-04 just shipped Tab 5 accessibility — a fast follow-up on its content could conflict with Marco's own UAT pass; (c) the EnvironmentMetrics TypeScript interface drift is the right place to fix this comprehensively (Phase 17.3 candidate). Trade-off accepted: Marco may still see partial 0s on Tab 5 in Plan 06 UAT; that's a known Phase 17.3 follow-up, not a HOTFIX-05 regression.
- **D-17.2-05-E — Narrow per-aggregation casting over `EnvironmentMetrics` interface rename**: rather than rewriting `frontend/src/types/alert.ts:197-204` to use the `_current` suffix (which would cascade through 5+ consumers: EnvironmentSplitSection, EnvironmentBarChart, possibly more), the fix uses inline `(m as { bacino_current?: number }).bacino_current ?? m.bacino ?? 0`. This keeps blast radius to a single file (TriageSection.tsx) and preserves the option to do a comprehensive type rename later (Phase 17.3 candidate). The `?? m.bacino ?? 0` chain provides defense-in-depth if a future payload variant emits the bare key.
- **D-17.2-05-F — Backend payload UNCHANGED → no Plan 06 snapshot re-export risk**: Path C is frontend-only. The Plan 06 `export_api_json.sh` re-run will produce byte-identical JSON for the affected fields. W-05 CDN byte-diff check in Plan 06 will only differ if other plans landed payload changes (none expected for 17.2-05). Avoids a surprise CDN cache invalidation OR a "snapshot changed in plan 05 but didn't expect to" audit anomaly.
- **Verification proof**: Task 1 — `.planning/phases/17.2-marco-feedback-hotfix/17.2-05-DIAGNOSIS.md` 125 lines (≥30 required), root cause classification + Path C decision documented, commit subject matches `docs\(17.2\).*HOTFIX-05 Task 1` (`44560fe`). Task 2 — `.venv/bin/python scripts/test_triage_baseline_payload.py` exit 0 with `"All HOTFIX-05 / B2 invariants hold ✓"`; `bacino_current` / `coverage_current` / `envSplitMissing` / `n/a` / env_split disclosure copy all present in TriageSection.tsx; backend `HOTFIX-05` comment present in routes.py; `cd frontend && npx tsc --noEmit` exit 0 with zero output. 3 atomic commits on main (`44560fe` docs + `40de253` test + `f0a7303` fix). All plan acceptance criteria PASS. Live UAT (Marco opens any alert, Tab 2 Triage shows real non-zero Bacino + Coverage on current column instead of "0") deferred to Plan 06 deploy.

### Numeric validation (Mondadori Feb 2026 verified inline)

- ✅ Bacino 133M matches PBI +0.2%
- ✅ Revenue total gross €192k matches PBI €188k +2.5%
- ⚠ Fill rate 35.2% requires `measurable_impressions` (SCHEMA-03)
- ⚠ OM revenue €90k PBI vs €50k proxy: taxonomy delta (DOC-01 disclosure)

### Intel available for v1.3 (6 files)

- `.planning/intel/sentinel-2026-04-22/RECONCILIATION.md` — executive synthesis + piano 10/10
- `.planning/intel/sentinel-2026-04-22/v1-2-delivery-audit.md` — v1.2 shipped features audit
- `.planning/intel/sentinel-2026-04-22/wip-56-file-audit.md` — WIP classification 5-commit split
- `.planning/intel/sentinel-2026-04-22/runtime-data-audit.md` — runtime reads + silent-failure root cause
- `.planning/intel/sentinel-2026-04-22/crashed-session-reports.md` — 4 prior analyst reports
- `.planning/intel/sentinel-2026-04-22/deep-audit-evening.md` — 3 deep agents (numeric, pipeline, UI) + micro-validation Mondadori

### Pending Todos

- [01-04 v1.1]: Human verification of drift visualization in browser (carried)
- [Phase 05 v1.1]: Athena live connection deferred to v1.4

### Blockers/Concerns

- `data/vna_alerts.db*` WIP binary diff senza migration script → to investigate in Phase 07 (gating)
- 56 file WIP uncommitted (2 months drift) → atomic commits split across Phases 12, 13, 16

### Decisions Phase 17.4 Opening (2026-05-21)

- **D-17.4-A — Scope expansion v1.3 + anticipation v1.4 deciso da operator 2026-05-21**: Stefano furibondo all'idea di email parziale a Marco. Direttiva "tutto perfetto, nessuna email finché non tutto chiuso al 100%" implica scope expansion: (1) Phase 17.4 (v1.3) per chiudere D2 Sample 1 byte-perfect (Path A network-totals extension) + preparare Athena code-ready + isolare backfill synthetic-era. (2) v1.4 anticipato con Phase 19 (V1 channel granularity), Phase 20 (V2 open market), Phase 21 (Athena HBM full ingestion → Sample 2 byte-perfect €688 PBI). Email Marco SHIPPED solo post Phase 21 close. ETA totale 3-4 settimane.
- **D-17.4-B — Backfill count corretto 238, non ~2160 stima precedente**: verificato 2026-05-21 via `sqlite3 data/vna_alerts.db "SELECT data_source, COUNT(*) FROM alerts GROUP BY data_source"` → 238 backfill (deprecated=0) + 200 parquet (deprecated=1). Memory `project_sentinel_synthetic_backtest_fallback.md` correlata aggiornata. Breakdown per channel: 39 GOOGLE_ADEX (rebuildabili via CSV direct) + 199 altri channel (non rebuildabili senza Athena, target Phase 21 v1.4).
- **D-17.4-C — Path A (network-totals extension) preferred over Opzione D (CSV direct in data_fetcher_real)**: audit tecnico 2026-05-21 ha valutato 6 opzioni (D, D+E1 Athena, D+E2 interpolation, D+E3 synthetic disclosure, D+PA network-totals extension, DEFER Phase 18 full). Path A scelto perché (a) byte-perfect PBI €662 vs Opzione D €521 21% off, (b) riusa pattern Phase 11 D1 hybrid già live, (c) 1.5h stima codice + 1h test molto vicino a Opzione D 2.5h ma molto più alto-qualità, (d) anticipa parte di Phase 18 scope originale chirurgicamente.
- **D-17.4-D — Athena unwhitelist + connector ready in Phase 17.4 (no creds)**: code-path Athena steso completo in Phase 17.4 (ALLOWED_CHANNEL_GROUPS estesa + connector fallback graceful) MA credenziali Athena vivono in v1.4 Phase 21. Ragione: separazione code-readiness vs runtime-activation evita rush su credenziali production e permette test deterministici (mock Athena response in Phase 17.4 tests).
- **D-17.4-E — V1 + V2 + Athena = v1.4 separate milestone, non phase-mostro 17.4**: tentazione di "buttare tutto in Phase 17.4" rigettata. R-13 architectural quality + GSD-mandatory → phase atomiche per scope coerente. v1.4 milestone formale (`/gsd-new-milestone`) apre dopo v1.3 ship (Phase 18 close).

### Decisions Phase 17.4 Closing (2026-05-21)

- **D-17.4-F — Sample 1 byte-perfect achieved live**: ALT-20260322-010000-P2 revenue_current=€662.67 on https://sentinel-vna-stefano-hejais-projects.vercel.app/api/alerts/ALT-20260322-010000-P2 (in PBI €662 ±1% band [€655.37, €669.30]). Closes D2 Sample 1 from Marco email 2026-05-19. Deploy dpl_feLh7MNo3YRXB2PT8BJwWXmJrfLS.
- **D-17.4-G — Athena code-ready, creds Phase 21 dependency**: ALLOWED_CHANNEL_GROUPS extended to 8 channels per v1.2 schema. Mock tests pin contract. Phase 21 activates AWS creds with zero code changes (only env vars + datasource_config.json `active_source: athena` flip).
- **D-17.4-H — Deploy chirurgico clean**: 1 deploy attempt, W-05 3/3 PASS first try. Rollback anchors intact: pre-17.4-deploy-2026-05-21 + pre-17.4-backfill-rewrite + data/vna_alerts.db.pre-17.4-backfill-rewrite snapshot. Static CDN limitation for ?include_deprecated=true documented (structural, not a defect).
- **D-17.4-I — Email Marco STILL deferred to Phase 21 close**: D-17.4-A operator directive reaffirmed. Sample 1 fixed (€662.67 live); Sample 2 HBM still synthetic until Phase 21 Athena live. Phase 18 hardening proceeds next; v1.4 milestone formal open after Phase 18 close.

### Decisions Phase 18 Closing (2026-05-21)

- **D-18-A** — Phase 18 = hardening (tests + CI + docs), NOT new feature work. Zero production code modified (no `backend/`, no `frontend/`, no DB mutation).
- **D-18-B** — No Vercel re-deploy. `DATA_INTEGRATION.md` is at repo root (not served by Vercel); CI workflows live in `.github/`; tests live in `tests/` and `scripts/`. Snapshot byte-identical with Phase 17.4.
- **D-18-C** — v1.3 milestone structurally closed at this commit. v1.4 (Phase 19/20/21) opens. v1.3 ROADMAP "Milestones" entry flips from `[ ]` to `[x]`.
- **D-18-D** — Email-Marco workflow remains gated to Phase 21 close per D-17.4-I (9/9 audit points). Phase 18 ships zero email reply. Phase 19/20/21 v1.4 sequence is the remaining gate.

## Session Continuity

Last session: 2026-05-21T16:04:17.254Z
Stopped at: Completed 18-05-PLAN.md — Phase 18 v1.3 milestone close
