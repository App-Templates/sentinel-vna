---
phase: 11-network-totals-endpoint-filter-api-server-side-baseline
verified: 2026-04-29T14:18:00Z
status: passed
score: 8/8 must-haves verified
overrides_applied: 0
re_verification: null
gaps: []
deferred: []
human_verification: []
---

# Phase 11: Network Totals Endpoint + Filter API + Server-Side Baseline — Verification Report

**Phase Goal:** PBI-parity dashboard totals via upstream-streaming endpoint; filter API supports sell_type_proxy; alert payload includes server-computed baselines.
**Verified:** 2026-04-29T14:18:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (merged from ROADMAP Success Criteria + 3 PLANs `must_haves.truths`)

| #   | Truth                                                                                                                                          | Status     | Evidence                                                                                                                                                                                                |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | ROADMAP SC#1 — `/api/metrics/network-totals?date=2026-01-12&channel=GOOGLE_ADEX` returns value matching PBI €27.2k gross within ±2%             | ✓ VERIFIED | Live smoke: `revenue_gross=27245.63`, inside [26656.00, 27744.00]; +0.17% vs PBI €27,200. `test_network_totals_pbi_parity.py` GREEN (4/4 in 2.292s).                                                       |
| 2   | ROADMAP SC#2 — `/api/publishers/top?sell_type=Open_Market` filters via channel_group mapping                                                    | ✓ VERIFIED | Live smoke: `sell_type_filter='Open_Market'`, `total_publishers=35`; invalid sell_type → 400; omitted → `sell_type_filter=null`. `test_sell_type_filter.py` GREEN (4/4 in 9.889s).                          |
| 3   | ROADMAP SC#3 — Alert payload contains `baseline_bacino` + `baseline_coverage` computed server-side, NOT derived client-side                     | ✓ VERIFIED | Live smoke ALT-20260123-010000-P2: `baseline_bacino=171503`, `baseline_coverage=0.8161` (matches RESEARCH §6 byte-identical). `test_alert_baseline_fields.py` GREEN (5/5).                                |
| 4   | Plan 11-02 — AlertDetail returns `baseline_bacino=None` and `baseline_coverage=None` for deprecated alerts or empty env_split — no panic, 200   | ✓ VERIFIED | `test_deprecated_alert_baseline_fields_none` GREEN; `_compute_baseline_from_env_split(None)` and `'{}'` return `(None, None)` — graceful path.                                                            |
| 5   | Plan 11-02 — Existing `test_health_alerts_pipeline.py` GREEN (no regression in adjacent endpoints)                                              | ✓ VERIFIED | Re-run 2026-04-29T14:16:17Z: 10/10 GREEN (`Ran 10 tests in 0.042s`).                                                                                                                                     |
| 6   | Plan 11-03 — Invalid sell_type literal (`Programmatic_Direct`) returns 400 with detail listing the 5 valid values                               | ✓ VERIFIED | `test_invalid_sell_type_returns_400` GREEN; live smoke `BadValue → 400`.                                                                                                                                  |
| 7   | Plan 11-03 — Omitted sell_type query param preserves existing behavior — no filter applied; `sell_type_filter` returned as None                 | ✓ VERIFIED | `test_no_filter_unchanged_behavior` GREEN; live smoke shows backwards compat returns 35 publishers + `sell_type_filter=null`.                                                                              |
| 8   | Plan 11-03 — Missing sell_type_proxy column in parquet returns HTTP 503 with diagnostic message (column guard wired)                            | ✓ VERIFIED | `grep -c '"sell_type_proxy" not in df.columns'` → 1 (publisher_routes.py:208). Live parquet has the column (Phase 08 SCHEMA-04), guard exists defensively for future ETL regression.                       |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact                                       | Expected                                                                                                | Status     | Details                                                                                                                                          |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `scripts/test_network_totals_pbi_parity.py`     | API-01 PBI-parity assertion — `PBI_TARGET_GROSS=27200` + 4 unittest methods                              | ✓ VERIFIED | Exists (153 lines); `PBI_TARGET_GROSS = 27200.0` present; 4 test methods discovered; GREEN at HEAD `68dbdec`.                                       |
| `scripts/test_sell_type_filter.py`              | API-02 filter assertion — 5-value whitelist verbatim, `sell_type_filter` transparency                    | ✓ VERIFIED | Exists (162 lines); 4 test methods; GREEN at HEAD.                                                                                                  |
| `scripts/test_alert_baseline_fields.py`         | API-03 schema assertion — top-level baseline_bacino/baseline_coverage, deprecated graceful, regression  | ✓ VERIFIED | Exists (265 lines); 5 test methods; GREEN at HEAD.                                                                                                  |
| `backend/api/schemas.py::NetworkTotalsResponse` | New Pydantic model with 9 fields + Field validators (date pattern, channel, revenue_gross ge=0)         | ✓ VERIFIED | `class NetworkTotalsResponse(BaseModel)` at line 151; verified import + import-time field set check.                                                |
| `backend/api/schemas.py::AlertDetail` extension | Add `baseline_bacino: Optional[int]` + `baseline_coverage: Optional[float]`                              | ✓ VERIFIED | Lines 88-89: `baseline_bacino: Optional[int] = None` / `baseline_coverage: Optional[float] = None`.                                                  |
| `backend/api/routes.py::network_totals`          | New endpoint reading raw `data/sentinel_db/daily_kpi.csv` via pyarrow column projection                  | ✓ VERIFIED | `@router.get("/metrics/network-totals", ...)` at line 911; 8.94M rows loaded (cached); whitelist at line 925; 404 range check; live verified.       |
| `backend/api/routes.py::_compute_baseline_from_env_split` | Pure aggregation helper, accepts JSON-string OR dict, `(None, None)` on empty/malformed       | ✓ VERIFIED | Defined at line 123; full try/except + isinstance guards verified by reading code.                                                                  |
| `backend/api/routes.py::get_alert` patch          | Wire helper into get_alert handler; add `data["baseline_bacino"]` / `data["baseline_coverage"]`         | ✓ VERIFIED | Lines 281-285 wire the call + dict assignments; live ALT-20260123-010000-P2 returns 171503 / 0.8161.                                                |
| `backend/api/publisher_routes.py::VALID_SELL_TYPES` | Module-level tuple (`Open_Market`, `Header_Bidding`, `Direct`, `Deal`, `Other`) verbatim from YAML  | ✓ VERIFIED | Line 37; comment points to `config/sell_type_proxy.yaml` SSOT.                                                                                       |
| `backend/api/publisher_routes.py::get_top_publishers` | sell_type Query param + 400 whitelist + 503 column guard + 3-path `sell_type_filter` echo         | ✓ VERIFIED | Lines 185, 199-227 (validation+filter), 232 (empty-year), 340 (success). Live verified all 3 polarities.                                              |

### Key Link Verification

| From                                              | To                                              | Via                                                                          | Status   | Details                                                                                          |
| ------------------------------------------------- | ----------------------------------------------- | ---------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------ |
| `scripts/test_network_totals_pbi_parity.py`        | `backend.main.app`                              | `TestClient(app).get('/api/metrics/network-totals?...')`                     | ✓ WIRED  | Test runs end-to-end via TestClient; GREEN.                                                       |
| `scripts/test_sell_type_filter.py`                 | `backend.main.app`                              | `TestClient(app).get('/api/publishers/top?sell_type=...')`                   | ✓ WIRED  | Test runs end-to-end; GREEN.                                                                       |
| `scripts/test_alert_baseline_fields.py`            | `backend.main.app`                              | `TestClient(app).get('/api/alerts/{alert_id}')`                              | ✓ WIRED  | Test runs end-to-end; live DB fixture discovery works.                                             |
| `routes.py::network_totals`                        | `data/sentinel_db/daily_kpi.csv`                | `pyarrow.csv.read_csv` with column projection + filter pushdown              | ✓ WIRED  | `import pyarrow.csv as pa_csv` at top of file; `pa_csv.read_csv(str(KPI_CSV_PATH), ...)` at line 195; live load logs `8937698 rows, max_date=2026-03-23`. |
| `routes.py::get_alert`                             | `_compute_baseline_from_env_split` helper       | `json.loads(environment_split_json) → aggregate`                              | ✓ WIRED  | Line 281 invokes helper; live ALT-20260123-010000-P2 returns expected aggregation.                  |
| `schemas.py::AlertDetail`                          | `frontend/src/components/alerts/TriageSection.tsx` (Phase 12) | New Optional fields available on contract; consumer landing in Phase 12       | ✓ WIRED (contract) | Contract shipped; consumer wiring intentionally deferred to Phase 12 per plan `<objective>` (RC-(e) closure split between API-03 contract here and frontend in P12). |
| `publisher_routes.py::get_top_publishers`           | `data/baseline/daily_aggregated.parquet sell_type_proxy` | `df = df[df["sell_type_proxy"] == sell_type]`                              | ✓ WIRED  | Line 216; live parquet has the column (Phase 08 SCHEMA-04); 35 publishers returned for Open_Market. |
| `publisher_routes.py::VALID_SELL_TYPES`             | `config/sell_type_proxy.yaml`                   | 5-value whitelist mirrors YAML keys verbatim                                  | ✓ WIRED  | Tuple matches YAML keys (Open_Market, Header_Bidding, Direct, Deal, Other). Drift risk noted in REVIEW WR-02 — mitigation deferred (info-only).      |

### Data-Flow Trace (Level 4)

| Artifact                          | Data Variable / Endpoint                         | Source                                       | Produces Real Data | Status      |
| --------------------------------- | ----------------------------------------------- | -------------------------------------------- | ------------------ | ----------- |
| `network_totals` endpoint          | `revenue_gross` from filtered pyarrow Table      | `data/sentinel_db/daily_kpi.csv` (8.94M rows) | Yes — €27,245.63   | ✓ FLOWING   |
| `network_totals` endpoint          | `impressions`                                    | same CSV                                      | Yes — 14,009,820   | ✓ FLOWING   |
| `network_totals` endpoint          | `measurable_impressions`                         | same CSV                                      | Yes — 13,795,596   | ✓ FLOWING   |
| `get_alert` `baseline_bacino`      | `data["environment_split"]` parsed from JSON     | `data/vna_alerts.db.alerts.environment_split_json` | Yes — 171,503 (live) | ✓ FLOWING   |
| `get_alert` `baseline_coverage`    | same env_split dict                              | same DB blob                                 | Yes — 0.8161 (live) | ✓ FLOWING   |
| `get_top_publishers` `publishers`  | filtered df_year                                 | `daily_aggregated.parquet` (5.04M rows)       | Yes — 35 rows for Open_Market | ✓ FLOWING   |
| `get_top_publishers` `sell_type_filter` | echo of param                                | request                                      | Yes — `Open_Market` round-trip | ✓ FLOWING   |

### Behavioral Spot-Checks

| Behavior                                                                                                       | Command                                                                                                                                | Result                                                                                       | Status   |
| -------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | -------- |
| API-01 PBI parity for Jan 12 GOOGLE_ADEX                                                                        | `TestClient.get('/api/metrics/network-totals?date=2026-01-12&channel=GOOGLE_ADEX')`                                                    | 200 + `revenue_gross=27245.63` (within [26656, 27744])                                       | ✓ PASS   |
| API-01 channel whitelist                                                                                        | `TestClient.get('/api/metrics/network-totals?date=2026-01-12&channel=BOGUS')`                                                          | (test harness) 400                                                                            | ✓ PASS   |
| API-01 out-of-range date                                                                                        | `TestClient.get('/api/metrics/network-totals?date=2099-01-01&channel=GOOGLE_ADEX')`                                                    | 404 (real reason: `date > _kpi_csv_max_date`)                                                | ✓ PASS   |
| API-02 Open_Market filter                                                                                       | `TestClient.get('/api/publishers/top?year=2026&sell_type=Open_Market')`                                                                | 200 + `sell_type_filter='Open_Market'` + 35 publishers                                       | ✓ PASS   |
| API-02 invalid sell_type                                                                                        | `TestClient.get('/api/publishers/top?year=2026&sell_type=BadValue')`                                                                   | 400                                                                                          | ✓ PASS   |
| API-02 backwards compat (no sell_type)                                                                          | `TestClient.get('/api/publishers/top?year=2026')`                                                                                      | 200 + `sell_type_filter=null` + 35 publishers                                                 | ✓ PASS   |
| API-03 baseline fields on real alert                                                                            | `TestClient.get('/api/alerts/ALT-20260123-010000-P2')`                                                                                  | 200 + `baseline_bacino=171503`, `baseline_coverage=0.8161`                                    | ✓ PASS   |
| Pre-Phase-11 non-regression on adjacent endpoint                                                                | `.venv/bin/python scripts/test_health_alerts_pipeline.py`                                                                              | 10/10 GREEN                                                                                  | ✓ PASS   |

### Requirements Coverage

| Requirement | Source Plan                | Description                                                                                                  | Status     | Evidence                                                                                                                                            |
| ----------- | -------------------------- | ------------------------------------------------------------------------------------------------------------ | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| API-01      | Plans 11-01, 11-02         | `/api/metrics/network-totals` reads `data/sentinel_db/*.csv` upstream via pyarrow streaming, bypassing top-50 | ✓ SATISFIED | Endpoint at routes.py:911; live test PBI parity 27245.63 (PBI €27,200 +0.17%); REQUIREMENTS.md line 34 marks `[x]`.                                  |
| API-02      | Plans 11-01, 11-03         | Query param `sell_type` via channel_group mapping (Phase 11 limits to `/api/publishers/top`; `/api/alerts` deferred to Phase 12) | ✓ SATISFIED | publisher_routes.py:185 + filter at 216; live test passes; REQUIREMENTS.md line 35 marks `[x]` with explicit Phase 12 deferral note.                  |
| API-03      | Plans 11-01, 11-02         | AlertDetail payload includes `baseline_bacino`, `baseline_coverage` server-computed (7w rolling same-weekday aggregation from env_split) | ✓ SATISFIED | schemas.py:88-89 + routes.py:281-285; live ALT-20260123-010000-P2 returns 171503/0.8161 byte-identical to RESEARCH §6; REQUIREMENTS.md line 36 marks `[x]`. |

**No orphaned requirements.** All Phase 11 requirement IDs from REQUIREMENTS.md (API-01, API-02, API-03) are claimed by at least one PLAN's `requirements:` field and verified satisfied.

**Note (informational, not a gap):** The traceability table at REQUIREMENTS.md lines 147-149 still lists API-01/02/03 as `Pending`, while the per-requirement bullets (lines 34-36) correctly show `[x]`. This is documentation drift between two parts of the same file — recommend updating during Phase 18 documentation pass. Does NOT affect Phase 11 goal achievement.

### Anti-Patterns Found

| File                                | Line  | Pattern                                            | Severity   | Impact                                                                                                                                                |
| ----------------------------------- | ----- | -------------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/api/routes.py`             | 90-93 | Hardcoded `NETWORK_TOTALS_CHANNELS` set duplicates `backend/db/models.py CHANNEL_GROUP_CHECK_VALUES` | ℹ️ Info    | REVIEW WR-01: drift risk on future migrations. Phase 11 does not regress today; HARD-03 drift gate covers SQL/enum but not this set. Tracked in REVIEW; not blocking. |
| `backend/api/publisher_routes.py`    | 37-43 | Hardcoded `VALID_SELL_TYPES` tuple duplicates `config/sell_type_proxy.yaml` keys                  | ℹ️ Info    | REVIEW WR-02: drift risk on v1.4 OPS-02. Comment in code points to YAML SSOT. Not blocking; recommend YAML-load for v1.4.                              |
| `backend/api/routes.py`             | 152-159 | `_compute_baseline_from_env_split` returns None for legitimate `total_bacino == 0`              | ℹ️ Info    | REVIEW WR-03: edge case — collapses "unknown" with "real zero". No live alert exhibits this; corner-case fix deferred.                                  |
| `backend/api/routes.py`             | 167-207 | Module-level cache globals lack concurrency guard on cold start                                  | ℹ️ Info    | REVIEW WR-04: latent race on first concurrent request to load 1.4 GB CSV. Pre-existing project pattern (matches `_load_hourly_data`). Not blocking; recommend single-flight lock or startup priming in Phase 18 hardening. |
| `backend/api/routes.py`             | 205-207 | `logger.error("...: %s", e)` instead of `logger.exception(...)`                                  | ℹ️ Info    | REVIEW IN-01: stack trace dropped. Pre-existing project pattern. Not blocking.                                                                          |

**Severity legend:** All findings classified as ℹ️ Info per REVIEW (depth=standard, 0 critical, 4 warnings, 7 info). No blocker found. No file in the Phase 11 diff contains TODO/FIXME placeholder code paths or empty-implementation returns. All anti-pattern matches above are documented in `11-REVIEW.md`; none block goal achievement.

### Pre-existing Regression (NOT Phase 11)

| File                                  | Test                                                                                  | Status               | Phase 11 impact |
| ------------------------------------- | ------------------------------------------------------------------------------------- | -------------------- | --------------- |
| `scripts/test_operations_idempotency.py` | `TestNotifierSaveToDbCanonicalFormat::test_save_to_db_returns_is_new_signal`           | ✗ PRE-EXISTING (10.1) | None — Phase 11 did NOT touch `agent/notifier.py` or `db/operations.py`. Failure reproduces at base `4b7f661` (pre-Phase-11). Already parked as backlog Phase 999.2 (see commit `68dbdec` — backlog promotion). NOT counted against Phase 11. |

### Human Verification Required

None. All success criteria for Phase 11 are programmatically verifiable:
- ROADMAP SC#1 verified by automated PBI bounds check.
- ROADMAP SC#2 verified by `sell_type_filter` round-trip + parquet column-flow.
- ROADMAP SC#3 verified by live aggregation against ALT-20260123-010000-P2 (numeric byte-identity vs RESEARCH §6).

Phase 12 will introduce frontend wiring (TriageSection consumes new fields) — at that time, Phase 12 verification will need a manual UI check. Phase 11 explicitly defers that wiring; the API contract is the only deliverable of this phase, and it is automatically verifiable.

### Gaps Summary

No gaps. All 8 must-haves verified, all 10 artifacts at all 3 levels (exists, substantive, wired) plus Level 4 data-flow, all 8 key links verified, all 3 requirement IDs (API-01/02/03) satisfied, all 8 behavioral spot-checks PASS, and the adjacent non-regression suite (`test_health_alerts_pipeline.py` 10/10) is GREEN.

The 4 warnings + 7 info findings from `11-REVIEW.md` are quality-improvement notes (drift risk on hardcoded whitelists, edge-case handling in zero-baseline collapse, concurrency cold-start, logging stacks). None block the phase goal — they are appropriately tracked in the REVIEW report and can be addressed in a future hardening pass (Phase 18 HARD-04 or a dedicated 11.1 if the operator chooses).

The single failing pre-existing test (`test_save_to_db_returns_is_new_signal`) is the parked Phase 999.2 backlog item from Phase 10.1 — not a Phase 11 regression.

**Phase 11 goal "PBI-parity dashboard totals via upstream-streaming endpoint; filter API supports sell_type_proxy; alert payload includes server-computed baselines" is achieved.**

---

_Verified: 2026-04-29T14:18:00Z_
_Verifier: Claude (gsd-verifier)_
