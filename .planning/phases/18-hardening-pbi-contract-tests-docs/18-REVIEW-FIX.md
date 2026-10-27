---
phase: 18-hardening-pbi-contract-tests-docs
fixed_at: 2026-05-21T00:00:00Z
review_path: .planning/phases/18-hardening-pbi-contract-tests-docs/18-REVIEW.md
iteration: 1
findings_in_scope: 12
fixed: 9
skipped: 3
status: all_fixed
---

# Phase 18: Code Review Fix Report (iteration 1, scope `--all`)

**Fixed at:** 2026-05-21T00:00:00Z
**Source review:** `.planning/phases/18-hardening-pbi-contract-tests-docs/18-REVIEW.md`
**Iteration:** 1

## Summary

- Findings in scope: **12** (3 Warning + 9 Info)
- Fixed this iteration: **9** (all 9 IN-* findings)
- Already-applied (predecessor pass): **3** (WR-01 / WR-02 / WR-03 closed by `a7c60d9`)
- Skipped (other reasons): **0**
- Status: **all_fixed**

The 3 WR-* findings appear in the (stale) REVIEW.md but the source code is
already in the recommended end state — verified by re-reading
`scripts/test_alert_revenue_pbi_parity.py` lines 60-75 + module docstring
(constant pinned to 662.00, comments show 655.38/668.62, docstring band
shows `[€655.38, €668.62]`). R-11 forbids cascade re-fixing, so they are
marked `already_applied` with no new commit.

Primary load-bearing fix this run: **IN-03** (Gap 2 blocker for v1.3 → v1.4
formal transition). INV-5 + INV-6 now execute and print verdicts BEFORE
INV-1's `sys.exit(2)` short-circuit fires in CI (DB-absent simulation
verified by renaming `data/vna_alerts.db` and re-running the script).

Final regression after all fixes: **58 passed + 12 skipped** (matches
pre-fix baseline — zero regression).

## Fixed Issues

### IN-01: `pq.read_table(...).to_pandas()` requires pandas, only pyarrow is import-guarded

**File:** `tests/contracts/conftest.py`
**Commit:** `f89cfcb`
**Applied fix:** Added `import pandas  # noqa: F401` inside the `try:` block.
If either pyarrow or pandas is missing, `pq = None` and `parquet_loader`
skips with the canonical "pyarrow not installed in active venv" message
instead of crashing inside pyarrow.
**Verification:** Tier 1 re-read + Tier 2 `ast.parse` syntax check + pytest
`tests/contracts/` → 3 passed + 12 skipped (unchanged).

### IN-02: pbi-parity.yml comment overstates which invariants `exit(2)`

**File:** `.github/workflows/pbi-parity.yml`
**Commit:** `ade8d24`
**Applied fix:** Replaced the inline comment + `::notice::` message to
accurately describe single-exit semantics AND the new IN-03 ordering:
INV-5 SKIP + INV-6 source-grep print verdicts FIRST, then INV-1's
`_open_db()` short-circuits with exit 2 in CI. Both informational —
no behavioral change.
**Verification:** Tier 1 re-read + Tier 2 `yaml.safe_load` YAML lint OK.

### IN-03: INV-6 (Path A guard) cannot run in CI as currently structured  [PRIORITY / Gap 2 blocker]

**File:** `scripts/test_alert_revenue_pbi_parity.py`
**Commit:** `2e6b7a3`
**Applied fix:** Reordered the `results` list in `main()` so DB-independent
invariants run first:

```
results = [
    test_invariant_5_sample2_hbm_pbi_parity_skip_until_phase21(),  # DB-indep
    test_invariant_6_path_a_guard_google_adex_only(),               # DB-indep
    test_invariant_1_sample1_path_a_pbi_parity(),                   # DB-bound
    test_invariant_2_google_adex_post_cutoff_never_synthetic(),     # DB-bound
    test_invariant_3_google_adex_backfill_rewrite_count(),          # DB-bound
    test_invariant_4_synthetic_era_deprecated_count(),              # DB-bound
]
```

Added explanatory comment block above the array citing IN-03.

**Verification:**
- Tier 1 re-read + Tier 2 `ast.parse` syntax OK.
- With DB present: all 6 invariants PASS in the new order (INV-5 SKIP,
  INV-6 PASS, INV-1..4 PASS). Sample 1 still shows €662.67 inside
  `[€655.38, €668.62]`.
- **Critical CI simulation** (rename `data/vna_alerts.db` →
  `data/vna_alerts.db.tmp-ci-simulate`, run script, rename back):
  - INV-5 prints `↷ SKIPPED: Phase 21 v1.4 Athena activation required`
  - INV-6 prints `✓ no forbidden channel literals in Path A guard condition`
  - THEN INV-1 prints its header and `FATAL: DB not found at ...`
  - Exit code = 2 (caught by the workflow notice-and-pass branch)
- DB file restored to `3411968` bytes after the simulation.

### IN-04: Stale Phase 10 docstring header on a file that also contains Phase 18 tests

**File:** `scripts/test_silent_failure_watch.py`
**Commit:** `d3fbbcd`
**Applied fix:** Added a paragraph to the module docstring naming the Phase
18 HARD-03 extension and the `TestPhase18HardeningRegression` class.
**Verification:** Tier 1 re-read + Tier 2 `ast.parse` + pytest 19 passed.

### IN-05: Inconsistent import style for `mock` / `MagicMock`

**File:** `scripts/test_silent_failure_watch.py`
**Commit:** `146baa0`
**Applied fix:** Removed `from unittest import mock`. Consolidated import to
`from unittest.mock import patch, MagicMock, Mock`. Rewrote 5 callsites
(2 `@mock.patch` → `@patch`; 1 `mock.MagicMock()` → `MagicMock()`;
2 `mock.Mock(...)` → `Mock(...)`).
**Verification:** Tier 1 re-read + Tier 2 `ast.parse` + grep confirms zero
remaining `mock.` references + pytest 19 passed.

### IN-06: Unused f-string prefix in test_models_sync.py

**File:** `scripts/test_models_sync.py`
**Commit:** `d5f04de`
**Applied fix:** Dropped the `f` prefix on the assertion message at line 263
(no `{}` interpolation present).
**Verification:** Tier 1 re-read + Tier 2 `ast.parse` + pytest 36 passed.

### IN-07: Test method ordering comment is internal-monologue style

**File:** `scripts/test_models_sync.py`
**Commit:** `dbc023c`
**Applied fix:** Replaced the stream-of-consciousness 2-line comment with a
single declarative sentence: "Method name prefix (a01, a02, ...) controls
unittest's alphabetical execution order so the file-existence prerequisite
runs first."
**Verification:** Tier 1 re-read + Tier 2 `ast.parse` + pytest 36 passed.

### IN-08: README.md "Fails when" column lists HARD-03 + HARD-04 on one row

**File:** `.github/workflows/README.md`
**Commit:** `db5c0e8`
**Applied fix:** Extended the table cell with a clarifying sentence: both
gates share one workflow; inspect the job log to identify which step
tripped (HARD-03 silent-failure regression vs HARD-04 PBI parity / Path A
guard). Preferred this over splitting into two workflows — keeps a single
PR status check while removing the ambiguity.
**Verification:** Tier 1 re-read; Tier 3 fallback (markdown — no syntax check).

### IN-09: DATA_INTEGRATION.md retains operator-machine-absolute paths

**File:** `DATA_INTEGRATION.md`
**Commit:** `1547b3e`
**Applied fix:** Inserted a blockquote callout at the top of "Source Data"
explaining the absolute paths are on Stefano's operator machine and noting
that porting requires either `VNA_DATASET_ROOT` env-var parameterization
(suggested) or local edits to `scripts/aggregate_parquet.py`.
**Verification:** Tier 1 re-read; Tier 3 fallback (markdown — no syntax check).

## Already-Applied (no new commits this iteration)

### WR-01: `SAMPLE_1_PBI_REVENUE` uses Sentinel value (662.67), not PBI truth source (662.00)

**File:** `scripts/test_alert_revenue_pbi_parity.py:68`
**Status:** `already_applied`
**Closed by:** commit `a7c60d9` (previous iteration)
**Current state:** `SAMPLE_1_PBI_REVENUE = 662.00  # gross EUR, from PBI ...`
(line 71). PBI-anchored truth source documented in lines 66-69 comment.

### WR-02: Inline-comment rounded bounds don't match computed values

**File:** `scripts/test_alert_revenue_pbi_parity.py:70-71`
**Status:** `already_applied`
**Closed by:** commit `a7c60d9`
**Current state:** Lines 73-74 show `# 655.38` and `# 668.62` —
self-consistent with `SAMPLE_1_PBI_REVENUE = 662.00 * (1 ± 0.01)`.

### WR-03: Module docstring and runtime print show different bands for INV-1

**File:** `scripts/test_alert_revenue_pbi_parity.py:12`
**Status:** `already_applied`
**Closed by:** commit `a7c60d9`
**Current state:** Module docstring (line 10) declares the INV-1 band as
`[€655.38, €668.62]` (PBI €662.00 ±1%) — matches the runtime print which
formats `SAMPLE_1_LOWER` and `SAMPLE_1_UPPER` from the same PBI-anchored
constant. Docstring, constant, computed band, and print verdicts align.

## Verification Results

| Stage | Command | Result |
|-------|---------|--------|
| Baseline (pre-fix) | `pytest scripts/test_models_sync.py scripts/test_silent_failure_watch.py tests/contracts/ -q` | 58 passed + 12 skipped |
| After IN-01 | `pytest tests/contracts/ -q` | 3 passed + 12 skipped |
| After IN-03 (DB present) | `python3 scripts/test_alert_revenue_pbi_parity.py` | 6/6 invariants PASS in new order |
| After IN-03 (DB absent — CI simulation) | rename DB + run + restore | INV-5 SKIP + INV-6 PASS verdicts printed before INV-1 exit 2 — Gap 2 closed |
| After IN-04 / IN-05 | `pytest scripts/test_silent_failure_watch.py -q` | 19 passed |
| After IN-06 / IN-07 | `pytest scripts/test_models_sync.py -q` | 36 passed |
| Final regression | `pytest scripts/test_models_sync.py scripts/test_silent_failure_watch.py tests/contracts/ -q` | **58 passed + 12 skipped** (matches baseline) |

YAML lint OK on `.github/workflows/pbi-parity.yml` after IN-02.

## Commit Summary

9 atomic commits (R-03), all on local `main` (R-05/R-07 — no push performed):

```
1547b3e fix(18): IN-09 DATA_INTEGRATION.md — note operator-machine absolute paths
db5c0e8 fix(18): IN-08 README workflow table — note how to distinguish HARD-03 vs HARD-04
dbc023c fix(18): IN-07 replace internal-monologue ordering comment with one-line note
d5f04de fix(18): IN-06 drop unused f-string prefix in test_models_sync.py:263
146baa0 fix(18): IN-05 consolidate mock import style on from unittest.mock import ...
d3fbbcd fix(18): IN-04 surface Phase 18 HARD-03 extension in module docstring
f89cfcb fix(18): IN-01 guard pandas in parquet_loader fixture
ade8d24 fix(18): IN-02 clarify pbi-parity.yml comment for INV-5/INV-6 first ordering
2e6b7a3 fix(18): IN-03 reorder main() so INV-5/INV-6 run before DB-bound invariants
```

No runtime mutation files (`data/vna_alerts.db-shm` / `-wal`) staged or
committed — only explicit fix-target files in each `git add`.

---

_Fixed: 2026-05-21T00:00:00Z_
_Fixer: Claude (gsd-code-fixer, Opus 4.7 1M context)_
_Iteration: 1_
