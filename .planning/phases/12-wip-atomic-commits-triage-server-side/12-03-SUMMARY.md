---
phase: 12
plan: 03
subsystem: backend/api
tags: [wip-04, atomic-commit, bacino-dedup, yoy-rolling, available-dates, path-variant, phase-11-preservation]
dependency_graph:
  requires:
    - "Phase 11 API-03 ship-commit 3141591 (`_compute_baseline_from_env_split` byte-identity preserved)"
    - "Phase 11 API-02 ship-commit 510f5e2 (`VALID_SELL_TYPES` + sell_type filter byte-identity preserved)"
    - "Phase 11 API-01 ship-commit b6140f5 (`/api/metrics/network-totals` untouched)"
    - "WIP source commit 7ea4a74 on `wip/pre-10.2-rescue` (parented at pre-Phase-11 b6c77ec)"
  provides:
    - "publisher_routes.py get_top_publishers — channel-deduped total_bacino + corrected avg_coverage + corrected fill_rate"
    - "routes.py revenue_status_24h — 7w rolling YoY + complete_dates + available_dates"
    - "routes.py revenue_status_24h_by_date — path-based date variant /metrics/revenue-status-24h/{date_path}"
    - "scripts/test_wip04_backend_correctness.py — 4-case TDD scaffold (RED→GREEN gate)"
  affects:
    - "Phase 13 RevenueStatus24h date selector — consumes available_dates field"
    - "Phase 13 / Phase 16 Vercel static export — consumes path-based variant for vercel build pre-render"
    - "Phase 13 frontend bacino consumers — corrected total_bacino flows to PublishersPage summary cards"
tech_stack:
  added: []
  patterns:
    - "git apply --3way --check validation gate before --3way apply for cross-base cherry-picks"
    - "channel-dedup via groupby([pub, date, env, geo])[channel].nunique() then divide bacino_per_cell"
    - "complete-day detection via groupby(date)[timestamp].apply(hour.nunique() >= 20)"
    - "synthetic per-hour YoY curve weighted by baseline_hourly distribution (sum normalizes to py_rev)"
key_files:
  created:
    - "scripts/test_wip04_backend_correctness.py"
  modified:
    - "backend/api/publisher_routes.py"
    - "backend/api/routes.py"
decisions:
  - "Option 1 path taken (git apply --3way --check then --3way) — both per-file validation gates returned exit 0 cleanly; Option 2 manual hunk application not needed"
  - "Phase 11 byte-identity preserved without conflict resolution — WIP hunks anchored OUTSIDE Phase 11 surfaces (sell_type filter L181-220, _compute_baseline_from_env_split L123-164)"
  - "RED gate captured: 4/4 tests FAIL on pre-cherry-pick HEAD before any production-code change (TDD-correct ordering)"
  - "GREEN gate captured: 4/4 WIP-04 tests + 5/5 alert_baseline + 4/4 sell_type + 4/4 network_totals = 17/17 PASS post-apply"
  - "Mondadori live numeric proof: naive bacino 2,608,852,415 → corrected 407,755,508 (~6.4× reduction; max_n_channels=7) — fix moves the value FURTHER from PBI 366M but the published parquet contract is now respected (RC-b family aggregation deferred to Phase 13)"
metrics:
  duration: "~10 minutes"
  completed_date: "2026-04-30"
  tasks: 2
  files: 3
  commits: 1
---

# Phase 12 Plan 03: WIP-04 Commit C Backend Correctness Summary

Backend correctness diff cherry-picked atomically: bacino dedup in
`get_top_publishers`, 7-week rolling YoY in `revenue_status_24h`,
`available_dates` array for date selector, and a path-based variant for
static-deploy compatibility — landed via `git apply --3way` with
per-file validation gate, Phase 11 surface byte-identical to ship-commits
3141591 + 510f5e2.

## Commit

| Field | Value |
|-------|-------|
| SHA | `c29673c` |
| Subject | `feat(api): backend correctness — bacino dedup + 7w YoY + available_dates + path-based date variant (WIP-04 Commit C)` |
| Branch | `main` |
| Files | 3 |
| Insertions | 359 |
| Deletions | 11 |

```
 backend/api/publisher_routes.py           |  15 +-
 backend/api/routes.py                     |  57 +++++-
 scripts/test_wip04_backend_correctness.py | 298 ++++++++++++++++++++++++++++++
 3 files changed, 359 insertions(+), 11 deletions(-)
```

## What Shipped

### 1. publisher_routes.py — Bacino dedup (R-13 mathematical correctness)

The parquet join replicates `bacino` across channel_group rows for the same
`(publisher_id, date, environment, geo_cluster)` cell. Naive `.agg("sum")`
overcounts by `n_channels` per cell. The fix:

```python
n_channels      = df_year.groupby(["publisher_id", "date", "environment", "geo_cluster"])["channel_group"].nunique()
bacino_per_cell = df_year.groupby(["publisher_id", "date", "environment", "geo_cluster"])["bacino"].sum()
bacino_corrected = (bacino_per_cell / n_channels).groupby("publisher_id").sum()
pub["total_bacino"] = pub["publisher_id"].map(bacino_corrected).fillna(0)
pub["avg_coverage"] = (pub["total_impressions"] / pub["total_bacino"]).where(pub["total_bacino"] > 0, 0.0)
pub["fill_rate"]    = pub["avg_coverage"]  # identical after bacino correction
```

Side effect: `avg_coverage` and `fill_rate` (which divide by `total_bacino`)
self-correct.

**Live numeric proof — Mondadori 2026:**

| Metric | Pre-fix (naive) | Post-fix (corrected) | Factor |
|--------|-----------------|----------------------|--------|
| `total_bacino` | 2,608,852,415 | 407,755,508 | ~6.4× reduction |
| `max_n_channels` (cell) | 7 | 7 | unchanged (data) |
| `avg_coverage` | (unbounded over-count) | 0.4304 | math-correct |
| `fill_rate` | (= avg_coverage) | 0.4304 | math-correct |

Note: the corrected value moves Mondadori bacino FURTHER from PBI 366M.
PBI uses `publisher_family` aggregation (Mondadori family = M + M_npa +
Adgage_mondocore + Mediamond) — that's RC-b in `STELLA-POLARE.md`, deferred
to Phase 13. **This plan addresses RC-d (legacy `GOOGLE` channel naming
math) at the math layer; RC-b at the family-aggregation layer is separate.**

### 2. routes.py revenue_status_24h — 7-week rolling YoY

Replaces single-point `prev_year_date` lookup (returned `null` whenever
prev-year same-weekday revenue happened to be zero) with average over 7
same-weekday weeks centered on `prev_year_center`. Adds:

- `prev_year.weeks_averaged: int ∈ [1, 7]` — data-sparsity transparency
- `prev_year.hours: list[float]` (24 entries) — synthetic per-hour YoY curve
  weighted by `baseline_hourly` distribution; `sum(hours) ≈ py_rev` ±0.5%

### 3. routes.py revenue_status_24h — complete_dates + available_dates

Detects which dates have ≥ 20 hours of data. Defaults `target_date` to last
complete day (not raw max — was returning incomplete current-day data
which produces the misleading "97% delta vs baseline" partial-day artifact
visible in the RED test scaffold capture). Surfaces:

- `available_dates: [str, ...]` (last 7 complete days, YYYY-MM-DD) — Phase 13
  RevenueStatus24h date selector dropdown source

### 4. routes.py revenue_status_24h_by_date — path-based variant

```python
@router.get("/metrics/revenue-status-24h/{date_path}")
@limiter.limit("60/minute")
def revenue_status_24h_by_date(request: Request, date_path: str):
    """Path-based date selector for static deploy compatibility."""
    return revenue_status_24h(request, date=date_path)
```

Required by Phase 13 / Phase 16 static-deploy export (vercel build
precomputes JSON snapshots by URL path; query strings don't survive
`vercel build` static export).

## Cherry-Pick Procedure (Option 1 path executed)

WIP source `7ea4a74` is parented at pre-Phase-11 `b6c77ec`. Phase 11
(`b6140f5` + `3141591` + `510f5e2`) has since added the sell_type filter +
server-side baseline aggregation. Naïve `cherry-pick -n` would silently
3-way merge against Phase 11 surface.

**Validation gate (mandatory per plan §B.1/B.2):**

```bash
$ git show 7ea4a74 -- backend/api/publisher_routes.py | git apply --3way --check
Applied patch to 'backend/api/publisher_routes.py' cleanly.
EXIT: 0

$ git show 7ea4a74 -- backend/api/routes.py | git apply --3way --check
Applied patch to 'backend/api/routes.py' cleanly.
EXIT: 0
```

**Apply (Option 1 path — both files clean, no fallback to manual hunk):**

```bash
$ git show 7ea4a74 -- backend/api/publisher_routes.py | git apply --3way
Applied patch to 'backend/api/publisher_routes.py' cleanly.

$ git show 7ea4a74 -- backend/api/routes.py | git apply --3way
Applied patch to 'backend/api/routes.py' cleanly.
```

Conflict pre-check from planner verified: Phase 11's `sell_type` filter at
publisher_routes.py L181-220 is BEFORE the WIP hunk anchor `agg_dict = {`
at L237 (was L185 in WIP source — Phase 11 shifted by ~50 lines). The WIP
hunk anchors structurally rather than positionally, so the 3-way merge
patches the right block.

## Phase 11 Byte-Identity Verification

```bash
$ diff <(git show 3141591:backend/api/routes.py | sed -n '123,164p') \
       <(sed -n '123,164p' backend/api/routes.py)
(empty — BYTE-IDENTICAL)

$ diff <(git show 510f5e2:backend/api/publisher_routes.py | sed -n '37,50p') \
       <(sed -n '37,50p' backend/api/publisher_routes.py)
(empty — BYTE-IDENTICAL)
```

`_compute_baseline_from_env_split` (Phase 11 API-03 ship surface) and
`VALID_SELL_TYPES` tuple (Phase 11 API-02 ship surface) are both
byte-identical to the originating ship-commits — Plan 03 does NOT regress
API-02 or API-03 (R-13 invariant).

## Test Outcome (RED → GREEN)

### RED — captured pre-cherry-pick (4/4 FAIL)

```
test_response_contains_available_dates_array          ... FAIL
  AssertionError: 'available_dates' not found in {'date': '2026-03-23',
  'day_of_week': 'Monday', 'hours': [...], 'total_revenue': 532.07,
  'total_baseline': 18069.91, 'total_delta_pct': -97.1,
  'prev_year': {'date': '2025-03-24', 'day_of_week': 'Monday',
                'total_revenue': 36438.51, 'delta_pct': -98.5,
                'hourly_avg': 1518.27}}

test_mondadori_total_bacino_dedup                     ... FAIL
  AssertionError: 2608852415.0 not less than 2608852415.0 :
  BACINO DEDUP REGRESSION: api total_bacino (2608852415.0) must be
  strictly less than naive parquet sum (2608852415.0) since
  max_n_channels=7.0 > 1. Equality means dedup logic is missing.

test_path_variant_matches_query_variant               ... FAIL
  AssertionError: 404 != 200 : path variant 2026-03-23 must yield 200;
  got 404; body: {"detail":"Not Found"}

test_prev_year_has_weeks_averaged_and_hours           ... FAIL
  AssertionError: 'weeks_averaged' not found in {'date': '2025-03-24',
  ..., 'hourly_avg': 1518.27}

Ran 4 tests in 7.873s
FAILED (failures=4)
```

The RED capture also shows the partial-current-day artifact (target_date
defaulted to `2026-03-23` with only hour 0 having data → `total_revenue=
532.07` vs `total_baseline=18069.91 → delta_pct=-97.1`). The `complete_dates`
+ `available_dates` fix turns the default to "last complete day" so this
misleading rendering goes away on every consumer that doesn't pass an
explicit `?date=` query.

### GREEN — captured post-cherry-pick (4/4 PASS)

```
test_response_contains_available_dates_array          ... ok
test_mondadori_total_bacino_dedup                     ... ok
test_path_variant_matches_query_variant               ... ok
test_prev_year_has_weeks_averaged_and_hours           ... ok

Ran 4 tests in 29.393s
OK
```

### Phase 11 non-regression — captured post-cherry-pick (13/13 PASS)

```
$ .venv/bin/python scripts/test_alert_baseline_fields.py
Ran 5 tests in 0.067s
OK

$ .venv/bin/python scripts/test_sell_type_filter.py
Ran 4 tests in 170.793s
OK

$ .venv/bin/python scripts/test_network_totals_pbi_parity.py
Ran 4 tests in 19.625s
OK
```

API-01 + API-02 + API-03 contracts all still pass — Plan 03 introduces zero
regressions on Phase 11 surface.

## Acceptance Criteria Sign-off

Task 1 — WIP-04 backend correctness diff applied:

- [x] `python -c "import ast; ..."` parses both files OK
- [x] `grep -c "bacino_per_cell" backend/api/publisher_routes.py` = 2 (>= 1)
- [x] `grep -c "n_channels" backend/api/publisher_routes.py` = 2 (>= 1)
- [x] `grep -c "available_dates" backend/api/routes.py` = 2 (>= 2)
- [x] `grep -c "weeks_averaged" backend/api/routes.py` = 1 (>= 1)
- [x] `grep -c "revenue_status_24h_by_date" backend/api/routes.py` = 1 (>= 1)
- [x] `grep -c "/metrics/revenue-status-24h/{date_path}" backend/api/routes.py` = 1
- [x] Byte-identity Phase 11 API-03 (`_compute_baseline_from_env_split`) — empty diff vs `3141591`
- [x] Byte-identity Phase 11 API-02 (`VALID_SELL_TYPES`) — empty diff vs `510f5e2`
- [x] `_compute_baseline_from_env_split` cardinality = 3 (>= 2)
- [x] `VALID_SELL_TYPES` cardinality = 3 (>= 2)
- [x] `sell_type_filter` cardinality = 3 (>= 3)
- [x] Test scaffold exists at `scripts/test_wip04_backend_correctness.py`
- [x] RED capture — 4/4 tests FAIL pre-apply
- [x] GREEN capture — 4/4 tests PASS post-apply
- [x] Phase 11 non-regression — 13/13 tests PASS

Task 2 — Atomic commit:

- [x] Subject begins `feat(api): backend correctness — bacino dedup + 7w YoY + available_dates + path-based date variant (WIP-04 Commit C)`
- [x] Exactly 3 files in commit (`backend/api/publisher_routes.py`, `backend/api/routes.py`, `scripts/test_wip04_backend_correctness.py`)
- [x] `git diff HEAD~1 HEAD --shortstat` reports `3 files changed, 359 insertions(+), 11 deletions(-)`
- [x] Commit on `main` branch
- [x] No frontend file in diff

## Deviations from Plan

None — plan executed exactly as written.

The `git apply --3way --check` Option 1 validation gate returned exit 0 for
both files, so the manual hunk application Option 2 fallback was not
exercised. Phase 11 byte-identity verified post-apply.

## Threat Model Disposition

| Threat ID | Status | Resolution |
|-----------|--------|------------|
| T-12-03-01 (path-param injection) | mitigated | Path param flows through `revenue_status_24h(request, date=date_path)` which validates via `datetime.strptime` raising HTTP 400 on `ValueError`; no SQL constructed |
| T-12-03-02 (DoS bacino dedup) | mitigated | 2 groupby ops on cached `_adrequests_cache` (~5M rows); cold-start ~few-hundred-ms acceptable; cached requests unchanged |
| T-12-03-03 (DoS complete_dates) | mitigated | `groupby(date)[ts].apply(hour.nunique())` ~50ms cold on 740K rows; cached `_hourly_cache` reused |
| T-12-03-04 (info disclosure available_dates) | accepted | Operationally public, no PII |
| T-12-03-05 (info disclosure weeks_averaged) | accepted | Sparsity transparency for operators (same posture as `delta_pct`) |
| T-12-03-06 (audit trail) | accepted | Commit body cites WIP source `7ea4a74` + Phase 11 byte-identity refs |
| T-12-03-07 (EoP new endpoint) | mitigated | `@limiter.limit("60/minute")` matching the query-string variant; no new auth surface |
| T-12-03-08 (Phase 11 surface regression) | mitigated | `git apply --3way --check` validation gate executed successfully BEFORE `--3way` apply; byte-identity diff post-apply confirmed empty for both Phase 11 surfaces; Phase 11 regression suite 13/13 GREEN |

## Next Up

Plan 12-04 (CORR-01 TriageSection wire `alert.baseline_bacino` +
`alert.baseline_coverage` + delete client-side heuristic L29-32) — consumes
the Phase 11 API-03 contract finalized at the API layer; the corrected
total_bacino from this plan also flows to Phase 13 PublishersPage.

Plan 12-05 (CORR-08 weighted avgFillRate + sell_type dropdown) and Plan 12-06
(CORR-09 KpiCards i18n) remain Wave 2 — unblocked once Plan 12-02 (IT→EN)
lands.

## Self-Check: PASSED

- [x] `backend/api/publisher_routes.py` modified (bacino dedup hunk)
- [x] `backend/api/routes.py` modified (4 hunks: path variant + complete_dates + 7w YoY + available_dates)
- [x] `scripts/test_wip04_backend_correctness.py` created (298 lines, 4 tests)
- [x] Commit `c29673c` exists on main
- [x] Phase 11 surface byte-identical to ship-commits `3141591` + `510f5e2`
- [x] All acceptance grep cardinalities met
- [x] WIP-04 tests 4/4 GREEN; Phase 11 regression 13/13 GREEN
