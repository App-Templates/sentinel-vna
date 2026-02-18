#!/bin/bash

# Value Network Alerting - Full Data Integration Script
# This script runs the complete data integration pipeline

set -e  # Exit on error

echo "================================================================================"
echo "VALUE NETWORK ALERTING - FULL DATA INTEGRATION"
echo "================================================================================"
echo "Start time: $(date)"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Clear log file
LOG_FILE="/tmp/vna-dataintegration.log"
echo "Clearing log file: $LOG_FILE"
> "$LOG_FILE"
echo ""

# Step 1: Verify data paths
echo "================================================================================"
echo "STEP 1: VERIFY DATA PATHS"
echo "================================================================================"
python3 scripts/verify_data_paths.py

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Source data files not found!"
    echo "Please ensure the parquet files are in the correct location."
    exit 1
fi

echo ""
read -p "Source data files found. Continue with aggregation? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted by user"
    exit 0
fi

# Step 2: Run aggregation
echo ""
echo "================================================================================"
echo "STEP 2: AGGREGATE PARQUET DATA"
echo "================================================================================"
echo "This will process 156M+ rows. Please be patient..."
echo ""

python3 scripts/aggregate_parquet.py

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Aggregation failed!"
    echo "Check logs at $LOG_FILE"
    exit 1
fi

# Step 3: Test integration
echo ""
echo "================================================================================"
echo "STEP 3: TEST INTEGRATION"
echo "================================================================================"
python3 scripts/test_integration.py

if [ $? -ne 0 ]; then
    echo ""
    echo "WARNING: Some integration tests failed"
    echo "Check the output above for details"
    echo ""
    read -p "Continue with alert seeding anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted by user"
        exit 0
    fi
fi

# Step 4: Seed alerts
echo ""
echo "================================================================================"
echo "STEP 4: SEED HISTORICAL ALERTS (OPTIONAL)"
echo "================================================================================"
echo "This will populate the dashboard with alerts from the last 7 days of data."
echo ""
read -p "Proceed with alert seeding? [y/N] " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    python3 scripts/seed_alerts_from_parquet.py

    if [ $? -ne 0 ]; then
        echo ""
        echo "WARNING: Alert seeding failed"
        echo "Check logs at $LOG_FILE"
    fi
else
    echo "Skipping alert seeding"
fi

# Summary
echo ""
echo "================================================================================"
echo "INTEGRATION COMPLETE"
echo "================================================================================"
echo "End time: $(date)"
echo ""
echo "Next steps:"
echo "  1. Start the backend: python -m backend.api.server"
echo "  2. Start the frontend: cd frontend && npm run dev"
echo "  3. Open dashboard: http://localhost:5173"
echo ""
echo "Logs available at: $LOG_FILE"
echo "================================================================================"
