---
phase: 11-network-totals-endpoint-filter-api-server-side-baseline
plan: 02
type: execute
wave: 1
depends_on: [11-01]
files_modified:
  - backend/api/routes.py
  - backend/api/schemas.py
autonomous: true
requirements: [API-01, API-03]

must_haves:
  truths:
    - "GET /api/metrics/network-totals?date=2026-01-12&channel=GOOGLE_ADEX returns revenue_gross between €26,656 and €27,744 (±2% of €27,200 PBI target — kills the top-50 filter for dashboard totals)."
    - "AlertDetail JSON response includes top-level baseline_bacino (int) and baseline_coverage (float in [0,1]) for non-deprecated alerts with environment_split_json."
    - "AlertDetail returns baseline_bacino=None and baseline_coverage=None for deprecated alerts or alerts with empty environment_split — no panic, HTTP 200."
    - "scripts/test_network_totals_pbi_parity.py exits 0 (GREEN) after this plan."
    - "scripts/test_alert_baseline_fields.py exits 0 (GREEN) after this plan."
    - "Existing scripts/test_health_alerts_pipeline.py still GREEN (no regression in adjacent endpoints)."
  artifacts:
    - path: "backend/api/routes.py"
      provides: "@router.get('/metrics/network-totals') endpoint + on-the-fly baseline aggregation in get_alert handler."
      contains: "/metrics/network-totals"
    - path: "backend/api/schemas.py"
      provides: "AlertDetail extended with baseline_bacino: Optional[int] and baseline_coverage: Optional[float]."
      contains: "baseline_bacino"
    - path: "backend/api/schemas.py"
      provides: "NetworkTotalsResponse Pydantic model — typed contract for /metrics/network-totals."
      contains: "NetworkTotalsResponse"
  key_links:
    - from: "backend/api/routes.py:network_totals"
      to: "data/sentinel_db/daily_kpi.csv"
      via: "pyarrow.csv.read_csv with column projection + filter pushdown"
      pattern: "pyarrow.csv.read_csv"
    - from: "backend/api/routes.py:get_alert"
      to: "_compute_baseline_from_env_split helper"
      via: "json.loads(environment_split_json) → aggregate"
      pattern: "_compute_baseline_from_env_split"
    - from: "backend/api/schemas.py:AlertDetail"
      to: "frontend/src/components/alerts/TriageSection.tsx (Phase 12)"
      via: "Pydantic Optional[int]/Optional[float] new fields — Phase 12 will consume; Phase 11 only ships the contract"
      pattern: "baseline_bacino: Optional[int]"
---

<objective>
Implement API-01 (`GET /api/metrics/network-totals`) and API-03 (server-side baseline fields in `AlertDetail`) so the 6 RED tests in `scripts/test_network_totals_pbi_parity.py` (4) and `scripts/test_alert_baseline_fields.py` (5 of which the 2 deprecated/aggregation-rule ones might already be NoneType-passing — see acceptance) flip to GREEN.

Purpose: Indirizza RC-(a) — top-50 filter strips €4,221 of revenue from dashboard totals — by reading raw upstream `daily_kpi.csv` (verified Jan 12 GOOGLE_ADEX gross = €27,245.63 → matches PBI €27,200 +0.17%). Indirizza RC-(e) — kills the `revenueRatio*0.95` and `avgCoverage+0.05` heuristic in `frontend/src/components/alerts/TriageSection.tsx:29-32` by exposing the real values from `environment_split_json` (verified live: ALT-20260123-010000-P2 has bacino_baseline=171503, coverage_baseline=0.8161).

Output: 1 new endpoint, 1 new Pydantic response model, 1 new helper function, 2 new fields on `AlertDetail`, on-the-fly aggregation in `get_alert` handler. NO DB migration (RESEARCH §6 Opzione A — recommended).

Phase 11 explicitly defers: TriageSection.tsx wiring (Phase 12), Migration 005 / DB persistence of baseline fields (Phase 18 HARD-04 if contract tests demand), Vercel deploy, NET revenue computation in network_totals (gross is primary per email Vito; net optional, deferred to Phase 13 CORR-03).
</objective>

<execution_context>
@/Users/admintemp/Downloads/Claude/.claude/get-shit-done/workflows/execute-plan.md
@/Users/admintemp/Downloads/Claude/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STELLA-POLARE.md
@.planning/intel/sentinel-2026-04-28/EMAIL-VITO-2026-04-22.md
@.planning/intel/sentinel-2026-04-28/SYNTHESIS.md
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/11-network-totals-endpoint-filter-api-server-side-baseline/11-RESEARCH.md
@.planning/phases/11-network-totals-endpoint-filter-api-server-side-baseline/11-VALIDATION.md
@CLAUDE.md
@backend/api/routes.py
@backend/api/schemas.py
@backend/db/operations.py
@scripts/test_network_totals_pbi_parity.py
@scripts/test_alert_baseline_fields.py
@scripts/etl_csv_to_parquet.py
@data/sentinel_db/daily_kpi.csv

<interfaces>
<!-- Contracts the executor needs. NO codebase exploration required. -->

From backend/api/routes.py (current pattern — endpoints register on `router = APIRouter(prefix="/api")`):
```python
BASE_DIR = Path(__file__).parent.parent.parent
HOURLY_PARQUET = BASE_DIR / "data" / "baseline" / "hourly_aggregated.parquet"
DAILY_PARQUET = BASE_DIR / "data" / "baseline" / "daily_aggregated.parquet"

@router.get("/alerts/{alert_id}", response_model=AlertDetailResponse)
@limiter.limit("60/minute")
def get_alert(request: Request, alert_id: str, include_deprecated: bool = Query(False)):
    data = get_alert_by_id(alert_id, include_deprecated=include_deprecated)
    if data is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    # ... parses environment_split_json into dict on `data["environment_split"]`
    alert = AlertDetail(**data, events=events, interventions=interventions)
    return AlertDetailResponse(alert=alert)
```

From backend/api/schemas.py:65-90 (current AlertDetail — Wave 1 will add 2 fields after `deprecation_reason`):
```python
class AlertDetail(BaseModel):
    # ... existing fields ...
    deprecated: bool = False
    deprecation_reason: Optional[str] = None
    events: list[AlertEvent] = []
    assignment: Optional[dict] = None
    interventions: list = []
    # ADD HERE (Plan 02):
    # baseline_bacino: Optional[int] = None
    # baseline_coverage: Optional[float] = None
```

CSV path (verified — repo-relative):
```
data/sentinel_db/daily_kpi.csv
columns: row_id, date, ad_unit_id_1, environment, country_criteria_id, channel_group,
         revenue_gross, impressions, measurable_impressions, viewable_impressions,
         clicks, ctr, viewability, ecpm
```

Channel whitelist (verified from backend/db/models.py CHANNEL_GROUP_CHECK_VALUES + sell_type_proxy.yaml):
```
GOOGLE_ADEX, OPEN_BIDDING, HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC,
TAM, DIRECT, DEAL, GOOGLE (legacy alias)
```

PBI bounds (must satisfy):
- Lower = €26,656.00 (= 27200 × 0.98)
- Upper = €27,744.00 (= 27200 × 1.02)
- Verified raw CSV value: €27,245.63 → +0.17% from target → inside bounds ✅

Aggregation formula (RESEARCH §6, copied verbatim):
```python
def _compute_baseline_from_env_split(environment_split_json) -> tuple[Optional[int], Optional[float]]:
    if not environment_split_json:
        return None, None
    try:
        env = json.loads(environment_split_json) if isinstance(environment_split_json, str) else environment_split_json
    except (json.JSONDecodeError, TypeError):
        return None, None
    env_entries = {k: v for k, v in env.items() if isinstance(v, dict)}
    if not env_entries:
        return None, None
    total_bacino = sum(v.get("bacino_baseline", 0) for v in env_entries.values())
    coverages = [v["coverage_baseline"] for v in env_entries.values()
                 if v.get("coverage_baseline") is not None]
    avg_coverage = sum(coverages) / len(coverages) if coverages else None
    return (int(total_bacino) if total_bacino > 0 else None,
            float(avg_coverage) if avg_coverage is not None else None)
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add NetworkTotalsResponse + AlertDetail extension to schemas.py</name>
  <files>backend/api/schemas.py</files>
  <read_first>
    - backend/api/schemas.py (current file in full — must preserve existing models)
    - .planning/phases/11-network-totals-endpoint-filter-api-server-side-baseline/11-RESEARCH.md (§4 NetworkTotalsResponse spec, §6 AlertDetail extension)
    - .planning/phases/11-network-totals-endpoint-filter-api-server-side-baseline/11-VALIDATION.md (verify rows binding to these models)
    - scripts/test_network_totals_pbi_parity.py (asserts response shape)
    - scripts/test_alert_baseline_fields.py (asserts top-level fields)
  </read_first>
  <behavior>
    - Test 1: Importing `NetworkTotalsResponse` from `backend.api.schemas` succeeds.
    - Test 2: `NetworkTotalsResponse(date="2026-01-12", channel="GOOGLE_ADEX", revenue_gross=27245.63, revenue_net=None, impressions=14009820, measurable_impressions=10000000, currency="EUR", source_date="2026-01-12", source="data/sentinel_db/daily_kpi.csv").model_dump()` returns dict with all 9 keys.
    - Test 3: `NetworkTotalsResponse(date="bad", channel="GOOGLE_ADEX", revenue_gross=1, impressions=1, currency="EUR", source_date="2026-01-12", source="x")` raises ValidationError due to date pattern (`YYYY-MM-DD`).
    - Test 4: `NetworkTotalsResponse(...)` with `revenue_gross=-1.0` raises ValidationError (`ge=0`).
    - Test 5: `AlertDetail` has `baseline_bacino: Optional[int]` defaulting to None.
    - Test 6: `AlertDetail` has `baseline_coverage: Optional[float]` defaulting to None.
    - Test 7: Existing AlertDetail tests pass (backward compat — fields are Optional, no breakage).
  </behavior>
  <action>
Open `backend/api/schemas.py`. Make TWO additions (no removals, no field reordering of existing models):

**Addition 1** — append a new model after `BacktestResultResponse` (line ~143) and before `TrendPoint` (line ~144). Use exact code:

```python
# ---------------------------------------------------------------------------
# Phase 11 API-01 — Network Totals Endpoint (PBI parity)
# ---------------------------------------------------------------------------

class NetworkTotalsResponse(BaseModel):
    """PBI-comparable totals for a single (date, channel) tuple.

    Phase 11 API-01 — RC-(a) closure. Reads raw `data/sentinel_db/daily_kpi.csv`
    upstream (bypasses the parquet top-50 filter that strips €4,221 from
    Jan 12 GOOGLE_ADEX gross revenue per AUDIT-A-NUMBERS-FORENSICS.md Bug3).
    """
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$",
                      description="ISO date YYYY-MM-DD")
    channel: str = Field(..., min_length=1, max_length=64,
                         description="channel_group or sell_type_proxy literal")
    revenue_gross: float = Field(..., ge=0,
                                 description="Gross revenue (pre-rev-share) in EUR")
    revenue_net: Optional[float] = Field(None, ge=0,
                                         description="Net revenue (post 60% rev-share) — None for Phase 11")
    impressions: int = Field(..., ge=0)
    measurable_impressions: Optional[int] = Field(None, ge=0)
    currency: str = Field("EUR", pattern=r"^[A-Z]{3}$")
    source_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$",
                             description="Last date present in source CSV (freshness signal)")
    source: str = Field("data/sentinel_db/daily_kpi.csv",
                        description="Origin file — proves API bypassed parquet top-50 filter")
```

Required import: ensure `Field` is imported alongside `BaseModel` at the top — `from pydantic import BaseModel, Field`. If `Field` already imported, no-op.

**Addition 2** — extend `AlertDetail` (line ~65). Add EXACTLY 2 lines AFTER the `deprecation_reason: Optional[str] = None` line and BEFORE the `events: list[AlertEvent] = []` line:

```python
    # Phase 11 API-03 — server-side baseline (kills TriageSection.tsx:29-32 heuristic). Optional for backward compat with deprecated alerts / empty env_split.
    baseline_bacino: Optional[int] = None
    baseline_coverage: Optional[float] = None
```

DO NOT modify any other field. DO NOT reorder. DO NOT change `AlertSummary` (only `AlertDetail`).

**Required import check:** `Optional` already imported (used by other fields).

Run `python -c "from backend.api.schemas import NetworkTotalsResponse, AlertDetail; print(NetworkTotalsResponse.model_fields.keys()); print('baseline_bacino' in AlertDetail.model_fields)"` to smoke-check.
  </action>
  <verify>
    <automated>.venv/bin/python -c "from backend.api.schemas import NetworkTotalsResponse, AlertDetail; assert 'baseline_bacino' in AlertDetail.model_fields; assert 'baseline_coverage' in AlertDetail.model_fields; assert {'date','channel','revenue_gross','revenue_net','impressions','measurable_impressions','currency','source_date','source'} &lt;= set(NetworkTotalsResponse.model_fields.keys()); print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "class NetworkTotalsResponse" backend/api/schemas.py` returns 1.
    - `grep -c "baseline_bacino: Optional\[int\] = None" backend/api/schemas.py` returns 1.
    - `grep -c "baseline_coverage: Optional\[float\] = None" backend/api/schemas.py` returns 1.
    - `grep -c "from pydantic import BaseModel, Field" backend/api/schemas.py` returns 1 (Field import present).
    - `.venv/bin/python -c "from backend.api.schemas import NetworkTotalsResponse, AlertDetail"` exits 0.
    - `.venv/bin/python -c "from pydantic import ValidationError; from backend.api.schemas import NetworkTotalsResponse; import sys; sys.exit(0 if NetworkTotalsResponse(date='2026-01-12', channel='GOOGLE_ADEX', revenue_gross=27245.63, impressions=14009820, source_date='2026-01-12').model_dump()['currency']=='EUR' else 1)"` exits 0.
    - `.venv/bin/python -c "from pydantic import ValidationError; from backend.api.schemas import NetworkTotalsResponse; \ntry:\n    NetworkTotalsResponse(date='bad', channel='X', revenue_gross=1, impressions=1, source_date='2026-01-12')\n    raise SystemExit(1)\nexcept ValidationError:\n    raise SystemExit(0)"` exits 0 (date pattern rejected).
  </acceptance_criteria>
  <done>schemas.py extended with NetworkTotalsResponse + 2 baseline fields on AlertDetail; existing tests still importable; Pydantic validators reject malformed payloads.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement /api/metrics/network-totals endpoint (API-01) in routes.py</name>
  <files>backend/api/routes.py</files>
  <read_first>
    - backend/api/routes.py (current file in full — see existing endpoint patterns at lines 599-728 for `/metrics/revenue-status-24h` shape)
    - backend/api/schemas.py (NetworkTotalsResponse just added in Task 1)
    - .planning/phases/11-network-totals-endpoint-filter-api-server-side-baseline/11-RESEARCH.md (§4 design + §9 R1 OOM mitigation)
    - scripts/test_network_totals_pbi_parity.py (asserts the contract)
    - scripts/etl_csv_to_parquet.py:160-180 (existing pyarrow/pandas chunked CSV pattern)
    - data/sentinel_db/daily_kpi.csv (header — column names verbatim)
  </read_first>
  <behavior>
    - Test 1: `GET /api/metrics/network-totals?date=2026-01-12&channel=GOOGLE_ADEX` returns 200 + JSON with `revenue_gross` in [26656, 27744] (PBI ±2%). Verified target: €27,245.63.
    - Test 2: `GET ...?date=2099-01-01&channel=GOOGLE_ADEX` returns 404 (date out of CSV range).
    - Test 3: `GET ...?date=not-a-date&channel=GOOGLE_ADEX` returns 400 or 422 (pattern rejection).
    - Test 4: `GET ...?channel=GOOGLE_ADEX` (no date) returns 400 or 422 (missing required param).
    - Test 5: `GET ...?date=2026-01-12&channel=INVALID_CHANNEL` returns 400 (whitelist rejection).
    - Test 6: Response includes `currency: "EUR"`, `source: "data/sentinel_db/daily_kpi.csv"`, `source_date` from CSV max(date).
    - Test 7: Endpoint is rate-limited (60/minute, matching `/metrics` pattern).
    - Test 8: Endpoint enforces `require_auth` via existing FastAPI dependency stack (no special handling — auth already applied app-wide; `ENVIRONMENT=development` bypasses in tests).
  </behavior>
  <action>
Open `backend/api/routes.py`.

**Add imports** at the top (with the other imports, alphabetical-ish):
```python
from typing import Optional
import pyarrow.csv as pa_csv
import pyarrow.compute as pc
import pyarrow as pa
from backend.api.schemas import (
    ..., NetworkTotalsResponse,  # Phase 11 API-01
)
```
Add `NetworkTotalsResponse` to the existing `from backend.api.schemas import (...)` block (lines 15-41) — preserve alphabetical-ish order; do NOT add a duplicate import block.

**Add module-level constants** near `HOURLY_PARQUET` / `DAILY_PARQUET` (after line 82):
```python
# Phase 11 API-01 — raw CSV upstream (bypasses parquet top-50 filter for PBI parity)
KPI_CSV_PATH = BASE_DIR / "data" / "sentinel_db" / "daily_kpi.csv"
NETWORK_TOTALS_CHANNELS = {
    "GOOGLE_ADEX", "OPEN_BIDDING", "HEADER_BIDDING_MAGNITE",
    "HEADER_BIDDING_PUBMATIC", "TAM", "DIRECT", "DEAL", "GOOGLE",  # legacy alias
}
_kpi_csv_cache: Optional[pa.Table] = None
_kpi_csv_max_date: Optional[str] = None
```

**Add the helper** before `@router.get("/alerts", ...)` (around line 110):
```python
def _load_kpi_csv() -> Optional[pa.Table]:
    """Load daily_kpi.csv with column projection. Cached in-process."""
    global _kpi_csv_cache, _kpi_csv_max_date
    if _kpi_csv_cache is not None:
        return _kpi_csv_cache
    if not KPI_CSV_PATH.exists():
        logger.warning("daily_kpi.csv not found at %s", KPI_CSV_PATH)
        return None
    try:
        # Column projection: read only what we need for network-totals
        convert_opts = pa_csv.ConvertOptions(
            include_columns=["date", "channel_group", "revenue_gross",
                             "impressions", "measurable_impressions"],
            column_types={
                "revenue_gross": pa.float64(),
                "impressions": pa.int64(),
                "measurable_impressions": pa.int64(),
            },
        )
        read_opts = pa_csv.ReadOptions(block_size=64 * 1024 * 1024)
        tbl = pa_csv.read_csv(str(KPI_CSV_PATH),
                              read_options=read_opts,
                              convert_options=convert_opts)
        _kpi_csv_cache = tbl
        # Compute max date once (used for 404 range check + freshness signal)
        max_date_arr = pc.max(tbl["date"])
        _kpi_csv_max_date = str(max_date_arr.as_py()) if max_date_arr.is_valid else None
        logger.info("Loaded daily_kpi.csv: %d rows, max_date=%s",
                    tbl.num_rows, _kpi_csv_max_date)
        return tbl
    except Exception as e:
        logger.error("Failed to load daily_kpi.csv: %s", e)
        return None
```

**Add the endpoint** at the end of the file (after the last existing endpoint, before any module-level `if __name__`):

```python
@router.get("/metrics/network-totals", response_model=NetworkTotalsResponse)
@limiter.limit("60/minute")
def network_totals(
    request: Request,
    date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$",
                      description="ISO date YYYY-MM-DD"),
    channel: str = Query(..., min_length=1, max_length=64),
):
    """Phase 11 API-01 — PBI-parity totals from raw daily_kpi.csv (bypasses top-50 parquet filter).

    Closes RC-(a) for the email Vito 2026-04-22 #2/#3 lamentele.
    Verified: Jan 12 GOOGLE_ADEX revenue_gross = €27,245.63 (PBI €27,200 +0.17%).
    """
    # Whitelist channel (per backend/db/models.py CHANNEL_GROUP_CHECK_VALUES)
    if channel not in NETWORK_TOTALS_CHANNELS:
        raise HTTPException(
            status_code=400,
            detail=f"channel must be one of {sorted(NETWORK_TOTALS_CHANNELS)}; got {channel!r}",
        )

    tbl = _load_kpi_csv()
    if tbl is None:
        raise HTTPException(status_code=503, detail="daily_kpi.csv not available")

    # 404 if date outside CSV range (uses cached max_date)
    if _kpi_csv_max_date is None or date > _kpi_csv_max_date:
        raise HTTPException(
            status_code=404,
            detail=f"date {date} out of CSV range (max available: {_kpi_csv_max_date})",
        )

    # Filter pushdown: date == target AND channel_group == target
    mask = pc.and_(
        pc.equal(tbl["date"], date),
        pc.equal(tbl["channel_group"], channel),
    )
    filtered = tbl.filter(mask)
    if filtered.num_rows == 0:
        raise HTTPException(
            status_code=404,
            detail=f"no rows for date={date} channel={channel}",
        )

    revenue_gross = float(pc.sum(filtered["revenue_gross"]).as_py() or 0.0)
    impressions = int(pc.sum(filtered["impressions"]).as_py() or 0)
    measurable_raw = pc.sum(filtered["measurable_impressions"]).as_py()
    measurable_impressions = int(measurable_raw) if measurable_raw is not None else None

    return NetworkTotalsResponse(
        date=date,
        channel=channel,
        revenue_gross=round(revenue_gross, 2),
        revenue_net=None,  # Phase 13 CORR-03 will add net via revenue_share.yaml
        impressions=impressions,
        measurable_impressions=measurable_impressions,
        currency="EUR",
        source_date=_kpi_csv_max_date,
        source="data/sentinel_db/daily_kpi.csv",
    )
```

**Constraints (per RESEARCH §9 risk register):**
- DO NOT use `pd.read_csv` without column projection (R1 OOM mitigation).
- DO NOT interpolate user input into file paths (R-04 / V5 path traversal).
- DO NOT hit the parquet (this endpoint EXISTS to bypass it).
- DO NOT compute net revenue (Phase 13 scope per RESEARCH §8 OQ5).
- DO NOT add a date range query (single date only — DoS mitigation R1).
- DO NOT modify the cache invalidation strategy beyond load-once (RESEARCH §4 — bassa frequenza endpoint).

The endpoint must be reachable at `GET /api/metrics/network-totals` (since router has `prefix="/api"` and the route registers `/metrics/network-totals`).
  </action>
  <verify>
    <automated>.venv/bin/python scripts/test_network_totals_pbi_parity.py</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c '@router.get("/metrics/network-totals"' backend/api/routes.py` returns 1.
    - `grep -c "def network_totals" backend/api/routes.py` returns 1.
    - `grep -c "KPI_CSV_PATH" backend/api/routes.py` returns ≥3 (constant + helper + endpoint).
    - `grep -c "import pyarrow.csv as pa_csv" backend/api/routes.py` returns 1.
    - `grep -c "include_columns" backend/api/routes.py` returns 1 (column projection — R1 OOM mitigation).
    - `grep -c "NETWORK_TOTALS_CHANNELS" backend/api/routes.py` returns ≥2.
    - `.venv/bin/python scripts/test_network_totals_pbi_parity.py` exits 0 (all 4 RED tests now GREEN).
    - `.venv/bin/python -c "from backend.main import app; from fastapi.testclient import TestClient; import os; os.environ['ENVIRONMENT']='development'; c = TestClient(app); r = c.get('/api/metrics/network-totals?date=2026-01-12&channel=GOOGLE_ADEX'); assert r.status_code == 200; b = r.json(); assert 26656 <= b['revenue_gross'] <= 27744, f'got {b[\"revenue_gross\"]}'; print(f'PBI parity OK: gross={b[\"revenue_gross\"]}')"` exits 0 and prints a value in [26656, 27744].
    - Channel whitelist enforced: `c.get('/api/metrics/network-totals?date=2026-01-12&channel=BOGUS').status_code == 400`.
  </acceptance_criteria>
  <done>API-01 GREEN: PBI parity within 2% (target Jan 12 GOOGLE_ADEX gross €27,200), 400/404 error contracts honored, no parquet read, no `pd.read_csv` full-load.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Wire on-the-fly baseline aggregation in get_alert handler (API-03)</name>
  <files>backend/api/routes.py</files>
  <read_first>
    - backend/api/routes.py:148-181 (current `get_alert` handler — JSON blob parse pattern at lines 165-175)
    - backend/api/schemas.py (AlertDetail extended in Task 1 of this plan)
    - backend/db/operations.py:140-170 (get_alert_by_id — returns dict with `environment_split_json` key, NOT the parsed dict — parsing happens in routes.py)
    - .planning/phases/11-network-totals-endpoint-filter-api-server-side-baseline/11-RESEARCH.md (§6 Opzione A + helper code verbatim)
    - scripts/test_alert_baseline_fields.py (asserts the 5 contract conditions)
  </read_first>
  <behavior>
    - Test 1: `GET /api/alerts/{id}` for a non-deprecated alert with environment_split_json returns top-level `baseline_bacino` (int > 0) and `baseline_coverage` (float in [0,1]).
    - Test 2: For ALT-20260123-010000-P2 specifically (verified live), `baseline_bacino == sum(env[k]['bacino_baseline'] for k in env)`. Expected per RESEARCH §6: ~171503.
    - Test 3: `baseline_coverage` ≠ avg_coverage_current + 0.05 (regression — kills the heuristic).
    - Test 4: For deprecated alerts (`include_deprecated=true`), both fields are None.
    - Test 5: For alerts where environment_split_json is empty/malformed, both fields are None — no panic, HTTP 200.
    - Test 6: AlertSummary (list endpoint `/api/alerts`) is UNCHANGED — no baseline fields on summary (out-of-scope per Phase 11).
  </behavior>
  <action>
Open `backend/api/routes.py`.

**Add helper function** in the module-level helpers section (after `_load_hourly_data` and `_load_kpi_csv`, before `@router.get("/alerts", ...)`):

```python
def _compute_baseline_from_env_split(
    environment_split_json,
) -> tuple[Optional[int], Optional[float]]:
    """Phase 11 API-03 — aggregate baseline_bacino + baseline_coverage from env_split JSON blob.

    Replaces TriageSection.tsx:29-32 client-side heuristic
    (`revenueRatio*0.95` + `avgCoverage+0.05`) with the real values
    that data_fetcher_real.py:142-260 already computed at alert
    creation time. Returns (None, None) for empty / malformed blobs
    (deprecated alerts, legacy pre-v1.2 alerts) — no panic.

    R-13 contract: Pure function, no I/O, no side effects.
    """
    if not environment_split_json:
        return None, None
    try:
        env = (json.loads(environment_split_json)
               if isinstance(environment_split_json, str)
               else environment_split_json)
    except (json.JSONDecodeError, TypeError):
        return None, None
    if not isinstance(env, dict):
        return None, None
    env_entries = {k: v for k, v in env.items() if isinstance(v, dict)}
    if not env_entries:
        return None, None
    total_bacino = sum(
        v.get("bacino_baseline", 0) or 0 for v in env_entries.values()
    )
    coverages = [
        v["coverage_baseline"]
        for v in env_entries.values()
        if v.get("coverage_baseline") is not None
    ]
    avg_coverage = sum(coverages) / len(coverages) if coverages else None
    return (
        int(total_bacino) if total_bacino > 0 else None,
        float(avg_coverage) if avg_coverage is not None else None,
    )
```

**Modify `get_alert` handler** (lines 148-181). After the existing JSON-blob parsing loop (line 165-175 ends with `data[obj_field] = ...`) and BEFORE the line `data["deprecated"] = bool(data.get("deprecated", 0))`, INSERT:

```python
    # Phase 11 API-03 — compute server-side baseline. We RE-READ the original
    # JSON string (not the already-parsed `data["environment_split"]` dict),
    # because get_alert_by_id() returns the raw blob in `environment_split_json`.
    # NOTE: by this point environment_split_json was already popped from `data`
    # via `raw = data.pop(json_field, ...)` for json_field == "environment_split_json".
    # We use the parsed dict directly via data["environment_split"].
    baseline_bacino, baseline_coverage = _compute_baseline_from_env_split(
        data.get("environment_split", {})
    )
    data["baseline_bacino"] = baseline_bacino
    data["baseline_coverage"] = baseline_coverage
```

**Critical:** since the existing loop pops `environment_split_json` and parses it into `data["environment_split"]` (already a dict), pass the already-parsed dict (not the raw string) to the helper. The helper accepts both via the `isinstance(environment_split_json, str)` branch — verified.

DO NOT modify `AlertSummary` or the `/api/alerts` list endpoint — Phase 11 ships baseline ONLY on the detail endpoint per VALIDATION row "API-03 ... `GET /api/alerts/{alert_id}`".

DO NOT add a DB migration. The values are computed on-the-fly at request time per RESEARCH §6 Opzione A. (Phase 18 HARD-04 may persist them later if contract tests demand.)

DO NOT change `get_alert_by_id` in `backend/db/operations.py` — Phase 11 keeps the DB read path stable; the aggregation lives in the API layer.
  </action>
  <verify>
    <automated>.venv/bin/python scripts/test_alert_baseline_fields.py</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def _compute_baseline_from_env_split" backend/api/routes.py` returns 1.
    - `grep -c "baseline_bacino, baseline_coverage = _compute_baseline_from_env_split" backend/api/routes.py` returns 1.
    - `grep -c 'data\["baseline_bacino"\] = baseline_bacino' backend/api/routes.py` returns 1.
    - `grep -c 'data\["baseline_coverage"\] = baseline_coverage' backend/api/routes.py` returns 1.
    - `.venv/bin/python -c "from backend.api.routes import _compute_baseline_from_env_split; assert _compute_baseline_from_env_split(None) == (None, None); assert _compute_baseline_from_env_split('{}') == (None, None); assert _compute_baseline_from_env_split('{\"WEB\":{\"bacino_baseline\":100,\"coverage_baseline\":0.8}}') == (100, 0.8); print('OK')"` exits 0.
    - `.venv/bin/python scripts/test_alert_baseline_fields.py` exits 0 (all 5 RED tests now GREEN).
    - `grep -c "AlertSummary" backend/api/schemas.py` unchanged from current count (regression: list endpoint unchanged).
  </acceptance_criteria>
  <done>API-03 GREEN: baseline_bacino + baseline_coverage exposed top-level on AlertDetail, computed from env_split via pure function, deprecated alerts return None gracefully, regression test confirms server-side ≠ heuristic.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| HTTP client → /api/metrics/network-totals | User-supplied `date` and `channel` query params cross into pyarrow CSV filter |
| HTTP client → /api/alerts/{id} | `alert_id` path param → SQLite parameterized query (existing pattern, unchanged) |
| filesystem → daily_kpi.csv | Read-only access to ~500MB CSV; cached in-process after first load |
| Pydantic → JSON response | Output sanitization layer — NetworkTotalsResponse + AlertDetail whitelist response fields |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-11-02-01 | Tampering | network_totals — `date` query param | medium | mitigate | Pydantic-level Query pattern `^\d{4}-\d{2}-\d{2}$` rejects path traversal / control chars. `date` is NEVER interpolated into file paths — only used as pyarrow filter operand on `tbl["date"]` column. KPI_CSV_PATH is a hardcoded `Path` constant. |
| T-11-02-02 | Tampering | network_totals — `channel` query param | medium | mitigate | Whitelist set `NETWORK_TOTALS_CHANNELS` (8 values from `backend/db/models.py`). Anything outside → HTTP 400. No string interpolation into queries. |
| T-11-02-03 | DoS | network_totals — full CSV materialization | high | mitigate | (1) Column projection via `include_columns=[...]` (5 of 14 cols only — RESEARCH §9 R1). (2) Cache loaded once per process. (3) `block_size=64MB` bounded read. (4) `@limiter.limit("60/minute")` per-IP rate limit. (5) Single date only — no range query → no quadratic blow-up. |
| T-11-02-04 | DoS | network_totals — repeated cache miss under concurrency | low | accept | First load is ~3s; subsequent requests hit `_kpi_csv_cache` global. Single-writer SQLite + single-process uvicorn (production constraint). Race window negligible. |
| T-11-02-05 | Information Disclosure | NetworkTotalsResponse | low | mitigate | Response Pydantic model whitelists exactly 9 fields — raw CSV rows never leak. `source` field discloses path (`data/sentinel_db/daily_kpi.csv`) but the path is documented in RESEARCH and PROJECT.md — operational transparency, not a secret. |
| T-11-02-06 | Information Disclosure | get_alert with baseline aggregation | low | accept | Aggregation reveals only summary statistics already implicit in the alert's `environment_split_json` blob (which is itself returned in the response). No new data exposure. |
| T-11-02-07 | Denial | malformed `environment_split_json` panics `_compute_baseline_from_env_split` | low | mitigate | Try/except around `json.loads`; isinstance guards on every dict access; returns `(None, None)` on any failure path. Pydantic `Optional[int]/Optional[float]` accepts None. |
| T-11-02-08 | Spoofing / AuthN | both endpoints | medium | mitigate | Existing `require_auth` dependency in `backend/main.py` covers all `/api/*` routes (per Phase 09 audit). New endpoints inherit. ENVIRONMENT=development bypass scoped to TestClient suite. |
| T-11-02-09 | Elevation of Privilege | None — both endpoints are read-only | n/a | n/a | Zero DB writes, zero filesystem writes, zero state mutation. |
| T-11-02-10 | Tampering | path traversal via `KPI_CSV_PATH` | low | mitigate | `KPI_CSV_PATH = BASE_DIR / "data" / "sentinel_db" / "daily_kpi.csv"` — pure `Path` constant, no user input ever joined to BASE_DIR for this endpoint. |

No `high` threats remain post-mitigation. ASVS L1 satisfied: V2 (auth via existing middleware), V5 (input validation via Pydantic Query patterns + whitelist).
</threat_model>

<verification>
After all 3 tasks complete:

```bash
# Wave 0 RED tests must now be GREEN:
.venv/bin/python scripts/test_network_totals_pbi_parity.py    # exit 0
.venv/bin/python scripts/test_alert_baseline_fields.py        # exit 0

# Adjacent tests must still be GREEN (no regression):
.venv/bin/python scripts/test_health_alerts_pipeline.py       # exit 0
.venv/bin/python scripts/test_models_sync.py                  # exit 0 (HARD-03 drift gate)

# Full Phase 11 + adjacent suite (per VALIDATION §sampling rate):
.venv/bin/python -m pytest scripts/test_network_totals_pbi_parity.py scripts/test_alert_baseline_fields.py scripts/test_health_alerts_pipeline.py -v
```

Manual smoke (see VALIDATION §manual-only):
```bash
curl 'http://localhost:8000/api/metrics/network-totals?date=2026-01-12&channel=GOOGLE_ADEX'
# expect: 200 + revenue_gross in [26656, 27744]

curl 'http://localhost:8000/api/alerts/<some-non-deprecated-id>'
# expect: 200 + alert.baseline_bacino: int, alert.baseline_coverage: float
```
</verification>

<success_criteria>
1. **API-01 GREEN:** `scripts/test_network_totals_pbi_parity.py` exits 0; live `/api/metrics/network-totals?date=2026-01-12&channel=GOOGLE_ADEX` returns `revenue_gross` in [26656, 27744].
2. **API-03 GREEN:** `scripts/test_alert_baseline_fields.py` exits 0; live `/api/alerts/{non-deprecated-id}` includes `baseline_bacino` (int) and `baseline_coverage` (float).
3. **No regression:** `scripts/test_health_alerts_pipeline.py` and `scripts/test_models_sync.py` still GREEN.
4. **No DB migration:** `git diff backend/db/` shows ZERO changes (Opzione A — on-the-fly compute).
5. **No `pd.read_csv` full-load:** `grep "pd\\.read_csv" backend/api/routes.py` shows ZERO new occurrences (only pyarrow column-projected reads).
6. **AlertSummary unchanged:** `git diff backend/api/schemas.py` shows additions ONLY to `AlertDetail` and a new `NetworkTotalsResponse` model.
</success_criteria>

<output>
After completion, create `.planning/phases/11-network-totals-endpoint-filter-api-server-side-baseline/11-02-SUMMARY.md` per template.

Atomic commits (per R-03 + R-06):
- Commit 1 after Task 1: `feat(11-02): add NetworkTotalsResponse + baseline fields to AlertDetail (API-01/API-03 schema)`
- Commit 2 after Task 2: `feat(11-02): /api/metrics/network-totals endpoint reads raw daily_kpi.csv (API-01)`
- Commit 3 after Task 3: `feat(11-02): on-the-fly baseline aggregation in get_alert handler (API-03)`

Per R-05: do NOT push. Local commits only. Stop at "ready for OK to deploy".
</output>
