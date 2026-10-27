---
phase: 11-network-totals-endpoint-filter-api-server-side-baseline
plan: 01
subsystem: testing
tags: [pytest, unittest, fastapi, testclient, tdd, nyquist, wave-0, red-scaffold]

# Dependency graph
requires:
  - phase: 10-pipeline-silent-failure-monitoring
    provides: TestClient(app) pattern (test_health_alerts_pipeline.py) — auth bypass via ENVIRONMENT=development, sys.path REPO_ROOT insert, setUpClass classmethod
  - phase: 09-alert-backfill-legacy-migration
    provides: 238 fresh alerts (deprecated=0) + 200 legacy alerts (deprecated=1) live in data/vna_alerts.db — fixture corpus for API-03 baseline test
  - phase: 08-schema-migration-etl-extensions
    provides: sell_type_proxy column in daily_aggregated.parquet (5 distinct values) — SCHEMA-04
provides:
  - 3 RED Nyquist scaffolds wired to /api/metrics/network-totals (API-01), /api/publishers/top?sell_type (API-02), /api/alerts/{id} baseline_bacino+baseline_coverage (API-03)
  - PBI bounds [26656.00, 27744.00] hardcoded (Vito email Jan 12 2026 GOOGLE_ADEX gross ±2%)
  - 5-value sell_type whitelist hardcoded verbatim from config/sell_type_proxy.yaml
  - Regression assertion baseline_coverage ≠ avgCoverage+0.05 (kills TriageSection.tsx:32 heuristic)
  - Fixture-discovery pattern (read-only sqlite3 SELECT in setUpClass) reusable for future API contract tests
affects: [11-02-network-totals-and-baseline, 11-03-sell-type-filter, phase-12-triage-server-side, phase-18-pbi-contract-tests, RC-a, RC-c, RC-e]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Nyquist Wave 0 RED scaffolds — author tests BEFORE implementation; tests must fail today and turn green when Wave 1 lands the contract"
    - "Read-only fixture discovery via sqlite3.connect(SELECT) in unittest.setUpClass — no fixtures, no mocks, binds tests to live DB shape"
    - "Subset acceptance for FastAPI status codes ((400, 422)) — accommodates either custom Query validator or default missing-required behavior"

key-files:
  created:
    - scripts/test_network_totals_pbi_parity.py
    - scripts/test_sell_type_filter.py
    - scripts/test_alert_baseline_fields.py
  modified: []

key-decisions:
  - "PBI bounds hardcoded as constants (PBI_TARGET_GROSS=27200.0, PBI_TOLERANCE_PCT=0.02) — not config-driven. Email Vito 2026-04-22 is the unchanging truth source for v1.3."
  - "VALID_SELL_TYPES inlined in test (not imported from config/sell_type_proxy.yaml) — RED scaffold must not depend on Wave 1 mapping import surface; verbatim copy is the contract."
  - "API-03 fixture discovery uses live data/vna_alerts.db read-only (per project precedent test_health_alerts_pipeline.py) — no in-memory fixture DB. SkipTest if DB missing."
  - "Test 4 (API-01 out-of-range 404) coincidentally passes today because FastAPI returns 404 for unknown routes — accepted tradeoff. Wave 1 implementation must yield 404 for the right reason (date outside CSV range, not missing route)."

patterns-established:
  - "Wave 0 RED scaffold: 3 self-contained scripts/test_*.py invocable directly via .venv/bin/python, exit non-zero today, exit zero after Wave 1. Pattern reused from Phase 08 SCHEMA-03 (test_mondadori_fill_rate_regression.py) and Phase 10 MONITOR-01 (test_health_alerts_pipeline.py)."
  - "ENVIRONMENT=development in os.environ at module top to bypass require_auth — canonical project pattern."

requirements-completed: [API-01, API-02, API-03]

# Metrics
duration: 4min
completed: 2026-04-29
---

# Phase 11 Plan 01: Nyquist Test Scaffold Summary

**3 RED Nyquist Wave 0 test scaffolds (13 unittest methods) authored before implementation — `/api/metrics/network-totals` PBI-parity (API-01), `/api/publishers/top?sell_type` filter (API-02), and `/api/alerts/{id}` baseline_bacino + baseline_coverage (API-03) — all failing today, ready for Wave 1 to flip GREEN.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-29T11:33:14Z
- **Completed:** 2026-04-29T11:37:24Z
- **Tasks:** 3
- **Files created:** 3 (no files modified — pure scaffold authoring, no production code touched)

## Accomplishments

- **API-01 RED scaffold** (`test_network_totals_pbi_parity.py`, 153 lines, 4 test methods): hardcodes PBI bounds [26656.00, 27744.00] from email Vito Jan 12 GOOGLE_ADEX €27,200 ±2%; asserts revenue_gross + currency=EUR + channel/date echo + 400/422 missing-date + 400/422 malformed-date + 404 out-of-range.
- **API-02 RED scaffold** (`test_sell_type_filter.py`, 162 lines, 4 test methods): VALID_SELL_TYPES = ["Open_Market", "Header_Bidding", "Direct", "Deal", "Other"] inlined verbatim from config/sell_type_proxy.yaml; asserts sell_type_filter transparency contract in payload + invalid value 400 + 5-value whitelist acceptance + backwards-compat (no-filter unchanged).
- **API-03 RED scaffold** (`test_alert_baseline_fields.py`, 265 lines, 5 test methods): read-only fixture discovery from live `data/vna_alerts.db`; asserts top-level baseline_bacino + baseline_coverage presence, exact aggregation rule `sum(env.bacino_baseline)`, regression vs killed TriageSection.tsx:32 heuristic (avg_coverage+0.05), graceful degradation for deprecated alerts.
- **Live RED verification** captured: all 3 tests exit non-zero on current main, with the right failure modes (endpoint 404, sell_type_filter key absent, baseline_bacino key absent + None != 171503 expected sum).
- **Live fixture binding verified:** `ALT-20260123-010000-P2` env_split sums to bacino_baseline = 95534+41421+34548 = **171,503** — matches RESEARCH §6 expected value byte-identically.

## Task Commits

Each task committed atomically:

1. **Task 1: Author scripts/test_network_totals_pbi_parity.py (API-01 RED)** — `1585b7e` (test)
2. **Task 2: Author scripts/test_sell_type_filter.py (API-02 RED)** — `87721d9` (test)
3. **Task 3: Author scripts/test_alert_baseline_fields.py (API-03 RED)** — `3e53ee0` (test)

## RED Verification Output (live, captured 2026-04-29)

| Test | Exit | Failures | Right-reason RED? |
|------|------|----------|-------------------|
| `scripts/test_network_totals_pbi_parity.py` | 1 | 3 / 4 | YES — endpoint 404 (does not exist); test 4 happens to PASS because FastAPI returns 404 for unknown routes (coincidentally the expected status). Wave 1 will turn 404→200 for the right reason. |
| `scripts/test_sell_type_filter.py` | 1 | 2 / 4 | YES — `sell_type_filter` key absent from payload (transparency contract not yet shipped); invalid sell_type silently accepted (filter not yet wired). Tests 3+4 pass coincidentally because the param is silently ignored — Wave 1 will make them meaningful. |
| `scripts/test_alert_baseline_fields.py` | 1 | 5 / 5 | YES — full RED across all 5 methods; AlertDetail keys lack baseline_bacino + baseline_coverage; aggregation expectation `None != 171503`. |

**All 3 exit non-zero — Wave 0 acceptance gate satisfied.** Plan 02 (API-01 + API-03) and Plan 03 (API-02) will flip to GREEN.

## Files Created/Modified

**Created:**
- `scripts/test_network_totals_pbi_parity.py` (153 lines) — API-01 PBI-parity assertion + input validation contract; 4 unittest methods.
- `scripts/test_sell_type_filter.py` (162 lines) — API-02 sell_type filter transparency contract + 5-value whitelist enforcement; 4 unittest methods.
- `scripts/test_alert_baseline_fields.py` (265 lines) — API-03 AlertDetail extension contract (top-level baseline_bacino/baseline_coverage) + heuristic regression + graceful deprecated; 5 unittest methods.

**Modified:** none — pure scaffold authoring, zero production code touched (per plan critical_constraints).

## Decisions Made

1. **Subset acceptance for FastAPI status codes** — Test `test_missing_date_returns_400` accepts `(400, 422)`; Wave 1 may use FastAPI default Query (422) or custom validator (400). Both are valid implementations.
2. **Fixture discovery in setUpClass, not per-test** — read-only sqlite3 connect once for the suite; cache `cls.alert_id` + `cls.dep_alert_id`; SkipTest if either missing rather than fail (graceful when DB drift / fresh install).
3. **Aggregation tolerance for heuristic regression = 0.001** — narrow band intentionally; if a single alert produces baseline_coverage within 0.001 of `avg_coverage_from_env_split + 0.05` by coincidence, the test fails for review (desired safety).
4. **Test 5 (API-03) uses live JSON `bacino_baseline`** — not hardcoded `171503`. The aggregation rule is what's asserted; the value is computed at test-time from the same env_split the server reads. Robust if a future seeding changes the baseline value but not the rule.

## Deviations from Plan

None — plan executed exactly as written. All 3 tasks landed atomically with the exact test method names, AC checks, and acceptance criteria specified. Zero production code touched. Zero deferred items. Zero auth gates. Zero architectural surprises.

## Issues Encountered

**1. Initial Bash exit-code masking during Task 1 verification**
The first verification run used `python script.py 2>&1 | tail; echo "EXIT=$?"` which captured the `echo` exit code (0), not the test exit. Re-ran with `python script.py > log 2>&1; EXIT=$?; echo "EXIT=$EXIT"` to get the true exit (1). Test was always RED — only the harness was misreading. Confirmed RED via `tail -3 log` showing `FAILED (failures=3)`.

**2. Test 4 of API-01 coincidentally PASSES today**
`test_date_out_of_csv_range_returns_404` asserts `404` for `?date=2099-01-01`. The endpoint doesn't exist yet, so FastAPI returns 404 for any path under it — coincidentally the expected status. Documented in the test's docstring + this Summary as a known caveat. Wave 1 implementation must produce 404 for the *right* reason (date outside `daily_kpi.csv` range, not missing route). The other 3 tests in that file fail clean RED (200 expected, 404 received), so the Wave 0 gate is still met.

**3. Tests 3+4 of API-02 coincidentally PASS today**
`test_no_filter_unchanged_behavior` and `test_each_valid_sell_type_returns_200` pass because the current endpoint silently ignores the `sell_type` param and returns 200 with the unfiltered top-publishers list. After Wave 1 wires the filter, these tests will become meaningful (they'll actually exercise the filter logic). Tests 1+2 fail clean RED, so the Wave 0 gate is met.

## Threat Surface Scan

No new security-relevant surface introduced. Threat register from PLAN frontmatter (T-11-01-01 through T-11-01-04) all `low`/`accept`/`mitigate` — read-only DB SELECT only, no PII, no DML. Mitigations applied:
- Test 3 sqlite3 connection uses default URI (read-write — but only SELECT issued, no `BEGIN`/`INSERT`/`UPDATE`/`DELETE`). Project precedent: test_health_alerts_pipeline.py.
- Conn closed in `finally:` blocks.
- SkipTest if DB missing — no panic.

No threat flags emerged that aren't in the plan. ASVS L1 invariants: V5 input validation tests authored (the contract-under-test); V2 auth bypassed via `ENVIRONMENT=development` per project pattern.

## User Setup Required

None — no external service configuration. All tests use the local FastAPI app + local SQLite DB.

## Next Phase Readiness

**Wave 1 (Plan 02) ready to start:**
- `scripts/test_network_totals_pbi_parity.py` and `scripts/test_alert_baseline_fields.py` are now the contract for Plan 02 implementation. Plan 02 lands `/api/metrics/network-totals` (must read `daily_kpi.csv` via pyarrow column projection per RESEARCH §4) + extends AlertDetail with on-the-fly aggregation (Opzione A per RESEARCH §6, no DB migration).
- Implementation is GREEN when both tests exit 0; until then, Plan 02 is incomplete.

**Wave 1 (Plan 03) ready to start:**
- `scripts/test_sell_type_filter.py` is the contract for Plan 03. Plan 03 wires `sell_type` Query param + 5-value whitelist + `df_year` filter + `sell_type_filter` echo in payload.

**No blockers.** Wave 1 plans (11-02, 11-03) can run in parallel — they touch different modules (`backend/api/routes.py` + `backend/db/operations.py` + `backend/api/schemas.py` for API-01/03; `backend/api/publisher_routes.py` for API-02) with no overlap.

## Self-Check: PASSED

**Files exist:**
- FOUND: scripts/test_network_totals_pbi_parity.py
- FOUND: scripts/test_sell_type_filter.py
- FOUND: scripts/test_alert_baseline_fields.py

**Commits exist:**
- FOUND: 1585b7e (test(11-01): add API-01 PBI-parity Nyquist Wave 0 RED scaffold)
- FOUND: 87721d9 (test(11-01): add API-02 sell_type filter Nyquist Wave 0 RED scaffold)
- FOUND: 3e53ee0 (test(11-01): add API-03 baseline fields Nyquist Wave 0 RED scaffold)

**Live RED gate:** all 3 tests exit non-zero on `git rev-parse HEAD` = 3e53ee0.

---
*Phase: 11-network-totals-endpoint-filter-api-server-side-baseline*
*Plan: 01-nyquist-test-scaffold*
*Completed: 2026-04-29*
