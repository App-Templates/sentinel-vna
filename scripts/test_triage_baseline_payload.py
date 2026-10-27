#!/usr/bin/env python3
"""Phase 17.2 HOTFIX-05 / B2 — regression test for Triage Bacino+Coverage rendering.

Pins the Path C contract (per `.planning/phases/17.2-marco-feedback-hotfix/17.2-05-DIAGNOSIS.md`):

ROOT CAUSE (verified 2026-05-20, all 238 snapshot alerts):
    environment_splitter emits {bacino_current, coverage_current, bacino_baseline,
    coverage_baseline} per env. TriageSection.tsx was reading m.bacino / m.coverage
    → undefined → ?? 0 → "Bacino + Coverage = 0" on every alert (Marco's report).

PATH C INVARIANTS (this test pins both layers):

  Primary (root-cause fix):
    1. TriageSection.tsx MUST read `bacino_current` (source-grep)
    2. TriageSection.tsx MUST read `coverage_current` (source-grep)

  Defensive (empty-env_split safety net):
    3. TriageSection.tsx MUST contain `envSplitMissing` predicate
    4. TriageSection.tsx MUST contain 'n/a' literal (for current-column substitution)
    5. TriageSection.tsx MUST contain env_split disclosure copy
       (mentions 'environment_split' or 'env_split' or 'splitter')

  Backend invariant (unchanged):
    6. _compute_baseline_from_env_split({}) returns (None, None)
    7. _compute_baseline_from_env_split(None) returns (None, None)
    8. _compute_baseline_from_env_split(populated) returns real (bacino, coverage)

Run:  .venv/bin/python scripts/test_triage_baseline_payload.py
Exit: 0 = all invariants hold; non-zero = regression.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

TRIAGE = REPO_ROOT / "frontend/src/components/alerts/TriageSection.tsx"

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL: {msg}", file=sys.stderr)


def assert_in(needle: str, haystack: str, where: str) -> None:
    if needle not in haystack:
        fail(f"'{needle}' missing from {where}")


# ---------------------------------------------------------------------------
# Backend invariant: _compute_baseline_from_env_split contract unchanged
# ---------------------------------------------------------------------------
try:
    from backend.api.routes import _compute_baseline_from_env_split

    for empty in ({}, None, "", "{}", "[]"):
        bb, bc = _compute_baseline_from_env_split(empty)
        if bb is not None or bc is not None:
            fail(
                f"_compute_baseline_from_env_split({empty!r}) = ({bb}, {bc}), "
                f"expected (None, None)"
            )

    # Populated sample → non-None aggregation
    sample = {
        "WEB": {"bacino_baseline": 1000, "coverage_baseline": 0.85},
        "AMP": {"bacino_baseline": 500, "coverage_baseline": 0.75},
    }
    bb, bc = _compute_baseline_from_env_split(sample)
    if bb != 1500:
        fail(
            f"_compute_baseline_from_env_split(populated) bacino = {bb}, "
            f"expected 1500"
        )
    # Coverage is mean of [0.85, 0.75] = 0.80
    if bc is None or abs(bc - 0.80) > 1e-6:
        fail(
            f"_compute_baseline_from_env_split(populated) coverage = {bc}, "
            f"expected ~0.80"
        )
except Exception as e:
    fail(f"backend helper import / invoke failed: {e!r}")

# ---------------------------------------------------------------------------
# Frontend invariant: TriageSection.tsx contract
# ---------------------------------------------------------------------------
if not TRIAGE.exists():
    fail(f"TriageSection.tsx not found at {TRIAGE}")
else:
    triage_src = TRIAGE.read_text()

    # Primary fix: read the correct payload field names (Path C root cause)
    assert_in("bacino_current", triage_src, "TriageSection.tsx (Path C primary fix)")
    assert_in("coverage_current", triage_src, "TriageSection.tsx (Path C primary fix)")

    # Defensive Path B: envSplitMissing predicate + 'n/a' substitution
    assert_in("envSplitMissing", triage_src, "TriageSection.tsx (Path B defensive)")
    assert_in("n/a", triage_src, "TriageSection.tsx (Path B defensive)")

    # Disclosure copy keyword presence — operator must know WHY n/a fired
    if not re.search(
        r"environment[_ ]split|env[_ ]split|splitter",
        triage_src,
        re.IGNORECASE,
    ):
        fail(
            "TriageSection.tsx missing env_split disclosure copy "
            "(operator must know WHY Bacino/Coverage are n/a)"
        )

if failures:
    print(f"\n{len(failures)} invariant(s) failed", file=sys.stderr)
    sys.exit(1)

print("All HOTFIX-05 / B2 invariants hold ✓")
sys.exit(0)
