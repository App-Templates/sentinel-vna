#!/usr/bin/env python3
"""
Verify Data Paths Script
Checks if source parquet files exist and shows their metadata.
"""

import os
import sys
from pathlib import Path

# Data paths
HOURLY_PATH = "/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_hourly/data.parquet"
DAILY_CHANNEL_PATH = "/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_daily/data_channel.parquet"
DAILY_ADREQUESTS_PATH = "/Users/admintemp/Downloads/Value Network - Yield Optimization and Alerting/dataset_daily/data_adrequests.parquet"

# Output directory
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "baseline"


def check_file(path: str, name: str) -> bool:
    """Check if file exists and show details"""
    print(f"\n{name}:")
    print(f"  Path: {path}")

    if os.path.exists(path):
        size_mb = os.path.getsize(path) / 1024 / 1024
        print(f"  ✓ EXISTS (size: {size_mb:.1f} MB)")

        # Try to read metadata
        try:
            import pyarrow.parquet as pq
            pf = pq.ParquetFile(path)
            print(f"  Rows: {pf.metadata.num_rows:,}")
            print(f"  Columns: {pf.schema.names}")
        except ImportError:
            print("  (install pyarrow to see metadata)")
        except Exception as e:
            print(f"  (error reading metadata: {e})")

        return True
    else:
        print(f"  ✗ NOT FOUND")
        return False


def main():
    print("=" * 80)
    print("DATA PATH VERIFICATION")
    print("=" * 80)

    # Check source files
    print("\nSOURCE DATA FILES:")
    hourly_ok = check_file(HOURLY_PATH, "Hourly Data")
    channel_ok = check_file(DAILY_CHANNEL_PATH, "Daily Channel Data")
    adrequests_ok = check_file(DAILY_ADREQUESTS_PATH, "Daily AdRequests Data")

    # Check output directory
    print("\n\nOUTPUT DIRECTORY:")
    print(f"  Path: {OUTPUT_DIR}")
    if OUTPUT_DIR.exists():
        print(f"  ✓ EXISTS")

        # Check aggregated files
        aggregated_files = list(OUTPUT_DIR.glob("*.parquet"))
        if aggregated_files:
            print(f"  Aggregated files found: {len(aggregated_files)}")
            for f in aggregated_files:
                size_mb = f.stat().st_size / 1024 / 1024
                print(f"    - {f.name} ({size_mb:.1f} MB)")
        else:
            print(f"  ✗ No aggregated files yet (run scripts/aggregate_parquet.py)")
    else:
        print(f"  ✗ NOT CREATED YET")
        print(f"  Will be created when you run scripts/aggregate_parquet.py")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY:")

    if hourly_ok and channel_ok and adrequests_ok:
        print("✓ All source data files found!")
        print("\nNext step: Run the aggregation script:")
        print("  cd /Users/admintemp/Downloads/Claude/value-network-alerting")
        print("  python scripts/aggregate_parquet.py")
    else:
        print("✗ Some source data files are missing!")
        print("\nMissing files:")
        if not hourly_ok:
            print(f"  - {HOURLY_PATH}")
        if not channel_ok:
            print(f"  - {DAILY_CHANNEL_PATH}")
        if not adrequests_ok:
            print(f"  - {DAILY_ADREQUESTS_PATH}")
        print("\nPlease ensure the source data files are in the correct location.")

    print("=" * 80)

    return 0 if (hourly_ok and channel_ok and adrequests_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
