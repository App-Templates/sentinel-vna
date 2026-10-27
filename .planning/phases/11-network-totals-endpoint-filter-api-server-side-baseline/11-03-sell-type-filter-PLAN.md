---
phase: 11-network-totals-endpoint-filter-api-server-side-baseline
plan: 03
type: execute
wave: 1
depends_on: [11-01]
files_modified:
  - backend/api/publisher_routes.py
autonomous: true
requirements: [API-02]

must_haves:
  truths:
    - "GET /api/publishers/top?year=2026&sell_type=Open_Market returns 200 with publishers filtered to channel_groups in {GOOGLE_ADEX, OPEN_BIDDING, GOOGLE} via sell_type_proxy column."
    - "Invalid sell_type literal (e.g., 'Programmatic_Direct') returns 400 with message listing the 5 valid values."
    - "Omitted sell_type query param preserves existing behavior — no filter applied (backwards compat for Phase 12 frontend)."
    - "Response payload includes sell_type_filter key (transparency contract — UI must be able to display 'filtered to Open_Market')."
    - "Missing sell_type_proxy column in parquet returns HTTP 503 with diagnostic message (column guard)."
    - "scripts/test_sell_type_filter.py exits 0 (GREEN) after this plan."
    - "Existing GET /api/publishers/top (no sell_type) still GREEN — zero regression on default behavior."
  artifacts:
    - path: "backend/api/publisher_routes.py"
      provides: "sell_type query param on /top endpoint with whitelist validation + parquet filter."
      contains: "sell_type"
    - path: "backend/api/publisher_routes.py"
      provides: "VALID_SELL_TYPES module constant (5-value tuple from sell_type_proxy.yaml)."
      contains: "VALID_SELL_TYPES"
  key_links:
    - from: "backend/api/publisher_routes.py:get_top_publishers"
      to: "data/baseline/daily_aggregated.parquet column sell_type_proxy"
      via: "df_year[df_year['sell_type_proxy'] == sell_type]"
      pattern: "sell_type_proxy"
    - from: "backend/api/publisher_routes.py:VALID_SELL_TYPES"
      to: "config/sell_type_proxy.yaml"
      via: "5-value whitelist matches YAML keys verbatim"
      pattern: 'VALID_SELL_TYPES = ("Open_Market", "Header_Bidding", "Direct", "Deal", "Other")'
---

<objective>
Implement API-02 by adding a `sell_type` query parameter to `GET /api/publishers/top` that filters the parquet via the existing `sell_type_proxy` column (already populated by Phase 08 SCHEMA-04 ETL — verified live in RESEARCH §5).

Purpose: First half of indirizzando RC-(b) email Vito #4a-#4d (Mondadori bacino, fill rate, eCPM, RPM). The `sell_type=Open_Market` filter lets the frontend (Phase 12+) request publisher metrics scoped to Open_Market only, matching the PBI "all sell type" vs "Open Market" distinction Vito explicitly cited in his email.

Output: 1 endpoint extended with `sell_type` Query, 1 new module constant, 1 column guard returning 503, 1 transparency contract field `sell_type_filter` added to response.

Phase 11 explicitly defers per RESEARCH §5 + §8 OQ1:
- `/api/alerts` sell_type filter — Phase 12 (requires DB column + Migration 006).
- `/api/metrics/revenue-status-24h` sell_type filter — Phase 12 (hourly parquet has only Open_Market rows).
- Mondadori + Mondadori_npa publisher_family aggregation — Phase 12/17 (RC-b core fix).
- Frontend wiring of the new filter param — Phase 12 (TriageSection refactor + PublishersPage).
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
@backend/api/publisher_routes.py
@config/sell_type_proxy.yaml
@scripts/test_sell_type_filter.py

<interfaces>
<!-- Contracts the executor needs. NO codebase exploration required. -->

From config/sell_type_proxy.yaml (canonical SSOT — verbatim, RESEARCH §5):
```yaml
Open_Market:    [GOOGLE_ADEX, OPEN_BIDDING, GOOGLE]
Header_Bidding: [HEADER_BIDDING_MAGNITE, HEADER_BIDDING_PUBMATIC]
Direct:         [DIRECT]
Deal:           [DEAL]
Other:          [TAM]
```

From backend/api/publisher_routes.py:168-289 (current `get_top_publishers` signature — extend, don't replace):
```python
@router.get("/top")
@limiter.limit("60/minute")
def get_top_publishers(
    request: Request,
    limit: int = Query(35, ge=1, le=200),
    year: int = Query(2025),
):
    df = _load_adrequests()
    if df is None:
        raise HTTPException(status_code=503, detail="Ad requests data not available")
    df_year = df[df["date"].dt.year == year]
    if df_year.empty:
        return {"publishers": [], "year": year, "total_publishers": 0}
    # ... aggregation logic ...
    return {
        "publishers": publishers,
        "year": year,
        "total_publishers": len(publishers),
    }
```

From data/baseline/daily_aggregated.parquet (verified RESEARCH §7 — 20 columns):
```
date, publisher_id, channel_group, sell_type_proxy, environment, geo_cluster,
revenue, revenue_gross, impressions, measurable_impressions, viewable_impressions,
bacino, clicks, floor_cpm, coverage, ecpm, rpm, ctr, viewability, gross_margin_pct
```

`sell_type_proxy` distinct values verified live: `["Deal", "Direct", "Header_Bidding", "Open_Market", "Other"]`.

Test contract (scripts/test_sell_type_filter.py — Wave 0 Plan 01):
- `body["sell_type_filter"] == "Open_Market"` when `?sell_type=Open_Market`
- `body.get("sell_type_filter") in (None, "")` when omitted
- `resp.status_code == 400` for invalid sell_type
- `resp.status_code in (200, 503)` for any of the 5 valid values
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add VALID_SELL_TYPES constant + sell_type Query param to get_top_publishers</name>
  <files>backend/api/publisher_routes.py</files>
  <read_first>
    - backend/api/publisher_routes.py (full file — must preserve all existing logic in get_top_publishers)
    - config/sell_type_proxy.yaml (verbatim — 5 keys top-level)
    - .planning/phases/11-network-totals-endpoint-filter-api-server-side-baseline/11-RESEARCH.md (§5 design + §8 OQ1 scope deferral)
    - scripts/test_sell_type_filter.py (asserts the contract — read all 4 test methods)
  </read_first>
  <behavior>
    - Test 1: Importing `VALID_SELL_TYPES` from `backend.api.publisher_routes` succeeds and contains exactly 5 strings: Open_Market, Header_Bidding, Direct, Deal, Other.
    - Test 2: `GET /api/publishers/top?year=2026&sell_type=Open_Market` returns 200; response includes `sell_type_filter == "Open_Market"`; all returned publishers have at least one Open_Market row in the source parquet (transitively via sell_type_proxy aggregation).
    - Test 3: `GET /api/publishers/top?year=2026&sell_type=Programmatic_Direct` returns 400; detail mentions valid values.
    - Test 4: `GET /api/publishers/top?year=2026` (no sell_type) returns 200; `sell_type_filter is None`; existing publisher list unchanged (regression — Phase 12 frontend depends on this).
    - Test 5: For each of the 5 valid sell_types, endpoint returns 200 OR 503 (503 acceptable when no top-50 publisher has rows for that sell_type — graceful empty result).
    - Test 6: When parquet does not contain `sell_type_proxy` column (simulated by guard check), endpoint returns 503 with message naming the missing column.
  </behavior>
  <action>
Open `backend/api/publisher_routes.py`.

**Add module-level constant** after the `_*_cache` declarations (around line 32, before `def _load_adrequests`):
```python
# Phase 11 API-02 — sell_type whitelist matches config/sell_type_proxy.yaml top-level keys verbatim.
# Single source of truth: config/sell_type_proxy.yaml. If that file evolves (v1.4 OPS-02
# adds real sell_type from upstream), update this tuple AND the Pydantic Query examples.
VALID_SELL_TYPES: tuple[str, ...] = (
    "Open_Market",
    "Header_Bidding",
    "Direct",
    "Deal",
    "Other",
)
```

**Modify `get_top_publishers` signature** (line 168-174). Replace the current decorator+def with:

```python
@router.get("/top")
@limiter.limit("60/minute")
def get_top_publishers(
    request: Request,
    limit: int = Query(35, ge=1, le=200),
    year: int = Query(2025),
    sell_type: Optional[str] = Query(
        None,
        description=(
            "Filter publishers by sell_type_proxy derived from channel_group. "
            "One of: Open_Market, Header_Bidding, Direct, Deal, Other. "
            "Omitted = no filter (backward compat). See config/sell_type_proxy.yaml."
        ),
    ),
):
```

**Insert validation + filter block** AFTER `df = _load_adrequests()` and BEFORE the existing `df_year = df[df["date"].dt.year == year]` line (approximately line 175):

```python
    if df is None:
        raise HTTPException(status_code=503, detail="Ad requests data not available")

    # Phase 11 API-02 — sell_type validation + filter (kept BEFORE year filter to fail fast).
    if sell_type is not None:
        if sell_type not in VALID_SELL_TYPES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"sell_type must be one of {list(VALID_SELL_TYPES)}; "
                    f"got {sell_type!r}. See config/sell_type_proxy.yaml."
                ),
            )
        if "sell_type_proxy" not in df.columns:
            raise HTTPException(
                status_code=503,
                detail=(
                    "sell_type_proxy column not present in parquet "
                    "(ETL SCHEMA-04 not yet applied or parquet outdated)."
                ),
            )
        df = df[df["sell_type_proxy"] == sell_type]
        if df.empty:
            # No rows for this sell_type — return empty list with transparency.
            return {
                "publishers": [],
                "year": year,
                "total_publishers": 0,
                "sell_type_filter": sell_type,
            }
```

(Note: the existing line `if df is None: raise HTTPException(503, ...)` already exists — DO NOT duplicate. The block above shows it for context; in the actual edit, only ADD the `if sell_type is not None: ...` block AFTER the existing 503 check.)

**Modify the return statement** at the end of `get_top_publishers` (around line 284-288). Replace:
```python
    return {
        "publishers": publishers,
        "year": year,
        "total_publishers": len(publishers),
    }
```
with:
```python
    return {
        "publishers": publishers,
        "year": year,
        "total_publishers": len(publishers),
        "sell_type_filter": sell_type,  # Phase 11 API-02 — None when no filter applied (transparency for UI).
    }
```

**Constraints:**
- DO NOT modify `_load_adrequests` cache logic. The filter applies AFTER cache load (per RESEARCH §9 R3 — stateless filter, no cache invalidation needed).
- DO NOT add `sell_type` to `/api/alerts` or `/api/metrics/revenue-status-24h` — Phase 12 scope (RESEARCH §5 + §8 OQ1).
- DO NOT remove the legacy `GOOGLE` channel from VALID_SELL_TYPES indirection — it's already mapped to `Open_Market` in `sell_type_proxy.yaml` at the ETL stage; the API works on the parquet column, not the raw channel.
- DO NOT modify the existing aggregation logic, weighted average, geo dominant, trend_4w, or any other field computation. The filter is a pure pre-aggregation filter on `df`.
- DO NOT change the `get_top_publishers` rate limit (60/minute stays).

The endpoint must remain at `GET /api/publishers/top` (router has `prefix="/api/publishers"` + route is `/top`).
  </action>
  <verify>
    <automated>.venv/bin/python scripts/test_sell_type_filter.py</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c 'VALID_SELL_TYPES' backend/api/publisher_routes.py` returns ≥3 (constant + 2 references in handler).
    - `grep -E '"Open_Market",\s*$' backend/api/publisher_routes.py` returns ≥1.
    - `grep -E '"Header_Bidding",\s*$' backend/api/publisher_routes.py` returns ≥1.
    - `grep -c 'sell_type: Optional\[str\] = Query' backend/api/publisher_routes.py` returns 1.
    - `grep -c 'sell_type not in VALID_SELL_TYPES' backend/api/publisher_routes.py` returns 1.
    - `grep -c '"sell_type_proxy" not in df.columns' backend/api/publisher_routes.py` returns 1.
    - `grep -c '"sell_type_filter": sell_type' backend/api/publisher_routes.py` returns ≥1.
    - `.venv/bin/python -c "from backend.api.publisher_routes import VALID_SELL_TYPES; assert VALID_SELL_TYPES == ('Open_Market', 'Header_Bidding', 'Direct', 'Deal', 'Other'); print('OK')"` exits 0.
    - `.venv/bin/python scripts/test_sell_type_filter.py` exits 0 (all 4 RED tests now GREEN).
    - `.venv/bin/python -c "from backend.main import app; from fastapi.testclient import TestClient; import os; os.environ['ENVIRONMENT']='development'; c=TestClient(app); r=c.get('/api/publishers/top?year=2026&sell_type=Open_Market'); assert r.status_code==200; b=r.json(); assert b['sell_type_filter']=='Open_Market'; print('OK,publishers=', b['total_publishers'])"` exits 0.
    - `.venv/bin/python -c "from backend.main import app; from fastapi.testclient import TestClient; import os; os.environ['ENVIRONMENT']='development'; c=TestClient(app); r=c.get('/api/publishers/top?year=2026&sell_type=BadValue'); assert r.status_code==400, r.status_code; print('OK')"` exits 0.
    - Backward compat: `.venv/bin/python -c "from backend.main import app; from fastapi.testclient import TestClient; import os; os.environ['ENVIRONMENT']='development'; c=TestClient(app); r=c.get('/api/publishers/top?year=2026'); assert r.status_code==200; b=r.json(); assert b['sell_type_filter'] is None; print('OK')"` exits 0.
  </acceptance_criteria>
  <done>API-02 GREEN on `/api/publishers/top`: sell_type whitelist enforced, parquet filter applied via existing column, transparency contract present, backward compat preserved (omitted param ⇒ None), column guard 503 wired.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| HTTP client → /api/publishers/top | User-supplied `sell_type` literal crosses into pandas filter (NOT into f-string SQL or eval) |
| in-memory parquet cache → response | Pre-existing pattern; no changes to cache lifecycle |
| Pydantic → JSON response | Existing dict-return shape; new `sell_type_filter` key joins it |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-11-03-01 | Tampering | sell_type query param | medium | mitigate | Strict whitelist `VALID_SELL_TYPES` (5 values from `config/sell_type_proxy.yaml`). Anything else → HTTP 400 with explicit detail. NO interpolation into SQL or shell or filesystem. Used only as pandas equality operand `df["sell_type_proxy"] == sell_type`. |
| T-11-03-02 | DoS | full parquet load on every request | low | accept | Pre-existing behavior of `_load_adrequests` — cached after first load. Filter is post-cache O(n) in number of rows; parquet is ~365k rows, sub-second pandas filter. `@limiter.limit("60/minute")` per-IP. |
| T-11-03-03 | Information Disclosure | empty result for sell_type with no rows | low | accept | Returns `{"publishers": [], "total_publishers": 0, "sell_type_filter": "X"}` — no leakage; the response shape is the same as an empty year. |
| T-11-03-04 | Denial | parquet missing sell_type_proxy column post-rebuild | low | mitigate | Column guard returns HTTP 503 with diagnostic message. Phase 08 SCHEMA-04 ETL produces the column; if a future ETL regression strips it, the guard prevents 500 panic and surfaces the issue. |
| T-11-03-05 | Spoofing / AuthN | endpoint auth | low | mitigate | Existing `require_auth` middleware in `backend/main.py` covers `/api/*` routes. ENVIRONMENT=development bypass scoped to TestClient suite. |
| T-11-03-06 | Tampering | year query param | low | accept | Pre-existing — `Query(2025)` accepts any int; pandas year filter is non-injectable. Out of scope for Phase 11 changes. |
| T-11-03-07 | Elevation of Privilege | endpoint is read-only | n/a | n/a | Zero DB writes, zero filesystem writes. |

No `high` threats. ASVS L1 satisfied: V5 Input Validation enforced via whitelist; V2 AuthN unchanged.
</threat_model>

<verification>
After Task 1 completes:

```bash
# Wave 0 RED test must now be GREEN:
.venv/bin/python scripts/test_sell_type_filter.py     # exit 0

# Adjacent tests must still be GREEN:
.venv/bin/python scripts/test_health_alerts_pipeline.py   # exit 0

# Live smoke (per VALIDATION §manual-only optional):
curl 'http://localhost:8000/api/publishers/top?year=2026&sell_type=Open_Market'
# expect: 200 + sell_type_filter:"Open_Market" + publishers list

curl 'http://localhost:8000/api/publishers/top?year=2026'
# expect: 200 + sell_type_filter:null (backwards compat)

curl 'http://localhost:8000/api/publishers/top?year=2026&sell_type=Bogus'
# expect: 400 + detail listing the 5 valid values
```
</verification>

<success_criteria>
1. **API-02 GREEN:** `scripts/test_sell_type_filter.py` exits 0; live `/api/publishers/top?sell_type=Open_Market` returns filtered results with `sell_type_filter: "Open_Market"`.
2. **Whitelist enforced:** Invalid sell_type → HTTP 400 with detail naming all 5 valid values.
3. **Column guard wired:** Missing `sell_type_proxy` column → HTTP 503 with diagnostic.
4. **Backward compat:** Omitted `sell_type` returns existing publisher list with `sell_type_filter: null`.
5. **Scope respected:** ZERO modifications to `/api/alerts` or `/api/metrics/revenue-status-24h` (Phase 12 scope).
6. **No regression:** Existing publisher aggregation logic (geo, trend_4w, eCPM, RPM, fill_rate, gross_margin_pct) untouched.
</success_criteria>

<output>
After completion, create `.planning/phases/11-network-totals-endpoint-filter-api-server-side-baseline/11-03-SUMMARY.md` per template.

Atomic commit (per R-03 + R-06): `feat(11-03): /api/publishers/top sell_type filter (API-02)`.

Per R-05: do NOT push. Local commit only. Stop at "ready for OK to deploy".
</output>
