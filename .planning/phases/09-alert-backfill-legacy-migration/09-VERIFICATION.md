---
phase: 09-alert-backfill-legacy-migration
verified: 2026-04-23T16:00:00Z
status: passed
score: 21/21 must-haves verified
overrides_applied: 0
re_verification: false
human_verification: []
---

# Phase 09: Alert Backfill + Legacy Migration — Verification Report

**Phase Goal (ROADMAP):** UI alert list populated 2026-01-23 → parquet_v2_max_date (2026-03-23); legacy pre-v1.2 alerts soft-deprecated. 31-day gap 2026-03-24 → current date disclosed in COVERAGE-GAP.md (v1.3.1 plant-seed).

**Requirements in scope:** BACKFILL-01, MIGRATE-01

**Verified:** 2026-04-23T16:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Roadmap Success Criteria + Plan must_haves)

| #   | Truth                                                                                                                     | Status     | Evidence                                                                                                                                                                                          |
| --- | ------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | ROADMAP SC#1: `scripts/backfill_alerts.py` run for 2026-01-23 → 2026-03-23 writes N > 0 alerts to DB                      | VERIFIED   | `SELECT COUNT(*) FROM alerts WHERE deprecated=0` = **238**. Script exists at `/Users/admintemp/Downloads/Claude/value-network-alerting/scripts/backfill_alerts.py` (12,338 bytes, executable).    |
| 2   | ROADMAP SC#2: ≥ 1 alert per ISO week 2026-01-23 → parquet_v2_max_date (2026-03-23); COVERAGE-GAP.md plant-seed             | VERIFIED   | All 10 weeks have ≥ 1 alert: W03=11, W04=29, W05=28, W06=21, W07=36, W08=31, W09=29, W10=26, W11=24, W12=3. COVERAGE-GAP.md exists at correct path, references parquet_v2_max_date and v1.3.1.   |
| 3   | ROADMAP SC#3: Pre-2026-02-01 alerts marked `deprecated=TRUE` with `deprecation_reason='v1.0 schema stale'` (canonical D-15) | VERIFIED   | `SELECT COUNT(*) FROM alerts WHERE deprecation_reason = 'v1.0 schema stale: legacy channel naming + v1.2 baseline divergence (Phase 09 deprecation)'` = **200/200** (exact byte match).        |
| 4   | alerts table has `deprecated INTEGER NOT NULL DEFAULT 0 CHECK(deprecated IN (0,1))` (PLAN 09-01)                          | VERIFIED   | `PRAGMA table_info(alerts)` row 19: `deprecated\|INTEGER\|1\|0\|0`. `sqlite_master.alerts.sql` contains `deprecated INTEGER NOT NULL DEFAULT 0 CHECK(deprecated IN (0, 1))`.                       |
| 5   | alerts table has `deprecation_reason TEXT` (PLAN 09-01)                                                                   | VERIFIED   | `PRAGMA table_info(alerts)` row 20: `deprecation_reason\|TEXT\|0\|\|0` (nullable, no default).                                                                                                    |
| 6   | All 200 pre-existing legacy alert rows preserved AND have `deprecated = 1` post-09-02 (PLAN 09-02)                        | VERIFIED   | Distribution: 0\|238 fresh + 1\|200 legacy. All 200 legacy alerts have ts < 2026-02-01 AND channel IN ('GOOGLE','OPEN_BIDDING') (107 GOOGLE + 93 OPEN_BIDDING). Zero over-deprecation.            |
| 7   | Zero over-deprecation: no alert with ts ≥ 2026-02-01 is deprecated; channel whitelist honored (PLAN 09-02)                | VERIFIED   | `WHERE deprecated=1 AND timestamp >= '2026-02-01T00:00:00'` = 0. `WHERE deprecated=1 AND channel_group NOT IN ('GOOGLE','OPEN_BIDDING')` = 0.                                                     |
| 8   | `vna_schema_migrations` ledger contains both `001_expand_channel_groups` and `002_add_alert_deprecation` rows              | VERIFIED   | Ledger rows: `001_expand_channel_groups\|2026-04-22 23:42:45` and `002_add_alert_deprecation\|2026-04-23 13:16:42`.                                                                              |
| 9   | `models.py SQL_CREATE_ALERTS` matches live DB byte-identical (HARD-03 drift gate stays green)                              | VERIFIED   | `python -m unittest scripts.test_models_sync` → Ran 17 tests, OK. TestModels002Sync class present (grep returns 2 matches).                                                                       |
| 10  | After backfill: `SELECT COUNT(DISTINCT date(timestamp)) FROM alerts WHERE deprecated=0 AND timestamp >= '2026-01-23'` = 60 | VERIFIED   | Returns exactly **60** (hardened R-04 gate per ERRATA B-5). Per-week distribution covers 10 ISO weeks W03-W12, all weeks ≥ 1.                                                                     |
| 11  | `data/.backfill_checkpoint.json` is gitignored (PLAN 09-03)                                                               | VERIFIED   | `.gitignore` line 31: `data/.backfill_checkpoint.json`.                                                                                                                                            |
| 12  | Each `run_pipeline` invocation records a `pipeline_runs` row (PLAN 09-03)                                                  | VERIFIED   | `mode='BACKTEST'` total = **1442** (60 × 8 × 3 = 1440 expected; +2 from observational re-run noted in 09-03-SUMMARY §Deviation 5). Distribution: success=238, no_alert=1204, failed=0.            |
| 13  | GET /api/alerts returns ONLY deprecated=0 alerts by default (implicit WHERE clause) (D-16)                                | VERIFIED   | `routes.py:124`: `include_deprecated: bool = Query(False)`. `operations.py:93-95`: `if not include_deprecated: conditions.append("alerts.deprecated = 0")`. Default behavior is to filter.        |
| 14  | GET /api/alerts?include_deprecated=true returns ALL alerts                                                                 | VERIFIED   | `routes.py:137` passes through. `operations.py:93-95` skips the WHERE clause when flag=True. 09-03-SUMMARY records live smoke: 238 vs 438 row counts.                                              |
| 15  | GET /api/alerts/{id} returns 404 for deprecated alert unless ?include_deprecated=true                                      | VERIFIED   | `routes.py:150-152`: `get_alert_by_id(alert_id, include_deprecated=...)`; `operations.py:138`/`150`: filter on `alert.get("deprecated") == 1` returns None when not opted in → 404 raised at 152. |
| 16  | Pydantic AlertSummary + AlertDetail include `deprecated: bool = False` and `deprecation_reason: Optional[str] = None`     | VERIFIED   | `schemas.py:52, 85`: `deprecated: bool = False`. `schemas.py:53, 86`: `deprecation_reason: Optional[str] = None`.                                                                                  |
| 17  | Idempotency: re-running backfill produces no new alerts (deterministic alert_id + INSERT OR IGNORE)                        | VERIFIED   | `operations.py:34, 39`: `INSERT OR IGNORE INTO alerts`. `test_operations_idempotency.py` 2/2 OK. HH-offset disambiguation: `backfill_alerts.py:234` `HH = channel_idx * len(TRIGGERS) + ...`.    |
| 18  | Pre-phase-09 git tag and DB backup exist for one-command rollback                                                          | VERIFIED   | `git tag -l v1.3-pre-phase-09` returns `v1.3-pre-phase-09`. `data/vna_alerts.db.pre-phase09.bak` exists (2,183,168 bytes); `PRAGMA table_info` shows 0 deprecated cols → confirmed pre-apply.    |
| 19  | `scripts/deprecate_legacy_alerts.py` is idempotent + supports --dry-run + --db-path (PLAN 09-02)                          | VERIFIED   | Script exists at `/.../scripts/deprecate_legacy_alerts.py` (6,498 bytes, executable). `test_deprecate_legacy_alerts.py` 12/12 OK including idempotency, dry-run, exit codes.                       |
| 20  | `scripts/apply_migration_002.py` is idempotent (second run exits 0 with SKIP)                                              | VERIFIED   | 09-01-SUMMARY documents apply driver SKIP behavior; smoke suite `test_migration_002_apply.py` test #11 (`test_second_apply_is_guarded_in_live_db`) passes. 11/11 OK.                              |
| 21  | COVERAGE-GAP.md documents 2026-03-24 → today gap with v1.3.1 plant-seed; ROADMAP Phase 09 block references both             | VERIFIED   | COVERAGE-GAP.md exists, contains "parquet_v2_max_date" + "v1.3.1" + "plant-seed". ROADMAP.md lines 92, 97 reference `parquet_v2_max_date (2026-03-23)` and `COVERAGE-GAP.md` per W-2.            |

**Score:** **21/21** truths verified.

### Required Artifacts

| Artifact                                                                                       | Expected                                                | Status     | Details                                                                                            |
| ---------------------------------------------------------------------------------------------- | ------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------- |
| `scripts/migrations/002_add_alert_deprecation.sql`                                             | ALTER TABLE + ledger guard + idx                        | VERIFIED   | Referenced + applied (ledger row present 2026-04-23 13:16:42).                                     |
| `scripts/migrations/002_rollback.sql`                                                          | DOWN script drops both cols + ledger row                | VERIFIED   | Referenced in 09-01-SUMMARY; HARD-03 test G asserts contents.                                      |
| `scripts/apply_migration_002.py`                                                               | Idempotent driver (lsof + flock + backup + post-verify) | VERIFIED   | Executable; SKIP semantics validated by smoke suite test #11.                                      |
| `scripts/test_migration_002_apply.py`                                                          | Live-DB smoke suite (11 tests)                          | VERIFIED   | Ran 11 tests, OK (post-09-02 evolved assertions).                                                  |
| `scripts/test_models_sync.py`                                                                  | HARD-03 drift detector (17 tests)                       | VERIFIED   | Ran 17 tests, OK; includes TestModels002Sync class.                                                |
| `backend/db/models.py` SQL_CREATE_ALERTS                                                       | Both cols byte-identical to migration 002 DDL           | VERIFIED   | Drift gate green proves byte-identity.                                                              |
| `data/vna_alerts.db.pre-phase09.bak`                                                           | WAL-safe pre-apply snapshot                             | VERIFIED   | Exists, 200 alerts, no deprecated col (proves pre-apply).                                          |
| `scripts/deprecate_legacy_alerts.py`                                                           | Idempotent UPDATE script                                | VERIFIED   | 12/12 tests OK; live UPDATE applied 200/200.                                                       |
| `scripts/test_deprecate_legacy_alerts.py`                                                      | 12-test fixture suite                                   | VERIFIED   | Ran 12 tests, OK.                                                                                  |
| `scripts/backfill_alerts.py`                                                                   | Orchestrator with HH offset + checkpoint + fail-soft    | VERIFIED   | Executable; uses BACKTEST mode + record_pipeline_run + create_alert.                               |
| `scripts/test_backfill_alerts.py`                                                              | 13-test backfill suite                                  | VERIFIED   | Ran 13 tests, OK.                                                                                  |
| `scripts/test_operations_idempotency.py`                                                       | INSERT OR IGNORE paired test (2 tests)                  | VERIFIED   | Ran 2 tests, OK.                                                                                   |
| `backend/db/operations.py` (INSERT OR IGNORE + include_deprecated)                             | Default filter + idempotent insert                      | VERIFIED   | grep confirms `INSERT OR IGNORE` (line 39) and `alerts.deprecated = 0` filter (line 95).            |
| `backend/api/schemas.py` (AlertSummary + AlertDetail)                                          | deprecated + deprecation_reason fields                  | VERIFIED   | Lines 52/53 and 85/86.                                                                             |
| `backend/api/routes.py` (include_deprecated query param + Pydantic coercion)                   | Filter + override + 404 semantics                       | VERIFIED   | Lines 124, 137, 150, 152 (list + by-id endpoints).                                                 |
| `.planning/phases/09-alert-backfill-legacy-migration/COVERAGE-GAP.md`                          | Gap disclosure + v1.3.1 plant-seed                      | VERIFIED   | File exists, references parquet_v2_max_date + Option A/B + v1.3.1.                                  |
| `.planning/ROADMAP.md` Phase 09 amendment                                                      | Goal + SC#2 reference parquet_v2_max_date + COVERAGE-GAP | VERIFIED   | Lines 92, 97; "→ today" purged from Phase 09 block.                                                 |
| `data/vna_alerts.db` (live DB)                                                                 | 238 fresh (deprecated=0) + 200 legacy (deprecated=1)    | VERIFIED   | Exact distribution confirmed: 0\|238, 1\|200. 60 distinct backfill dates.                          |
| `.gitignore` `data/.backfill_checkpoint.json` entry                                            | Checkpoint excluded                                     | VERIFIED   | Line 31 present.                                                                                    |
| Git tag `v1.3-pre-phase-09`                                                                    | Annotated rollback anchor                               | VERIFIED   | `git tag -l` returns `v1.3-pre-phase-09`.                                                          |

### Key Link Verification

| From                                  | To                                  | Via                                                            | Status   | Details                                                                                              |
| ------------------------------------- | ----------------------------------- | -------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------- |
| `scripts/backfill_alerts.py`          | `backend.workflow.graph.run_pipeline` | Import + invoke with `mode="BACKTEST"`                         | WIRED    | Line 31 imports run_pipeline; line 246 invokes; line 249 passes `mode="BACKTEST"`.                  |
| `scripts/backfill_alerts.py`          | `data/.backfill_checkpoint.json`    | JSON read/write with completed/failed/start_ts                 | WIRED    | Pattern present per 09-03-SUMMARY (file path + atomic tmp+rename); checkpoint observed in DB resume. |
| `backend/api/routes.py /api/alerts`   | `backend/db/operations.get_alerts`  | Query param `include_deprecated: bool = Query(False)` → param  | WIRED    | routes.py:124 declares; routes.py:137 passes through; operations.py:81 accepts.                      |
| `backend/db/operations.get_alerts`    | `data/vna_alerts.db.alerts`         | Conditional `WHERE alerts.deprecated = 0` when flag=False       | WIRED    | operations.py:93-95 implements conditional clause.                                                   |
| `scripts/deprecate_legacy_alerts.py`  | `data/vna_alerts.db.alerts`         | Single UPDATE with cutoff + channel whitelist + idempotency clause | WIRED | Live state proves wiring: 200/200 rows updated with exact reason text.                              |
| `migration 002` → `models.py`         | byte-identity check                 | `scripts/test_models_sync.py` (HARD-03 gate)                   | WIRED    | 17/17 tests OK including TestModels002Sync.                                                          |

### Data-Flow Trace (Level 4)

| Artifact                              | Data Variable                | Source                                            | Produces Real Data | Status   |
| ------------------------------------- | ---------------------------- | ------------------------------------------------- | ------------------ | -------- |
| `backend/api/routes.py` list_alerts   | `rows`                        | `get_alerts(...)` → `data/vna_alerts.db`         | Yes — 238 default, 438 with flag | FLOWING |
| `backend/api/routes.py` get_alert     | `data`                        | `get_alert_by_id(alert_id, include_deprecated)`  | Yes — 09-03-SUMMARY records 200 vs 404 by-id smoke | FLOWING |
| `data/vna_alerts.db` alerts table     | rows in 60-day backfill range | `scripts/backfill_alerts.py` invocations         | Yes — 238 actual alerts written | FLOWING |
| `data/vna_alerts.db` pipeline_runs    | BACKTEST rows                 | `record_pipeline_run` per tuple                  | Yes — 1442 rows (success=238, no_alert=1204, failed=0) | FLOWING |

### Behavioral Spot-Checks

| Behavior                                                            | Command                                                              | Result                       | Status |
| ------------------------------------------------------------------- | -------------------------------------------------------------------- | ---------------------------- | ------ |
| HARD-03 drift detector full suite                                    | `python -m unittest scripts.test_models_sync`                         | Ran 17 tests, OK             | PASS   |
| Migration 002 live-DB smoke suite                                    | `python -m unittest scripts.test_migration_002_apply`                | Ran 11 tests, OK             | PASS   |
| MIGRATE-01 fixture suite                                             | `python -m unittest scripts.test_deprecate_legacy_alerts`             | Ran 12 tests, OK             | PASS   |
| BACKFILL-01 orchestrator suite                                       | `python -m unittest scripts.test_backfill_alerts`                     | Ran 13 tests, OK             | PASS   |
| INSERT OR IGNORE idempotency suite                                   | `python -m unittest scripts.test_operations_idempotency`              | Ran 2 tests, OK              | PASS   |
| Live DB column shape                                                 | `sqlite3 ... "PRAGMA table_info(alerts)"`                            | 21 cols incl. deprecated + deprecation_reason | PASS |
| Live DB CHECK clause                                                 | `sqlite3 ... "SELECT sql FROM sqlite_master..."`                    | `CHECK(deprecated IN (0, 1))` present | PASS |
| Live DB row distribution                                             | `sqlite3 ... "SELECT deprecated, COUNT(*) FROM alerts GROUP BY deprecated"` | 0\|238 / 1\|200 | PASS |
| Live DB canonical reason text count                                  | `sqlite3 ... "SELECT COUNT(*) ... WHERE deprecation_reason='<D-15>'"` | 200 | PASS |
| Live DB distinct backfill dates                                      | `sqlite3 ... "SELECT COUNT(DISTINCT DATE(timestamp)) WHERE deprecated=0 AND timestamp >= '2026-01-23'"` | 60 | PASS |
| Per-ISO-week coverage                                                | `sqlite3 ... GROUP BY strftime('%Y-W%W', timestamp)`                 | 10 weeks W03-W12, all ≥ 1   | PASS |
| Per-channel coverage of fresh alerts                                 | `sqlite3 ... GROUP BY channel_group`                                  | All 8 channels ≥ 24 alerts  | PASS |
| BACKTEST pipeline_runs count                                         | `sqlite3 ... "SELECT COUNT(*) WHERE mode='BACKTEST'"`                | 1442                         | PASS   |
| BACKTEST failed count                                                | `sqlite3 ... "WHERE mode='BACKTEST' AND status='failed'"`            | 0                            | PASS   |
| Migration ledger rows                                                | `sqlite3 ... "SELECT * FROM vna_schema_migrations"`                   | 001 + 002 present            | PASS   |
| Pre-phase tag exists                                                 | `git tag -l v1.3-pre-phase-09`                                       | `v1.3-pre-phase-09`          | PASS   |
| Pre-phase backup exists + pre-apply                                  | `ls + sqlite3 ... PRAGMA table_info`                                  | 200 rows, 0 deprecated cols  | PASS   |
| Zero over-deprecation (date)                                         | `sqlite3 ... "WHERE deprecated=1 AND timestamp >= '2026-02-01...'"`  | 0                            | PASS   |
| Zero over-deprecation (channel)                                      | `sqlite3 ... "WHERE deprecated=1 AND channel NOT IN legacy"`          | 0                            | PASS   |

All 19 spot-checks PASS.

### Requirements Coverage

| Requirement | Source Plan(s)            | Description                                                                                                                                | Status      | Evidence                                                                                                                                                                            |
| ----------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| BACKFILL-01 | 09-03                     | Re-run pipeline genera alert per range 2026-01-23 → parquet_max (D-09 amendment)                                                            | SATISFIED   | 238 fresh alerts, 60 distinct dates, all 10 ISO weeks ≥ 1, 8/8 channels populated. Hardened R-04 commit gate passed. Marked complete in REQUIREMENTS.md body line 16 (`[x]`).      |
| MIGRATE-01  | 09-01, 09-02              | Soft-deprecate pre-2026-02-01 alerts with stable reason text                                                                               | SATISFIED   | 200/200 legacy rows have deprecated=1 with exact D-15 canonical reason. Zero over-deprecation. Marked `[x]` in REQUIREMENTS.md body line 52, but traceability table line 121 still shows "Pending" (documentation drift; see Anti-Patterns). |

**Note on traceability inconsistency:** REQUIREMENTS.md body marks both BACKFILL-01 (line 16) and MIGRATE-01 (line 52) as complete with `[x]`, but the Phase 09 traceability table at lines 120-121 shows BACKFILL-01 = Complete and MIGRATE-01 = Pending. This is a stale-table issue (documentation drift), not a functional gap — the live DB unambiguously satisfies MIGRATE-01. Recommend updating the traceability table to mark MIGRATE-01 = Complete in a follow-up docs commit.

### Anti-Patterns Found

| File                              | Line | Pattern                                                              | Severity | Impact                                                                                       |
| --------------------------------- | ---- | -------------------------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------- |
| `.planning/REQUIREMENTS.md`       | 121  | MIGRATE-01 status = "Pending" in traceability table                  | Info     | Stale table — body marks complete with `[x]`. Cosmetic doc drift; not a code/data issue.   |

No blockers. No warnings. One info-level finding (REQUIREMENTS.md table needs a status flip to match the body).

### Human Verification Required

None. All criteria verifiable programmatically (DB queries, test suites, file existence, grep). No UI/visual/real-time/external-service checks required for Phase 09 scope — UI surfacing of the deprecated flag is explicitly deferred to Phase 14 (CORR-05) per ROADMAP. The `/api/alerts` endpoint behavior was already smoke-tested in 09-03-SUMMARY (uvicorn on :8765 with documented response counts: 238 default vs 438 with `?include_deprecated=true`); this is recorded evidence in the summary, not a pending check.

### Gaps Summary

No gaps. Every must-have from ROADMAP Success Criteria, plan frontmatters, and CONTEXT decisions (D-01..D-22) is satisfied by direct evidence in the live DB, code, tests, and planning docs. The 22 locked D-XX decisions in 09-CONTEXT.md were honored:

- D-01..D-03 (script architecture + run_pipeline + per-tuple persist): VERIFIED via grep on backfill_alerts.py.
- D-04..D-06 (granularity + resume + fail-soft): VERIFIED via 1442 BACKTEST rows + 0 failed + checkpoint file.
- D-07 (HH-offset + INSERT OR IGNORE): VERIFIED via 24-distinct-HH-per-day derivation in code + paired idempotency suite.
- D-08, D-09 (date range + ROADMAP amendment): VERIFIED via COVERAGE-GAP.md + ROADMAP lines 92, 97.
- D-10..D-12 (migration 002 schema + apply + sync): VERIFIED via ledger row + drift detector 17/17.
- D-13 (execution order migrate→legacy→backfill): VERIFIED via commit chronology in summaries.
- D-14, D-15 (cutoff + canonical reason text): VERIFIED via 200/200 byte-match.
- D-16, D-17 (API filter + Pydantic): VERIFIED via routes.py + schemas.py + operations.py grep.
- D-18, D-19 (trigger set + degrade): VERIFIED via TRIGGERS=['A1','A2','A3'] + per-channel coverage.
- D-20 (pipeline_runs observability): VERIFIED via 1442 BACKTEST rows.
- D-21, D-22 (rollback): VERIFIED via tag + .bak.

Phase Goal achieved: BACKFILL-01 + MIGRATE-01 closed against the new schema; 200 legacy alerts soft-deprecated with stable reason; 238 fresh alerts span 60 calendar days × 10 ISO weeks × 8 channels; deprecation field exposed in API with default-hide + opt-in override + 404 semantics; 31-day gap (2026-03-24 → today) explicitly disclosed in COVERAGE-GAP.md as v1.3.1 plant-seed.

---

*Verified: 2026-04-23T16:00:00Z*
*Verifier: Claude (gsd-verifier)*
