#!/usr/bin/env python3
"""
Seed Alerts from Real Parquet Data
Populates the dashboard with real historical alerts from the last 7 days of hourly data.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.backtest.runner_real import BacktestRunnerReal
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Path to hourly data
BASE_DIR = Path(__file__).parent.parent
HOURLY_PARQUET = BASE_DIR / "data" / "baseline" / "hourly_aggregated.parquet"


def log(msg: str):
    """Log to console and file"""
    print(f"[{datetime.now().isoformat()}] {msg}")
    with open("/tmp/vna-dataintegration.log", "a") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")


def seed_alerts():
    """
    Seed alerts from the last 7 days of available hourly data.
    """
    log("=" * 80)
    log("SEEDING ALERTS FROM REAL PARQUET DATA")
    log("=" * 80)

    if not os.path.exists(HOURLY_PARQUET):
        log(f"ERROR: Hourly parquet not found at {HOURLY_PARQUET}")
        log("Please run scripts/aggregate_parquet.py first")
        return False

    # Load data to find date range
    import pandas as pd

    df = pd.read_parquet(HOURLY_PARQUET)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    data_start = df['timestamp'].min()
    data_end = df['timestamp'].max()

    log(f"Data available from {data_start} to {data_end}")

    # Take last 7 days of data
    backtest_start = data_end - timedelta(days=7)
    backtest_end = data_end

    log(f"Seeding alerts for period: {backtest_start.date()} to {backtest_end.date()}")

    # Create backtest runner
    runner = BacktestRunnerReal(
        start_date=backtest_start.strftime("%Y-%m-%d"),
        end_date=backtest_end.strftime("%Y-%m-%d"),
        step_hours=2  # Check every 2 hours
    )

    # Run backtest
    backtest_id = f"seed_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    log(f"Starting backtest with ID: {backtest_id}")

    result = runner.run(backtest_id)

    if result.get("status") == "COMPLETED":
        log("=" * 80)
        log("✓ ALERT SEEDING COMPLETED SUCCESSFULLY")
        log(f"  Total checks: {result['total_checks']}")
        log(f"  Alerts generated: {result['alerts_generated']}")
        log(f"  Trigger rate: {100.0 * result['alerts_generated'] / result['total_checks']:.1f}%")
        log(f"  Date range: {result['actual_start']} to {result['actual_end']}")
        log("=" * 80)
        return True
    else:
        log("=" * 80)
        log("✗ ALERT SEEDING FAILED")
        log(f"  Error: {result.get('error', 'Unknown error')}")
        log("=" * 80)
        return False


def main():
    """Main entry point"""
    log("\n" + "=" * 80)
    log("VALUE NETWORK ALERTING - ALERT SEEDING")
    log("=" * 80)
    log(f"Start time: {datetime.now()}")

    success = seed_alerts()

    log(f"End time: {datetime.now()}")
    log("=" * 80 + "\n")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
