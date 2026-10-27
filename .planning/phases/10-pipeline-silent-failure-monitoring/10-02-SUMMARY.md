---
phase: 10
plan: "02"
plan_name: health-endpoint-alerts-pipeline
subsystem: pipeline-monitoring
tags:
  - fastapi
  - endpoint
  - monitor-01
  - watchdog-contract

dependency_graph:
  requires:
    - "10-01 (alerts_written_count column + migration 003)"
  provides:
    - "GET /api/health/alerts-pipeline (MONITOR-01) — external + watchdog contract"
    - "backend/db/operations.get_alerts_pipeline_health() helper (consumable directly by 10-03)"
    - "backend/api/schemas.AlertsPipelineHealth Pydantic model (ge=0 on counts)"
  affects:
    - "backend/api/routes.py (+29 lines, endpoint handler + 2 imports)"

tech_stack:
  reused:
    - "FastAPI @router.get with response_model"
    - "slowapi rate-limit decorator (60/minute, consistent with /health)"
    - "unittest.TestCase + TestClient pattern"
  patterns:
    - "Thin handler / business logic in db.operations"
    - "Fail-soft: DB error → HTTPException(503) not 500 (distinguishes health-check breakage from data state)"
    - "deprecated=0 filter inherited from Phase 09 D-16 semantic"

key_files:
  created:
    - scripts/test_health_alerts_pipeline.py
  modified:
    - backend/api/schemas.py (AlertsPipelineHealth model)
    - backend/db/operations.py (get_alerts_pipeline_health helper)
    - backend/api/routes.py (handler + 2 imports — scope verified clean against pre-existing WIP)

decisions:
  - "Counts are ge=0 not strict int: rejects negative at Pydantic layer; prevents contract drift if SQL changes"
  - "Helper opens its own sqlite3 connection (no conn kwarg): isolates watchdog from request-scoped conn pool"
  - "503 (not 500) on DB failure: uptime monitors can distinguish endpoint broken vs data state"
  - "Counts response excludes alerts_written_count aggregate: MONITOR-01 contract frozen at 3 fields; 10-03 queries that column directly"

metrics:
  duration: "~20 minutes (agent) + ~10 minutes (independent verification + closure)"
  tasks_completed: 2
  files_changed: 4
  completed_date: "2026-04-23"
---

# Phase 10 Plan 02: /api/health/alerts-pipeline Endpoint (MONITOR-01) Summary

Exposes three silent-failure metrics as a read-only endpoint: `last_alert_at`, `alerts_last_24h`, `pipeline_runs_last_24h`. Non-deprecated filter (Phase 09 D-16 semantic). Consumed by external synthetic probes and by Plan 10-03 watchdog via the same helper function.

## Task Completion

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | AlertsPipelineHealth schema + get_alerts_pipeline_health helper | 2bd1a0e | backend/api/schemas.py, backend/db/operations.py |
| 2 | Endpoint + TestClient smoke suite | 64b5b19 | backend/api/routes.py, scripts/test_health_alerts_pipeline.py |

## Independent Verification (post-commit, orchestrator-run)

Executed after agent stream timeout to validate closure without trusting partial agent output.

### T1 — Endpoint test suite (scripts/test_health_alerts_pipeline.py)
```
Ran 4 tests in 0.034s — OK
- test_endpoint_returns_200
- test_last_alert_at_is_null_or_iso8601
- test_response_matches_schema
- test_endpoint_does_not_mutate_db
```

### T2 — HARD-03 drift gate (regression from 10-01)
```
Ran 23 tests in 0.072s — OK (incl. TestModels003Sync)
```

### T3 — Migration 003 idempotency
```
[23:02:32] SKIP: migration 003 already applied (alerts_written_count col present + ledger row).
```

### T4 — Pydantic ge=0 constraint enforcement
```
OK: negative alerts_last_24h rejected
OK: negative pipeline_runs_last_24h rejected
OK: null last_alert_at accepted
```

### T5 — Helper contract + deprecated=0 filter
```python
>>> from backend.db.operations import get_alerts_pipeline_health
>>> get_alerts_pipeline_health()
{'last_alert_at': '2026-03-23T13:00:00+00:00', 'alerts_last_24h': 0, 'pipeline_runs_last_24h': 1446}
```
SQL verified: `MAX(created_at) ... WHERE deprecated=0` for both `last_alert_at` and `alerts_last_24h`.

### T6 — Endpoint latency (live DB, 438 alerts + 4,032 pipeline_runs)
```
status=200 latency=1.9ms budget=<1000ms -> PASS
payload: {"last_alert_at": "2026-03-23T13:00:00+00:00", "alerts_last_24h": 0, "pipeline_runs_last_24h": 1446}
```

### T7 — R-01 scope verification (commit 64b5b19 on routes.py)
- Staged diff contains ONLY: 2 import lines + 26-line endpoint handler + 2 blank separators = 29 lines added
- No unrelated pre-existing WIP lines swept in
- 57 lines of pre-existing WIP on routes.py still untouched in working tree post-commit (`git diff --stat`)

## Live-DB Snapshot (2026-04-23)

```json
{
  "last_alert_at": "2026-03-23T13:00:00+00:00",
  "alerts_last_24h": 0,
  "pipeline_runs_last_24h": 1446
}
```

**Interpretation:** This is exactly the divergence pattern Plan 10-03 watches for. `pipeline_runs_last_24h=1446 > 0 AND alerts_last_24h=0` is the silent-failure signature v1.2 had for 2 months undetected. Phase 10-03 will trigger a Slack P0 on this pattern within one cycle of the watchdog.

## Downstream Contract for 10-03

Plan 10-03 `silent_failure_watch.py` can consume this via either path (both stable and tested):

1. **Direct helper call** (preferred — no HTTP overhead, no auth bypass needed):
   ```python
   from backend.db.operations import get_alerts_pipeline_health
   metrics = get_alerts_pipeline_health()
   ```
2. **HTTP probe** (useful for running watchdog out-of-process or in a sidecar):
   ```
   GET http://localhost:8000/api/health/alerts-pipeline
   → 200 AlertsPipelineHealth JSON
   ```

## R-01 Preservation Ledger

Pre-existing WIP on the working tree untouched across this plan:
- `backend/api/publisher_routes.py` (modified, not staged)
- `backend/api/routes.py` — 57 lines of pre-phase-10 WIP preserved (commit 64b5b19 scope-clean, verified)
- Frontend, data/*.db-{shm,wal}, i18n stubs: untouched

## Success Criteria Check

- [x] `GET /api/health/alerts-pipeline` returns live JSON matching `AlertsPipelineHealth` schema (Ropen 200 + 3 fields on live DB)
- [x] Test suite passes 4/4 on current live DB (verified independently)
- [x] 2 atomic commits (Task 1: schema+helper; Task 2: route+tests) — each independently revertible
- [x] Downstream consumer contract stable (both helper call and HTTP probe paths work)
- [x] Latency < 1s budget (measured 1.9ms on warm endpoint, 16ms cold per agent's initial test)
- [x] R-01: pre-existing WIP preserved end-to-end

## Deviations

None. Agent execution of the two tasks was clean; only the closure (SUMMARY + STATE + ROADMAP) was completed inline by the orchestrator after an agent stream timeout. All agent outputs were independently re-verified before closure.

---
**Next:** Wave 3 (10-03) — watchdog that consumes this helper and emits Slack P0 on the `runs > 0 ∧ alerts = 0` divergence over a 24h window.
