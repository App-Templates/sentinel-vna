---
phase: 11-network-totals-endpoint-filter-api-server-side-baseline
reviewed: 2026-04-29T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - scripts/test_network_totals_pbi_parity.py
  - scripts/test_sell_type_filter.py
  - scripts/test_alert_baseline_fields.py
  - backend/api/schemas.py
  - backend/api/routes.py
  - backend/api/publisher_routes.py
findings:
  critical: 0
  warning: 4
  info: 7
  total: 11
status: issues_found
---

# Phase 11: Code Review Report

**Reviewed:** 2026-04-29
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Phase 11 ships three focused additions on top of `4b7f661`:

- New endpoint `GET /api/metrics/network-totals` (routes.py:911-969) reading raw `data/sentinel_db/daily_kpi.csv` to bypass the parquet top-50 filter for PBI parity (RC-(a)).
- New helpers `_load_kpi_csv` (routes.py:167-207) with column-projection caching and `_compute_baseline_from_env_split` (routes.py:123-164), pure aggregation over env_split JSON.
- `AlertDetail` schema gains optional top-level `baseline_bacino` + `baseline_coverage` (schemas.py:87-89), populated server-side in `get_alert` (routes.py:281-285) — kills the TriageSection.tsx:29-32 client heuristic.
- New `sell_type` Query param on `/api/publishers/top` with whitelist validation + transparency echo (publisher_routes.py:185-224, 340).
- Three RED Nyquist test scaffolds, now GREEN per the SUMMARY chain.

Overall implementation is clean, defensive, and well-aligned with RESEARCH/PLAN docs. No critical issues. Findings cluster around two concerns: (1) hardcoded whitelists that drift from their canonical sources (`backend/db/models.py CHANNEL_GROUP_CHECK_VALUES` and `config/sell_type_proxy.yaml`) — the same anti-pattern bridge-contracts solves cross-repo, and (2) a few edge cases in the baseline aggregation and 404 ordering that are corner-case but worth tightening.

## Warnings

### WR-01: `NETWORK_TOTALS_CHANNELS` duplicates `CHANNEL_GROUP_CHECK_VALUES` (drift risk)

**File:** `backend/api/routes.py:90-93`
**Issue:** The whitelist used to validate the `channel` Query param is hardcoded as a literal set:

```python
NETWORK_TOTALS_CHANNELS = {
    "GOOGLE_ADEX", "OPEN_BIDDING", "HEADER_BIDDING_MAGNITE",
    "HEADER_BIDDING_PUBMATIC", "TAM", "DIRECT", "DEAL", "GOOGLE",  # legacy alias
}
```

The error-message comment at routes.py:924 says "per backend/db/models.py CHANNEL_GROUP_CHECK_VALUES" but no import enforces it. `backend/db/models.py:52-55` already exposes a tuple with this exact contract. Future migrations that expand the channel domain (e.g., real `sell_type` upstream per v1.4 OPS-02) will silently leave this endpoint behind — same shape as the canonical Bug #15 in R-14, just intra-repo. `scripts/test_models_sync.py` covers the SQL/enum/tuple triad but not this set.

**Fix:** Import the tuple and reuse it:

```python
from backend.db.models import CHANNEL_GROUP_CHECK_VALUES
# ...
NETWORK_TOTALS_CHANNELS: frozenset[str] = frozenset(CHANNEL_GROUP_CHECK_VALUES)
```

If a sub-list is intentional (e.g., legacy `GOOGLE` should be rejected here even though the DB CHECK still allows it), encode that delta explicitly with a comment naming the excluded values.

### WR-02: `VALID_SELL_TYPES` duplicates `config/sell_type_proxy.yaml` top-level keys

**File:** `backend/api/publisher_routes.py:37-43`
**Issue:** Same drift pattern as WR-01. The tuple

```python
VALID_SELL_TYPES: tuple[str, ...] = (
    "Open_Market", "Header_Bidding", "Direct", "Deal", "Other",
)
```

is hardcoded in Python and must be kept in sync with the YAML manually. The comment at publisher_routes.py:34-36 acknowledges this and points the reader at `config/sell_type_proxy.yaml`, but the recipe is "edit two places, hope the human remembers". `scripts/etl_csv_to_parquet.py` is also a consumer per the YAML header — three places now. v1.4 OPS-02 explicitly plans an expansion ("real sell_type from upstream") and this whitelist will silently 400 a legitimate request post-expansion until the tuple is touched.

**Fix:** Load from YAML once at module init, with a clear failure mode if the file is missing:

```python
import yaml
_SELL_TYPE_YAML = BASE_DIR / "config" / "sell_type_proxy.yaml"

def _load_valid_sell_types() -> tuple[str, ...]:
    with open(_SELL_TYPE_YAML) as f:
        data = yaml.safe_load(f) or {}
    keys = tuple(k for k in data.keys() if not k.startswith("_"))
    if not keys:
        raise RuntimeError(f"sell_type_proxy.yaml has no top-level mappings: {_SELL_TYPE_YAML}")
    return keys

VALID_SELL_TYPES: tuple[str, ...] = _load_valid_sell_types()
```

Adds an import-time assertion so a missing/corrupt YAML fails fast rather than silently allowing zero whitelisted values (which would 400 every request).

### WR-03: `_compute_baseline_from_env_split` returns `None` for legitimate `total_bacino == 0`

**File:** `backend/api/routes.py:152-163`
**Issue:** The function returns

```python
return (
    int(total_bacino) if total_bacino > 0 else None,
    float(avg_coverage) if avg_coverage is not None else None,
)
```

The `> 0` guard collapses two distinct cases into one:
1. "no env_split data / parse failure" — should return None (semantic "unknown").
2. "env_split present, but all entries have `bacino_baseline == 0` (or the field is missing/None)" — semantically the value IS 0, not unknown.

Test `test_baseline_bacino_matches_aggregation_of_env_split` (test_alert_baseline_fields.py:244-261) asserts equality with the in-Python aggregation of the same env_split. If a real alert has all-zero `bacino_baseline` entries, server returns `None` while the test computes `0` → test fails on a legitimate edge case. The empty-blob case is already handled earlier (`if not env_entries: return None, None` at line 150-151), so the `> 0` guard is over-broad.

**Fix:**

```python
return (
    int(total_bacino),  # legitimate 0 stays 0; "no data" already returned earlier
    float(avg_coverage) if avg_coverage is not None else None,
)
```

If the intent IS to suppress the `0` case (e.g., the UI treats it as "missing"), document the rationale inline so future readers don't undo it, and tighten the test to exclude this edge.

### WR-04: Module-level cache globals lack concurrency guard on cold start

**File:** `backend/api/routes.py:96-98, 167-207`
**Issue:** `_kpi_csv_cache` and `_kpi_csv_max_date` are plain module globals. `_load_kpi_csv` is called from a sync FastAPI handler (`network_totals`). If two requests arrive concurrently before the cache is populated, both will enter `pa_csv.read_csv` on the 1.4 GB file. uvicorn `--workers > 1` already multiplies the resident set; concurrent cold-start requests inside a single worker can amplify it further (transient ~2× peak RAM during the second read). Same pre-existing pattern in `_load_hourly_data` (routes.py:101-120) and `_load_adrequests` (publisher_routes.py:46-65), so this is consistent with project style — but Phase 11 introduces a notably larger payload (1.4 GB CSV vs the smaller parquets), making the latent risk more acute.

**Fix:** Single-flight pattern with a lock:

```python
import threading
_kpi_csv_lock = threading.Lock()

def _load_kpi_csv() -> Optional[pa.Table]:
    global _kpi_csv_cache, _kpi_csv_max_date
    if _kpi_csv_cache is not None:
        return _kpi_csv_cache
    with _kpi_csv_lock:
        if _kpi_csv_cache is not None:  # double-checked
            return _kpi_csv_cache
        # ... existing read_csv body ...
```

Alternatively, prime the cache at app startup (`@app.on_event("startup")` or FastAPI `lifespan`) so the first user request never pays the load cost. This also surfaces a missing-file failure at boot rather than at first call.

## Info

### IN-01: `_load_kpi_csv` swallows full traceback in `except Exception`

**File:** `backend/api/routes.py:205-207`
**Issue:** `logger.error("Failed to load daily_kpi.csv: %s", e)` drops the stack. Pre-existing project pattern (`_load_hourly_data` line 119 same shape), but for a brand-new code path it's worth using `logger.exception(...)` to capture frames at first deploy when failures are most likely.
**Fix:** `logger.exception("Failed to load daily_kpi.csv")` (no `%s` — `exception` already logs the active exception with traceback).

### IN-02: 404-range check at line 936 misses the lower bound

**File:** `backend/api/routes.py:935-940`
**Issue:** `if _kpi_csv_max_date is None or date > _kpi_csv_max_date` only protects against dates beyond max. A request for `1999-01-01` (well before any CSV row) falls through to the filter and lands on the "no rows" 404 at line 949 with the less informative detail `"no rows for date=... channel=..."`. Both responses are 404, so end behaviour is correct, but the freshness signal in the detail is asymmetric (over-range gets the helpful "max available: ...", under-range gets nothing).
**Fix:** Compute `_kpi_csv_min_date` alongside `_kpi_csv_max_date` in `_load_kpi_csv` and reject either side with a unified detail:

```python
if _kpi_csv_min_date is None or _kpi_csv_max_date is None or not (_kpi_csv_min_date <= date <= _kpi_csv_max_date):
    raise HTTPException(
        status_code=404,
        detail=f"date {date} out of CSV range [{_kpi_csv_min_date}, {_kpi_csv_max_date}]",
    )
```

### IN-03: `revenue_net=None` hardcoded — no contract test pinning it for Phase 13

**File:** `backend/api/routes.py:963` and `backend/api/schemas.py:164-165`
**Issue:** Comment says "Phase 13 CORR-03 will add net via revenue_share.yaml". Schema declares `Optional[float]`, value is hardcoded `None`. No regression test asserts `revenue_net is None` today, so a Phase 13 implementer flipping the wire on without updating tests/docs would not get a CI signal here.
**Fix:** Add a one-line assertion in `test_network_totals_pbi_parity.py` step 1:

```python
self.assertIsNone(body.get("revenue_net"), "revenue_net must remain None until Phase 13 CORR-03 lands")
```

It will turn red the moment Phase 13 wires it, forcing the test author to update the contract.

### IN-04: Tests rely on real `data/sentinel_db/daily_kpi.csv` with no skipTest fallback

**File:** `scripts/test_network_totals_pbi_parity.py:54-99`
**Issue:** If the CSV is missing on a fresh clone or in CI without the 1.4 GB fixture, `_load_kpi_csv` returns `None` → endpoint returns 503 → `assertEqual(resp.status_code, 200)` fails with a misleading message (a stack-trace about "expected 200 got 503" rather than "fixture missing"). The other two test files use `unittest.SkipTest` for missing fixtures (test_alert_baseline_fields.py:86-88).
**Fix:** Add a fixture guard in `setUpClass`:

```python
KPI_CSV = REPO_ROOT / "data" / "sentinel_db" / "daily_kpi.csv"
if not KPI_CSV.exists():
    raise unittest.SkipTest(f"daily_kpi.csv not present at {KPI_CSV} — fixture missing")
```

### IN-05: `_compute_baseline_from_env_split` includes `coverage_baseline == 0.0` in the average

**File:** `backend/api/routes.py:155-159`
**Issue:** The list comprehension keeps every entry where `coverage_baseline is not None`, so a legitimate `0.0` value is averaged in. RESEARCH §6 indicates `coverage_baseline=0` is a valid signal (a real measured zero), so this is the intended behaviour — but it diverges from the killed TriageSection.tsx:29-32 heuristic which used `coverage_current` (averaged with the same `is not None` rule). The regression test `test_baseline_coverage_not_heuristic_avgcov_plus_005` only asserts the values differ by >0.001, which is structurally true since `coverage_baseline` and `coverage_current` are different fields — the test passes "by accident" of source-field choice rather than by independent computation. Worth a docstring note.
**Fix:** Add an explicit comment in `_compute_baseline_from_env_split` clarifying that `coverage_baseline=0` is included on purpose, and consider strengthening the regression test to assert the server value matches the `coverage_baseline` aggregation (positive assertion) rather than only "not the heuristic".

### IN-06: Hardcoded source path in response payload

**File:** `backend/api/routes.py:968` and `backend/api/schemas.py:171-172`
**Issue:** `source="data/sentinel_db/daily_kpi.csv"` is a literal in two places (Field default + handler kwarg). If the CSV is relocated or alternated (e.g., a Parquet sibling lands in v1.4), both sites must change in lockstep, and the Field default would become misleading until a manual edit.
**Fix:** Reference `KPI_CSV_PATH.relative_to(BASE_DIR)` (or a constant string holding the relative form) so the path is single-sourced:

```python
KPI_CSV_REL = "data/sentinel_db/daily_kpi.csv"
KPI_CSV_PATH = BASE_DIR / KPI_CSV_REL
# ...
return NetworkTotalsResponse(..., source=KPI_CSV_REL, ...)
```

And drop the default from the Pydantic Field (or keep the default but mark it as a fallback only).

### IN-07: `test_alert_baseline_fields.py` opens DB connection without context manager

**File:** `scripts/test_alert_baseline_fields.py:49-60, 67-74`
**Issue:** `conn = sqlite3.connect(...)` + `try/finally: conn.close()` works correctly, but the project elsewhere (e.g., backend/db/operations.py `get_db`) uses a context manager. For consistency and exception-safety on `Path.exists()`-then-disappears races (rare), prefer:

```python
with sqlite3.connect(str(DB_PATH)) as conn:
    row = conn.execute(...).fetchone()
return row[0] if row else None
```

Note: `sqlite3.Connection.__exit__` commits/rollbacks but does NOT close the connection — for the read-only fetchone here the `try/finally` form is actually safer for explicit resource release. Keep current form OR switch to `closing(sqlite3.connect(...))` from `contextlib`. Style nit only.

---

_Reviewed: 2026-04-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
