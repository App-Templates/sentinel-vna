#!/bin/bash
# Export all GET API endpoints to static JSON files for Vercel deployment
# Usage: ./scripts/export_api_json.sh [BASE_URL]

BASE=${1:-http://localhost:8000}
OUT=frontend/dist/api
mkdir -p "$OUT"

echo "=== Exporting SENTINEL API to $OUT ==="

# Helper: export endpoint to file, creating directories as needed
export_ep() {
  local ep="$1"
  local file="$OUT/${ep}.json"
  mkdir -p "$(dirname "$file")"
  curl -s "$BASE/api/$ep" > "$file"
  local size=$(wc -c < "$file" | tr -d ' ')
  echo "  $ep → $file ($size bytes)"
}

# Simple endpoints
for ep in health metrics; do
  export_ep "$ep"
done

# Admin endpoints
for ep in "admin/alerting-rules" "admin/datasources" "admin/slack-config"; do
  export_ep "$ep"
done

# Revenue Status 24h — default (last complete day)
export_ep "metrics/revenue-status-24h"

# Extract available_dates from default response and export each
DATES=$(python3 -c "import json,sys; d=json.load(sys.stdin); [print(x) for x in d.get('available_dates',[])]" < "$OUT/metrics/revenue-status-24h.json")
for dt in $DATES; do
  export_ep "metrics/revenue-status-24h/$dt"
done

# Alerts list (multiple pages/filters)
for status in "" "OPEN" "ACK" "RESOLVED"; do
  for sev in "" "P0" "P1" "P2"; do
    PARAMS="limit=500"
    FNAME="alerts"
    [ -n "$status" ] && PARAMS="$PARAMS&status=$status" && FNAME="${FNAME}_${status}"
    [ -n "$sev" ] && PARAMS="$PARAMS&severity=$sev" && FNAME="${FNAME}_${sev}"
    curl -s "$BASE/api/alerts?$PARAMS" > "$OUT/${FNAME}.json"
    echo "  alerts($PARAMS) → ${FNAME}.json"
  done
done

# Individual alerts + sub-endpoints
ALERT_IDS=$(curl -s "$BASE/api/alerts?limit=500" | python3 -c "import json,sys; [print(a['alert_id']) for a in json.load(sys.stdin).get('alerts',[])]")
ALERT_COUNT=$(echo "$ALERT_IDS" | wc -l | tr -d ' ')
echo "  Exporting $ALERT_COUNT individual alerts..."

for aid in $ALERT_IDS; do
  mkdir -p "$OUT/alerts/$aid"
  curl -s "$BASE/api/alerts/$aid" > "$OUT/alerts/${aid}.json"
  curl -s "$BASE/api/alerts/$aid/trend" > "$OUT/alerts/$aid/trend.json"
  curl -s "$BASE/api/alerts/$aid/feedbacks" > "$OUT/alerts/$aid/feedbacks.json"
done

# Publishers top
mkdir -p "$OUT/publishers"
for yr in 2024 2025 2026; do
  curl -s "$BASE/api/publishers/top?year=$yr&limit=50" > "$OUT/publishers/top_${yr}.json"
  echo "  publishers/top?year=$yr → top_${yr}.json"
done
# Default top (no year param)
curl -s "$BASE/api/publishers/top?limit=50" > "$OUT/publishers/top.json"
echo "  publishers/top → top.json"

PUB_IDS=$(curl -s "$BASE/api/publishers/top?limit=50" | python3 -c "import json,sys; [print(p['publisher_id']) for p in json.load(sys.stdin).get('publishers',[])]")
PUB_COUNT=$(echo "$PUB_IDS" | wc -l | tr -d ' ')
echo "  Exporting $PUB_COUNT publisher details..."

for pid in $PUB_IDS; do
  SAFE_PID=$(echo "$pid" | sed 's/ /%20/g')
  mkdir -p "$OUT/publishers/$SAFE_PID"
  curl -s "$BASE/api/publishers/$SAFE_PID/weekly-kpis" > "$OUT/publishers/$SAFE_PID/weekly-kpis.json"
  curl -s "$BASE/api/publishers/$SAFE_PID/ecpm-analysis" > "$OUT/publishers/$SAFE_PID/ecpm-analysis.json"
  curl -s "$BASE/api/publishers/$SAFE_PID/recurring-patterns" > "$OUT/publishers/$SAFE_PID/recurring-patterns.json"
  curl -s "$BASE/api/publishers/$SAFE_PID/feedback-history" > "$OUT/publishers/$SAFE_PID/feedback-history.json"
  curl -s "$BASE/api/publishers/$SAFE_PID/interventions" > "$OUT/publishers/$SAFE_PID/interventions.json"
done

# Backtest
export_ep "backtest"

TOTAL=$(find "$OUT" -name "*.json" | wc -l | tr -d ' ')
echo ""
echo "=== Export complete: $TOTAL JSON files ==="
