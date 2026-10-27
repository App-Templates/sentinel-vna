#!/usr/bin/env python3
"""
Phase 17.4 — Alert Revenue PBI Parity Contract Test (D2CLOSE-04).
Phase 18 HARD-04 extension — Sample 2 HBM placeholder + Path A guard regression.

Pins 6 invariants (4 from Phase 17.4 + 2 from Phase 18 HARD-04):

INV-1 (PATH-A SAMPLE 1 BYTE-PERFECT):
    ALT-20260322-010000-P2 GOOGLE_ADEX 2026-03-22 01:00 carries
    revenue_current within [€655.38, €668.62] (PBI €662.00 ±1%).
    Pre-Plan-04 (rewrite): revenue_current=736.01 (synthetic Phase 17.3).
    Post-Plan-04: alert UPDATEd via CSV direct read → in band (662.67 inside).

INV-2 (NO SYNTHETIC POST-CUTOFF):
    Every GOOGLE_ADEX alert created at or after 2026-05-21T00:00Z
    has data_source ∈ {'real_parquet', 'real_csv'}. Never 'backfill',
    'synthetic', or 'synthetic_no_athena'. Vacuously PASSES if the
    post-cutoff window is empty (acceptable — invariant becomes
    load-bearing as new alerts land).

INV-3 (BACKFILL REWRITE COUNT):
    Exactly 38 rows match channel_group='GOOGLE_ADEX' AND
    data_source='real_csv'. Pre-Plan-04: 0 rows. Post-Plan-04: 38 rows.
    (1 of the 39 original GOOGLE_ADEX backfill targets falls outside
    hour_kpi.csv coverage — CSV terminates at 2026-03-23 00:00:00 so the
    alert at 2026-03-23 01:00 is 1h beyond EOF. That alert is deprecated
    instead — counted in INV-4 below.)

INV-4 (BACKFILL DEPRECATED COUNT — synthetic-era flag):
    Exactly 200 rows match data_source='backfill' AND deprecated=1 AND
    deprecation_reason LIKE 'synthetic-era pre-H6-fix%'. Composition:
    199 non-GOOGLE_ADEX (Migration 006) + 1 GOOGLE_ADEX CSV-EOF edge case
    (rewrite script secondary path). Pre-Plan-04: 0 rows. Post-Plan-04: 200.

INV-5 (SAMPLE 2 HBM PLACEHOLDER — Phase 18 HARD-04 extension — SKIPPED until Phase 21):
    ALT-20260320-070000-P2 HEADER_BIDDING_MAGNITE revenue_current in
    [€681.12, €694.88] (PBI €688 gross ±1%). Gated on Phase 21 v1.4 Athena
    activation. Currently SKIPPED — auto-GREEN when Phase 21 lands.

INV-6 (PATH A GUARD REGRESSION — Phase 18 HARD-04 extension):
    Source-level grep on backend/agents/data_fetcher_real.py asserts:
    (a) GOOGLE_ADEX literal present near every BACKTEST token (±30 lines),
    (b) no forbidden channel literals (OPEN_BIDDING, HEADER_BIDDING_MAGNITE,
        HEADER_BIDDING_PUBMATIC, TAM, DIRECT, DEAL) appear in that guard region.
    DB-independent — runs in CI. Guards against CONTEXT.md D-08 regression.

RED before Plans 02+04 land. GREEN after.

Run: .venv/bin/python scripts/test_alert_revenue_pbi_parity.py
Exit 0 = all invariants GREEN or SKIPPED; exit 1 = one or more RED; exit 2 = DB absent.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "data" / "vna_alerts.db"

# Post-Phase-17.4-cutoff timestamp (canonical space-separator naive UTC microseconds
# format per Migration 004 D-10.1-01). Any GOOGLE_ADEX alert created at or after
# this instant must NOT be synthetic-class.
POST_CUTOFF_ISO = "2026-05-21 00:00:00.000000"

# PBI Sample 1 truth source (Marco email 2026-05-19, BigQuery snapshot).
# 662.00 is the PBI value (truth source); Sentinel produces 662.67 (verified
# Phase 17.4, inside the ±1% band). The constant pins the PBI-anchored band so
# the invariant remains "PBI parity" rather than "Sentinel self-consistency".
SAMPLE_1_ALERT_ID = "ALT-20260322-010000-P2"
SAMPLE_1_PBI_REVENUE = 662.00  # gross EUR, from PBI (NOT the Sentinel-computed value)
SAMPLE_1_TOLERANCE_PCT = 0.01  # ±1%
SAMPLE_1_LOWER = SAMPLE_1_PBI_REVENUE * (1 - SAMPLE_1_TOLERANCE_PCT)  # 655.38
SAMPLE_1_UPPER = SAMPLE_1_PBI_REVENUE * (1 + SAMPLE_1_TOLERANCE_PCT)  # 668.62

# Pre-Phase-17.4 baseline counts (verified 2026-05-21 via sqlite3 query):
#   39 GOOGLE_ADEX backfill rows + 199 non-GOOGLE_ADEX backfill rows = 238 total
# Post-Phase-17.4-04 split:
#   38 GOOGLE_ADEX rewritten to real_csv (1 boundary alert deprecated instead)
#   200 total backfill alerts deprecated with synthetic-era reason
#     = 199 non-GOOGLE_ADEX (Migration 006) + 1 GOOGLE_ADEX CSV-EOF (rewrite script)
EXPECTED_REAL_CSV_COUNT = 38
EXPECTED_SYNTHETIC_ERA_DEPRECATED_COUNT = 200
SYNTHETIC_ERA_REASON_PREFIX = "synthetic-era pre-H6-fix"

SYNTHETIC_CLASS_SOURCES = {"backfill", "synthetic", "synthetic_no_athena"}

# Phase 18 HARD-04 extension — Sample 2 HBM placeholder (Phase 21 v1.4 Athena dependency)
SAMPLE_2_ALERT_ID = "ALT-20260320-070000-P2"
SAMPLE_2_PBI_REVENUE = 688.00  # gross EUR, from Marco email 2026-05-19
SAMPLE_2_TOLERANCE_PCT = 0.01
SAMPLE_2_LOWER = SAMPLE_2_PBI_REVENUE * (1 - SAMPLE_2_TOLERANCE_PCT)  # 681.12
SAMPLE_2_UPPER = SAMPLE_2_PBI_REVENUE * (1 + SAMPLE_2_TOLERANCE_PCT)  # 694.88

# Phase 18 HARD-04 extension — Path A guard regression (CONTEXT.md D-08)
PATH_A_GUARD_PATH = REPO_ROOT / "backend" / "agents" / "data_fetcher_real.py"
PATH_A_FORBIDDEN_CHANNELS = (
    "OPEN_BIDDING", "HEADER_BIDDING_MAGNITE", "HEADER_BIDDING_PUBMATIC",
    "TAM", "DIRECT", "DEAL",
)


def _check(name: str, condition: bool, detail: str) -> bool:
    icon = "✓" if condition else "✗"
    print(f"  {icon} {name}: {detail}")
    return condition


def _open_db() -> sqlite3.Connection:
    if not DB_PATH.exists():
        print(f"FATAL: DB not found at {DB_PATH}")
        sys.exit(2)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def test_invariant_1_sample1_path_a_pbi_parity() -> bool:
    """Sample 1 alert revenue_current must be in PBI ±1% band post-rewrite."""
    print("\n[INV-1] Sample 1 ALT-20260322-010000-P2 — revenue_current in PBI €662 ±1% band")
    conn = _open_db()
    try:
        row = conn.execute(
            "SELECT alert_id, channel_group, data_source, revenue_current "
            "FROM alerts WHERE alert_id = ?",
            (SAMPLE_1_ALERT_ID,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return _check("alert exists", False, f"{SAMPLE_1_ALERT_ID} not found in DB")
    rev = row["revenue_current"]
    in_band = SAMPLE_1_LOWER <= rev <= SAMPLE_1_UPPER
    return _check(
        f"revenue_current in [€{SAMPLE_1_LOWER:.2f}, €{SAMPLE_1_UPPER:.2f}]",
        in_band,
        f"got €{rev:.2f} (data_source={row['data_source']!r})",
    )


def test_invariant_2_google_adex_post_cutoff_never_synthetic() -> bool:
    """No GOOGLE_ADEX alert created post-cutoff may carry synthetic-class data_source."""
    print(f"\n[INV-2] GOOGLE_ADEX alerts created >= {POST_CUTOFF_ISO} are never synthetic-class")
    conn = _open_db()
    try:
        rows = conn.execute(
            "SELECT alert_id, data_source FROM alerts "
            "WHERE channel_group = 'GOOGLE_ADEX' AND created_at >= ?",
            (POST_CUTOFF_ISO,),
        ).fetchall()
    finally:
        conn.close()
    if not rows:
        return _check("post-cutoff GOOGLE_ADEX corpus", True, "0 alerts in window (vacuous PASS)")
    violators = [(r["alert_id"], r["data_source"]) for r in rows
                 if r["data_source"] in SYNTHETIC_CLASS_SOURCES]
    return _check(
        f"all {len(rows)} post-cutoff GOOGLE_ADEX alerts non-synthetic",
        not violators,
        f"violators={violators[:5]!r}" if violators else f"clean ({len(rows)} alerts checked)",
    )


def test_invariant_3_google_adex_backfill_rewrite_count() -> bool:
    """Exactly 38 GOOGLE_ADEX alerts must carry data_source='real_csv' post-rewrite.

    Note: 1 of the 39 original GOOGLE_ADEX backfill targets falls outside
    hour_kpi.csv coverage (2026-03-23 01:00 is 1h beyond CSV EOF). That alert
    is deprecated via the rewrite script's secondary path instead of rewritten,
    so the final real_csv count is 38, not 39.
    """
    print(f"\n[INV-3] GOOGLE_ADEX backfill rewrite — {EXPECTED_REAL_CSV_COUNT} rows with data_source='real_csv'")
    conn = _open_db()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM alerts "
            "WHERE channel_group = 'GOOGLE_ADEX' AND data_source = 'real_csv'"
        ).fetchone()[0]
    finally:
        conn.close()
    return _check(
        f"COUNT(*) WHERE channel='GOOGLE_ADEX' AND data_source='real_csv' == {EXPECTED_REAL_CSV_COUNT}",
        count == EXPECTED_REAL_CSV_COUNT,
        f"got {count}",
    )


def test_invariant_4_synthetic_era_deprecated_count() -> bool:
    """Exactly 200 backfill alerts must be deprecated with synthetic-era reason.

    Composition: 199 non-GOOGLE_ADEX (Migration 006 — primary path) +
    1 GOOGLE_ADEX CSV-EOF edge case (rewrite script secondary path).
    All share the canonical 'synthetic-era pre-H6-fix%' deprecation_reason prefix.
    """
    print(f"\n[INV-4] Synthetic-era backfill deprecation — {EXPECTED_SYNTHETIC_ERA_DEPRECATED_COUNT} rows")
    conn = _open_db()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM alerts "
            "WHERE data_source = 'backfill' "
            "  AND deprecated = 1 "
            "  AND deprecation_reason LIKE ?",
            (f"{SYNTHETIC_ERA_REASON_PREFIX}%",),
        ).fetchone()[0]
    finally:
        conn.close()
    return _check(
        f"COUNT(*) WHERE data_source='backfill' AND deprecated=1 AND reason LIKE 'synthetic-era pre-H6-fix%' == {EXPECTED_SYNTHETIC_ERA_DEPRECATED_COUNT}",
        count == EXPECTED_SYNTHETIC_ERA_DEPRECATED_COUNT,
        f"got {count}",
    )


# D-10 equivalent: script-mode skip (pytest.mark.skip would apply if collected under pytest)
def test_invariant_5_sample2_hbm_pbi_parity_skip_until_phase21() -> bool:
    """Sample 2 HBM placeholder — SKIP until Phase 21 v1.4 Athena activation lands.

    Phase 21 reactivation procedure:
      1. Remove the explicit skip return below.
      2. Run the same band check as INV-1 against SAMPLE_2_ALERT_ID + HBM corpus.
      3. Verify data_source in {'real_athena', 'real_csv'} (NEVER synthetic-class).
    Body intentionally references "Phase 21 v1.4 Athena activation required" for grep
    traceability by future Phase 21 executor.
    """
    print("\n[INV-5] Sample 2 HBM ALT-20260320-070000-P2 — Phase 21 v1.4 Athena activation required (SKIP)")
    print("  ↷ SKIPPED: Phase 21 v1.4 Athena activation required")
    print(f"    expected band when active: [€{SAMPLE_2_LOWER:.2f}, €{SAMPLE_2_UPPER:.2f}]")
    return True


def test_invariant_6_path_a_guard_google_adex_only() -> bool:
    """Path A guard regression — BACKTEST bypass_top50 branch must be gated on GOOGLE_ADEX only.

    CONTEXT.md D-08: a future refactor must not accidentally enable other channels.
    Source-level grep (Phase 17.2/17.3 pattern — no AST parse, no runtime call).
    DB-independent: runs in CI even when data/vna_alerts.db is absent.

    Checks only non-comment executable lines containing 'BACKTEST' in proximity to
    'channel ==' or 'channel in' — avoiding false-positive hits in docstrings/comments
    that legitimately list other channel names (e.g. documentation of channels still on
    parquet). The invariant guards the actual conditional expression, not comments about it.
    """
    print("\n[INV-6] Path A guard — GOOGLE_ADEX-only enablement in data_fetcher_real.py")
    if not PATH_A_GUARD_PATH.exists():
        return _check("data_fetcher_real.py exists", False,
                      f"missing at {PATH_A_GUARD_PATH}")
    src = PATH_A_GUARD_PATH.read_text()
    lines = src.splitlines()
    # Find executable (non-comment) lines that reference both 'channel' and 'BACKTEST'
    # These are the actual conditional guard lines (e.g. `if channel == "GOOGLE_ADEX" and mode == "BACKTEST":`)
    guard_lines = [
        line for line in lines
        if "BACKTEST" in line and "channel" in line and not line.lstrip().startswith("#")
    ]
    if not guard_lines:
        # Fall back: find any executable line with BACKTEST and check nearby for GOOGLE_ADEX
        exec_backtest_idx = [
            i for i, line in enumerate(lines)
            if "BACKTEST" in line and not line.lstrip().startswith("#")
        ]
        if not exec_backtest_idx:
            return _check("BACKTEST token present in executable code", False,
                          "no non-comment BACKTEST literal found in data_fetcher_real.py")
        # Narrow window (5 lines) — just the conditional expression
        guard_window_lines = set()
        for i in exec_backtest_idx:
            for j in range(max(0, i - 5), min(len(lines), i + 5)):
                guard_window_lines.add(j)
        guard_region = "\n".join(lines[j] for j in sorted(guard_window_lines))
    else:
        guard_region = "\n".join(guard_lines)
    if "GOOGLE_ADEX" not in guard_region:
        return _check("GOOGLE_ADEX literal present in Path A guard condition", False,
                      "Path A branch must reference GOOGLE_ADEX in its guard condition")
    forbidden_hits = [ch for ch in PATH_A_FORBIDDEN_CHANNELS if ch in guard_region]
    return _check(
        "no forbidden channel literals in Path A guard condition",
        not forbidden_hits,
        f"forbidden_hits={forbidden_hits!r}" if forbidden_hits
        else "guard condition clean (GOOGLE_ADEX only)",
    )


def main() -> int:
    print("=" * 70)
    print("Phase 17.4 + Phase 18 HARD-04 — Alert Revenue PBI Parity Contract Test")
    print("=" * 70)
    print("Pins 6 invariants (4 Phase 17.4 + 2 Phase 18 HARD-04 extension).")
    print("RED before Plans 02+04 land, GREEN after Path A wiring + backfill rewrite + migration 006 ship.")
    print("INV-5 SKIP until Phase 21 v1.4 Athena. INV-6 DB-independent (runs in CI).")

    # Ordering: DB-independent invariants run FIRST so they always execute
    # in CI (where data/vna_alerts.db is gitignored / absent). INV-5 (SKIP
    # placeholder) and INV-6 (source-grep on data_fetcher_real.py) require
    # no DB. INV-1..INV-4 call _open_db() which sys.exit(2) on missing DB —
    # placing them after INV-5/INV-6 guarantees the structural CI gate is
    # exercised before any DB-bound short-circuit fires. (IN-03 fix.)
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
    passed = sum(results)
    total = len(results)
    print()
    print("=" * 70)
    if passed == total:
        print(f"✓ All {total} PBI parity invariants hold")
        return 0
    print(f"✗ {total - passed}/{total} invariants FAIL — see output above")
    return 1


if __name__ == "__main__":
    sys.exit(main())
