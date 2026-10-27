---
phase: 18-hardening-pbi-contract-tests-docs
plan: "01"
subsystem: contract-tests
tags: [contract-tests, parquet-db-ui, pytest-parametrize, pbi-parity, multi-channel, HARD-01]
dependency_graph:
  requires:
    - "17.4-SUMMARY.md (Phase 17.4 D2 closure — ALT-20260322-010000-P2 anchor)"
    - "scripts/test_alert_revenue_pbi_parity.py (PBI constants SAMPLE_1_PBI_REVENUE=662.67)"
    - "data/vna_alerts.db (read-only — Phase 17.4 Plan 04 rewrite applied)"
    - "frontend/dist/api/alerts/*.json (export_api_json.sh output)"
  provides:
    - "tests/contracts/test_parquet_db_ui.py (HARD-01 deliverable)"
    - "tests/contracts/conftest.py (5 shared fixtures)"
    - "18-01-FIXTURES.md (per-channel anchor mapping)"
  affects:
    - "HARD-01 acceptance criteria (REQUIREMENTS.md)"
    - "Phase 21 extension point (6 channels become GREEN when Athena real_csv lands)"
tech_stack:
  added:
    - "pytest 9.0.3 (via .venv — already in requirements.txt)"
  patterns:
    - "pytest.mark.parametrize over 7 channel ids"
    - "sqlite3 read-only URI (mode=ro) for DB fixture"
    - "json_snapshot_loader with multi-path search + wrapper unwrap"
    - "SKIP with reason for gated channels (Phase 21 dependency)"
key_files:
  created:
    - tests/__init__.py
    - tests/contracts/__init__.py
    - tests/contracts/conftest.py
    - tests/contracts/test_parquet_db_ui.py
    - .planning/phases/18-hardening-pbi-contract-tests-docs/18-01-FIXTURES.md
  modified: []
decisions:
  - "UI snapshot path is frontend/dist/api/ (not frontend/public/api/) — export_api_json.sh writes to dist/"
  - "JSON snapshots wrap alert under {alert: {...}} top-level key — json_snapshot_loader unwraps transparently"
  - "conftest searches both dist/ and public/ paths for forward-compatibility"
  - "MODELS_CHECK_CHANNELS includes legacy GOOGLE alias to match backend/db/models.py CHECK constraint exactly"
metrics:
  duration: "~5 minutes"
  completed: "2026-05-21T15:34:34Z"
  tasks_completed: 2
  files_created: 5
  files_modified: 0
  commits: 2
---

# Phase 18 Plan 01: HARD-01 Cross-Layer Contract Test Suite Summary

**One-liner:** Pytest parametrized 7-channel parquet->DB->UI contract test pinning ALT-20260322-010000-P2 EUR 662.67 as byte-perfect GOOGLE_ADEX anchor with 6 channels SKIP-gated on Phase 21 Athena.

## Objective

Create the first cross-layer contract test suite (HARD-01) that validates parquet -> DB -> UI consistency for one known-good alert per channel (7 cases). Prevents recurrence of the silent-failure class defined v1.3 (CHECK constraint drift undetected for 2 months).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Fixture index + package scaffolding | `4bca5ff` | tests/__init__.py, tests/contracts/__init__.py, tests/contracts/conftest.py, 18-01-FIXTURES.md |
| 2 | Parametrized 7-channel contract test (GREEN) | `9d07ac5` | tests/contracts/test_parquet_db_ui.py |

## Test Results

```
pytest tests/contracts/test_parquet_db_ui.py -v
============================= test session starts ==============================
platform darwin -- Python 3.11.14, pytest-9.0.3, pluggy-1.6.0
collected 15 items

tests/contracts/test_parquet_db_ui.py::test_parquet_db_ui_consistency[GOOGLE_ADEX] PASSED
tests/contracts/test_parquet_db_ui.py::test_parquet_db_ui_consistency[OPEN_BIDDING] SKIPPED
tests/contracts/test_parquet_db_ui.py::test_parquet_db_ui_consistency[HEADER_BIDDING_MAGNITE] SKIPPED
tests/contracts/test_parquet_db_ui.py::test_parquet_db_ui_consistency[HEADER_BIDDING_PUBMATIC] SKIPPED
tests/contracts/test_parquet_db_ui.py::test_parquet_db_ui_consistency[TAM] SKIPPED
tests/contracts/test_parquet_db_ui.py::test_parquet_db_ui_consistency[DIRECT] SKIPPED
tests/contracts/test_parquet_db_ui.py::test_parquet_db_ui_consistency[DEAL] SKIPPED
tests/contracts/test_parquet_db_ui.py::test_known_good_alert_id_is_not_deprecated[GOOGLE_ADEX] PASSED
tests/contracts/test_parquet_db_ui.py::test_known_good_alert_id_is_not_deprecated[OPEN_BIDDING] SKIPPED
tests/contracts/test_parquet_db_ui.py::test_known_good_alert_id_is_not_deprecated[HEADER_BIDDING_MAGNITE] SKIPPED
tests/contracts/test_parquet_db_ui.py::test_known_good_alert_id_is_not_deprecated[HEADER_BIDDING_PUBMATIC] SKIPPED
tests/contracts/test_parquet_db_ui.py::test_known_good_alert_id_is_not_deprecated[TAM] SKIPPED
tests/contracts/test_parquet_db_ui.py::test_known_good_alert_id_is_not_deprecated[DIRECT] SKIPPED
tests/contracts/test_parquet_db_ui.py::test_known_good_alert_id_is_not_deprecated[DEAL] SKIPPED
tests/contracts/test_parquet_db_ui.py::test_models_check_constraint_lists_all_7_channels PASSED

======================== 3 passed, 12 skipped in 0.03s =========================
```

**Exit code: 0** -- All acceptance criteria met.

## What Was Built

### tests/contracts/conftest.py (5 fixtures)

1. `repo_root` (session-scoped) -- Path to repository root
2. `db_conn` (session-scoped) -- Read-only sqlite3.Connection with row_factory; skips if DB absent
3. `json_snapshot_loader` (function-scoped) -- Factory loading frontend/dist/api/alerts/{id}.json; unwraps {"alert": {...}} wrapper from export_api_json.sh; searches dist/ and public/ paths
4. `parquet_loader` (function-scoped) -- Factory loading data/baseline/{name}.parquet via pyarrow; skips if pyarrow absent or file missing
5. `known_alert_fixture` (function-scoped) -- 7-channel mapping factory; GOOGLE_ADEX = live anchor ALT-20260322-010000-P2 EUR 662.67 real_csv tol=1%; other 6 SKIP (Phase 21)

### tests/contracts/test_parquet_db_ui.py (3 test functions, 206 lines)

1. `test_parquet_db_ui_consistency` (parametrized x7) -- 3-layer assertion: DB row (revenue in PBI band, data_source, channel_group) + UI JSON (byte-identical to DB values) + PBI band reassertion
2. `test_known_good_alert_id_is_not_deprecated` (parametrized x7) -- Fixture sanity: anchor alert must have deprecated=0
3. `test_models_check_constraint_lists_all_7_channels` (singular) -- CHECK constraint regression guard: asserts all 8 channel literals present in CREATE TABLE DDL

### 18-01-FIXTURES.md

7-row markdown table with channel_group, alert_id, expected_revenue_eur, expected_data_source, tolerance_pct, skip_reason, rationale. Includes "Updating the table" instructions for Phase 21 activation and DB inventory reference for 2026-05-21 state.

## Deviations from Plan

### Auto-resolved discovery (Rule 2 -- correctness)

**UI snapshot path correction**

- **Found during:** Task 1 read phase (verify step before conftest creation)
- **Issue:** Plan template assumed UI snapshots at `frontend/public/api/alerts/{id}.json`. Actual path is `frontend/dist/api/alerts/{id}.json` (Vite build output, written by `scripts/export_api_json.sh` line 6: `OUT=frontend/dist/api`). The `public/` directory does not exist in this repo.
- **Fix:** `json_snapshot_loader` fixture searches `_UI_SEARCH_PATHS = [frontend/dist/api/alerts, frontend/public/api/alerts]` in order. dist/ is found first. The forward-compat public/ path is kept for future Vite static asset migration.
- **Files modified:** `tests/contracts/conftest.py`
- **Impact:** Zero test breakage -- both PASS and SKIP outcomes unchanged.

**JSON wrapper unwrap in json_snapshot_loader**

- **Found during:** Task 1 verification (read frontend/dist/api/alerts/ALT-20260322-010000-P2.json)
- **Issue:** Plan template assumed flat `{"revenue_current": ..., "data_source": ...}` JSON. Actual file is `{"alert": {"revenue_current": 662.67, "data_source": "real_csv", ...}}` (export_api_json.sh calls `/api/alerts/{id}` which wraps under "alert" key).
- **Fix:** `json_snapshot_loader` detects single-key "alert" wrapper and unwraps transparently. Callers receive the flat alert dict matching the DB row shape.
- **Files modified:** `tests/contracts/conftest.py`
- **Commit:** `4bca5ff` (included in Task 1 scaffold)

## Known Stubs

None. GOOGLE_ADEX anchor is wired to live data (ALT-20260322-010000-P2 EUR 662.67 real_csv in DB + UI snapshot). Other 6 channels are documented SKIP with explicit Phase 21 reason -- not stubs, intentional deferred assertions.

## Threat Flags

None. No new network endpoints, auth paths, file access patterns, or schema changes introduced. Tests open data/vna_alerts.db read-only via URI mode=ro (T-18-01-02 mitigation verified).

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| tests/__init__.py exists | FOUND |
| tests/contracts/__init__.py exists | FOUND |
| tests/contracts/conftest.py exists | FOUND |
| tests/contracts/test_parquet_db_ui.py exists | FOUND |
| 18-01-FIXTURES.md exists | FOUND |
| Commit 4bca5ff exists | FOUND |
| Commit 9d07ac5 exists | FOUND |
| pytest exit 0 (3 passed, 12 skipped, 0 failed) | VERIFIED |
