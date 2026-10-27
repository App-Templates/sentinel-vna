# Phase 09: Alert Backfill + Legacy Migration - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning
**Mode:** Assumptions (non-interactive, decided by architect given chirurgico 10/10 mandate)

<domain>
## Phase Boundary

Populate `alerts` table with new-schema alerts for the range **2026-01-23 → parquet_v2_max_date (2026-03-23)** by invoking the production pipeline (`run_pipeline(mode="BACKTEST")`) against the Phase-08 parquet v2 (`data/baseline/daily_aggregated.parquet`, 20-col, 8-channel). Schema-migrate the `alerts` table to expose a `deprecated` flag and soft-deprecate the 200 pre-2026-02-01 legacy alerts (stale `GOOGLE`/`OPEN_BIDDING` channel naming, v1.0 baselines).

**In scope:** BACKFILL-01, MIGRATE-01, migration 002, legacy UPDATE, API default filter on `/api/alerts`, Pydantic `Alert.deprecated` field.

**Out of scope (explicitly deferred):**
- ETL re-run to extend parquet past 2026-03-23 (adjusts Success Criterion #2 — see D-05)
- UI toggle / badge for deprecated alerts → Phase 14 (CORR-05 labeling)
- `pipeline_runs.alerts_written_count` column → Phase 10 (MONITOR-03)
- A8 cross-channel trigger wiring → v1.4+ (INTEL)

</domain>

<decisions>
## Implementation Decisions

### Script Architecture
- **D-01 (REVISED post-checker 2026-04-23):** Fresh `scripts/backfill_alerts.py` orchestrator. Do NOT modify legacy `scripts/regenerate_alerts.py` or `scripts/generate_real_alerts.py` (seed scripts reading the pre-Phase-08 parquet — leave intact for historical reproducibility). **Correction:** prior rationale claiming `backend/backtest/runner_real.py` "writes to `backtest_results`" was wrong — `runner_real.py:279` actually calls `create_alert()` and persists to the live `alerts` table. We STILL do not reuse `BacktestRunnerReal` (it reads `hourly_aggregated.parquet` GOOGLE_ADEX-only, not `daily_aggregated.parquet` 8-channels — scope mismatch), but the orchestrator DOES explicitly invoke `create_alert(AlertModel(**state['alert_payload']))` after each `run_pipeline()` that fires an alert. Pattern reference: `backend/backtest/runner_real.py:271-279`.
- **D-02:** Backfill invokes `run_pipeline(trigger_type=..., channel_group=..., mode="BACKTEST", timestamp=...)` from `backend.workflow.graph` — same code path as LIVE. `mode="BACKTEST"` activates parquet reads via `data_fetcher_real.py` and skips `notifier` via `graph.py:58`. **`run_pipeline()` does NOT persist — the orchestrator is responsible for `create_alert()` + `record_pipeline_run()` calls based on the returned `AlertState`.** This preserves the rule that `graph.py` / `data_fetcher_real.py` are NOT modified in Phase 09.
- **D-03:** Orchestrator loops: `for date in daterange × for channel in 8-channel-list × for trigger in ['A1','A2','A3']`. A0/A5/A6/A7 emerge internally from the pipeline (not external triggers) — no pipeline code modifications in Phase 09. A8 (cross-channel) not wired in pipeline → skipped. Per-tuple flow: `state = run_pipeline(...)` → if `state.get('alert_triggered')`: build `AlertModel(**state['alert_payload'])` → `create_alert(model)` + `record_pipeline_run(...)` → else just `record_pipeline_run(...)` for observability.

### Granularity + Resumability
- **D-04:** Daily-batch granularity. One `run_pipeline` call per `(date, channel, trigger)` tuple. Total calls: ~60 days × 8 channels × 3 triggers ≈ **1,440 invocations**.
- **D-05:** Resumable via checkpoint file `data/.backfill_checkpoint.json` — records completed `(date, channel, trigger)` tuples keyed by ISO-timestamp. On re-invocation: skip completed tuples. `--force` flag overrides. `--resume` is the default.
- **D-06:** Fail-soft-per-tuple: if one invocation raises, log ERROR + add to `failed_tuples` in checkpoint, continue batch. Batch exits non-zero if `failed_tuples > 0` at end (surfaces to CI).

### Idempotency
- **D-07 (REVISED 2× post-checker 2026-04-23):** `generate_alert_id(severity, ts)` in `backend/db/models.py:190` is deterministic on `(severity, timestamp)` ONLY — format `ALT-{YYYYMMDD}-{HHMMSS}-{sev}`. Channel and rule are NOT in the PK derivation.
  - **Collision problem:** if the orchestrator invokes all 24 (channel × trigger) tuples on the same day at identical `HH:MM:SS` (e.g., `00:00:00`), they collide on alert_id. `INSERT OR IGNORE` would silently drop 21+/day. Backfill would produce max ~180 alerts (3 severities × 60 days), not ~1,440.
  - **Deterministic disambiguation (applied in 09-03 Task 1):** per-tuple `HH = CHANNELS.index(channel) * 3 + TRIGGERS.index(trigger)` ∈ [0, 23]. With 8 channels × 3 triggers = 24 distinct HH per day. `ts_dt = datetime(d.year, d.month, d.day, HH, 0, 0, tzinfo=UTC)`. Each tuple gets a unique `ts` → unique alert_id (even at same severity). Re-run of same tuple → same HH → same alert_id → `INSERT OR IGNORE` is the intended no-op (true idempotency).
  - **Idempotency fix (paired):** Plan 09-03 Task 1b modifies `backend/db/operations.py:36` from `INSERT INTO alerts` to `INSERT OR IGNORE INTO alerts`. Safe for LIVE path (scheduler produces fresh `datetime.utcnow()` per run → no PK collision possible outside backfill).
  - **Verification:** `scripts/test_operations_idempotency.py` (2 tests: first-insert succeeds + duplicate-noop + existing row `updated_at` preserved). `scripts/test_backfill_alerts.py` Test #13 asserts 24 distinct alert_ids on a single-day full-grid stub run.

### Date Range
- **D-08:** Start: `2026-01-23` (day after max existing legacy alert timestamp 2026-01-22). End: `min(today, daily_aggregated.parquet.max_date)` auto-detected at script launch, currently **2026-03-23**. Range is ~60 days.
- **D-09:** Success Criterion #2 in ROADMAP amended during plan-phase: "UI shows ≥1 alert per week 2026-01-23 → **parquet_max_date**" (was "→ today"). Rationale: the 31-day gap 2026-03-24 → today requires an ETL re-run that would: (a) change parquet under a DB that Phase 08 validated against exact checksums, (b) require Mondadori fill-rate re-regression, (c) introduce scope creep outside "Alert Backfill" scope. Gap documented in `09-SUMMARY.md` as a known v1.3 limitation; resolution plant-seeded for Phase 10 (add ETL refresh cron) or v1.3.1.

### MIGRATE-01 Schema + Order
- **D-10:** Migration `scripts/migrations/002_add_alert_deprecation.sql` — adds two columns via `ALTER TABLE alerts`:
  - `deprecated INTEGER NOT NULL DEFAULT 0 CHECK(deprecated IN (0,1))`
  - `deprecation_reason TEXT`
  Transactional with ledger guard (pattern from `001_expand_channel_groups.sql`). DOWN script `002_rollback.sql` drops both columns (SQLite `ALTER TABLE DROP COLUMN` supported since 3.35 — verify on live DB; fallback: table-rebuild pattern).
- **D-11:** Apply script `scripts/apply_migration_002.py` mirrors `apply_migration_001.py` (pre-apply SHA256 backup, idempotent via ledger row check, post-apply smoke SELECT).
- **D-12:** Sync `backend/db/models.py` `SQL_CREATE_ALERTS` — add both columns **byte-identical** to migration 002 DDL. `scripts/test_models_sync.py` (HARD-03 gate, Phase 08 fixture) must stay green post-change.
- **D-13:** Execution order within phase: **migrate FIRST → legacy UPDATE → backfill LAST**. Rationale: fresh alerts from backfill inherit `deprecated=0` via DEFAULT naturally, avoiding post-hoc UPDATE on the much larger new dataset.

### MIGRATE-01 Cutoff
- **D-14:** Legacy cutoff: `timestamp < '2026-02-01T00:00:00' AND channel_group IN ('GOOGLE', 'OPEN_BIDDING')`. Belt-and-suspenders: date cutoff from ROADMAP Success #3 (primary) + legacy channel whitelist (defensive — future-proof if any Phase 08 UAT alert landed with pre-v2 channel naming). Verified: all 200 existing rows match both conditions.
- **D-15:** `deprecation_reason = 'v1.0 schema stale: legacy channel naming + v1.2 baseline divergence (Phase 09 deprecation)'`. Stable, greppable string.

### API + Pydantic
- **D-16:** `backend/api/routes.py` `/api/alerts` default behavior: implicit `WHERE deprecated = 0` filter. Query param `?include_deprecated=true` (boolean) surfaces all. Same for `/api/alerts/{id}` — deprecated alerts 404 unless flag set (audit/admin reachability preserved). `/api/admin/*` routes unaffected.
- **D-17:** Pydantic `Alert` schema in `backend/api/schemas.py` gains `deprecated: bool = False` field (Optional w/ default for backward compat during serialization). `deprecation_reason: Optional[str] = None`.

### Alert Rules Coverage
- **D-18:** Trigger set: `['A1', 'A2', 'A3']` (the 3 external triggers per `backend/workflow/graph.py:162-173`). Emergent rules A0/A5/A6/A7 fire internally via `anomaly_detector.py` during A1 runs (A0=data_gap bypass at graph.py:42, A5=margin, A6=coverage-zero, A7=pricing — per existing code paths). A4 skipped (deliberately absent per models.py comment). A8 skipped (cross-channel detection not wired).
- **D-19:** Hourly-dependent rules (A1 consecutive, A3 consecutive) gracefully degrade for the 7 non-GOOGLE_ADEX channels (hourly parquet is GOOGLE_ADEX-only per Phase 08 ETL). `anomaly_detector.py:145` already logs `"A1 consecutive check skipped: no hourly data"` and continues with daily baseline. No code change needed.

### Observability
- **D-20:** Each `run_pipeline` call records a `pipeline_runs` row via existing `record_pipeline_run` (confirm wire-up in implementation; if not, add it). Phase 10 consumes these rows for MONITOR-01/02 validation (can replay historical pipeline_runs against meta-alert rule to prove it fires correctly).

### Safety / Rollback (R-04 chirurgico 10/10)
- **D-21:** Pre-phase checkpoint:
  - `git tag v1.3-pre-phase-09`
  - `cp data/vna_alerts.db data/vna_alerts.db.pre-phase09.bak` (ledgered in commit message)
  - Migration 002 is transactional → atomic success/failure
- **D-22:** Rollback path per plan:
  - 09-01 (migration 002): `apply_migration_002.py --rollback` OR restore `.bak` + `git revert`
  - 09-02 (legacy UPDATE): `UPDATE alerts SET deprecated=0, deprecation_reason=NULL WHERE deprecated=1`
  - 09-03 (backfill): `DELETE FROM alerts WHERE created_at >= '<phase09_start_ts>'` (tracked in checkpoint file)

### Folded Todos
*(None — no backlog items matched Phase 09 scope in todo-match-phase.)*

### Claude's Discretion
- Exact checkpoint JSON schema (array vs nested-by-date — implementation detail)
- CLI flag names on `backfill_alerts.py` (`--start-date`, `--end-date`, `--channel`, `--rule`, `--force`, `--dry-run`, `--resume`)
- Logging verbosity per tuple (quiet-by-default with `-v` escalation)
- Batch parallelism (pipeline is not thread-safe per sqlite single-writer — serial execution preferred; if parallelism needed, use process pool with per-process DB connection — defer to planner)
- Exact SQL for the default `deprecated=0` filter (JOIN vs WHERE vs CASE — planner decides based on existing route pattern)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents (researcher, planner, executor) MUST read these before planning or implementing.**

### Roadmap / Requirements / State
- `.planning/ROADMAP.md` §Phase 09 — phase goal, success criteria, dependencies
- `.planning/REQUIREMENTS.md` §BACKFILL-01, §MIGRATE-01 — requirement text
- `.planning/STATE.md` — current wave / last committed SHA

### Phase 08 artifacts (upstream state)
- `.planning/phases/08-schema-migration-etl-extensions/08-03-SUMMARY.md` — DB post-Phase-08 state (200 legacy alerts, ledger `001_expand_channel_groups`)
- `.planning/phases/08-schema-migration-etl-extensions/08-04-SUMMARY.md` — parquet v2 schema + coverage (20 cols, daily 2025-02-16 → 2026-03-23, hourly 2025-12-23 → 2026-03-23 GOOGLE_ADEX only)
- `.planning/phases/08-schema-migration-etl-extensions/08-UAT.md` — Phase 08 UAT (confirms DB + parquet + models.py in sync)
- `scripts/migrations/001_expand_channel_groups.sql` — migration pattern authority (transactional + ledger guard + PRAGMA foreign_keys=OFF BEFORE BEGIN TRANSACTION — Phase 08 incident learnt)
- `scripts/apply_migration_001.py` — apply-script pattern (SHA256 pre-check, idempotency, post-smoke)
- `scripts/test_models_sync.py` — drift detector gate (HARD-03 CI gate; must stay green post-migration-002)

### Schema + pipeline authorities
- `backend/db/models.py` §SQL_CREATE_ALERTS — schema source of truth (must stay byte-identical to migration 002 DDL)
- `backend/db/models.py` §generate_alert_id — deterministic alert_id generation
- `backend/db/operations.py` §create_alert, §record_pipeline_run — DB write entrypoints reused by backfill
- `backend/workflow/graph.py` §run_pipeline — pipeline entrypoint invoked per tuple
- `backend/workflow/graph.py` §_should_skip_notifier — BACKTEST mode skip-path
- `backend/agents/data_fetcher_real.py` §BACKTEST branches — parquet read behavior
- `backend/agents/anomaly_detector.py` — A1/A2/A3 detection + A5/A6/A7 enrichment triggers; graceful-degrade logic on missing hourly

### API + UI integration
- `backend/api/routes.py` §`/api/alerts` — list endpoint (needs default `deprecated=0` filter)
- `backend/api/schemas.py` §Alert — Pydantic model (needs `deprecated: bool = False`)
- `config/alerting_rules.yaml` — rule thresholds (A1/A2/A3 severity bands, dual_thresholds, cross_channel_detection, gross_margin_alert)

### Project-level rules (global)
- `~/.claude/CLAUDE.md` — R-03 (atomic commits), R-04 (chirurgico 10/10), R-11 (1 fix/verify/commit), R-13 (top-tier architectural quality)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`run_pipeline()`** (`backend/workflow/graph.py:162`) — complete pipeline entrypoint, supports `mode="BACKTEST"` parquet reads + notifier skip. Zero modifications needed for backfill.
- **`generate_alert_id()`** (`backend/db/models.py`) — deterministic alert_id. Backfill reuses; idempotency flows from this determinism.
- **`create_alert()` + `record_pipeline_run()`** (`backend/db/operations.py`) — DB write entrypoints already invoked by pipeline internals.
- **Migration + ledger pattern** (`scripts/migrations/001_expand_channel_groups.sql`) — transactional + idempotent via ledger check. Copy structure for 002.
- **Apply-script pattern** (`scripts/apply_migration_001.py`) — SHA256 backup + idempotent apply + post-smoke. Copy structure for 002.
- **Drift detector** (`scripts/test_models_sync.py`) — Phase 08 HARD-03 gate. Extend test fixture to cover 002 columns; must stay green.

### Established Patterns
- **Transactional migrations with ledger guard** (Phase 08 pattern) — `vna_schema_migrations` table records applied migrations; re-apply is no-op by ledger check.
- **`PRAGMA foreign_keys=OFF` BEFORE `BEGIN TRANSACTION`** (Phase 08 bug learnt) — inside-tx is silent no-op, causes CASCADE delete on DROP.
- **BACKTEST mode notifier skip** (`graph.py:58`) — existing guard; backfill needs no special handling.
- **Graceful degrade on missing hourly** (`anomaly_detector.py:145`) — A1/A3 consecutive checks log-and-skip when hourly unavailable; backfill of non-GOOGLE_ADEX channels will use daily-only baseline automatically.

### Integration Points
- **`data/vna_alerts.db`** — single writer. Backfill runs serially (no parallelism in Phase 09).
- **`data/.backfill_checkpoint.json`** — new file, gitignored (add to `.gitignore` if not already covered by `data/` rule).
- **`backend/api/routes.py`** — single-file edit to add default filter (low risk, reversible).
- **Phase 10 handoff** — `pipeline_runs` rows from backfill become Phase 10's historical test corpus for MONITOR-01/02 meta-alert validation.

</code_context>

<specifics>
## Specific Ideas

- **Chirurgico 10/10 mandate (R-04)**: every step reversible (git tag, DB bak, migration DOWN script); surgical scope (one PLAN per concern: migration → UPDATE → backfill); dry-run first (`--dry-run` on backfill prints count of tuples without writing); verify post-action (SELECT queries per UAT checkpoint).
- **Plan split**: 3 plans, each one atomic commit at minimum:
  - **09-01**: Migration 002 (SQL + apply script + models.py sync + drift detector test update)
  - **09-02**: MIGRATE-01 legacy UPDATE (one-shot script `scripts/deprecate_legacy_alerts.py` + UAT SELECT)
  - **09-03**: BACKFILL-01 (`scripts/backfill_alerts.py` + API filter + Pydantic field + smoke test + full-range execution)
- **ROADMAP amendment** handled during `/gsd-plan-phase 09`: planner edits Success Criterion #2 wording + adds the 2026-03-24 → today gap disclosure as `.planning/phases/09-alert-backfill-legacy-migration/COVERAGE-GAP.md`. Plant-seed for v1.3.1 ETL refresh.
- **Drift detector HARD-03**: Phase 08 set the gate — models.py and live DB must stay byte-identical. Migration 002 is the first real regression test of this gate; green result validates Phase 18 CI strategy.

</specifics>

<deferred>
## Deferred Ideas

- **ETL re-run to extend parquet past 2026-03-23** — scope creep for Phase 09 (would re-touch Phase 08 validated checksums + require Mondadori fill-rate re-regression). Plant seed for v1.3.1 or Phase 10 (add ETL refresh cron as part of MONITOR-01 pipeline health).
- **UI toggle "Show deprecated" checkbox + badge** — belongs in Phase 14 (UI Labeling + Filter Exposure, requirement CORR-05/06). Phase 09 delivers backend support; UI surfacing is a separate concern.
- **`pipeline_runs.alerts_written_count` column** — MONITOR-03, Phase 10 scope. Phase 09 only populates `pipeline_runs` rows (without the count column), which is enough for Phase 10 to later ALTER + backfill the column.
- **A8 cross-channel detection trigger wiring** — v1.4+ (INTEL-01/02 deferred backlog). Phase 09 excludes A8 from trigger loop.
- **Backfill parallelism** — v1.4+ if regeneration cadence becomes routine. Phase 09 is serial (SQLite single-writer; process-pool would need per-process connection + cross-process checkpoint lock — out of scope for a one-shot backfill).
- **Reviewed Todos (not folded)** — none (no todo-match-phase hits for 09).

</deferred>

---

*Phase: 09-alert-backfill-legacy-migration*
*Context gathered: 2026-04-23*
*Mode: non-interactive (assumptions by architect per "10/10 professional" mandate)*
