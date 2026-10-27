---
phase: 11-network-totals-endpoint-filter-api-server-side-baseline
plan: 02
subsystem: api
tags: [fastapi, pydantic, pyarrow, csv, baseline, network-totals, alert-detail, pbi-parity, rc-a, rc-e]

# Dependency graph
requires:
  - phase: 11-01-nyquist-test-scaffold
    provides: 2 RED Wave 0 contracts (test_network_totals_pbi_parity.py, test_alert_baseline_fields.py) — 9 unittest methods total — that this plan flips to GREEN.
  - phase: 09-alert-backfill-legacy-migration
    provides: 238 fresh alerts (deprecated=0) with populated environment_split_json containing bacino_baseline + coverage_baseline — the data source the new aggregation reads from.
  - phase: 08-schema-migration-etl-extensions
    provides: data/sentinel_db/daily_kpi.csv 8.94M-row upstream truth source the new endpoint reads (SCHEMA-04).
provides:
  - GET /api/metrics/network-totals — PBI-parity totals from raw daily_kpi.csv (bypasses parquet top-50 filter; closes RC-(a) for email Vito 2026-04-22 #2/#3).
  - AlertDetail.baseline_bacino + AlertDetail.baseline_coverage top-level fields, computed on-the-fly from environment_split_json — kills TriageSection.tsx:29-32 client-side heuristic (closes RC-(e)).
  - NetworkTotalsResponse Pydantic model — typed contract with date/channel pattern validation, ge=0 numeric guards, EUR currency default, freshness source_date echo.
  - _compute_baseline_from_env_split() pure helper — accepts both raw JSON string and parsed dict, returns (None, None) on empty/malformed/legacy blobs.
  - _load_kpi_csv() module-level cache helper — pyarrow.csv with column projection (5 of 14 cols) + 64MB block_size, loaded once per uvicorn worker.
affects: [11-03-sell-type-filter, phase-12-triage-server-side, phase-13-dashboard-corrections, phase-14-ui-labeling, phase-18-hardening, RC-a, RC-e]

# Tech tracking
tech-stack:
  added: []  # pyarrow, pyarrow.csv, pyarrow.compute were already present (etl_csv_to_parquet.py); routes.py simply imports them now.
  patterns:
    - "Pyarrow CSV column projection at API edge — read 5 of 14 columns with block_size=64MB + typed conversion (R-13 + RESEARCH §9 R1 OOM mitigation). Module-level pa.Table cache keyed by absolute path; cache miss ~3s, subsequent requests O(filter)."
    - "Pyarrow `date` column forced to pa.string() at load time — avoids date32[day] kernel mismatch with str query params; keeps `_kpi_csv_max_date` string-typed for the 404-range comparison. Idiom for pyarrow + FastAPI date filtering."
    - "Pure-function baseline aggregation helper (`_compute_baseline_from_env_split`) — accepts BOTH raw JSON string and parsed dict, isinstance-guarded, try/except around json.loads, returns (None, None) on every failure path. Pattern reusable for future env_split-derived metrics."
    - "On-the-fly aggregation in API handler (Opzione A from RESEARCH §6) — zero DB migration, value computed at request time from existing JSON blob. Phase 18 HARD-04 may persist later if SQL-side queries demand."

key-files:
  created: []
  modified:
    - backend/api/schemas.py  # NetworkTotalsResponse model + 2 Optional fields on AlertDetail
    - backend/api/routes.py   # 2 new helpers (_load_kpi_csv, _compute_baseline_from_env_split) + 1 new endpoint + 1 line-pair patch in get_alert

key-decisions:
  - "D-11.02-01 — Force pyarrow `date` column to pa.string() at load time. pyarrow auto-infers date32[day], but pc.equal(date32, str) raises ArrowNotImplementedError. Casting at load time is cheaper than per-request casting; also keeps the 404-range string-comparison path (`date > _kpi_csv_max_date`) consistent end-to-end. This was Rule 1 auto-fix #1 during Task 2."
  - "D-11.02-02 — Helper accepts both raw JSON string AND parsed dict. The `get_alert` JSON-blob loop already deserializes `environment_split_json` into `data['environment_split']` dict. Branching via `isinstance(env, str)` keeps the helper reusable from future callers that have only the raw blob (e.g., a Phase 18 backfill script). Pure function, no I/O, no side effects (R-13)."
  - "D-11.02-03 — Wire baseline aggregation AFTER the JSON-blob parse loop, BEFORE the deprecated coerce. The parse loop pops `environment_split_json` out of `data` and replaces it with the parsed dict at `data['environment_split']`. The aggregation then reads that dict and writes 2 new keys, before the Pydantic `**data` unpack at the bottom. This single insertion point is the natural seam — minimal diff, single responsibility."
  - "D-11.02-04 — Channel whitelist hardcoded as Python set, NOT imported from config. The 8 values match `backend/db/models.py CHANNEL_GROUP_CHECK_VALUES + GOOGLE legacy alias`. A set is O(1) membership and a constant — config-driven indirection would only add YAML-load overhead for a 1-line whitelist. If models.py changes the canonical list, HARD-03 drift gate catches it; this set is a compile-time mirror. R-13 'top-tier code': clarity > flexibility for an 8-element whitelist."
  - "D-11.02-05 — In-process pa.Table cache (no TTL, no eviction). The CSV is bounded (~1.3GB on disk → ~750MB in pa.Table form), uvicorn runs single-worker (per main.py), and ETL writes the CSV at most daily. A bounded one-shot cache is correct here. If multi-worker or hot-swap is needed later, a file-mtime invalidation can be bolted on without changing the API contract (Phase 18 HARD-04 territory)."

patterns-established:
  - "API-edge column-projected CSV reads with pyarrow — pattern reusable for any future endpoint that needs PBI-parity numbers from raw upstream data (Phase 13 CORR-03 NET revenue calc, Phase 14 UI labeling backfill)."
  - "Watertight schema additive extension — Optional[T]=None fields on response models keep backward compat with existing fixtures + tests. AlertDetail occurrence count in schemas.py unchanged (4→4); AlertSummary contract zero-touch."

requirements-completed: [API-01, API-03]

# Metrics
duration: 5min
completed: 2026-04-29
---

# Phase 11 Plan 02: Network Totals Endpoint + Server-Side Baseline Summary

**API-01 + API-03 GREEN — `/api/metrics/network-totals` reads raw `data/sentinel_db/daily_kpi.csv` returning Jan 12 GOOGLE_ADEX gross €27,245.63 (PBI €27,200 +0.17%, well inside ±2% tolerance), and `AlertDetail` exposes top-level `baseline_bacino` + `baseline_coverage` aggregated on-the-fly from `environment_split_json` (verified live: ALT-20260123-010000-P2 → 171503, 0.8161 — byte-identical to RESEARCH §6).**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-29T11:43:03Z
- **Completed:** 2026-04-29T11:48:07Z
- **Tasks:** 3
- **Files modified:** 2 (`backend/api/schemas.py`, `backend/api/routes.py`)

## Accomplishments

- **API-01 RC-(a) closure** — `GET /api/metrics/network-totals?date=YYYY-MM-DD&channel=...` reads raw upstream CSV (8.94M rows, max_date=2026-03-23) via pyarrow column projection + filter pushdown. Live verification: Jan 12 GOOGLE_ADEX revenue_gross=€27,245.63 (PBI €27,200 +0.17%), impressions=14,009,820, measurable=13,795,596. Bypasses the parquet top-50 filter that strips €4,221 of revenue per AUDIT-A-NUMBERS-FORENSICS.md Bug3.
- **API-03 RC-(e) closure** — `AlertDetail` gains 2 top-level Optional fields (`baseline_bacino: int`, `baseline_coverage: float`) computed on-the-fly inside `get_alert` handler from `environment_split_json`. Kills `TriageSection.tsx:29-32` client-side heuristic (`revenueRatio*0.95` + `avgCoverage+0.05`) by exposing the real values that `data_fetcher_real.py:142-260` already computed at alert creation time.
- **Pure-function helper `_compute_baseline_from_env_split`** — accepts both raw JSON string and parsed dict; returns `(None, None)` on empty/malformed/legacy/non-dict blobs (deprecated alerts, pre-v1.2 alerts) — graceful HTTP 200, no panic. Verified via 8 unit smoke cases + the live regression test (T-11-02-07 mitigation).
- **Watertight boundary preservation (R-13)** — `AlertSummary` contract UNCHANGED (occurrence count 4→4 in schemas.py); `backend/db/` UNCHANGED (zero diff); `/api/health/alerts-pipeline` UNCHANGED; HARD-03 drift gate UNCHANGED (28/28 tests still GREEN). Zero DB migration (Opzione A from RESEARCH §6).
- **Wave 0 RED → GREEN flip atomic** — both target tests `test_network_totals_pbi_parity.py` (4/4) and `test_alert_baseline_fields.py` (5/5) flipped from RED to GREEN within the 3 task commits. No commit straddles the gate.

## Task Commits

Each task was committed atomically (R-03 + R-06):

1. **Task 1: Add NetworkTotalsResponse + AlertDetail extension to schemas.py** — `034d180` (feat)
2. **Task 2: Implement /api/metrics/network-totals endpoint (API-01)** — `b6140f5` (feat)
3. **Task 3: Wire on-the-fly baseline aggregation in get_alert (API-03)** — `3141591` (feat)

## Verification Output (live, captured 2026-04-29 post-commit `3141591`)

| Test | Methods | Status | Captured Output |
|------|---------|--------|-----------------|
| `scripts/test_network_totals_pbi_parity.py` | 4/4 | GREEN | `Ran 4 tests in 1.504s` / `OK` |
| `scripts/test_alert_baseline_fields.py` | 5/5 | GREEN | `Ran 5 tests in 0.014s` / `OK` |
| `scripts/test_health_alerts_pipeline.py` | 10/10 | GREEN (no regression) | `Ran 10 tests in 0.040s` / `OK` |
| `scripts/test_models_sync.py` | 28/28 | GREEN (HARD-03 drift gate) | `Ran 28 tests in 0.089s` / `OK` |

**Live live-DB smoke (Task 2 acceptance):**
```
PBI parity OK: gross=27245.63 impressions=14009820 measurable=13795596 source_date=2026-03-23
Whitelist OK: BOGUS rejected with 400
```

**Helper unit smoke (Task 3 acceptance):**
```
None / "" / "{}" / {} / "not-json"  →  (None, None)
{"WEB":{"bacino_baseline":100,"coverage_baseline":0.8}}  →  (100, 0.8)
{"WEB":{...100,0.8},"AMP":{...50,0.6}}  →  (150, 0.7)
{"WEB":{"bacino_baseline":50}}  →  (50, None)         # missing coverage
{"WEB":{"bacino_baseline":0,"coverage_baseline":0.5}}  →  (None, 0.5)  # zero bacino
ALT-20260123-010000-P2 live blob  →  (171503, 0.8161)
```

## Files Created/Modified

**Modified (2):**

- `backend/api/schemas.py` (+31 lines) — Added `NetworkTotalsResponse` Pydantic model (9 fields with pattern + ge constraints + EUR default) after `BacktestResultResponse`. Added 2 Optional fields (`baseline_bacino`, `baseline_coverage`) to `AlertDetail` between `deprecation_reason` and `events`. `Field` import already present from prior phases — no import change. `Optional` already in use — no import change.
- `backend/api/routes.py` (+121 +54 lines = +175 net) — Imports `pyarrow`, `pyarrow.csv as pa_csv`, `pyarrow.compute as pc`. New module-level constants: `KPI_CSV_PATH`, `NETWORK_TOTALS_CHANNELS` (8 values), `_kpi_csv_cache`, `_kpi_csv_max_date`. New helper `_load_kpi_csv()` (column-projected pyarrow CSV reader with in-process cache). New helper `_compute_baseline_from_env_split()` (pure function, no I/O). New endpoint `@router.get('/metrics/network-totals')` with `@limiter.limit('60/minute')` and `response_model=NetworkTotalsResponse`. 7-line patch in existing `get_alert` handler (helper call + 2 dict assignments) inserted between the JSON-blob parse loop and the `data['deprecated']` coerce.

**Created (0):** This plan ships pure modifications. No new files.

## Decisions Made

See frontmatter `key-decisions`. Five canonical decisions:
- D-11.02-01: pyarrow `date` column forced to pa.string() at load time (Rule 1 auto-fix during Task 2).
- D-11.02-02: helper accepts both raw JSON string and parsed dict.
- D-11.02-03: aggregation wire-point AFTER JSON-blob parse loop, BEFORE deprecated coerce.
- D-11.02-04: channel whitelist as hardcoded Python set, not config-driven.
- D-11.02-05: in-process pa.Table cache without TTL/eviction (single-worker uvicorn + daily ETL → bounded).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Forced pyarrow `date` column to pa.string() at load time**
- **Found during:** Task 2 (initial verification run of `test_network_totals_pbi_parity.py`)
- **Issue:** Plan §interfaces specified `column_types={"revenue_gross": pa.float64(), "impressions": pa.int64(), "measurable_impressions": pa.int64()}` but did NOT specify `date`. pyarrow auto-inferred `date32[day]`, and `pc.equal(tbl["date"], date_str_param)` raised `ArrowNotImplementedError: Function 'equal' has no kernel matching input types (date32[day], string)`. The endpoint returned HTTP 500 instead of HTTP 200; 1/4 tests still failing post-Task-2 first try.
- **Fix:** Added `"date": pa.string()` to `ConvertOptions.column_types`. Both equality (`pc.equal`) and ordering (`date > _kpi_csv_max_date` Python string cmp) now work directly on str↔str without pyarrow date kernel involvement. Cleaner than per-request `pc.cast(tbl['date'], pa.string())` (which would re-cast 8.94M rows on every request).
- **Files modified:** `backend/api/routes.py` (1-line addition inside `_load_kpi_csv`'s `ConvertOptions.column_types` dict)
- **Verification:** Re-ran `scripts/test_network_totals_pbi_parity.py` → 4/4 GREEN. Live smoke `gross=27245.63` matches RESEARCH §4 byte-identically.
- **Committed in:** `b6140f5` (part of Task 2 commit — fix landed before the commit, so the commit is internally consistent)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Single-line addition to `ConvertOptions.column_types`; no scope change; no new files; no architectural shift. Captured as D-11.02-01 in frontmatter for future plans that read pyarrow CSVs at the API edge.

## Issues Encountered

**1. Test 4 of API-01 (`test_date_out_of_csv_range_returns_404`) coincidentally PASSED today AND yesterday**
The test asserts HTTP 404 for `?date=2099-01-01`. Pre-Plan-02 the endpoint didn't exist → FastAPI returned 404 for unknown route (right answer, wrong reason). Post-Plan-02 the endpoint exists and explicitly raises HTTPException(404) for `date > _kpi_csv_max_date`. The test now passes for the right reason. Documented in Plan 01 SUMMARY caveat (D-11.01-05) — Plan 02 closes the caveat.

**2. Bash exit-code masking on initial RED-state verification (cosmetic only)**
First call to `.venv/bin/python script.py 2>&1 | tail; echo "EXIT=$?"` captured the `echo` exit (0) instead of the test's exit (1). This was the same harness quirk noted in Plan 01 SUMMARY Issue #1. The test was always RED — only the captured echo was misleading. Re-ran with explicit log redirect to confirm. Did not affect commit decisions (RED state was visually obvious from `FAILED (failures=N)` lines).

## Threat Surface Scan

No new security-relevant surface beyond what is already declared in the plan's `<threat_model>`. All 10 threats T-11-02-01 through T-11-02-10 mitigated as planned:

- **T-11-02-01 (date param tampering):** Pydantic Query `pattern=r"^\d{4}-\d{2}-\d{2}$"` — enforced; `KPI_CSV_PATH` is a hardcoded `Path` constant, no user input ever joined.
- **T-11-02-02 (channel param tampering):** `NETWORK_TOTALS_CHANNELS` set membership check — verified live `BOGUS → 400`.
- **T-11-02-03 (DoS via full CSV materialization):** column projection (5/14 cols) + 64MB block_size + 60/min rate limit + single-date-only (no range) — all in code.
- **T-11-02-04 (cache miss concurrency):** accepted per plan; uvicorn single-worker enforces single-writer (per backend/main.py:147).
- **T-11-02-05 (info disclosure NetworkTotalsResponse):** Pydantic whitelist of 9 fields; `source` path is operational metadata, documented public.
- **T-11-02-06 (info disclosure baseline aggregation):** accepted; aggregation is a summary of values already in `environment_split_json` (which the same endpoint returns).
- **T-11-02-07 (panic on malformed env_split):** try/except around `json.loads` + `isinstance` guards on every dict access + `(None, None)` fallback. Verified via 5 unit smoke cases.
- **T-11-02-08 (auth bypass):** existing `require_auth` dep covers all `/api/*` routes via `backend/main.py:115`. New endpoints inherit. ENVIRONMENT=development bypass scoped to TestClient.
- **T-11-02-09 (privilege escalation):** N/A — both endpoints read-only, zero DB write, zero filesystem write.
- **T-11-02-10 (path traversal via KPI_CSV_PATH):** hardcoded `Path` constant; user input never joined to `BASE_DIR`.

Zero new threat flags emerged. ASVS L1 invariants V2 + V5 satisfied.

## User Setup Required

None — no external service configuration. The endpoint reads a local CSV; the aggregation reads a SQLite blob already in the live DB.

## Next Phase Readiness

**Wave 1 sibling (Plan 03 — API-02 sell_type filter):**
- Plan 03 can run in parallel — touches `backend/api/publisher_routes.py` (different module). No conflict with this plan's diff.
- Wave 0 RED scaffold for Plan 03 (`scripts/test_sell_type_filter.py`) is unaffected by Plan 02 — still RED on the same 2/4 methods that were RED at Plan 01 completion.

**Phase 12 (triage server-side rewrite):**
- API-03 contract is now stable — Phase 12 can wire `frontend/src/components/alerts/TriageSection.tsx` to consume the new top-level `baseline_bacino` + `baseline_coverage` and DELETE the `revenueRatio*0.95` + `avgCoverage+0.05` heuristic at `:29-32`. Plan 02 explicitly defers the frontend wiring per the plan `<objective>` ("Phase 11 only ships the contract; Phase 12 will consume").
- The regression test `test_baseline_coverage_not_heuristic_avgcov_plus_005` is now the contract for Phase 12 to keep GREEN.

**Phase 13 (CORR-03 gross+net side-by-side):**
- `NetworkTotalsResponse.revenue_net` is `Optional[float] = None` and the endpoint always returns `None` for `revenue_net` per the deferral in plan `<objective>`. Phase 13 will load `config/revenue_share.yaml`, compute `revenue_net = revenue_gross * (1 - rev_share)`, and flip the field non-None. The shape is forward-compatible — frontend can already check `revenue_net !== null` to decide whether to show the NET label.

**Phase 18 (HARD-04 hardening):**
- If contract tests later demand SQL-side baseline queries (e.g., `SELECT * FROM alerts WHERE baseline_bacino > X`), Phase 18 can add Migration 005 + a `record_pipeline_run`-style backfill to persist `baseline_bacino` + `baseline_coverage` as columns. Today's on-the-fly aggregation is forward-compatible — the API contract is unchanged whether the values come from a SQL column or an aggregation.

**No blockers.** Plan 02 is fully self-contained, atomically committed, and verified GREEN end-to-end.

## Self-Check: PASSED

**Files exist:**
- FOUND: `backend/api/schemas.py` (modified — `NetworkTotalsResponse` + 2 AlertDetail fields)
- FOUND: `backend/api/routes.py` (modified — 2 helpers + 1 endpoint + 7-line get_alert patch)
- FOUND: `.planning/phases/11-network-totals-endpoint-filter-api-server-side-baseline/11-02-network-totals-and-baseline-SUMMARY.md` (this file)

**Commits exist:**
- FOUND: `034d180` feat(11-02): add NetworkTotalsResponse + baseline fields to AlertDetail (API-01/API-03 schema)
- FOUND: `b6140f5` feat(11-02): /api/metrics/network-totals endpoint reads raw daily_kpi.csv (API-01)
- FOUND: `3141591` feat(11-02): on-the-fly baseline aggregation in get_alert handler (API-03)

**Live GREEN gate:** all 3 verification suites exit 0 on `git rev-parse HEAD` = `3141591`.

---
*Phase: 11-network-totals-endpoint-filter-api-server-side-baseline*
*Plan: 02-network-totals-and-baseline*
*Completed: 2026-04-29*
