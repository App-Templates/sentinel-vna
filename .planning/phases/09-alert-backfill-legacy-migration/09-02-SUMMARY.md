---
phase: 09-alert-backfill-legacy-migration
plan: 02
subsystem: database

tags: [sqlite, migration, soft-delete, idempotent, tdd, migrate-01]

# Dependency graph
requires:
  - phase: 09-alert-backfill-legacy-migration
    plan: 01
    provides: "alerts.deprecated + alerts.deprecation_reason columns; 200 legacy rows with deprecated=0 inherited via DEFAULT; idx_alerts_deprecated; HARD-03 17-test drift gate; pre-phase-09 tag + .bak"
provides:
  - "200 legacy alerts (timestamp < 2026-02-01 AND channel_group IN ('GOOGLE','OPEN_BIDDING')) flipped to deprecated=1 with D-15 canonical reason text"
  - "scripts/deprecate_legacy_alerts.py — idempotent one-shot UPDATE script (--dry-run + --db-path + IDEMPOTENT-NOOP on re-run)"
  - "scripts/test_deprecate_legacy_alerts.py — 12-test fixture suite (cutoff + channel whitelist + idempotency + dry-run + exit codes + reason text byte-match)"
  - "data/vna_alerts.db with MIGRATE-01 applied (200/200 deprecated=1, 0/200 deprecated=0, single distinct reason)"
  - "scripts/test_migration_002_apply.py evolved to post-09-02 state assertions (deprecated=1 + D-15 reason byte-match)"
affects:
  - "09-03-backfill (backfill appends fresh alerts with deprecated=0 inherited from DEFAULT; they appear in /api/alerts default list while legacy remains hidden behind ?include_deprecated=true in plan 09-03 API filter)"
  - "10-monitoring (MONITOR-03 alerts_written_count semantics unaffected — deprecated alerts still count as writes)"
  - "14-ui-labeling (CORR-05/06 UI surfacing of deprecation badge — 200-row corpus available)"

# Tech tracking
tech-stack:
  added: []  # stdlib only — sqlite3 + argparse + fcntl + subprocess + unittest
  patterns:
    - "Belt-and-suspenders WHERE clause for soft-delete migrations (date cutoff AND channel whitelist — triple guard with `AND deprecated=0` idempotency clause)"
    - "Parameterized IN-clause via `','.join('?' * len(tuple))` + tuple spread — zero SQL-injection risk, no string concat into SQL body"
    - "lsof + fcntl.LOCK_EX live-DB-only guard pattern (skip on non-live DBs for tempfile test isolation) — reusable template for future one-shot DB scripts"
    - "TDD RED-then-GREEN with tempfile fixture subprocess invocation (no live-DB pollution in tests)"
    - "Schema lifecycle test evolution: smoke-suite assertions track state transitions across sibling plans (09-01 deprecated=0 → 09-02 deprecated=1)"

key-files:
  created:
    - "scripts/deprecate_legacy_alerts.py"
    - "scripts/test_deprecate_legacy_alerts.py"
  modified:
    - "data/vna_alerts.db (200 rows flipped deprecated=0 → 1 + reason text)"
    - "scripts/test_migration_002_apply.py (2 test methods renamed + assertions evolved to post-09-02 state)"

key-decisions:
  - "ERRATA I-1 applied: severity is an explicit 4th FIXTURE_ROWS column, not derived via rsplit('-', 1)[-1] — less fragile for future fixture additions, clearer intent"
  - "Lock-file sidecars (*.deprecate.lock / *.apply.lock) left untracked (0-byte ephemeral flock artifacts) — not added to .gitignore in this commit to avoid touching WIP-modified .gitignore (separate concern)"
  - "test_migration_002_apply.py assertions evolved in-place (not new test methods) — the pre-09-02 state is no longer reachable on the live DB; keeping the stale assertions would permanently red-flag the suite. Test names updated: *_all_deprecated_zero → *_all_deprecated_one; *_all_deprecation_reason_null → *_all_deprecation_reason_d15"
  - "WAL sidecar churn (-shm / -wal now in WIP as deletions, were WIP-modified pre-session): left unstaged, consistent with 09-01 precedent that committed only the main DB file"

patterns-established:
  - "Idempotency via `AND deprecated = 0` clause in BOTH count-candidates and UPDATE queries: second run matches 0 rows, NOT 200 rows that no-op — the query plan physically skips them. IDEMPOTENT-NOOP is a distinct codepath, not an incidental rowcount=0."
  - "Dry-run prints `DRY RUN: N rows would be deprecated` with the EXACT candidate count — enables pre-commit UAT to verify expected scope before mutation."
  - "Plan 09-02 introduces a state transition that invalidates 2 assertions in plan 09-01's smoke suite — demonstrates the Phase 18 CI strategy must handle schema-lifecycle evolution across sibling plans (not just in-phase drift)."

requirements-completed:
  - MIGRATE-01

# Metrics
duration: 6min22s
completed: 2026-04-23
---

# Phase 09 Plan 02: MIGRATE-01 Legacy Alert Deprecation Summary

**200 pre-v1.2 legacy alerts soft-deleted: `deprecated=1` + D-15 canonical reason text applied atomically via idempotent one-shot script; belt-and-suspenders filter (timestamp < 2026-02-01 AND channel_group IN legacy whitelist) verified against all 200 rows; 12-test fixture suite green; zero over-deprecation, zero wrong-channel deprecation.**

## Performance

- **Duration:** 6 min 22 s
- **Started:** 2026-04-23T13:28:30Z
- **Completed:** 2026-04-23T13:34:52Z
- **Tasks:** 3 atomic commits (Task 1 TDD RED + Task 2 TDD GREEN + Task 3 live apply)
- **Files modified:** 3 (2 created + 1 test evolved + 1 DB binary)

## Accomplishments

- MIGRATE-01 requirement closed: 200/200 legacy alerts now have `deprecated=1` + stable D-15 reason text (`v1.0 schema stale: legacy channel naming + v1.2 baseline divergence (Phase 09 deprecation)`).
- Belt-and-suspenders filter proven: zero over-deprecation (no rows with ts >= cutoff flipped), zero wrong-channel deprecation (no rows outside `{GOOGLE, OPEN_BIDDING}` touched).
- TDD-authored script: `scripts/deprecate_legacy_alerts.py` — 12-test fixture suite (cutoff, channel whitelist, idempotency, dry-run, exit codes, reason byte-match) all green.
- Idempotency verified end-to-end: second invocation against live DB logs `IDEMPOTENT-NOOP`, exits 0, DB byte-unchanged.
- HARD-03 drift detector stays green (17/17) and 002 smoke suite evolved to post-09-02 invariant (11/11 green after in-place test update).

## Task Commits

Each task committed atomically:

1. **Task 1: Author test suite (TDD RED)** — `019f010` (test)
2. **Task 2: Author script (TDD GREEN — 12/12)** — `5fbf670` (feat)
3. **Task 3: Apply MIGRATE-01 to live DB + smoke-suite evolution** — `1518e81` (feat)

**Plan metadata commit:** Pending (final docs commit for SUMMARY + STATE + ROADMAP).

## Pre/Post State — Live DB

| Metric | Pre-apply (post-09-01) | Post-apply (1518e81) |
|--------|------------------------|----------------------|
| Total rows | 200 | 200 |
| deprecated=0 | 200 | 0 |
| deprecated=1 | 0 | 200 |
| deprecation_reason IS NULL | 200 | 0 |
| deprecation_reason = D-15 canonical | 0 | 200 |
| Distinct deprecation_reason | 0 | 1 |
| deprecated=1 AND channel_group='GOOGLE' | 0 | 107 |
| deprecated=1 AND channel_group='OPEN_BIDDING' | 0 | 93 |
| deprecated=1 AND ts >= '2026-02-01T00:00:00' | 0 | 0 (zero over-deprecation) |
| deprecated=1 AND channel NOT IN ('GOOGLE','OPEN_BIDDING') | 0 | 0 (channel whitelist honored) |
| MIN(ts) for deprecated=1 | — | 2024-02-01T14:15:14 |
| MAX(ts) for deprecated=1 | — | 2026-01-22T14:39:40 |

## Reason Text (D-15 Canonical)

```
v1.0 schema stale: legacy channel naming + v1.2 baseline divergence (Phase 09 deprecation)
```

Byte-for-byte verified against all 200 affected rows via `SELECT COUNT(*) FROM alerts WHERE deprecation_reason = '<literal>'` returning exactly `200`.

## Idempotency Proof

```
$ .venv/bin/python scripts/deprecate_legacy_alerts.py
[15:31:47] MIGRATE-01 deprecation — DB=.../data/vna_alerts.db
[15:31:47] Candidate rows (timestamp < 2026-02-01T00:00:00 AND channel IN ('GOOGLE', 'OPEN_BIDDING') AND deprecated=0): 0
IDEMPOTENT-NOOP: no candidate rows found (deprecation already applied or no legacy alerts).
# exit 0
```

Post-apply `--dry-run` also prints `DRY RUN: 0 rows would be deprecated`, confirming the candidate set is empty even for a read-only check.

## Test Suite Results

| Suite | Tests | Status | Notes |
|-------|-------|--------|-------|
| `scripts/test_deprecate_legacy_alerts.py` | 12 | OK | TDD contract suite — all green (RED at commit 019f010, GREEN at 5fbf670 onward) |
| `scripts/test_models_sync.py` | 17 | OK | HARD-03 drift gate — no regression |
| `scripts/test_migration_002_apply.py` | 11 | OK | Evolved 2 assertions in-place to reflect post-09-02 lifecycle state (see Decisions) |

## Files Created/Modified

- `scripts/deprecate_legacy_alerts.py` — 192-line idempotent one-shot UPDATE script (lsof + flock on live DB; --dry-run + --db-path; IDEMPOTENT-NOOP exit 0)
- `scripts/test_deprecate_legacy_alerts.py` — 239-line TDD contract suite, 12 tests, tempfile fixture with 7-row seed (3 should-deprecate + 4 should-NOT-deprecate)
- `scripts/test_migration_002_apply.py` — renamed + re-asserted 2 methods (`_all_deprecated_zero` → `_all_deprecated_one`; `_all_deprecation_reason_null` → `_all_deprecation_reason_d15`) to track the lifecycle transition
- `data/vna_alerts.db` — 200 rows flipped deprecated=0→1 with D-15 reason; byte delta only in the 200 affected row slots + their updated SQLite pages

## Decisions Made

- **ERRATA I-1 applied (severity as explicit 4th fixture column):** passed through cleanly — fixture rows are less fragile for future additions. The severity in FIXTURE_ROWS is used directly in the INSERT, no rsplit-based derivation.
- **ERRATA I-3 (transient empty-list note in Task 3 `<done>`):** Context only — executors are informed that between 09-02 commit and 09-03 completion, `/api/alerts` will return an empty list by default (all 200 alerts now deprecated=1; no new alerts written yet). This is expected UI-observer transient state; backfill in 09-03 will populate the default list with fresh alerts.
- **Lock-file sidecars not gitignored in this commit:** `data/vna_alerts.db.*.lock` are 0-byte flock artifacts. Adding them to `.gitignore` would require touching the WIP-modified `.gitignore` file, which risks WIP contamination. Deleted locally post-apply; will be regenerated on next script invocation. Cleaner to handle gitignore in a separate WIP-cleanup commit outside this plan.
- **test_migration_002_apply.py in-place evolution (not net-new tests):** The two assertions encoded a transient post-09-01 / pre-09-02 state that no longer exists on the live DB. Keeping them as red-flagged assertions would permanently poison the smoke suite. Renaming + re-asserting in the same commit as the DB mutation keeps the test file coherent with the schema lifecycle (tightly coupled change).
- **WAL sidecars (`-shm`/`-wal`) left unstaged:** They appeared in WIP as deletions after SQLite cleaned them up on connection close. They pre-existed as WIP-modified, now they're WIP-deleted — no net new WIP touched. Consistent with 09-01 precedent (commit 8d837bb only staged the main DB).

## Deviations from Plan

### Acceptance-criterion interpretation (Task 1)

**1. [Rule 3 — Blocking] RED-state fail count below the strict ≥12 threshold**
- **Found during:** Task 1 acceptance verification.
- **Issue:** The plan's RED acceptance criterion required `grep -cE "FAIL|ERROR" ≥ 12`. Actual result: 9 explicit FAIL lines (3 of the 12 tests pass trivially in RED because they assert "row STAYS deprecated=0" — a state already satisfied by the seed fixture, regardless of whether the script exists). These 3 tests become load-bearing in GREEN (they must STILL stay deprecated=0 after the script runs, proving the belt-and-suspenders filter excludes them).
- **Fix:** Accepted the 9/12 RED state as sufficient evidence of TDD-RED (script absence is the primary RED signal — `subprocess.run` on a non-existent file produces exit code 2 and stderr `No such file or directory`; the 9 failing tests are all triggered by this). Documented in commit 019f010 message. Not a test-suite bug; a minor over-specification in the plan acceptance criterion.
- **Verification:** After Task 2 GREEN, all 12 tests pass (`Ran 12 tests in 0.555s — OK`) — the 3 initially-passing tests remain green, confirming they are now load-bearing (filter excludes them even though the UPDATE ran).
- **Committed in:** `019f010` (documented in commit message).

### Test-suite evolution (Task 3)

**2. [Rule 2 — Missing critical test coverage for new state] smoke-suite assertions evolved**
- **Found during:** Task 3 Step 7 regression run of `scripts/test_migration_002_apply.py`.
- **Issue:** Two tests in the 09-01 smoke suite (`test_existing_200_rows_all_deprecated_zero`, `test_existing_200_rows_all_deprecation_reason_null`) asserted the exact state that plan 09-02 is designed to mutate. Failing them with `FAILED (failures=2)` would leave a permanent red regression in the phase-09 CI posture — deprecated=0/reason=NULL is no longer reachable on the live DB post-09-02.
- **Fix:** Renamed the 2 tests and flipped the assertions to the post-09-02 invariant (deprecated=1 + D-15 canonical reason byte-match). Committed inline with the DB mutation (same commit as the state transition they track — tightly coupled).
- **Files modified:** `scripts/test_migration_002_apply.py`
- **Verification:** `scripts/test_migration_002_apply.py` — Ran 11 tests, OK.
- **Committed in:** `1518e81` (same commit as Task 3 live DB mutation).

---

**Total deviations:** 2 — 1 plan-acceptance-criterion interpretation (Rule 3), 1 test-suite schema-lifecycle evolution (Rule 2). No Rule 1 (bug) or Rule 4 (architectural) items. Zero scope creep.

**Impact on plan:** Both deviations are narrow and unblocking. The test-suite evolution is strictly necessary for CI green posture; the acceptance-criterion interpretation is cosmetic (doesn't affect the TDD RED-then-GREEN workflow correctness).

## Issues Encountered

- **Flock sidecar files in repo root:** `*.apply.lock` and `*.deprecate.lock` left as untracked 0-byte files post-apply. Resolved by local `rm -f` (they're regenerated on demand). Not added to `.gitignore` in this commit to preserve WIP-modified `.gitignore` integrity.
- **WAL sidecars transitioned from M to D status in WIP:** `data/vna_alerts.db-shm` / `-wal` were `M` (modified) before this session; after our script's clean-close cycle, SQLite checkpointed the WAL and the OS removed them, now showing as `D` (deleted) in WIP. Not staged — same WIP, different status label. Consistent with 09-01 precedent.

## User Setup Required

None — no external service configuration. The script runs locally against `data/vna_alerts.db` with no network / auth dependencies.

## Known Stubs

None. The plan delivered the full UPDATE + idempotent re-run guard + test suite. No placeholder data, no "coming soon" paths.

## Threat Mitigations Verified

From plan `<threat_model>`:

- **T-09-02-01 (Tampering, over-deprecation):** Post-apply SQL `SELECT COUNT(*) FROM alerts WHERE deprecated=1 AND timestamp >= '2026-02-01T00:00:00'` returns `0`. Also verified `SELECT COUNT(*) FROM alerts WHERE deprecated=1 AND channel_group NOT IN ('GOOGLE','OPEN_BIDDING')` returns `0`. Three fixture tests (boundary-exclusive, modern-channel-excluded, DIRECT-excluded) encode this invariant in the test suite.
- **T-09-02-02 (Repudiation):** Single distinct `deprecation_reason` value (`SELECT COUNT(DISTINCT deprecation_reason) FROM alerts WHERE deprecated=1` = 1); value matches D-15 byte-for-byte (200/200 rows). Audit trail recoverable via `SELECT alert_id, timestamp, channel_group FROM alerts WHERE deprecation_reason LIKE '%Phase 09%'` returning all 200 affected rows.
- **T-09-02-03 (Tampering, SQL injection):** LEGACY_CHANNELS tuple is expanded via `','.join('?' * N)` + parameter spread `(..., *LEGACY_CHANNELS)` — zero user input reaches SQL as string concatenation. CUTOFF_TIMESTAMP and DEPRECATION_REASON are module constants, parameterized via `?` bind. `--db-path` goes to `sqlite3.connect(str(db_path))` — no SQL synthesis.
- **T-09-02-04 (DoS, wrong DB):** `--db-path` is explicit opt-in (default is live `data/vna_alerts.db`). `_check_lsof` aborts on concurrent handle; `_acquire_lock` (fcntl.LOCK_EX) prevents concurrent self-invocation.
- **T-09-02-05 (Info disclosure of reason text):** Accepted — text is Phase 09 internal, not PII. API filter in plan 09-03 will hide deprecated alerts from `/api/alerts` default response.
- **T-09-02-06 (EoP):** Accepted — dev-run one-shot. Idempotency guard (`AND deprecated = 0`) ensures no harm on accidental re-run.
- **T-09-02-07 (Future re-run flips modern alerts):** Timestamp literal `'2026-02-01T00:00:00'` is FIXED — alerts with ts >= cutoff NEVER match. `AND deprecated = 0` further narrows to rows that have not been touched. Plan 09-03's backfill writes ts >= 2026-01-23 AND channels IN the 7-channel v2 set (GOOGLE_ADEX etc., NOT legacy GOOGLE) — triple guard.
- **T-09-02-08 (DoS, slow UPDATE):** `idx_alerts_deprecated` index in place (from 09-01); 200-row UPDATE measured sub-millisecond (script wall-clock ~0.3s total, dominated by Python startup + lsof + flock, not the SQL itself).

## Next Phase Readiness (Plan 09-03)

- **DB state ready for backfill:** 200 legacy alerts deprecated=1 + 0 deprecated=0. Fresh backfill alerts (plan 09-03) will inherit `deprecated=0` via DEFAULT naturally — no post-hoc UPDATE needed on the new ~1,440-row dataset.
- **Transient API state (per ERRATA I-3):** Between this commit (1518e81) and plan 09-03 Task 3 completion, `/api/alerts` default response is an empty list (all 200 alerts have deprecated=1; the default filter in 09-03 Task 2 will hide them; backfill in 09-03 Task 3 will populate the list). This transient state is expected — UI observers will see a "no alerts" state until backfill completes. Admin reachability preserved via `?include_deprecated=true` once 09-03 Task 2 lands.
- **MIGRATE-01 Success Criteria:** 1/1 closed here (200 rows with deprecated=1 + D-15 reason). ROADMAP.md Success Criterion #3 now achievable by inspection.

## Self-Check: PASSED

- [x] `scripts/deprecate_legacy_alerts.py` — FOUND + executable
- [x] `scripts/test_deprecate_legacy_alerts.py` — FOUND
- [x] `.planning/phases/09-alert-backfill-legacy-migration/09-02-SUMMARY.md` — FOUND (this file)
- [x] Commit `019f010` — FOUND (Task 1 TDD RED)
- [x] Commit `5fbf670` — FOUND (Task 2 TDD GREEN)
- [x] Commit `1518e81` — FOUND (Task 3 live apply + smoke-suite evolution)
- [x] `sqlite3 data/vna_alerts.db "SELECT COUNT(*) FROM alerts WHERE deprecated=1"` = 200
- [x] `sqlite3 data/vna_alerts.db "SELECT COUNT(*) FROM alerts WHERE deprecation_reason = '<D-15>'"` = 200
- [x] `sqlite3 data/vna_alerts.db "SELECT COUNT(DISTINCT deprecation_reason) FROM alerts WHERE deprecated=1"` = 1
- [x] Zero over-deprecation (ts >= cutoff OR channel NOT IN legacy)
- [x] Second invocation returns IDEMPOTENT-NOOP, exit 0
- [x] `scripts/test_deprecate_legacy_alerts.py` — 12/12 OK
- [x] `scripts/test_models_sync.py` — 17/17 OK (HARD-03 no regression)
- [x] `scripts/test_migration_002_apply.py` — 11/11 OK (lifecycle-evolved)

---

*Phase: 09-alert-backfill-legacy-migration*
*Completed: 2026-04-23*
