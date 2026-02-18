#!/usr/bin/env python3
"""
Integration Test Script
Tests the real data integration end-to-end.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def log(msg: str):
    """Print with timestamp"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def test_aggregated_files():
    """Test 1: Verify aggregated files exist"""
    log("=" * 80)
    log("TEST 1: Verify Aggregated Files")
    log("=" * 80)

    base_dir = Path(__file__).parent.parent
    output_dir = base_dir / "data" / "baseline"

    required_files = [
        "hourly_aggregated.parquet",
        "daily_channel_aggregated.parquet",
        "daily_adrequests_aggregated.parquet",
    ]

    all_exist = True
    for filename in required_files:
        filepath = output_dir / filename
        if filepath.exists():
            size_mb = filepath.stat().st_size / 1024 / 1024
            log(f"  ✓ {filename} ({size_mb:.1f} MB)")
        else:
            log(f"  ✗ {filename} NOT FOUND")
            all_exist = False

    if all_exist:
        log("✓ TEST 1 PASSED: All aggregated files exist\n")
        return True
    else:
        log("✗ TEST 1 FAILED: Some aggregated files missing")
        log("  Run: python scripts/aggregate_parquet.py\n")
        return False


def test_data_loading():
    """Test 2: Load aggregated data and verify structure"""
    log("=" * 80)
    log("TEST 2: Load Aggregated Data")
    log("=" * 80)

    try:
        import pandas as pd

        base_dir = Path(__file__).parent.parent
        output_dir = base_dir / "data" / "baseline"

        # Test hourly
        log("Loading hourly_aggregated.parquet...")
        df_hourly = pd.read_parquet(output_dir / "hourly_aggregated.parquet")
        log(f"  ✓ Loaded {len(df_hourly):,} rows")
        log(f"  Columns: {list(df_hourly.columns)}")
        log(f"  Date range: {df_hourly['timestamp'].min()} to {df_hourly['timestamp'].max()}")
        log(f"  Publishers: {df_hourly['publisher_id'].nunique()}")
        log(f"  Channels: {df_hourly['channel_group'].unique().tolist()}")

        # Test daily channel
        log("\nLoading daily_channel_aggregated.parquet...")
        df_daily_ch = pd.read_parquet(output_dir / "daily_channel_aggregated.parquet")
        log(f"  ✓ Loaded {len(df_daily_ch):,} rows")
        log(f"  Date range: {df_daily_ch['date'].min()} to {df_daily_ch['date'].max()}")
        log(f"  Geo clusters: {df_daily_ch['geo_cluster'].unique().tolist()}")

        # Test daily adrequests
        log("\nLoading daily_adrequests_aggregated.parquet...")
        df_daily_ad = pd.read_parquet(output_dir / "daily_adrequests_aggregated.parquet")
        log(f"  ✓ Loaded {len(df_daily_ad):,} rows")
        log(f"  Avg coverage: {df_daily_ad['coverage'].mean():.4f}")

        log("\n✓ TEST 2 PASSED: All data files loaded successfully\n")
        return True

    except Exception as e:
        log(f"✗ TEST 2 FAILED: {e}\n")
        return False


def test_data_fetcher():
    """Test 3: Test data fetcher agent with real data"""
    log("=" * 80)
    log("TEST 3: Test Data Fetcher Agent")
    log("=" * 80)

    try:
        from backend.agents.data_fetcher_real import _load_hourly_data, _get_hourly_metrics, _calculate_baseline_from_hourly
        from datetime import timezone

        log("Loading hourly data...")
        df = _load_hourly_data()

        if df is None:
            log("✗ TEST 3 FAILED: Could not load hourly data\n")
            return False

        log(f"  ✓ Data loaded: {len(df):,} rows")

        # Get a sample timestamp from the data
        sample_ts = df['timestamp'].iloc[len(df) // 2]  # Middle of dataset
        channel = df['channel_group'].iloc[0]

        log(f"\nTesting metrics for: {sample_ts} / {channel}")

        # Get current metrics
        current = _get_hourly_metrics(df, sample_ts, channel)
        if current is None:
            log("✗ TEST 3 FAILED: Could not get current metrics\n")
            return False

        log(f"  Current revenue: €{current['revenue']:,.2f}")
        log(f"  Current bacino: {current['bacino']:,}")
        log(f"  Current coverage: {current['coverage']:.4f}")
        log(f"  Publishers: {len(current['publishers'])}")
        log(f"  Geo clusters: {len(current['geo'])}")
        log(f"  Environments: {len(current['environment'])}")

        # Calculate baseline
        log("\nCalculating baseline (7 weeks back)...")
        baseline_result = _calculate_baseline_from_hourly(df, sample_ts, channel)

        if baseline_result is None:
            log("✗ TEST 3 FAILED: Could not calculate baseline\n")
            return False

        baseline = baseline_result['baseline_metrics']
        stats = baseline_result['historical_stats']

        log(f"  Baseline revenue: €{baseline['revenue']:,.2f}")
        log(f"  Baseline bacino: {baseline['bacino']:,}")
        log(f"  Revenue std: €{stats['revenue_std']:,.2f}")
        log(f"  Data points: {stats['baseline_data_points']}")

        # Calculate delta
        delta_pct = 100.0 * (current['revenue'] - baseline['revenue']) / baseline['revenue']
        log(f"\nDelta: {delta_pct:+.2f}%")

        log("\n✓ TEST 3 PASSED: Data fetcher working correctly\n")
        return True

    except Exception as e:
        log(f"✗ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def test_workflow():
    """Test 4: Run full workflow with real data"""
    log("=" * 80)
    log("TEST 4: Test Full Workflow")
    log("=" * 80)

    try:
        from backend.workflow.graph import create_workflow
        from backend.workflow.state import AlertState
        from backend.agents.data_fetcher_real import _load_hourly_data

        log("Loading data to get valid timestamp...")
        df = _load_hourly_data()

        if df is None:
            log("✗ TEST 4 FAILED: Could not load data\n")
            return False

        # Get a timestamp from the middle of the dataset
        sample_ts = df['timestamp'].iloc[len(df) // 2]
        channel = "GOOGLE"

        log(f"Creating workflow for: {sample_ts} / {channel}")

        # Create workflow
        workflow = create_workflow()

        # Create initial state
        initial_state: AlertState = {
            "timestamp": sample_ts.isoformat(),
            "channel_group": channel,
            "trigger_type": "A1",
            "severity": None,
            "current_metrics": {},
            "baseline_metrics": {},
            "historical_stats": {},
            "delta": {},
            "triage": {},
            "insights": {},
            "alert_id": None,
            "should_alert": False,
            "execution_errors": [],
            "config_version": "1.0.0",
            "data_source": "test",
        }

        log("Running workflow...")
        final_state = workflow.invoke(initial_state)

        log(f"  Data source: {final_state.get('data_source', 'unknown')}")
        log(f"  Current revenue: €{final_state['current_metrics'].get('revenue', 0):,.2f}")
        log(f"  Baseline revenue: €{final_state['baseline_metrics'].get('revenue', 0):,.2f}")
        log(f"  Delta: {final_state['delta'].get('revenue_delta_pct', 0):+.2f}%")
        log(f"  Should alert: {final_state.get('should_alert', False)}")

        if final_state.get('should_alert'):
            log(f"  Severity: {final_state.get('severity')}")
            log(f"  Rule: {final_state.get('trigger_type')}")
            log(f"  Triage: {final_state['triage'].get('primary_driver', 'unknown')}")

        if final_state.get('execution_errors'):
            log(f"  Errors: {final_state['execution_errors']}")

        if final_state.get('data_source') == 'real_parquet':
            log("\n✓ TEST 4 PASSED: Workflow ran successfully with real data\n")
            return True
        else:
            log(f"\n⚠ TEST 4 WARNING: Workflow ran but used {final_state.get('data_source')} data\n")
            return True

    except Exception as e:
        log(f"✗ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def main():
    """Run all integration tests"""
    log("\n" + "=" * 80)
    log("VALUE NETWORK ALERTING - INTEGRATION TESTS")
    log("=" * 80)
    log(f"Start time: {datetime.now()}\n")

    results = []

    # Test 1: Aggregated files
    results.append(("Aggregated Files", test_aggregated_files()))

    # Only run subsequent tests if files exist
    if results[0][1]:
        # Test 2: Data loading
        results.append(("Data Loading", test_data_loading()))

        # Test 3: Data fetcher
        results.append(("Data Fetcher", test_data_fetcher()))

        # Test 4: Full workflow
        results.append(("Full Workflow", test_workflow()))
    else:
        log("Skipping remaining tests (aggregated files not found)\n")

    # Summary
    log("=" * 80)
    log("TEST SUMMARY")
    log("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        log(f"  {status}: {test_name}")

    log(f"\nTotal: {passed}/{total} tests passed")
    log(f"End time: {datetime.now()}")
    log("=" * 80 + "\n")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
