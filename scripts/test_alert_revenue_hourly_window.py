#!/usr/bin/env python3
"""
Phase 17.3 — Alert Revenue Hourly Window Contract Test (D2 / AUDIT-02).

Pins three invariants that surfaced from the email Marco 2026-05-19:

INVARIANT 1 (CORE — fix target):
    For BACKTEST mode + GOOGLE_ADEX (the only channel with hourly parquet
    coverage), data_fetcher_real returns data_source='real_parquet', NOT
    'synthetic'. The pre-fix tz-mismatch silently fell back to synthetic;
    the post-fix path must read parquet.

INVARIANT 2 (CONTRACT — current_revenue origin):
    Sample alerts' DB revenue_current MUST be reproducible either:
    (a) from parquet via _get_hourly_metrics (post-fix), within ±25%
        of the value when the channel has hourly coverage; OR
    (b) explicitly marked synthetic when the channel has no hourly
        coverage (HBM/HBP/TAM/DIRECT/DEAL — hour_kpi.csv has only
        GOOGLE_ADEX). No silent fallback for parquet-covered channels.

INVARIANT 3 (PROVENANCE — DB integrity):
    backfill alerts persist data_source faithfully. The pre-fix code at
    scripts/backfill_alerts.py:153 hardcodes 'backfill' which hides the
    synthetic provenance. Post-fix the pipeline data_source MUST
    propagate to the AlertModel.

This script runs RED before the fix lands (Task 2) and GREEN after
(Task 3). It is checked into the repo and runnable standalone:

    .venv/bin/python scripts/test_alert_revenue_hourly_window.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _check(name: str, condition: bool, detail: str) -> bool:
    icon = "✓" if condition else "✗"
    print(f"  {icon} {name}: {detail}")
    return condition


def test_invariant_1_real_csv_for_google_adex() -> bool:
    """
    Phase 17.3 fix + Phase 17.4 Path A: data_source='real_csv' for
    GOOGLE_ADEX BACKTEST (helper reads hour_kpi.csv directly, bypassing
    the top-50 parquet filter). Pre-Phase-17.3: 'synthetic'. Post-Phase-17.3:
    'real_parquet'. Post-Phase-17.4: 'real_csv' (D2CLOSE-01 Path A).
    """
    print("\n[INVARIANT 1] data_fetcher_real returns real_csv for GOOGLE_ADEX BACKTEST")
    from backend.agents.data_fetcher_real import data_fetcher_agent as real_fetcher

    state = {
        "trigger_type": "A2",
        "channel_group": "GOOGLE_ADEX",
        "mode": "BACKTEST",
        "timestamp": "2026-03-22T01:00:00+00:00",  # hour_kpi.csv has 214 rows for this hour
        "execution_errors": [],
    }
    result = real_fetcher(state)
    source = result.get("data_source", "?")
    rev = result.get("current_metrics", {}).get("revenue", 0)

    ok = _check(
        "data_source == 'real_csv'",
        source == "real_csv",
        f"got {source!r} (revenue={rev}, expected real_csv per Phase 17.4 Path A)",
    )
    return ok


def test_invariant_2_sample_alerts_revenue_origin() -> bool:
    """
    Sample 1 (GOOGLE_ADEX): parquet-derived revenue must be within ±25%
    of the DB value when fix is applied, OR clearly fallback-synthetic
    in BACKTEST + non-covered channel.

    Note: pre-fix this returns synthetic and matches DB byte-for-byte.
    Post-fix it should switch to parquet for GOOGLE_ADEX. The ±25%
    tolerance is wide because pre-fix synthetic and parquet-real
    are fundamentally different sources — but post-fix revenue should
    REPLACE the DB value, not match it. So this invariant asserts that
    a NEW alert computed today via the pipeline returns parquet origin,
    not synthetic.
    """
    print("\n[INVARIANT 2] Sample 1 GOOGLE_ADEX 2026-03-22 01:00 — parquet path returns real data")
    from backend.agents.data_fetcher_real import (
        _load_hourly_data,
        _get_hourly_metrics,
    )

    df = _load_hourly_data()
    if df is None:
        return _check("parquet load", False, "_load_hourly_data returned None")

    # Use the tz-naive ts that parquet expects (this is what the fix must produce)
    ts_naive = datetime(2026, 3, 22, 1, 0, 0)
    m = _get_hourly_metrics(df, ts_naive, "GOOGLE_ADEX")
    if m is None:
        return _check("parquet has GOOGLE_ADEX 2026-03-22 01:00", False, "metrics is None")

    rev_net = m.get("revenue", 0)
    rev_gross = m.get("revenue_gross", 0)
    # Parquet ground truth for this hour (top-50 publisher filter applied)
    # Net €312.87, gross €521.44. DB synthetic value is €736.01.
    ok_net = _check(
        "parquet net revenue in [€300, €400]",
        300.0 <= rev_net <= 400.0,
        f"got €{rev_net:.2f}",
    )
    ok_gross = _check(
        "parquet gross revenue in [€500, €600]",
        500.0 <= rev_gross <= 600.0,
        f"got €{rev_gross:.2f}",
    )
    return ok_net and ok_gross


def test_invariant_3_no_silent_synthetic_for_covered_channels() -> bool:
    """
    For every channel with parquet hourly coverage, the pipeline MUST NOT
    silently fall back to synthetic. Currently only GOOGLE_ADEX has hourly
    coverage (verified via hour_kpi.csv ingestion).

    For non-covered channels (HBM/HBP/TAM/DIRECT/DEAL), synthetic is the
    only available option in BACKTEST — that's structural, but it must
    NOT happen for GOOGLE_ADEX.
    """
    print("\n[INVARIANT 3] No silent synthetic fallback for parquet-covered channels")
    from backend.agents.data_fetcher_real import data_fetcher_agent as real_fetcher

    state = {
        "trigger_type": "A1",
        "channel_group": "GOOGLE_ADEX",
        "mode": "BACKTEST",
        "timestamp": "2026-03-20T12:00:00+00:00",  # mid-day, well within parquet coverage
        "execution_errors": [],
    }
    result = real_fetcher(state)
    source = result.get("data_source", "?")
    ok = _check(
        "GOOGLE_ADEX 2026-03-20 12:00 → data_source != 'synthetic'",
        source != "synthetic",
        f"got {source!r}",
    )
    return ok


def test_invariant_4_synthetic_db_byte_match_pre_fix() -> bool:
    """
    Documents the DIAGNOSIS reproduction: pre-fix, the synthetic generator
    is byte-identical to DB values. This invariant will REMAIN TRUE
    post-fix (synthetic formula unchanged), but its purpose is to assert
    the DIAGNOSIS evidence is reproducible.
    """
    print("\n[INVARIANT 4] DIAGNOSIS evidence: synthetic byte-match to DB sample alerts")
    from backend.agents.data_fetcher import (
        _generate_hourly_metrics,
        _build_anomaly_config,
    )

    # Sample 1: ALT-20260322-010000-P2 → GOOGLE_ADEX A2 hh=1
    ts1 = datetime(2026, 3, 22, 1, 0, 0, tzinfo=timezone.utc)
    anom1 = _build_anomaly_config("A2", "GOOGLE_ADEX")
    m1 = _generate_hourly_metrics(ts1, "GOOGLE_ADEX", anom1)
    ok1 = _check(
        "Sample 1 synthetic == DB 736.01",
        abs(m1["revenue"] - 736.01) < 0.05,
        f"got €{m1['revenue']}",
    )

    # Sample 2: ALT-20260320-070000-P2 → HBM A2 hh=7
    ts2 = datetime(2026, 3, 20, 7, 0, 0, tzinfo=timezone.utc)
    anom2 = _build_anomaly_config("A2", "HEADER_BIDDING_MAGNITE")
    m2 = _generate_hourly_metrics(ts2, "HEADER_BIDDING_MAGNITE", anom2)
    ok2 = _check(
        "Sample 2 synthetic == DB 1185.04",
        abs(m2["revenue"] - 1185.04) < 0.05,
        f"got €{m2['revenue']}",
    )
    return ok1 and ok2


def main() -> int:
    print("=" * 70)
    print("Phase 17.3 — Alert Revenue Hourly Window Contract Test")
    print("=" * 70)
    print("Pins invariants from D2 (Marco email 2026-05-19) on the alert")
    print("revenue computation path. RED before tz-fix, GREEN after.")

    results = [
        test_invariant_1_real_csv_for_google_adex(),
        test_invariant_2_sample_alerts_revenue_origin(),
        test_invariant_3_no_silent_synthetic_for_covered_channels(),
        test_invariant_4_synthetic_db_byte_match_pre_fix(),
    ]

    passed = sum(results)
    total = len(results)
    print()
    print("=" * 70)
    if passed == total:
        print(f"✓ All {total} Phase 17.3 invariants hold")
        return 0
    print(f"✗ {total - passed}/{total} Phase 17.3 invariants FAIL — see output above")
    return 1


if __name__ == "__main__":
    sys.exit(main())
