---
phase: 11-network-totals-endpoint-filter-api-server-side-baseline
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - scripts/test_network_totals_pbi_parity.py
  - scripts/test_sell_type_filter.py
  - scripts/test_alert_baseline_fields.py
autonomous: true
requirements: [API-01, API-02, API-03]

must_haves:
  truths:
    - "Test `test_network_totals_pbi_parity.py` exists, is invocable, and FAILS today (endpoint missing — proves the test is wired)."
    - "Test `test_sell_type_filter.py` exists, is invocable, and FAILS today (sell_type query param not yet accepted)."
    - "Test `test_alert_baseline_fields.py` exists, is invocable, and FAILS today (baseline_bacino/baseline_coverage not yet exposed)."
    - "All 3 test files import `from backend.main import app` and use `fastapi.testclient.TestClient` per Phase 10 pattern."
    - "Each test file is self-contained, exits with non-zero status on RED."
  artifacts:
    - path: "scripts/test_network_totals_pbi_parity.py"
      provides: "API-01 PBI-parity assertion: GOOGLE_ADEX 2026-01-12 revenue_gross within ±2% of €27,200; date validation 400; out-of-range 404."
      contains: "PBI_TARGET_GROSS"
    - path: "scripts/test_sell_type_filter.py"
      provides: "API-02 filter assertion: ?sell_type=Open_Market returns only rows with sell_type_proxy=Open_Market; invalid value 400; missing column 503."
      contains: "Open_Market"
    - path: "scripts/test_alert_baseline_fields.py"
      provides: "API-03 schema assertion: AlertDetail has top-level baseline_bacino + baseline_coverage; deprecated alert returns None; baseline_coverage ≠ avgCoverage+0.05."
      contains: "baseline_bacino"
  key_links:
    - from: "scripts/test_network_totals_pbi_parity.py"
      to: "backend.main.app"
      via: "TestClient(app).get('/api/metrics/network-totals?...')"
      pattern: "TestClient"
    - from: "scripts/test_sell_type_filter.py"
      to: "backend.main.app"
      via: "TestClient(app).get('/api/publishers/top?sell_type=...')"
      pattern: "TestClient"
    - from: "scripts/test_alert_baseline_fields.py"
      to: "backend.main.app"
      via: "TestClient(app).get('/api/alerts/{alert_id}')"
      pattern: "TestClient"
---

<objective>
Author the 3 Nyquist test scripts called for in `11-VALIDATION.md` BEFORE any production-code change. Tests must FAIL today (RED) — proving they truly bind to behavior that does not yet exist. Wave 1 implementations will turn them GREEN (per Plan 02 and Plan 03).

Purpose: Closes the Nyquist gate. Per `11-VALIDATION.md`, Wave 0 is mandatory for nyquist_compliant=true. Per `~/.claude/CLAUDE.md` R-13 (production-grade) and the project rule "Wave 0 must author tests BEFORE implementation".

Output: 3 new test scripts under `scripts/` invocable as `.venv/bin/python scripts/test_*.py`. Each is RED on this commit, GREEN after Wave 1.

Phase 11 explicitly defers: TriageSection.tsx wiring (Phase 12+), `/api/alerts` sell_type filter (Phase 12 — see RESEARCH §8 OQ1), Vercel deploy (operator-gated, R-04/R-05).
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
@scripts/test_health_alerts_pipeline.py
@scripts/test_mondadori_fill_rate_regression.py
@backend/api/schemas.py
@backend/api/routes.py
@backend/api/publisher_routes.py
@config/sell_type_proxy.yaml
@data/sentinel_db/daily_kpi.csv

<interfaces>
<!-- Reference contracts the executor needs. Tests must bind to these BEFORE Wave 1 implementation lands them. -->

From scripts/test_health_alerts_pipeline.py (canonical TestClient pattern to copy):
```python
import os, sys, unittest
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
os.environ["ENVIRONMENT"] = "development"  # bypass auth in tests
from fastapi.testclient import TestClient
from backend.main import app

class TestX(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

if __name__ == "__main__":
    unittest.main()
```

From backend/api/schemas.py (current AlertDetail — Wave 1 Plan 02 will extend):
```python
class AlertDetail(BaseModel):
    alert_id: str
    timestamp: str
    severity: str
    channel_group: str
    status: str
    alert_rule: str
    revenue_current: float
    revenue_baseline: float
    revenue_delta_pct: float
    triage_label: str
    contributors: list = []
    geo_breakdown: list = []
    environment_split: dict = {}
    insights: dict = {}
    execution_time_sec: float
    data_source: str
    config_version: str
    created_at: str
    updated_at: str
    deprecated: bool = False
    deprecation_reason: Optional[str] = None
    events: list[AlertEvent] = []
    assignment: Optional[dict] = None
    interventions: list = []
    # Wave 1 Plan 02 will ADD:
    # baseline_bacino: Optional[int] = None
    # baseline_coverage: Optional[float] = None
```

From data/sentinel_db/daily_kpi.csv (header verified live):
```
row_id, date, ad_unit_id_1, environment, country_criteria_id, channel_group,
revenue_gross, impressions, measurable_impressions, viewable_impressions,
clicks, ctr, viewability, ecpm
```

From config/sell_type_proxy.yaml (canonical mapping — verbatim):
```yaml
Open_Market: [GOOGLE_ADEX, OPEN_BIDDING, GOOGLE]
Header_Bidding: [HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC]
Direct: [DIRECT]
Deal: [DEAL]
Other: [TAM]
```

PBI target verified live in research §4: raw CSV Jan 12 GOOGLE_ADEX revenue_gross = €27,245.63 → ±2% of €27,200 = [€26,656, €27,744].

API-01 endpoint contract (Wave 1 Plan 02 will implement):
```
GET /api/metrics/network-totals?date=YYYY-MM-DD&channel=<CHANNEL_GROUP>
Response 200: {"date": "2026-01-12", "channel": "GOOGLE_ADEX",
                "revenue_gross": 27245.63, "revenue_net": null,
                "impressions": 14009820, "measurable_impressions": <int>,
                "currency": "EUR", "source": "data/sentinel_db/daily_kpi.csv"}
Response 400 on bad date format / missing param
Response 404 on date outside CSV range
Response 503 on CSV unreadable
```

API-02 endpoint contract (Wave 1 Plan 03 will implement):
```
GET /api/publishers/top?year=<int>&sell_type=<Open_Market|Header_Bidding|Direct|Deal|Other>
Filters df_year by sell_type_proxy column == query value before aggregation.
Adds "sell_type_filter" key in response payload for transparency.
Response 400 on invalid sell_type literal
Response 503 if parquet missing sell_type_proxy column
```

API-03 contract (Wave 1 Plan 02 will implement on-the-fly per RESEARCH §6 Opzione A — NO DB migration):
```
GET /api/alerts/{alert_id} returns AlertDetail with NEW top-level fields:
  baseline_bacino: Optional[int]    (sum of bacino_baseline across env_split entries)
  baseline_coverage: Optional[float] (mean of coverage_baseline across env_split entries with non-None coverage_baseline)
For non-deprecated alerts with environment_split_json: both non-None.
For deprecated alerts or empty env_split: both None.
For ALT-20260123-010000-P2 (verified live): baseline_bacino ≈ 171503, baseline_coverage ≈ 0.8161.
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Author scripts/test_network_totals_pbi_parity.py (API-01 RED)</name>
  <files>scripts/test_network_totals_pbi_parity.py</files>
  <read_first>
    - scripts/test_health_alerts_pipeline.py (TestClient pattern to mirror — sys.path, ENVIRONMENT, setUpClass)
    - scripts/test_mondadori_fill_rate_regression.py (PBI assertion + tolerance pattern)
    - .planning/phases/11-network-totals-endpoint-filter-api-server-side-baseline/11-RESEARCH.md (§4 API-01 design + §10 verify rows)
    - .planning/phases/11-network-totals-endpoint-filter-api-server-side-baseline/11-VALIDATION.md (per-task verification map rows for API-01)
    - data/sentinel_db/daily_kpi.csv (header — confirm column names verbatim)
    - backend/api/routes.py (confirm router prefix `/api` and FastAPI Query patterns)
  </read_first>
  <action>
Create new file `scripts/test_network_totals_pbi_parity.py`. Mirror the canonical pattern in `scripts/test_health_alerts_pipeline.py` (sys.path insert, `os.environ["ENVIRONMENT"] = "development"` to bypass `require_auth`, `TestClient(app)` in `setUpClass`). Use `unittest.TestCase` (not bare pytest functions — matches project convention for `scripts/test_*.py`).

Constants at module top, copied verbatim from research:
```python
PBI_TARGET_GROSS = 27200.0          # email Vito 2026-04-22, Jan 12 GOOGLE_ADEX
PBI_TOLERANCE_PCT = 0.02            # ±2% per ROADMAP Phase 11 SC#1
LOWER_BOUND = PBI_TARGET_GROSS * (1 - PBI_TOLERANCE_PCT)  # 26,656.00
UPPER_BOUND = PBI_TARGET_GROSS * (1 + PBI_TOLERANCE_PCT)  # 27,744.00
ENDPOINT_PATH = "/api/metrics/network-totals"
TARGET_DATE = "2026-01-12"
TARGET_CHANNEL = "GOOGLE_ADEX"
```

Author exactly these 4 test methods (all expected to FAIL today since the endpoint does not exist — Wave 1 Plan 02 will land it):

1. `test_pbi_parity_jan12_google_adex` — `resp = client.get(f"{ENDPOINT_PATH}?date={TARGET_DATE}&channel={TARGET_CHANNEL}")`; assert `resp.status_code == 200`; parse `body = resp.json()`; assert `LOWER_BOUND <= body["revenue_gross"] <= UPPER_BOUND` with f-string message including the actual value; assert `body["currency"] == "EUR"`; assert `body["channel"] == TARGET_CHANNEL`; assert `body["date"] == TARGET_DATE`.

2. `test_missing_date_returns_400` — `resp = client.get(f"{ENDPOINT_PATH}?channel={TARGET_CHANNEL}")`; assert `resp.status_code == 422` (FastAPI default for missing required Query) OR `400` (if endpoint custom-validates). Use `assertIn(resp.status_code, (400, 422))` to accept either valid implementation.

3. `test_malformed_date_returns_400` — `resp = client.get(f"{ENDPOINT_PATH}?date=not-a-date&channel={TARGET_CHANNEL}")`; assert `resp.status_code in (400, 422)`. Body must contain `"detail"`.

4. `test_date_out_of_csv_range_returns_404` — `resp = client.get(f"{ENDPOINT_PATH}?date=2099-01-01&channel={TARGET_CHANNEL}")`; assert `resp.status_code == 404`.

DO NOT call any pre-existing endpoint; DO NOT mutate the DB or CSV; DO NOT implement the endpoint. Tests should produce assertion failures when run — that is the RED state.

Add a `if __name__ == "__main__": unittest.main()` block at the end. Make file executable bit set (`os.chmod` not needed — `python scripts/test_*.py` is the canonical invocation pattern in this repo).

Add module docstring per project convention (see `test_mondadori_fill_rate_regression.py` for tone): "Phase 11 API-01 — Nyquist Wave 0 RED test for /api/metrics/network-totals PBI parity. Authored before implementation per VALIDATION contract. Expected RED until Plan 02 lands the endpoint."
  </action>
  <verify>
    <automated>.venv/bin/python scripts/test_network_totals_pbi_parity.py 2>&1 | tee /tmp/11-01-task1.log; grep -E "FAIL|ERROR|404|500|Not Found" /tmp/11-01-task1.log &gt; /dev/null; test $? -eq 0</automated>
  </verify>
  <acceptance_criteria>
    - File `scripts/test_network_totals_pbi_parity.py` exists.
    - `grep -c "PBI_TARGET_GROSS = 27200" scripts/test_network_totals_pbi_parity.py` returns ≥1.
    - `grep -c "PBI_TOLERANCE_PCT = 0.02" scripts/test_network_totals_pbi_parity.py` returns ≥1.
    - `grep -c "TestClient(app)" scripts/test_network_totals_pbi_parity.py` returns ≥1.
    - `grep -E "def test_(pbi_parity_jan12_google_adex|missing_date_returns_400|malformed_date_returns_400|date_out_of_csv_range_returns_404)" scripts/test_network_totals_pbi_parity.py | wc -l` returns 4.
    - `.venv/bin/python scripts/test_network_totals_pbi_parity.py` exits non-zero (RED — proves test binds to behavior that does not yet exist).
    - File contains string `"/api/metrics/network-totals"`.
    - `grep -c "if __name__" scripts/test_network_totals_pbi_parity.py` returns ≥1.
  </acceptance_criteria>
  <done>Test file authored, RED on current main, follows project pattern, asserts the exact PBI bounds [26656, 27744].</done>
</task>

<task type="auto">
  <name>Task 2: Author scripts/test_sell_type_filter.py (API-02 RED)</name>
  <files>scripts/test_sell_type_filter.py</files>
  <read_first>
    - scripts/test_health_alerts_pipeline.py (TestClient pattern)
    - .planning/phases/11-network-totals-endpoint-filter-api-server-side-baseline/11-RESEARCH.md (§5 API-02 design)
    - .planning/phases/11-network-totals-endpoint-filter-api-server-side-baseline/11-VALIDATION.md (3 API-02 verification rows)
    - config/sell_type_proxy.yaml (verbatim mapping — 5 sell_types)
    - backend/api/publisher_routes.py:168-289 (current `get_top_publishers` signature)
  </read_first>
  <action>
Create new file `scripts/test_sell_type_filter.py`. Mirror the TestClient pattern from `scripts/test_health_alerts_pipeline.py`.

Constants at module top:
```python
ENDPOINT_PATH = "/api/publishers/top"
VALID_SELL_TYPES = ["Open_Market", "Header_Bidding", "Direct", "Deal", "Other"]
# Year present in current parquet (verified by RESEARCH §7 — max_date=2026-03-23)
QUERY_YEAR = 2026
```

Author exactly these 4 test methods (RED today):

1. `test_open_market_filter_returns_only_open_market` — `resp = client.get(f"{ENDPOINT_PATH}?year={QUERY_YEAR}&sell_type=Open_Market")`; assert `resp.status_code == 200`; parse `body`; assert `body["sell_type_filter"] == "Open_Market"` (transparency contract per RESEARCH §5); assert `len(body["publishers"]) > 0` (Open_Market is the dominant sell_type, must return rows); assert `body["year"] == QUERY_YEAR`.

2. `test_invalid_sell_type_returns_400` — `resp = client.get(f"{ENDPOINT_PATH}?year={QUERY_YEAR}&sell_type=Programmatic_Direct")` (NOT in the 5-value whitelist); assert `resp.status_code == 400`; assert `"sell_type" in resp.json().get("detail", "")` OR contains the canonical list of valid values.

3. `test_no_filter_unchanged_behavior` — `resp = client.get(f"{ENDPOINT_PATH}?year={QUERY_YEAR}")`; assert `resp.status_code == 200`; assert `"publishers" in resp.json()`; assert `body.get("sell_type_filter") in (None, "")` (omitted or null when no filter applied — backwards compat for Phase 12 frontend that does not yet pass the param).

4. `test_each_valid_sell_type_returns_200` — for each `st in VALID_SELL_TYPES`: `resp = client.get(f"{ENDPOINT_PATH}?year={QUERY_YEAR}&sell_type={st}")`; assert `resp.status_code in (200, 503)` (503 acceptable for sell_types with zero rows in current parquet — `Other`/`TAM` may have no top-50 publishers; the test asserts the contract, not the data).

DO NOT mutate the parquet; DO NOT call any new endpoint. Module docstring: "Phase 11 API-02 — Nyquist Wave 0 RED test for sell_type filter on /api/publishers/top. Authored before implementation per VALIDATION contract. Expected RED until Plan 03 wires the param."

Add `if __name__ == "__main__": unittest.main()`.
  </action>
  <verify>
    <automated>.venv/bin/python scripts/test_sell_type_filter.py 2>&1 | tee /tmp/11-01-task2.log; grep -E "FAIL|ERROR|sell_type_filter" /tmp/11-01-task2.log &gt; /dev/null; test $? -eq 0</automated>
  </verify>
  <acceptance_criteria>
    - File `scripts/test_sell_type_filter.py` exists.
    - `grep -c 'VALID_SELL_TYPES = \["Open_Market", "Header_Bidding", "Direct", "Deal", "Other"\]' scripts/test_sell_type_filter.py` returns ≥1.
    - `grep -E "def test_(open_market_filter_returns_only_open_market|invalid_sell_type_returns_400|no_filter_unchanged_behavior|each_valid_sell_type_returns_200)" scripts/test_sell_type_filter.py | wc -l` returns 4.
    - `grep -c "/api/publishers/top" scripts/test_sell_type_filter.py` returns ≥1.
    - `grep -c "sell_type_filter" scripts/test_sell_type_filter.py` returns ≥1.
    - `.venv/bin/python scripts/test_sell_type_filter.py` exits non-zero today (RED — sell_type query param not yet supported by `/api/publishers/top`).
  </acceptance_criteria>
  <done>Test file authored, RED on current main, asserts exact 5-value whitelist from sell_type_proxy.yaml + transparency contract sell_type_filter in response.</done>
</task>

<task type="auto">
  <name>Task 3: Author scripts/test_alert_baseline_fields.py (API-03 RED)</name>
  <files>scripts/test_alert_baseline_fields.py</files>
  <read_first>
    - scripts/test_health_alerts_pipeline.py (TestClient pattern)
    - .planning/phases/11-network-totals-endpoint-filter-api-server-side-baseline/11-RESEARCH.md (§6 API-03 design + Opzione A on-the-fly)
    - .planning/phases/11-network-totals-endpoint-filter-api-server-side-baseline/11-VALIDATION.md (3 API-03 verification rows)
    - backend/api/schemas.py (current AlertDetail — must NOT have baseline_bacino yet)
    - backend/db/operations.py:140-170 (get_alert_by_id signature — environment_split_json column)
    - frontend/src/components/alerts/TriageSection.tsx (lines 29-32 — the heuristic this kills: `baselineCoverage = avgCoverage + 0.05`)
  </read_first>
  <action>
Create new file `scripts/test_alert_baseline_fields.py`. Mirror TestClient pattern.

Setup helper: `_first_non_deprecated_alert_id()` queries the live `data/vna_alerts.db` (read-only, sqlite3 connect, `SELECT alert_id FROM alerts WHERE deprecated = 0 AND environment_split_json IS NOT NULL AND environment_split_json != '{}' LIMIT 1`). Cache in `setUpClass`. If query returns None, `unittest.SkipTest("no non-deprecated alerts with env_split in DB — phase prerequisite missing")`.

Setup helper: `_first_deprecated_alert_id()` same pattern but `WHERE deprecated = 1 LIMIT 1` for the deprecated-graceful-degradation test.

Author exactly these 5 test methods (RED today — top-level fields do not exist):

1. `test_alert_detail_includes_baseline_bacino_top_level` — `resp = client.get(f"/api/alerts/{cls.alert_id}")`; assert `resp.status_code == 200`; `body = resp.json()["alert"]`; assert `"baseline_bacino" in body` (top-level, NOT inside environment_split); assert `body["baseline_bacino"] is not None`; assert `isinstance(body["baseline_bacino"], int)`; assert `body["baseline_bacino"] > 0`.

2. `test_alert_detail_includes_baseline_coverage_top_level` — same fixture; assert `"baseline_coverage" in body`; assert `body["baseline_coverage"] is not None`; assert `isinstance(body["baseline_coverage"], float)`; assert `0.0 <= body["baseline_coverage"] <= 1.0`.

3. `test_baseline_coverage_not_heuristic_avgcov_plus_005` — REGRESSION TEST per VALIDATION §11-VALIDATION.md row "API-03 regression". Compute `avg_coverage_from_env_split` by reading `body["environment_split"]` and averaging `coverage_current` values present (mirroring the heuristic input). Assert `abs(body["baseline_coverage"] - (avg_coverage_from_env_split + 0.05)) > 0.001` — i.e., the server-side baseline must NOT equal the killed heuristic. (If by coincidence a single alert produces a value within 0.001, the test will flag and require review — that is the desired safety.)

4. `test_deprecated_alert_baseline_fields_none` — uses `_first_deprecated_alert_id()`; `resp = client.get(f"/api/alerts/{cls.dep_alert_id}?include_deprecated=true")`; assert `resp.status_code == 200` (no panic); `body = resp.json()["alert"]`; assert `body["baseline_bacino"] is None OR body["baseline_bacino"] == 0` (graceful per RESEARCH §6 Pydantic Optional contract). Same for `baseline_coverage`.

5. `test_baseline_bacino_matches_aggregation_of_env_split` — fetches the same alert as test 1; computes expected via:
   ```python
   env = body["environment_split"]
   expected = sum(v.get("bacino_baseline", 0) for v in env.values() if isinstance(v, dict))
   self.assertEqual(body["baseline_bacino"], expected)
   ```
   Asserts the exact aggregation rule from RESEARCH §6 `_compute_baseline_from_env_split`.

DO NOT add a fixture DB; use the live `data/vna_alerts.db` read-only (the project's existing tests already do this — see `test_health_alerts_pipeline.py`). Module docstring: "Phase 11 API-03 — Nyquist Wave 0 RED test for top-level baseline_bacino + baseline_coverage in AlertDetail. Authored before implementation per VALIDATION contract. Expected RED until Plan 02 extends AlertDetail and aggregates from environment_split_json. Kills the TriageSection.tsx:31-32 heuristic."

Add `if __name__ == "__main__": unittest.main()`.
  </action>
  <verify>
    <automated>.venv/bin/python scripts/test_alert_baseline_fields.py 2>&1 | tee /tmp/11-01-task3.log; grep -E "FAIL|ERROR|KeyError|baseline_bacino" /tmp/11-01-task3.log &gt; /dev/null; test $? -eq 0</automated>
  </verify>
  <acceptance_criteria>
    - File `scripts/test_alert_baseline_fields.py` exists.
    - `grep -E "def test_(alert_detail_includes_baseline_bacino_top_level|alert_detail_includes_baseline_coverage_top_level|baseline_coverage_not_heuristic_avgcov_plus_005|deprecated_alert_baseline_fields_none|baseline_bacino_matches_aggregation_of_env_split)" scripts/test_alert_baseline_fields.py | wc -l` returns 5.
    - `grep -c "baseline_bacino" scripts/test_alert_baseline_fields.py` returns ≥4.
    - `grep -c "baseline_coverage" scripts/test_alert_baseline_fields.py` returns ≥4.
    - `grep -c "/api/alerts/" scripts/test_alert_baseline_fields.py` returns ≥1.
    - `grep -c "deprecated = 0" scripts/test_alert_baseline_fields.py` returns ≥1 (read-only fixture query).
    - `.venv/bin/python scripts/test_alert_baseline_fields.py` exits non-zero today (RED — top-level baseline fields not exposed).
  </acceptance_criteria>
  <done>Test file authored, RED on current main, asserts the 5 contract conditions (presence, regression vs heuristic, deprecated graceful, exact aggregation rule).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| pytest → backend.main.app | Tests instantiate the live FastAPI app via `TestClient`; auth bypass enabled via `os.environ["ENVIRONMENT"] = "development"` (project pattern) |
| pytest → live DB (read-only) | Test 3 reads `data/vna_alerts.db` to discover a fixture alert_id; SELECT only, no UPDATE/INSERT/DELETE |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-11-01-01 | Tampering | scripts/test_alert_baseline_fields.py — DB read | low | mitigate | Read-only `sqlite3.connect` with `SELECT` only; no `with conn:` write context. Project precedent: `scripts/test_health_alerts_pipeline.py` follows same pattern. Test exits cleanly even if DB unreadable (`SkipTest`). |
| T-11-01-02 | DoS | full test suite invocation | low | accept | Tests are RED on first run (Wave 0) — short-circuit on first assertion failure; ~1-3s runtime each per VALIDATION §runtime estimate. |
| T-11-01-03 | Information Disclosure | test output may leak alert_id / publisher_id | low | accept | Test stdout is local-only; CI/CD not configured for this repo. Stefano runs locally. No PII in alert_id (synthetic format `ALT-YYYYMMDD-HHMMSS-<sev>`). |
| T-11-01-04 | Repudiation | None — Wave 0 is read-only test scaffolding | n/a | n/a | Tests do not write to DB or filesystem outside `scripts/test_*.py` itself + `/tmp` log files. |

No `high` threats. ASVS L1 satisfied — V5 Input Validation tests live in this plan (verify the API-01/02/03 will reject malformed inputs); V2 Authentication intentionally bypassed via `ENVIRONMENT=development` per existing project test pattern.
</threat_model>

<verification>
After all 3 tasks complete:

```bash
.venv/bin/python scripts/test_network_totals_pbi_parity.py; echo "exit=$?"
.venv/bin/python scripts/test_sell_type_filter.py; echo "exit=$?"
.venv/bin/python scripts/test_alert_baseline_fields.py; echo "exit=$?"
```

ALL THREE must exit non-zero (RED). Wave 0 success means: tests authored, syntactically valid (Python parses, imports succeed), and bind to behavior that does not yet exist.

Wave 1 (Plans 02 + 03) flips them to GREEN. If any of the 3 tests is GREEN today, the test is mis-authored — it is asserting current behavior, not future behavior.
</verification>

<success_criteria>
1. 3 new test files exist under `scripts/`, all 3 RED on current main.
2. Each file imports `TestClient(app)` from `backend.main`, sets `ENVIRONMENT=development` for auth bypass.
3. Combined test method count: 4 (API-01) + 4 (API-02) + 5 (API-03) = 13 test methods.
4. PBI bounds hardcoded: [26656.00, 27744.00] in `test_network_totals_pbi_parity.py`.
5. 5-value sell_type whitelist hardcoded verbatim in `test_sell_type_filter.py` matching `config/sell_type_proxy.yaml`.
6. Regression assertion `baseline_coverage ≠ avgCoverage + 0.05` present in `test_alert_baseline_fields.py`.
7. No production code touched in this plan (only `scripts/`).
</success_criteria>

<output>
After completion, create `.planning/phases/11-network-totals-endpoint-filter-api-server-side-baseline/11-01-SUMMARY.md` per template.

Atomic commit: `test(11-01): wave-0 nyquist red scaffolds for API-01/02/03`. Per R-03 + R-06, commit without asking.

Per R-05: do NOT push. Local commit only.
</output>
