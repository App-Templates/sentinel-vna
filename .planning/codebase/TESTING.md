# Testing Patterns

**Analysis Date:** 2026-02-18

## Test Framework

**Runner (Python):**
- Listed in `requirements.txt`: `pytest>=7.4.0`, `pytest-asyncio>=0.21.0`
- No `pytest.ini`, `pyproject.toml`, `setup.cfg`, or `conftest.py` found
- **No test files exist** in the project (no `test_*.py`, `*_test.py`, or `tests/` directory)

**Runner (TypeScript):**
- No test framework configured (no `vitest.config.*`, `jest.config.*`)
- No test files exist in `frontend/src/` (no `*.test.ts`, `*.test.tsx`, `*.spec.ts`)
- `package.json` has no test script

**Run Commands:**
```bash
# Python (would work if tests existed)
pytest                     # Run all tests
pytest -x                  # Stop on first failure
pytest --cov=backend       # Coverage (pytest-cov not in requirements)

# TypeScript (not configured)
# No test runner available
```

## Test File Organization

**Location:**
- No test files exist anywhere in the project (excluding `node_modules`)
- `requirements.txt` includes pytest but it has never been used

**What exists instead of tests:**
- `scripts/test_integration.py` - A manual integration script (288 lines) that verifies:
  - Aggregated parquet files exist
  - Data loading works
  - Alert generation produces valid alerts
  - API endpoints respond correctly (requires running server)
  - This is NOT a pytest test suite; it is a standalone script run manually

## Test Structure

**No automated test suites exist.** The codebase relies entirely on:
1. Manual verification via `scripts/test_integration.py`
2. Pydantic validation on request/response schemas
3. SQLite CHECK constraints on data integrity
4. Type hints (Python) and strict TypeScript compilation

**What a test suite should cover:**

```python
# Example: tests/test_anomaly_detector.py
import pytest
from backend.agents.anomaly_detector import _statistical_fallback, _calculate_zscore

def test_zscore_calculation():
    assert _calculate_zscore(100, 200, 50) == -2.0
    assert _calculate_zscore(100, 100, 50) == 0.0
    assert _calculate_zscore(100, 200, 0) == 0.0  # zero std guard

def test_statistical_fallback_no_alert():
    state = {
        "trigger_type": "A1",
        "delta": {"revenue_pct": -2.0, "bacino_pct": 0, "coverage_pct": 0},
        "historical_stats": {"revenue_std": 100, "hour_of_day": 12, "day_of_week": "Monday"},
        "current_metrics": {"revenue": 980},
        "baseline_metrics": {"revenue": 1000},
        "validation_status": "OK",
        "execution_errors": [],
    }
    result = _statistical_fallback(state)
    assert result["alert_triggered"] is False
```

## Mocking

**Framework:** No mocking framework in use

**What should be mocked:**
- Anthropic API calls (currently uses live API or skips via env var check)
- Parquet file loading (use fixture DataFrames)
- SQLite database (use in-memory DB or tmpdir)
- `time.monotonic()` for cache TTL testing
- OAuth callbacks (authlib integration)

**What NOT to mock:**
- Pydantic validation (test with real models)
- Config loading from YAML (test with real config file)
- Agent state transformations (pure functions, test directly)

## Fixtures and Factories

**Test Data:**
- `frontend/src/mocks/mockData.ts` (669 lines) - Contains mock data for frontend development:
  - `mockAlertSummaries` - 10 mock AlertSummary objects
  - `mockAlerts` - Full Alert objects with all fields
  - `mockMetrics` - MetricDataPoint arrays
  - `mockBacktestResults` - BacktestResult arrays
  - `mockHealth` - HealthStatus objects
  - **Note:** This file is only used for frontend development, not for testing

**Backend fixtures needed:**
- Sample parquet DataFrames (hourly, daily_channel, daily_adrequests)
- Sample AlertState dictionaries for each agent
- Sample config (YAML -> AlertingConfig)
- Pre-populated SQLite DB for operations tests

## Coverage

**Requirements:** None enforced. No coverage tooling configured.

**Estimated critical coverage gaps:**
- Anomaly detection logic (P0/P1/P2 thresholds, consecutive hours, Z-score)
- Triage classification (TRAFFIC_DRIVEN, COVERAGE_DRIVEN, MIXED, REVENUE_ONLY)
- Database CRUD operations
- API endpoint response shapes and status codes
- Baseline calculation (7-week same-weekday same-hour)
- Publisher KPI aggregation
- Config loading and validation
- Auth flow (OAuth callback, session management, domain restriction)
- Scheduler job execution
- Backtest runner

## Test Types

**Unit Tests:**
- **Status: NONE EXIST**
- Should test: agent functions, utility functions, config validation, DB operations
- All agent functions are pure-ish (AlertState -> AlertState), highly testable
- `_calculate_zscore`, `_statistical_fallback`, `triage_classifier_agent` are deterministic

**Integration Tests:**
- **Status: NONE EXIST** (manual script at `scripts/test_integration.py` is not pytest)
- Should test: API routes end-to-end, pipeline invocation, scheduler jobs
- FastAPI `TestClient` not used anywhere

**E2E Tests:**
- **Status: NONE EXIST**
- No Playwright, Cypress, or similar configured
- Frontend has no test runner at all

## Common Patterns

**What WOULD be tested (priority order):**

1. **Anomaly detector thresholds** (`backend/agents/anomaly_detector.py`)
   - P0/P1/P2 threshold matching
   - Consecutive hours validation
   - Off-peak Z-score suppression
   - LLM fallback on API failure

2. **Triage classifier** (`backend/agents/triage_classifier.py`)
   - All 4 labels + NO_ALERT
   - Edge cases at threshold boundaries

3. **Database operations** (`backend/db/operations.py`)
   - CRUD for alerts, events, rechecks, backtests
   - Filter combinations in `get_alerts()`
   - Concurrent access (WAL mode)

4. **API routes** (`backend/api/routes.py`, `backend/api/publisher_routes.py`)
   - Response schema validation
   - 404/400/503 error paths
   - Pagination (limit/offset)
   - Rate limiting

5. **Config loading** (`backend/utils/config_loader.py`)
   - Singleton behavior
   - Reload mechanism
   - Missing file handling
   - Pydantic validation of YAML

6. **Baseline calculation** (spread across agents)
   - 7-week lookback (range(1,8))
   - Missing weeks handling
   - Bessel's correction (ddof=1)

**Async Testing:**
```python
# Scheduler and auth routes are async
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app

@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
```

**Error Testing:**
```python
def test_alert_not_found():
    # Using FastAPI TestClient
    from fastapi.testclient import TestClient
    from backend.main import app

    client = TestClient(app)
    response = client.get("/api/alerts/NONEXISTENT-ID")
    assert response.status_code == 404
    assert response.json()["detail"] == "Alert not found"
```

---

*Testing analysis: 2026-02-18*
