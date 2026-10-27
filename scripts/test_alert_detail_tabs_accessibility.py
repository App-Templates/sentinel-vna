#!/usr/bin/env python3
"""Phase 17.2 HOTFIX-04 / B1 — regression test for AlertDetailPage Tabs 3/4/5.

Marco Manduca feedback 2026-05-19 (B1): Tabs 3 (Top Contributors), 4 (Geo
Breakdown), 5 (Environment Split) appeared 'non più accessibili'. The
smoking gun (per 17.2-04-DIAGNOSIS.md) was a render-guard short-circuit at
AlertDetailPage:259 that hid the Environment Split tab's content when
env_split was null/empty. Tabs 3 + 4 had secondary UX defects — sections
rendered but with misleading half-empty layouts instead of clean empty-state
cards.

Source-grep approach (no jsdom). Pins 3 invariants:

  1. STEPS array entries for 'contributors', 'geo', 'environment' have NO
     `condition` predicate (i.e. always visible in the tab strip).
  2. The render branch for currentStep === 'environment' does NOT carry
     `Object.keys(...).length > 0` short-circuit (which was the smoking gun).
  3. Each of the 3 section components contains an explicit empty-state copy
     ('No <X> data available') so reaching the section with empty data
     yields a clean visible card rather than a half-bait layout.

Test approach precedent: Phase 17.1 `test_publisher_drilldown_reverse_mapping.py`
also uses source-grep + AST-light validation against TS files when a full
jsdom test would require new tooling.

Run:  .venv/bin/python scripts/test_alert_detail_tabs_accessibility.py
Exit: 0 = all invariants hold; non-zero = regression.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "frontend/src/pages/AlertDetailPage.tsx"
CONTRIBUTORS = ROOT / "frontend/src/components/alerts/ContributorsSection.tsx"
GEO = ROOT / "frontend/src/components/alerts/GeoBreakdownSection.tsx"
ENV_SECTION = ROOT / "frontend/src/components/alerts/EnvironmentSplitSection.tsx"

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL: {msg}", file=sys.stderr)


def must_exist(path: Path) -> str:
    if not path.exists():
        fail(f"file missing: {path.relative_to(ROOT)}")
        return ""
    return path.read_text()


page_src = must_exist(PAGE)
contrib_src = must_exist(CONTRIBUTORS)
geo_src = must_exist(GEO)
env_src = must_exist(ENV_SECTION)

# --- Invariant 1: STEPS has entries for contributors/geo/environment WITHOUT condition.
# The STEPS array entries look like: { id: 'contributors', label: 'Top Contributors' }
# We want to assert each of the 3 step IDs is present AND its entry does NOT include
# the `condition` key on the same `{ ... }` object literal.
for step_id in ("contributors", "geo", "environment"):
    # Match a non-nested `{ ... }` object literal containing `id: 'step_id'`.
    # The STEPS array entries are single-line, so a simple non-} pattern is safe.
    pattern = re.compile(
        r"\{\s*id:\s*['\"]" + re.escape(step_id) + r"['\"][^}]*\}",
        re.MULTILINE,
    )
    match = pattern.search(page_src)
    if not match:
        fail(f"STEPS entry for '{step_id}' not found in AlertDetailPage")
        continue
    entry = match.group(0)
    if "condition" in entry:
        fail(
            f"STEPS entry for '{step_id}' has a condition predicate — "
            "B1 invariant requires always-visible tab"
        )

# --- Invariant 2: render branch for currentStep === 'environment' MUST NOT carry
# `Object.keys(...).length > 0` short-circuit.
env_branch_pattern = re.compile(
    r"currentStep\s*===\s*['\"]environment['\"][^}]*?Object\.keys\([^)]*\)\.length\s*>\s*0",
    re.DOTALL,
)
if env_branch_pattern.search(page_src):
    fail(
        "AlertDetailPage env render branch still has "
        "Object.keys(...).length > 0 short-circuit (B1 root cause)"
    )

# --- Invariant 3: each section has its own empty-state card.
# ContributorsSection
if "safeContributors" not in contrib_src:
    fail("ContributorsSection missing safeContributors null-coalesce")
if not re.search(r"No\s+(contributor|data)", contrib_src, re.IGNORECASE):
    fail(
        "ContributorsSection missing 'No contributor data available' "
        "empty-state copy — Task 2 must add it"
    )
# GeoBreakdownSection
if "safeGeoBreakdown" not in geo_src:
    fail("GeoBreakdownSection missing safeGeoBreakdown null-coalesce")
if not re.search(r"No\s+(geo|data)", geo_src, re.IGNORECASE):
    fail(
        "GeoBreakdownSection missing 'No geo data available' "
        "empty-state copy — Task 2 must add it"
    )
# EnvironmentSplitSection — already has the empty-state pattern at lines 22-37
if "No environment data available" not in env_src:
    fail("EnvironmentSplitSection lost the existing empty-state card")

if failures:
    print(f"\n{len(failures)} invariant(s) failed", file=sys.stderr)
    sys.exit(1)
print("All 3 HOTFIX-04 / B1 invariants hold ✓")
sys.exit(0)
