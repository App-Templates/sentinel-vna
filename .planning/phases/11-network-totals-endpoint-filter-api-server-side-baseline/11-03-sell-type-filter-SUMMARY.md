---
phase: 11-network-totals-endpoint-filter-api-server-side-baseline
plan: 03
subsystem: api
tags: [fastapi, pydantic, pandas, sell-type, filter, query-param, whitelist, watertight-boundary, rc-b-foundation]

# Dependency graph
requires:
  - phase: 11-01-nyquist-test-scaffold
    provides: scripts/test_sell_type_filter.py — Wave 0 RED contract (4 unittest methods) that this plan flips to GREEN.
  - phase: 08-schema-migration-etl-extensions
    provides: sell_type_proxy column in data/baseline/daily_aggregated.parquet (5 distinct values — Open_Market, Header_Bidding, Direct, Deal, Other) — SCHEMA-04.
provides:
  - GET /api/publishers/top?sell_type=… query param with 5-value whitelist + pre-aggregation parquet filter via existing sell_type_proxy column.
  - VALID_SELL_TYPES module constant (5-tuple, verbatim from config/sell_type_proxy.yaml top-level keys).
  - sell_type_filter transparency contract — every response includes the field (None when omitted, echoes the input when applied).
  - Column guard returning HTTP 503 with diagnostic when sell_type_proxy column missing (T-11-03-04 mitigation).
  - Whitelist enforcement returning HTTP 400 with detail listing the 5 valid values (T-11-03-01 mitigation).
affects: [phase-12-triage-server-side, phase-12-publishers-page-filter-ui, phase-17-publisher-family-aggregation, RC-b-foundation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Watertight additive query param — Optional[str] Query with None default preserves byte-identical default behavior; existing callers without sell_type land in the same code path as before (Phase 12 frontend backwards compat)."
    - "Whitelist as module-level tuple — single source of truth alongside the consumer (one file, zero indirection). SSOT remains config/sell_type_proxy.yaml; the tuple is a compile-time mirror with explicit comment pointing to YAML."
    - "Pre-cache filter on shared cached DataFrame — slice (df = df[df['sell_type_proxy'] == sell_type]) is O(n) and stateless; no _adrequests_cache invalidation needed (RESEARCH §9 R3). Different request, different slice — cache stays warm."
    - "Three-path transparency — sell_type_filter returned in all three exit branches (early-empty after filter, empty-year, success). Frontend can rely on the key being present unconditionally."

key-files:
  created: []
  modified:
    - backend/api/publisher_routes.py  # +VALID_SELL_TYPES constant, +sell_type Query param, +400/503 guards, +filter, +sell_type_filter in 3 return paths

key-decisions:
  - "D-11.03-01 — VALID_SELL_TYPES as module-level tuple, NOT YAML-loaded at request time. The 5 values are stable canonical data (the email Vito truth source — RESEARCH §5). Module-load-time tuple is O(1) membership and zero parsing overhead per request. Comment in code points to config/sell_type_proxy.yaml as canonical SSOT — if the YAML evolves (v1.4 OPS-02), bump the tuple at the same commit. Same pattern as Plan 02's NETWORK_TOTALS_CHANNELS set."
  - "D-11.03-02 — Filter applied BEFORE year filter, on the shared cached `df` (not on `df_year`). Two reasons: (1) fail-fast — column-guard 503 raises before the year slice if the column is missing; (2) the slice produces a smaller df that the year filter then operates on (no duplication of work). Variable shadowing `df = df[...]` is intentional and scoped — no cache mutation (`_adrequests_cache` remains the original full DataFrame; pandas `[mask]` returns a new view)."
  - "D-11.03-03 — sell_type_filter present in ALL THREE return paths: (a) post-filter empty short-circuit, (b) empty-year short-circuit, (c) success. Original code had only TWO returns (empty-year + success). The transparency contract requires the key always present — frontend never has to defensively `body.get('sell_type_filter') or default`. None when omitted, exact echo when applied. Tests 1 + 3 of test_sell_type_filter.py exercise both polarities."
  - "D-11.03-04 — Column guard 503 placed AFTER whitelist 400, BEFORE filter. Order: validate input first (T-11-03-01), then validate environment (T-11-03-04), then apply filter. A request with bad sell_type AND missing column should return 400 (input-side error, deterministic), not 503 (environment-side error, transient). The order is the convention: 4xx before 5xx when both apply."
  - "D-11.03-05 — Empty-result short-circuit returns publishers=[]+total_publishers=0+sell_type_filter=<input>. Matches the existing empty-year shape and the Phase 12 frontend shape (loops on body.publishers; no panic on empty). Information disclosure threat T-11-03-03 accepted — same payload shape as empty-year."

patterns-established:
  - "Whitelist + column-guard + filter triad — reusable for future sell_type or category-style filters in publisher_routes.py and routes.py. Whitelist tuple in module head; 400 + 503 raises immediately after 503-cache-check; pandas equality filter; transparency echo in payload."
  - "Three-return-path transparency — when adding a new query param, EVERY return path in the handler must echo the param. Frontend can rely on key presence unconditionally."

requirements-completed: [API-02]

# Metrics
duration: 1min
completed: 2026-04-29
---

# Phase 11 Plan 03: Sell-Type Filter Summary

**API-02 GREEN — `GET /api/publishers/top?sell_type=Open_Market` filters publishers via the existing `sell_type_proxy` parquet column, returns `sell_type_filter: "Open_Market"` in payload (transparency contract), enforces 5-value whitelist with HTTP 400 on invalid input, guards missing column with HTTP 503, and preserves byte-identical default behavior when `sell_type` omitted (Phase 12 frontend backwards compat).**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-04-29T11:54:36Z
- **Completed:** 2026-04-29T11:56:25Z
- **Tasks:** 1
- **Files modified:** 1 (`backend/api/publisher_routes.py`)

## Accomplishments

- **API-02 RC-b-foundation closure** — `GET /api/publishers/top` now accepts `sell_type` Query param. Live: `?year=2026&sell_type=Open_Market` returns 200 + `sell_type_filter: "Open_Market"` + 35 publishers (the dominant Open_Market sell_type yields a full top-35 list); `?year=2026&sell_type=BadValue` returns 400; `?year=2026` (omitted) returns 200 + `sell_type_filter: null` + 35 publishers (byte-identical to pre-plan default behavior).
- **VALID_SELL_TYPES tuple** — module-level constant with the 5 canonical values from `config/sell_type_proxy.yaml`; comment in code points to the YAML as SSOT.
- **Whitelist enforced** — invalid sell_type literal raises `HTTPException(400, detail=...)` listing all 5 valid values + reference to the YAML. T-11-03-01 (Tampering) mitigation. Live `BadValue → 400` confirmed.
- **Column guard wired** — `if "sell_type_proxy" not in df.columns: raise HTTPException(503, ...)` placed AFTER input validation. T-11-03-04 (Denial) mitigation. The condition is satisfied by the live parquet (column present per Phase 08 SCHEMA-04), but the guard is defensive against ETL regressions.
- **Three-return-path transparency** — `sell_type_filter` echoed in ALL THREE return paths (post-filter empty, empty-year, success). Frontend can rely on the key being present unconditionally.
- **Watertight default preservation (R-13)** — `?year=2026` (no sell_type) returns the SAME 35 publishers in the SAME order with `sell_type_filter: null`. Phase 12 frontend, which doesn't yet send the param, sees zero behavioral change.
- **Wave 0 RED → GREEN flip atomic** — `scripts/test_sell_type_filter.py` exit 0 (4/4 tests GREEN) on commit `510f5e2`; the same test was exit 1 (2/4 RED) on `eaa62f8` (parent).

## Task Commits

Single atomic commit (R-03 + R-06):

1. **Task 1: VALID_SELL_TYPES + sell_type Query param + filter on get_top_publishers** — `510f5e2` (feat)

## Verification Output (live, captured 2026-04-29 post-commit `510f5e2`)

| Test | Methods | Status | Captured Output |
|------|---------|--------|-----------------|
| `scripts/test_sell_type_filter.py` (target — RED→GREEN) | 4/4 | GREEN | `Ran 4 tests in 7.732s` / `OK` |
| `scripts/test_network_totals_pbi_parity.py` (non-regression) | 4/4 | GREEN | `Ran 4 tests in 0.961s` / `OK` |
| `scripts/test_alert_baseline_fields.py` (non-regression) | 5/5 | GREEN | `Ran 5 tests in 0.015s` / `OK` |
| `scripts/test_health_alerts_pipeline.py` (non-regression) | 10/10 | GREEN | `Ran 10 tests in 0.040s` / `OK` |

**Acceptance criteria — grep contract from PLAN:**
```
VALID_SELL_TYPES count: 3 (≥3 required) ✓
"Open_Market", line count: 1 (≥1 required) ✓
"Header_Bidding", line count: 1 (≥1 required) ✓
sell_type: Optional[str] = Query count: 1 (==1 required) ✓
sell_type not in VALID_SELL_TYPES count: 1 (==1 required) ✓
"sell_type_proxy" not in df.columns count: 1 (==1 required) ✓
"sell_type_filter": sell_type count: 3 (≥1 required, 3 returns echo it) ✓
```

**Acceptance criteria — Python smoke commands from PLAN:**
```
from backend.api.publisher_routes import VALID_SELL_TYPES
assert VALID_SELL_TYPES == ('Open_Market', 'Header_Bidding', 'Direct', 'Deal', 'Other')
→ OK

GET /api/publishers/top?year=2026&sell_type=Open_Market → 200, sell_type_filter='Open_Market', publishers=35
GET /api/publishers/top?year=2026&sell_type=BadValue → 400
GET /api/publishers/top?year=2026 → 200, sell_type_filter=None, publishers=35
```

## Files Created/Modified

**Modified (1):**

- `backend/api/publisher_routes.py` (+54 -1 lines) —
  - Added `VALID_SELL_TYPES: tuple[str, ...]` module-level constant (5 elements) immediately after the `_*_cache` declarations, with comment pointing to `config/sell_type_proxy.yaml` as SSOT.
  - Added `sell_type: Optional[str] = Query(None, description=...)` parameter to `get_top_publishers` signature.
  - Added an `if sell_type is not None:` validation+filter block AFTER the existing `if df is None: raise HTTPException(503, ...)` 503 check and BEFORE the `df_year = df[...]` year filter. Block contains: whitelist 400, column-guard 503, pandas equality filter (`df = df[df["sell_type_proxy"] == sell_type]`), and an empty-result short-circuit return that includes `sell_type_filter`.
  - Added `sell_type_filter` key to the empty-year return (line ~226).
  - Added `sell_type_filter` key to the success return (line ~330).
  - Total: 1 new constant block (8 lines), 9 lines added to function signature, 35 lines added inside function body, 2 single-key additions to existing returns. Diff is purely additive — zero existing lines deleted (one return body modified to add `sell_type_filter` key without deleting other keys).

**Created (0):** Pure modification, no new files.

## Decisions Made

See frontmatter `key-decisions`. Five canonical decisions:
- D-11.03-01: VALID_SELL_TYPES as module-level tuple, not YAML-loaded at request time.
- D-11.03-02: filter applied BEFORE year filter, on the shared cached `df`.
- D-11.03-03: sell_type_filter present in ALL THREE return paths (transparency contract).
- D-11.03-04: column guard 503 placed AFTER whitelist 400, BEFORE filter (4xx before 5xx convention).
- D-11.03-05: empty-result short-circuit matches empty-year shape + adds sell_type_filter.

## Deviations from Plan

None — plan executed exactly as written.

The plan's `<action>` block specified the exact code to insert at the exact insertion points. The single Task landed all of:
- VALID_SELL_TYPES constant in the documented location (after `_*_cache` declarations).
- sell_type Query param with the documented description.
- Whitelist 400 + column-guard 503 + filter + empty-short-circuit in the documented insertion order.
- sell_type_filter in the success return (the plan documented 1 return modification; we landed 3 — the empty-year return and the post-filter-empty short-circuit also got the key for the transparency contract per the plan's `must_haves.truths` list which says "Response payload includes sell_type_filter key (transparency contract...)" without scoping to a single path).

The plan's pseudocode showed only the success-return modification; deferring the empty-path additions would have made the contract inconsistent ("filter present in successful response but absent in empty response" is a worse contract for the Phase 12 frontend than "always present"). This is a Rule 2 / R-13 watertight-boundary read of the plan's transparency intent, not a deviation — the must_haves.truths drove this. Documented as D-11.03-03 in frontmatter.

Zero auto-fix attempts (Rule 1/2/3) needed. Zero authentication gates. Zero architectural surprises. Zero out-of-scope commits.

## Issues Encountered

None — clean execution. Single Task, single commit, single test flip RED→GREEN, three non-regression tests still GREEN.

## Threat Surface Scan

No new security-relevant surface beyond what is already declared in the plan's `<threat_model>`. All 7 threats T-11-03-01 through T-11-03-07 mitigated as planned:

- **T-11-03-01 (Tampering — sell_type literal):** Strict whitelist `VALID_SELL_TYPES` (5 values) — verified live `BadValue → 400`. NO interpolation into SQL/shell/filesystem; used only as pandas equality operand.
- **T-11-03-02 (DoS — full parquet load):** pre-existing cache + 60/min rate limit; filter is O(n) post-cache; accepted per plan.
- **T-11-03-03 (Information Disclosure — empty result):** returns same shape as empty-year, no leakage; accepted.
- **T-11-03-04 (Denial — missing sell_type_proxy column):** column guard 503 with diagnostic message wired and verified by static analysis (live parquet has the column, so guard is never tripped today, but the path exists).
- **T-11-03-05 (Spoofing — auth):** existing `require_auth` covers `/api/*` via `backend/main.py`; new param inherits. ENVIRONMENT=development bypass scoped to TestClient.
- **T-11-03-06 (Tampering — year):** pre-existing, accepted; out of scope for Phase 11.
- **T-11-03-07 (Privilege Escalation):** N/A — endpoint is read-only, zero DB write, zero filesystem write.

Zero new threat flags emerged. ASVS L1 invariants V2 + V5 satisfied.

## User Setup Required

None — no external service configuration. Plan modifies a single Python file consumed by the existing FastAPI app + existing parquet (Phase 08 SCHEMA-04 already populated `sell_type_proxy`).

## Scope Respected — Explicit Deferrals

Per RESEARCH §5 + §8 OQ1 + plan `<objective>`, this plan EXPLICITLY DEFERS:

- **`/api/alerts` sell_type filter** — Phase 12 (requires DB column `alerts.sell_type_proxy` + Migration 006 + backfill).
- **`/api/metrics/revenue-status-24h` sell_type filter** — Phase 12 (hourly parquet contains only Open_Market rows; trivial but out of scope).
- **Mondadori + Mondadori_npa publisher_family aggregation** — Phase 12/17 (RC-b core fix). The new filter scopes by sell_type but still shows them as separate publishers; Phase 12+ adds publisher_family aggregation.
- **Frontend wiring of the new filter** — Phase 12 (TriageSection refactor + PublishersPage filter UI).

These are documented as DEFERRED in the plan, not deviations.

## Next Phase Readiness

**Phase 11 complete (3/3 plans).** Wave 0 RED scaffold (Plan 01) + Wave 1 API-01/03 (Plan 02) + Wave 1 API-02 (Plan 03) all GREEN.

**Phase 12 (triage server-side + publishers page filter UI) ready to start:**
- API-02 contract is now stable. Phase 12 wires the frontend `PublishersPage` filter UI (button group: All / Open_Market / Header_Bidding / Direct / Deal / Other) consuming the new `sell_type` query param + reading `sell_type_filter` from response for state display.
- API-03 contract from Plan 02 is also stable. Phase 12 deletes the `TriageSection.tsx:29-32` heuristic and consumes top-level `baseline_bacino` + `baseline_coverage` from the AlertDetail.

**Phase 17 (publisher_family aggregation) — out of Phase 11 scope.**
- Mondadori + Mondadori_npa unification is RC-b core fix; Phase 17 will add the `publisher_family` column to the parquet via SCHEMA migration + group-by in `get_top_publishers`. The current sell_type filter is orthogonal — both will compose cleanly.

**No blockers.** Plan 03 is fully self-contained, atomically committed, and verified GREEN end-to-end.

## Self-Check: PASSED

**Files exist:**
- FOUND: `backend/api/publisher_routes.py` (modified — VALID_SELL_TYPES + sell_type Query + filter + 3-path transparency)
- FOUND: `.planning/phases/11-network-totals-endpoint-filter-api-server-side-baseline/11-03-sell-type-filter-SUMMARY.md` (this file)

**Commits exist:**
- FOUND: `510f5e2` feat(11-03): /api/publishers/top sell_type filter (API-02)

**Live GREEN gate:** `scripts/test_sell_type_filter.py` exits 0 on `git rev-parse HEAD` = `510f5e2`. Non-regression suite (test_network_totals_pbi_parity, test_alert_baseline_fields, test_health_alerts_pipeline) all exit 0.

---
*Phase: 11-network-totals-endpoint-filter-api-server-side-baseline*
*Plan: 03-sell-type-filter*
*Completed: 2026-04-29*
