# Phase 09: Alert Backfill + Legacy Migration - Discussion Log

> **Audit trail only.** Not consumed by downstream agents. Decisions are in CONTEXT.md.

**Date:** 2026-04-23
**Phase:** 09-alert-backfill-legacy-migration
**Mode:** Non-interactive (user mandate: "deve funzionare 10/10, sbrigati, super professionale")
**Areas analyzed:** Script architecture, Backfill granularity, Idempotency, Parquet coverage gap, MIGRATE-01 schema, MIGRATE-01 order + cutoff, API/Pydantic integration, Alert rules scope, Observability, Rollback safety

---

## Pre-decision findings (from codebase scout)

| Finding | Source | Impact |
|---------|--------|--------|
| 200 alerts exist, all legacy `GOOGLE`/`OPEN_BIDDING`, max `timestamp=2026-01-22` | `sqlite3 data/vna_alerts.db` | Backfill range starts 2026-01-23; MIGRATE-01 targets all 200 rows |
| Parquet v2 `daily_aggregated.parquet` covers 2025-02-16 → 2026-03-23 (20 cols, 8 channels) | `pyarrow.parquet.read_table` | Backfill end date capped at 2026-03-23 (31-day gap to today) |
| Hourly parquet covers 2025-12-23 → 2026-03-23, GOOGLE_ADEX only | `pyarrow.parquet.read_table` | Consecutive-hours A1/A3 checks available only for GOOGLE_ADEX; 7 other channels degrade to daily baseline (existing graceful degrade in `anomaly_detector.py:145`) |
| `run_pipeline(mode="BACKTEST")` exists in `graph.py:162` with parquet path in `data_fetcher_real.py` + notifier-skip in `graph.py:58` | Source read | Backfill reuses pipeline as-is; zero pipeline modifications |
| `scripts/regenerate_alerts.py` reads OLD parquet `daily_channel_aggregated.parquet` (pre-Phase-08, 7 cols) | Script head read | Legacy seed script — must NOT be reused for backfill |
| No `deprecated` / `deprecation_reason` column in `backend/db/models.py` `SQL_CREATE_ALERTS` | grep | Migration 002 required (ALTER TABLE) |
| `scripts/migrations/001_expand_channel_groups.sql` uses transactional + ledger + `PRAGMA foreign_keys=OFF` BEFORE BEGIN | Source read | Authoritative pattern for 002 |
| `scripts/test_models_sync.py` is the HARD-03 drift detector (Phase 08) | Phase 08 SUMMARY | Must stay green after 002 + models.py sync |
| Trigger types wired in pipeline: A1 / A2 / A3 external; A0 / A5 / A6 / A7 internal emergent | `graph.py:162-173`, `anomaly_detector.py` | Trigger loop = `['A1','A2','A3']`; other rules emerge naturally |

---

## Areas + assumptions

### Script Architecture
**Assumption (D-01 / D-02 / D-03):** Fresh `scripts/backfill_alerts.py` that invokes `run_pipeline(mode="BACKTEST")` per `(date, channel, trigger)` tuple.
**Evidence:** Pipeline supports BACKTEST mode end-to-end; reusing it guarantees LIVE/BACKFILL parity (no divergence — key architectural quality constraint R-13).
**If wrong:** Two code paths drift. Backfill-generated alerts would have different shape than LIVE alerts. Caught by smoke test comparing alert JSON structure.
**Confidence:** Confident.
**User correction:** None.

### Backfill Granularity + Resumability
**Assumption (D-04 / D-05 / D-06):** Daily-batch, resumable via `data/.backfill_checkpoint.json`, fail-soft per tuple.
**Evidence:** ~1,440 pipeline invocations × transient failures likely (I/O, parquet slicing) → resumability non-optional.
**If wrong:** Single failure aborts ~20-minute batch; no partial-progress recovery.
**Confidence:** Confident.
**User correction:** None. User explicitly asked for resumable strategy in original instructions.

### Idempotency
**Assumption (D-07):** `generate_alert_id()` deterministic; `INSERT OR IGNORE` on collision.
**Evidence:** Existing ID generation is `sha256(timestamp|channel|rule)[:N]` pattern (per `models.py` inspection in prior phases).
**If wrong:** Re-runs double-write alerts. Caught by UAT checkpoint #2 ("idempotent re-run is no-op").
**Confidence:** Likely. Implementation detail verified in plan-phase research.

### Parquet Coverage Gap (2026-03-24 → today)
**Assumption (D-08 / D-09):** Accept parquet ceiling 2026-03-23; amend Success Criterion #2 to "→ parquet_max_date"; plant-seed ETL refresh for v1.3.1 / Phase 10.
**Evidence:** ETL re-run introduces: (a) Phase 08 checksum re-validation, (b) Mondadori fill-rate re-regression test, (c) potential schema drift from upstream CSV evolution — all scope creep.
**If wrong:** Stakeholder disappointment ("the UI should show alerts to today"). Mitigated by explicit disclosure in SUMMARY + Phase 10 MONITOR-01 adding ETL freshness check.
**Confidence:** Confident (scope discipline > nominal spec fulfillment).

### MIGRATE-01 Schema
**Assumption (D-10 / D-11 / D-12):** `ALTER TABLE alerts ADD COLUMN deprecated INTEGER / deprecation_reason TEXT` via migration 002, sync models.py, extend drift detector.
**Evidence:** SQLite 3.35+ supports `ALTER TABLE ADD COLUMN` with DEFAULT non-null (widely supported, used by migration 001 pattern).
**If wrong:** Schema change needs table rebuild (copy to new table, swap). Fallback pattern documented in migration 002 comments.
**Confidence:** Confident.

### MIGRATE-01 Execution Order
**Assumption (D-13):** Migrate first → legacy UPDATE → backfill last.
**Evidence:** `deprecated INTEGER NOT NULL DEFAULT 0` means fresh inserts inherit `0` automatically. Reverse order (backfill → migrate) would require post-hoc UPDATE over ~N new rows, larger blast radius.
**If wrong:** None — this is the lower-risk ordering.
**Confidence:** Confident.

### MIGRATE-01 Cutoff
**Assumption (D-14 / D-15):** `timestamp < '2026-02-01T00:00:00' AND channel_group IN ('GOOGLE','OPEN_BIDDING')`.
**Evidence:** ROADMAP Success #3 specifies date cutoff; defensive channel whitelist protects against future edge-case alerts that predate 2026-02-01 but use new channel names (none currently, but future-proof).
**If wrong:** Over-deprecation (unlikely — no rows match one condition without the other currently) or under-deprecation (if new-channel-name alert predates 2026-02-01 → still technically stale under v1.2 baseline, but the AND filter would skip it). Verified 0 rows in this edge category today.
**Confidence:** Confident.

### API + Pydantic
**Assumption (D-16 / D-17):** Default `deprecated=0` filter on `/api/alerts`; `?include_deprecated=true` surfaces all; Pydantic `Alert.deprecated: bool = False` field.
**Evidence:** Admin routes reachability preserved by explicit flag; UI default stays clean.
**If wrong:** Users lose access to historical alerts. Mitigated by flag escape hatch.
**Confidence:** Confident.

### Alert Rules Coverage
**Assumption (D-18 / D-19):** Trigger set `['A1','A2','A3']`; A0/A5/A6/A7 emergent; A4/A8 skipped.
**Evidence:** `run_pipeline` signature + `anomaly_detector` internal flow confirmed via grep. A8 is cross-channel, requires multi-channel state not wired yet.
**If wrong:** A8 missing from backfill = no cross-channel alerts for the 60-day range. Documented as v1.4+ deferred.
**Confidence:** Confident.

### Observability (Phase 10 handoff)
**Assumption (D-20):** Each `run_pipeline` call records `pipeline_runs` row (existing pattern in `scheduler.py`; confirm wire-up in implementation).
**Evidence:** `scheduler.py` imports `record_pipeline_run`; backfill shares pipeline, should share recording.
**If wrong:** Phase 10 MONITOR-01/02 loses historical test corpus. Planner verifies in plan-phase.
**Confidence:** Likely.

### Rollback Safety (R-04)
**Assumption (D-21 / D-22):** git tag + DB backup + migration DOWN script + `DELETE` path on backfilled rows.
**Evidence:** R-04 chirurgico 10/10 mandatory rule; Phase 08 used same pattern (`vna_alerts.db.pre-phase08.bak`).
**If wrong:** Failed phase = unrecoverable DB. Mitigated by 3 independent rollback vectors.
**Confidence:** Confident.

---

## User interactions

| Turn | User input | Interpretation |
|------|-----------|----------------|
| 1 | "/clear" intro + "Fai /gsd-discuss-phase 09 per decidere granularità del backfill..." | Run workflow, lean on assumptions — user flagged the core gray areas upfront |
| 2 | "non voglio discutere un cazzo per dio deve funzioanre 10/10 sbrigati e fai una cosa super professionale" | Skip multiSelect; architect decides all gray areas at 10/10 level; proceed to write CONTEXT.md directly |

---

## Deferred Ideas (captured during analysis)

- ETL re-run to extend parquet past 2026-03-23 → v1.3.1 / Phase 10
- UI toggle + badge for deprecated alerts → Phase 14 (CORR-05/06)
- `pipeline_runs.alerts_written_count` column → Phase 10 (MONITOR-03)
- A8 cross-channel detection wiring → v1.4+ (INTEL)
- Backfill parallelism → v1.4+ (requires per-process SQLite connection + cross-process checkpoint lock)

## Claude's Discretion

- Exact checkpoint JSON schema
- CLI flag names on `backfill_alerts.py`
- Logging verbosity
- Exact SQL for default `deprecated=0` filter pattern (JOIN vs WHERE vs CASE)
- Migration 002 DOWN strategy (native DROP COLUMN vs table-rebuild fallback)
