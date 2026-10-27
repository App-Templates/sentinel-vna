---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Ready to execute
stopped_at: "Completed 10.1-08-PLAN.md (Phase 10.1 CLOSED: watchdog re-enabled, Case C confirmed, all MONITOR-0{4..8} requirements satisfied, 74 tests green)"
last_updated: "2026-04-25T19:23:23.990Z"
progress:
  total_phases: 15
  completed_phases: 6
  total_plans: 26
  completed_plans: 22
  percent: 85
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-22)

**Core value:** Trovare gli alert in tempo quasi reale comunicando solo ciò che è davvero importante — rendendo visibili i cali graduali che oggi nessuno nota.
**Current focus:** Phase 999.1 — investigate-live-pipeline-silent-since-2026-03-23

## Current Position

Phase: 999.1
Plan: Not started
Plans completed: Phase 08 5/5 ✓ | Phase 09 3/3 ✓ | Phase 10 3/3 ✓ | Watchdog live: triggered=True on pipeline_runs_last_24h=1446 AND alerts_last_24h=0
Next: Phase 10 verification (or advance to Phase 11)

Progress v1.3: [███░░░░░░░░░] 25% (3/12 phases complete: 07, 08, 09)
Critical path 07→10: 3/4 complete (10 remaining to unblock production alerts with MONITOR-01/02/03)

## Milestone History

**v1.1 Alerting Evoluto** — completed 2026-02-21

- 6 phases (01 Alerting Evoluto, 02 Nuovi Tipi Alert, 03 Operator Workflow, 04 Notifiche Slack, 06 Revisione Documentale)
- 17 plans, 1.95h total execution
- Phase 05 (Dati Live / Athena) deferred to v1.4

**v1.2 New IT Dataset** — shipped 2026-03-26 (non-GSD drift)

- Commits: `7de84ab feat(v1.2)` + `a975590 fix: TS build errors, UNKNOWN env`
- Delivered: 7-channel dataset, 50 publishers, A8 margin alert, leading indicators, cross-channel detection
- Gap: silent-failure discovered in v1.3 intel (CHECK constraint stale)

**v1.3 Stabilization** — in progress, started 2026-04-22, expanded evening same day

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

## Session Continuity

Last session: 2026-04-24T14:02:56.761Z
Stopped at: Completed 10.1-08-PLAN.md (Phase 10.1 CLOSED: watchdog re-enabled, Case C confirmed, all MONITOR-0{4..8} requirements satisfied, 74 tests green)
Resume file: None
