#!/usr/bin/env python3
"""Phase 17.2 GAP-CLOSURE — alert detail sections × payload contract pin.

UAT Check 5 + Check 6 root cause (2026-05-20): EnvironmentSplitSection,
ContributorsSection, GeoBreakdownSection (+ chart siblings BarChart /
PieChart) read OLD field names that don't exist on the real wire payload:

  Producer (verified via live snapshot):
    environment_split[env]:  revenue_current / revenue_baseline / delta_abs /
                             delta_pct / bacino_current / bacino_baseline /
                             coverage_current / coverage_baseline
    + sibling scalar:        amp_drift_detected: bool   (MUST be filtered)
    contributors[]:          publisher_id / display_name / revenue_current /
                             revenue_baseline / delta_eur / delta_pct /
                             quota_of_drop          (quota_of_drop is a
                             PERCENTAGE 0..100, NOT a 0..1 fraction)
    geo_breakdown[]:         cluster / cluster_name / revenue_current /
                             revenue_baseline / delta_eur / delta_pct /
                             quota_of_drop / status (same percentage scale)

  Consumer pre-gap-closure was reading: revenue / baseline_revenue /
  delta_percent / delta_absolute / bacino / coverage / publisher_name /
  current_revenue / geo_cluster / contribution — every read returned
  undefined, the .toFixed() / .toLocaleString() crashed inside the JSX,
  AlertDetailPage's error boundary caught it, all alert tabs went blank.

This script pins:

  A. types/alert.ts has the CANONICAL field names (TypeScript contract).
  B. The four section + chart consumers all read the canonical field names.
  C. EnvironmentSplitSection AND EnvironmentBarChart filter the
     amp_drift_detected scalar before iterating per-env metrics
     (typeof === 'object' guard).
  D. Quota-of-drop renders are NOT multiplied by 100 (already a percentage).
  E. Live snapshot sample alert really has the canonical fields populated
     (covers regression against future producer changes).

Run:  .venv/bin/python scripts/test_alert_sections_payload_contract.py
Exit: 0 = all invariants hold; non-zero = regression.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

ALERT_TYPES = REPO_ROOT / "frontend/src/types/alert.ts"
ENV_SECTION = REPO_ROOT / "frontend/src/components/alerts/EnvironmentSplitSection.tsx"
ENV_BAR = REPO_ROOT / "frontend/src/components/charts/EnvironmentBarChart.tsx"
CONTRIB = REPO_ROOT / "frontend/src/components/alerts/ContributorsSection.tsx"
GEO_SECTION = REPO_ROOT / "frontend/src/components/alerts/GeoBreakdownSection.tsx"
GEO_PIE = REPO_ROOT / "frontend/src/components/charts/GeoBreakdownPieChart.tsx"
TRIAGE = REPO_ROOT / "frontend/src/components/alerts/TriageSection.tsx"

# Canonical sample known to have all sections populated (Wave 1 W-01 inventory)
SAMPLE_ALERT = REPO_ROOT / "frontend/dist/api/alerts/ALT-20260123-010000-P2.json"

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL: {msg}", file=sys.stderr)


def assert_in(needle: str, haystack: str, where: str) -> None:
    if needle not in haystack:
        fail(f"'{needle}' missing from {where}")


def assert_not_in(needle: str, haystack: str, where: str) -> None:
    if needle in haystack:
        fail(f"'{needle}' STILL PRESENT in {where} (should be removed)")


def assert_regex(pattern: str, haystack: str, where: str) -> None:
    if not re.search(pattern, haystack):
        fail(f"pattern {pattern!r} missing from {where}")


# ---------------------------------------------------------------------------
# A. types/alert.ts canonical contract
# ---------------------------------------------------------------------------
if not ALERT_TYPES.exists():
    fail(f"types/alert.ts not found at {ALERT_TYPES}")
else:
    src = ALERT_TYPES.read_text()
    # Canonical fields MUST be declared
    for field, ifname in [
        ("revenue_current", "EnvironmentMetrics/Contributor/GeoBreakdown"),
        ("revenue_baseline", "EnvironmentMetrics/Contributor/GeoBreakdown"),
        ("delta_abs", "EnvironmentMetrics"),
        ("delta_pct", "EnvironmentMetrics/Contributor/GeoBreakdown"),
        ("bacino_current", "EnvironmentMetrics"),
        ("bacino_baseline", "EnvironmentMetrics"),
        ("coverage_current", "EnvironmentMetrics"),
        ("coverage_baseline", "EnvironmentMetrics"),
        ("delta_eur", "Contributor/GeoBreakdown"),
        ("display_name", "Contributor"),
        ("quota_of_drop", "Contributor/GeoBreakdown"),
        ("cluster_name", "GeoBreakdown"),
    ]:
        assert_in(field, src, f"types/alert.ts ({ifname})")

    # Legacy fields MUST be removed FROM the three migrated interfaces
    # (Contributor, GeoBreakdown, EnvironmentMetrics). Other interfaces
    # may still legitimately use names like `current_revenue` (e.g.
    # MovingAverage14d) — those are intentionally out of scope.
    for iface in ("Contributor", "GeoBreakdown", "EnvironmentMetrics"):
        m = re.search(
            rf"export interface {iface} \{{([^}}]+)\}}",
            src,
            re.DOTALL,
        )
        if not m:
            fail(f"interface {iface} not found in types/alert.ts")
            continue
        body = m.group(1)
        for legacy in [
            "publisher_name:",
            "current_revenue:",
            "baseline_revenue:",
            "delta_absolute:",
            "delta_percent:",
            "geo_cluster:",
            "contribution:",
        ]:
            if legacy in body:
                fail(
                    f"legacy field '{legacy}' still in types/alert.ts "
                    f"interface {iface}"
                )


# ---------------------------------------------------------------------------
# B + C. Consumer source-grep
# ---------------------------------------------------------------------------
consumers: list[tuple[Path, list[str], list[str]]] = [
    (
        ENV_SECTION,
        # Required canonical reads
        [
            "metrics.revenue_current",
            "metrics.revenue_baseline",
            "metrics.delta_pct",
            "metrics.bacino_current",
            "metrics.coverage_current",
        ],
        # Forbidden legacy reads
        [
            "metrics.revenue\n",
            "metrics.revenue ",
            "metrics.revenue)",
            "metrics.baseline_revenue",
            "metrics.delta_percent",
            "metrics.bacino\n",
            "metrics.bacino ",
            "metrics.bacino.",
            "metrics.coverage\n",
            "metrics.coverage ",
            "metrics.coverage.",
        ],
    ),
    (
        ENV_BAR,
        [
            "metrics.revenue_current",
            "metrics.revenue_baseline",
            "metrics.delta_pct",
        ],
        [
            "metrics.revenue,",
            "metrics.baseline_revenue",
            "metrics.delta_percent",
        ],
    ),
    (
        CONTRIB,
        [
            "row.display_name",
            "row.revenue_current",
            "row.revenue_baseline",
            "row.delta_eur",
            "row.delta_pct",
            "row.quota_of_drop",
        ],
        [
            "row.publisher_name",
            "row.current_revenue",
            "row.baseline_revenue",
            "row.delta_absolute",
            "row.delta_percent",
        ],
    ),
    (
        GEO_SECTION,
        [
            "row.cluster_name",
            "row.cluster",
            "row.revenue_current",
            "row.revenue_baseline",
            "row.delta_eur",
            "row.delta_pct",
            "row.quota_of_drop",
        ],
        [
            "row.geo_cluster",
            "row.current_revenue",
            "row.baseline_revenue",
            "row.delta_absolute",
            "row.delta_percent",
            "row.contribution",
        ],
    ),
    (
        GEO_PIE,
        [
            "g.cluster",
            "g.revenue_current",
            "g.delta_pct",
        ],
        [
            "g.geo_cluster",
            "g.current_revenue",
            "g.delta_percent",
        ],
    ),
]

for path, required, forbidden in consumers:
    if not path.exists():
        fail(f"consumer not found: {path}")
        continue
    text = path.read_text()
    for need in required:
        assert_in(need, text, str(path.relative_to(REPO_ROOT)))
    for ban in forbidden:
        assert_not_in(ban, text, str(path.relative_to(REPO_ROOT)))


# ---------------------------------------------------------------------------
# C-bis. Iterating consumers must filter amp_drift_detected (typeof guard)
# ---------------------------------------------------------------------------
for path in (ENV_SECTION, ENV_BAR, TRIAGE):
    if not path.exists():
        continue
    text = path.read_text()
    # Look for the typeof object guard pattern (already established in
    # TriageSection per HOTFIX-05).
    if "typeof entry[1] === 'object'" not in text and "typeof entry[1] === \"object\"" not in text:
        fail(
            f"{path.relative_to(REPO_ROOT)} missing the 'typeof entry[1] === \\'object\\''"
            " predicate — amp_drift_detected sibling scalar will poison reduce/iteration"
        )


# ---------------------------------------------------------------------------
# D. quota_of_drop NOT multiplied by 100 (payload is already a percentage)
# ---------------------------------------------------------------------------
for path in (CONTRIB, GEO_SECTION):
    if not path.exists():
        continue
    text = path.read_text()
    # forbid `quota_of_drop * 100` (with optional whitespace)
    if re.search(r"quota_of_drop\s*\*\s*100", text):
        fail(
            f"{path.relative_to(REPO_ROOT)}: quota_of_drop * 100 still present "
            "(payload value is already a percentage 0..100)"
        )


# ---------------------------------------------------------------------------
# E. Live snapshot sample has canonical fields populated
# ---------------------------------------------------------------------------
if not SAMPLE_ALERT.exists():
    # Soft warning — snapshot may have been regenerated under a different ID;
    # don't fail the test outright. But emit a notice so operator can verify.
    print(
        f"NOTE: canonical sample alert not found at {SAMPLE_ALERT.relative_to(REPO_ROOT)}; "
        "snapshot-fidelity check skipped (frontend code-contract still verified above).",
    )
else:
    with SAMPLE_ALERT.open() as fh:
        payload = json.load(fh)
    alert = payload.get("alert", payload)
    es = alert.get("environment_split") or {}
    if not isinstance(es, dict) or not es:
        fail("sample alert environment_split is empty — pick a different canonical sample")
    else:
        # Find first per-env dict (skip amp_drift_detected scalar)
        env_metrics = next(
            (v for v in es.values() if isinstance(v, dict)),
            None,
        )
        if env_metrics is None:
            fail("sample alert environment_split has no dict entries")
        else:
            for f in (
                "revenue_current",
                "revenue_baseline",
                "delta_abs",
                "delta_pct",
                "bacino_current",
                "bacino_baseline",
                "coverage_current",
                "coverage_baseline",
            ):
                if f not in env_metrics:
                    fail(
                        f"sample env_metrics missing canonical field '{f}' — producer "
                        f"contract drift suspected (path: {SAMPLE_ALERT.relative_to(REPO_ROOT)})"
                    )
    contribs = alert.get("contributors") or []
    if contribs and isinstance(contribs[0], dict):
        for f in (
            "publisher_id",
            "display_name",
            "revenue_current",
            "revenue_baseline",
            "delta_eur",
            "delta_pct",
            "quota_of_drop",
        ):
            if f not in contribs[0]:
                fail(f"sample contributors[0] missing canonical field '{f}'")
    geo = alert.get("geo_breakdown") or []
    if geo and isinstance(geo[0], dict):
        for f in (
            "cluster",
            "cluster_name",
            "revenue_current",
            "revenue_baseline",
            "delta_eur",
            "delta_pct",
            "quota_of_drop",
        ):
            if f not in geo[0]:
                fail(f"sample geo_breakdown[0] missing canonical field '{f}'")


if failures:
    print(f"\n{len(failures)} invariant(s) failed", file=sys.stderr)
    sys.exit(1)

print("All Phase 17.2 gap-closure invariants hold ✓")
sys.exit(0)
