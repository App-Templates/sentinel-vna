---
phase: 18-hardening-pbi-contract-tests-docs
reviewed: 2026-05-21T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - .github/workflows/README.md
  - .github/workflows/pbi-parity.yml
  - .github/workflows/schema-drift.yml
  - DATA_INTEGRATION.md
  - scripts/test_alert_revenue_pbi_parity.py
  - scripts/test_models_sync.py
  - scripts/test_silent_failure_watch.py
  - tests/__init__.py
  - tests/contracts/__init__.py
  - tests/contracts/conftest.py
  - tests/contracts/test_parquet_db_ui.py
findings:
  critical: 0
  warning: 3
  info: 9
  total: 12
status: issues_found
---

# Phase 18: Code Review Report

**Reviewed:** 2026-05-21T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 18 ships additive hardening: 2 first-in-repo GitHub Actions workflows
(schema-drift, pbi-parity), 1 new pytest contracts package, 3 extended
validation scripts, and a 503-line DATA_INTEGRATION.md rewrite with the v1.3
Reproducibility Matrix + Gap Disclosure. Per Phase 18 CONTEXT.md, no
`backend/` or `frontend/` source files were mutated — all changes are
test/CI/docs surface.

Overall the surface is well-structured, defensively documented, and follows
the R-13 production-grade standard. The workflow files are correctly pinned
(`@v4`, `@v5`), use the canonical Python 3.11, and the contracts package
follows pytest fixture conventions cleanly. The `tests/contracts/conftest.py`
properly opens the DB in URI mode=ro to prevent accidental mutation. The
schema-drift gate's composite chain test (`TestComposeChainAgainstModels`) is
particularly strong — it makes models.py/migration divergence structurally
impossible.

Three Warning-class findings cluster around a single root cause:
**inconsistency between the documented PBI tolerance band, the constant
declared in `SAMPLE_1_PBI_REVENUE`, and the rendered band string in `_check`
output.** The math drifts by ~0.7 EUR — small enough that the band still
contains the Sentinel value (662.67), so the test stays GREEN, but the
"byte-perfect" claim in the docstring is undermined when the band itself is
computed from the Sentinel value rather than the PBI truth-source value.
Nine Info-class findings are cosmetic or low-risk maintainability items.

## Warnings

### WR-01: `SAMPLE_1_PBI_REVENUE` uses Sentinel value (662.67), not PBI truth source (662.00)

**File:** `scripts/test_alert_revenue_pbi_parity.py:68`
**Issue:** Per `DATA_INTEGRATION.md:380` the PBI value is **€662.00** and the
Sentinel value is **€662.67**. The constant is named `SAMPLE_1_PBI_REVENUE`
(implying the PBI truth source), and INV-1's documented purpose is to assert
revenue_current is in the **PBI ±1% band**. But the constant is set to the
Sentinel value, so the band is computed from 662.67 rather than 662.00. The
resulting bands are subtly different:

- From 662.00 (PBI): `[€655.38, €668.62]`
- From 662.67 (Sentinel): `[€656.04, €669.30]`

The Sentinel-computed value 662.67 is inside both bands, so the test stays
GREEN. But the contract is no longer "PBI parity" — it's "Sentinel
self-consistency with ±1% slack". A future drift where Sentinel returns
€670 would pass against the wider band but fail the stricter PBI-anchored
band. This silently relaxes the invariant.

Note: the docstring on line 12 says `[€655.37, €668.62]` (the
PBI-anchored band, rounded). The const's print output uses
`[€656.04, €669.30]` (the Sentinel-anchored band). The two callsites
disagree on what the invariant is.

**Fix:** Pin the constant to the PBI truth source:
```python
# PBI Sample 1 truth source (Marco email 2026-05-19, BigQuery snapshot)
# 662.00 is the PBI value (truth); Sentinel produces 662.67 (verified Phase 17.4).
SAMPLE_1_PBI_REVENUE = 662.00  # gross EUR, from PBI (NOT the Sentinel-computed value)
SAMPLE_1_TOLERANCE_PCT = 0.01  # ±1%
SAMPLE_1_LOWER = SAMPLE_1_PBI_REVENUE * (1 - SAMPLE_1_TOLERANCE_PCT)  # 655.38
SAMPLE_1_UPPER = SAMPLE_1_PBI_REVENUE * (1 + SAMPLE_1_TOLERANCE_PCT)  # 668.62
```

Then update the docstring `# 655.37 (rounded)` to `# 655.38` and remove the
inconsistency.

### WR-02: Inline-comment rounded bounds don't match computed values

**File:** `scripts/test_alert_revenue_pbi_parity.py:70-71`
**Issue:** Lines 70-71 declare:
```python
SAMPLE_1_LOWER = SAMPLE_1_PBI_REVENUE * (1 - SAMPLE_1_TOLERANCE_PCT)  # 655.37 (rounded)
SAMPLE_1_UPPER = SAMPLE_1_PBI_REVENUE * (1 + SAMPLE_1_TOLERANCE_PCT)  # 669.30 (rounded)
```

But with `SAMPLE_1_PBI_REVENUE = 662.67`, the actual values are:
- `662.67 * 0.99 = 656.0433` (comment says `655.37` — wrong by 0.67)
- `662.67 * 1.01 = 669.2967` (comment says `669.30` — correct)

The `655.37` value matches `662.00 * 0.99 = 655.38` (which would be correct
if WR-01 were applied), not `662.67 * 0.99`. The comments mix
PBI-anchored bounds with a Sentinel-anchored constant, leaving them
internally inconsistent. A future reader cannot tell from the source alone
which band is intended.

**Fix:** After applying WR-01, the comments will be self-consistent. If
WR-01 is not applied, fix the comment instead:
```python
SAMPLE_1_LOWER = SAMPLE_1_PBI_REVENUE * (1 - SAMPLE_1_TOLERANCE_PCT)  # 656.04 (rounded)
SAMPLE_1_UPPER = SAMPLE_1_PBI_REVENUE * (1 + SAMPLE_1_TOLERANCE_PCT)  # 669.30 (rounded)
```

### WR-03: Module docstring and runtime print show different bands for INV-1

**File:** `scripts/test_alert_revenue_pbi_parity.py:12`
**Issue:** The module docstring (line 12) declares the INV-1 band as
`[€655.37, €668.62]`, but `test_invariant_1_sample1_path_a_pbi_parity()`
prints the band using the f-string at line 132 which formats
`SAMPLE_1_LOWER` and `SAMPLE_1_UPPER` (currently `656.04` and `669.30`).
A reader debugging a RED INV-1 will see one band in the docstring and a
different band in the CLI output. This violates the R-13 "documented
=== executed" principle.

The print on line 117 (`"...PBI €662 ±1% band"`) also uses 662 (the PBI
value), conflicting with the constant which is 662.67. Three different
sources of truth for one invariant.

**Fix:** Apply WR-01 (set constant to 662.00). Then the docstring,
constant, computed band, and print all align on the PBI-anchored band
`[€655.38, €668.62]`. Optionally also update the docstring of
`test_invariant_1_sample1_path_a_pbi_parity` to spell out the band
verbatim instead of relying on the print template.

## Info

### IN-01: `pq.read_table(...).to_pandas()` requires pandas, only pyarrow is import-guarded

**File:** `tests/contracts/conftest.py:84-89`
**Issue:** The `parquet_loader` fixture checks `pq is None` (pyarrow import
guard) and skips if absent, but the actual conversion to pandas via
`.to_pandas()` requires pandas to be installed. If a CI runner installs
pyarrow but not pandas, the test will fail with `ImportError` from inside
pyarrow rather than skipping cleanly.

**Fix:** Also guard pandas:
```python
try:
    import pyarrow.parquet as pq
    import pandas  # noqa: F401  needed by pq.to_pandas()
except ImportError:
    pq = None
```

Or return the pyarrow Table directly and let callers convert if needed.

### IN-02: pbi-parity.yml comment overstates which invariants `exit(2)`

**File:** `.github/workflows/pbi-parity.yml:37-40`
**Issue:** The inline comment says "Live DB-bound invariants (INV-1..INV-4)
will exit(2) when data/vna_alerts.db is absent". In practice only the first
`_open_db()` call (in INV-1) executes `sys.exit(2)` (line 109 of the
script); INV-2..INV-4 never get a chance to run once the process exits. The
behaviour is correct (single exit), but the comment implies each invariant
independently signals exit-2, which would suggest accumulation. Minor
clarity bug.

**Fix:**
```yaml
# data/vna_alerts.db is gitignored, so the script's _open_db() helper
# exits(2) on the first DB-bound invariant (INV-1). Subsequent DB-bound
# invariants (INV-2..INV-4) are skipped as a consequence. The structural
# invariants (INV-5 SKIP + INV-6 source-grep) only run when the DB is
# present; in CI, INV-6's CI value is realised only on operator-machine
# pre-push runs. The CI value of this gate is HARD-03 silent-failure
# regression below.
```

(Note: this also clarifies that INV-6 currently does NOT run in CI when the
DB is absent — because `_open_db()` exits before INV-6 is called. See
IN-03.)

### IN-03: INV-6 (Path A guard) cannot run in CI as currently structured

**File:** `scripts/test_alert_revenue_pbi_parity.py:281-296` (`main()`)
**Issue:** The README.md (line 12) and the script's own header (lines 5-7)
both claim INV-6 is DB-independent and runs in CI. But `main()` calls the
invariants in order (lines 289-295), and `test_invariant_1_*` calls
`_open_db()` which `sys.exit(2)` when DB is absent. INV-6 is the LAST in
the list, so in CI (no DB) the process exits before INV-6 ever executes.
The structural invariant has no live CI coverage — defeating the stated
purpose of having a DB-independent invariant.

**Fix:** Reorder so the DB-independent invariants (INV-5 SKIP, INV-6
source-grep) run first, OR wrap each DB-bound invariant in a try/except
that defers exit-2 until after structural invariants have run:
```python
results = [
    # DB-independent FIRST (always run, even without DB)
    test_invariant_5_sample2_hbm_pbi_parity_skip_until_phase21(),
    test_invariant_6_path_a_guard_google_adex_only(),
    # DB-bound (will sys.exit(2) inside _open_db if DB absent)
    test_invariant_1_sample1_path_a_pbi_parity(),
    test_invariant_2_google_adex_post_cutoff_never_synthetic(),
    test_invariant_3_google_adex_backfill_rewrite_count(),
    test_invariant_4_synthetic_era_deprecated_count(),
]
```

This matches the documented CI contract.

### IN-04: Stale Phase 10 docstring header on a file that also contains Phase 18 tests

**File:** `scripts/test_silent_failure_watch.py:1-4`
**Issue:** The module docstring says "Phase 10 Plan 03 -- silent_failure_watch.py
test suite." But the file now contains `TestPhase18HardeningRegression`
(lines 249-375) added in Phase 18 HARD-03. New readers won't realize Phase
18 contracts live here.

**Fix:** Update the module docstring:
```python
"""Phase 10 Plan 03 -- silent_failure_watch.py test suite.

Phase 18 HARD-03 extension — CSV-EOF boundary + post-cutoff synthetic-class
regression (TestPhase18HardeningRegression class).

Mocks get_alerts_pipeline_health + urlopen to cover all trigger paths.
"""
```

### IN-05: Inconsistent import style for `mock` / `MagicMock`

**File:** `scripts/test_silent_failure_watch.py:12-13`
**Issue:** Both `from unittest import mock` and
`from unittest.mock import patch, MagicMock` are imported, and the file
uses both `@mock.patch(...)` (lines 116, 117) and `@patch(...)`
(elsewhere). Same for `MagicMock` vs `mock.MagicMock` (line 138 mixes
both styles in the same test). This is harmless but inconsistent.

**Fix:** Pick one style (recommend the existing `from unittest.mock
import patch, MagicMock` for consistency with the rest of the file) and
convert the Phase 18 additions to match.

### IN-06: Unused f-string prefix in test_models_sync.py

**File:** `scripts/test_models_sync.py:263`
**Issue:** `f"Expected ledger INSERT not found verbatim in migration 002"`
has no `{}` interpolation. Minor style.

**Fix:** Drop the `f`:
```python
self.assertIn(expected_insert, self.migration_002_src,
              "Expected ledger INSERT not found verbatim in migration 002")
```

### IN-07: Test method ordering comment is internal-monologue style

**File:** `scripts/test_models_sync.py:210-211`
**Issue:** Comment reads `"(file existence — ordering: runs first
alphabetically in unittest? No, unittest sorts by method name. We prefix
to control order: D then A..G.)"`. This is debugging stream-of-thought and
would distract a future reader. The intent (alphabetical method-name
ordering via `test_a0N_*` prefix) is already conveyed by the prefix
naming.

**Fix:** Replace with a brief one-line note or remove:
```python
# Method name prefix (a01, a02, ...) controls unittest's
# alphabetical execution order.
```

### IN-08: README.md "Fails when" column lists both HARD-03 and HARD-04 on one row but the workflow runs both regardless of which is failing

**File:** `.github/workflows/README.md:12`
**Issue:** The table row says
`pbi-parity.yml | HARD-03 + HARD-04 | Phase 18 | Path A guard regression
... OR silent-failure regression case ... fails`. Both are bundled into a
single workflow. If one fails it's ambiguous which gate (HARD-03 vs
HARD-04) tripped without reading the job logs. For a v1.3 production
gate, splitting them into two jobs (or two workflows) gives clearer
signal in PR status checks.

**Fix:** Either split into two jobs in the same workflow (each with its
own `name:`), or accept the bundled signal and add a note to the table:
```
| pbi-parity.yml | HARD-03 + HARD-04 | Phase 18 | See job log to
distinguish HARD-03 (silent-failure) vs HARD-04 (Path A guard) |
```

### IN-09: DATA_INTEGRATION.md retains operator-machine-absolute paths in source-data section

**File:** `DATA_INTEGRATION.md:14, 18, 22, 99`
**Issue:** Four lines reference
`/Users/admintemp/Downloads/Value Network - Yield Optimization and
Alerting/...` as if it were a stable repo-relative location. While this is
the operator machine and the document is operator-facing, it's noise for
any other reader (CI, reviewer, future maintainer). Consider parameterizing
via an env var or describing as "operator dataset root".

**Fix:** Add a one-line note at the top of "Source Data":
```
> Paths below are on Stefano's operator machine. Substitute your local
> path to the raw parquet datasets; the aggregation script reads from
> `$VNA_DATASET_ROOT` if set.
```

(No code change needed if the aggregate script does not actually consume
the env var — this is a documentation-only suggestion.)

---

_Reviewed: 2026-05-21T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
