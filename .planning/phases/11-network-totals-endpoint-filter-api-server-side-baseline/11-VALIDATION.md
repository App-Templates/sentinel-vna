---
phase: 11
slug: network-totals-endpoint-filter-api-server-side-baseline
status: draft
nyquist_compliant: true
wave_0_complete: false  # remains false until Plan 01 (Wave 0 test scaffold) executes
created: 2026-04-28
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from `11-RESEARCH.md` §10 (Validation Architecture).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing `scripts/test_*.py`) + `fastapi.testclient.TestClient` for integration |
| **Config file** | none — tests live under `scripts/` and are invoked directly via `.venv/bin/python` |
| **Quick run command** | `.venv/bin/python scripts/test_network_totals_pbi_parity.py` (per-task focused) |
| **Full suite command** | `.venv/bin/python -m pytest scripts/ -v --ignore=.venv` |
| **Estimated runtime** | ~30-60 seconds (Phase 11 tests only); ~3 minutes full suite |

---

## Sampling Rate

- **After every task commit:** Run the specific test for the touched component (e.g., `test_network_totals_pbi_parity.py` after edits to `network_totals` endpoint)
- **After every plan wave:** Run full Phase 11 suite (`test_network_totals_pbi_parity.py` + `test_sell_type_filter.py` + `test_alert_baseline_fields.py`)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds for per-task; 180 seconds for per-wave full suite

---

## Per-Task Verification Map

> Task IDs are placeholders — `gsd-planner` will assign concrete `{N}-{plan}-{task}` IDs. The map below binds each Phase 11 requirement to its automated test.

| Req ID | Behavior | Test Type | Automated Command | File Exists | Status |
|--------|----------|-----------|-------------------|-------------|--------|
| API-01 | `GET /api/metrics/network-totals?date=2026-01-12&channel=GOOGLE_ADEX` returns `revenue_gross` within 2% of €27,200 | integration | `.venv/bin/python scripts/test_network_totals_pbi_parity.py` | ❌ Wave 0 | ⬜ pending |
| API-01 | Missing/malformed `date` param → HTTP 400 with descriptive message | unit | same suite | ❌ Wave 0 | ⬜ pending |
| API-01 | Date out of CSV range → HTTP 404 | unit | same suite | ❌ Wave 0 | ⬜ pending |
| API-02 | `GET /api/publishers/top?sell_type=Open_Market` returns only rows tagged Open_Market via `sell_type_proxy` | integration | `.venv/bin/python scripts/test_sell_type_filter.py` | ❌ Wave 0 | ⬜ pending |
| API-02 | Invalid `sell_type` value → HTTP 400 (enum mismatch from `config/sell_type_proxy.yaml`) | unit | same suite | ❌ Wave 0 | ⬜ pending |
| API-02 | `sell_type_proxy` column missing in parquet → HTTP 503 (column guard) | unit | same suite | ❌ Wave 0 | ⬜ pending |
| API-03 | `GET /api/alerts/{alert_id}` returns non-None `baseline_bacino` + `baseline_coverage` for non-deprecated alert | integration | `.venv/bin/python scripts/test_alert_baseline_fields.py` | ❌ Wave 0 | ⬜ pending |
| API-03 | `baseline_coverage` server-side ≠ `avgCoverage + 0.05` (regression — TriageSection heuristic killed) | regression | same suite | ❌ Wave 0 | ⬜ pending |
| API-03 | Deprecated alert → `baseline_bacino=None`, `baseline_coverage=None` (no panic, payload still 200) | unit | same suite | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Tests that MUST be authored before implementation (TDD gate for Nyquist):

- [ ] `scripts/test_network_totals_pbi_parity.py` — PBI-parity assertion €27.2k ±2%; fixture: subset CSV Jan 12 (use `pyarrow` column projection like `scripts/test_mondadori_fill_rate_regression.py`)
- [ ] `scripts/test_sell_type_filter.py` — sell_type filter on `/api/publishers/top`; fixture: small parquet with both Open_Market and Programmatic_Direct rows
- [ ] `scripts/test_alert_baseline_fields.py` — `AlertDetail` response shape; fixture: in-memory SQLite (`vna_alerts.db` schema) with one alert containing `environment_split_json`

**Pattern reference:** Follow `scripts/test_health_alerts_pipeline.py` for `TestClient(app)` integration tests; follow `scripts/test_mondadori_fill_rate_regression.py` for parquet fixture pattern.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| PBI-side cross-check on €27.2k for a SECOND date | API-01 | Vito's email cites only Jan 12; second date validates not just lucky-hit | After implementation, query `/network-totals?date=2026-02-15` (or any non-Jan-12 PBI date Vito has access to), compare with PBI dashboard manually |
| Frontend wiring (TriageSection consumes server-side baselines) | API-03 | Frontend wiring is Phase 12+ scope; Phase 11 only ships the API contract | Manual curl + JSON inspection on `/api/alerts/{id}` endpoint pre-merge |

---

## Validation Sign-Off

- [x] All 9 verification rows have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all ❌ rows (3 new test scripts)
- [x] No watch-mode flags in commands (CI-safe)
- [x] Feedback latency < 60s per task / 180s per wave
- [x] `nyquist_compliant: true` set in frontmatter after planner authors tasks with verify commands

**Approval:** pending
