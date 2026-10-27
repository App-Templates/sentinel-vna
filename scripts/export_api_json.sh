#!/bin/bash
# Export all GET API endpoints to static JSON files for Vercel deployment
# Usage: ./scripts/export_api_json.sh [BASE_URL]

BASE=${1:-http://localhost:8000}
OUT=frontend/dist/api
mkdir -p "$OUT"

echo "=== Exporting SENTINEL API to $OUT ==="

# Pre-export housekeeping: clean stale per-entity files so an older entity
# rename or removal cannot ship via Vercel (hardening from Phase 17.1 Wave 4
# DEPLOY-LOG.md deviation §1 — stale Mondadori_family/eAdv/AdGage_*
# survived from 2026-05-07 pre-regen). The top-level files (publishers_top,
# alerts list permutations, metrics_*) are overwritten in place so they
# are safe; only the per-id subdirs need a clean slate.
rm -rf "$OUT/publishers" "$OUT/alerts" "$OUT/metrics"

# urlencode helper — multi-word publisher_ids (e.g. "Prensa Ibérica",
# "Grupo Godó") break naive curl URLs. Use Python urllib.parse.quote
# so spaces, accents, and other reserved chars are escaped consistently.
urlencode() {
  python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=''))" "$1"
}

# Simple endpoints
for ep in health metrics "metrics/revenue-status-24h" "admin/alerting-rules" "admin/datasources" "admin/slack-config"; do
  FILE="$OUT/$(echo $ep | tr '/' '_').json"
  curl -s "$BASE/api/$ep" > "$FILE"
  echo "  $ep → $FILE ($(wc -c < "$FILE") bytes)"
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

# Iterate via `while read` so any whitespace inside an alert_id stays intact
# (defensive: alerts shouldn't contain spaces today, but the publishers loop
# below absolutely does — applying the same pattern here removes the
# class-of-bug entirely).
mkdir -p "$OUT/alerts"
while IFS= read -r aid; do
  [ -z "$aid" ] && continue
  ENC_AID=$(urlencode "$aid")
  curl -s "$BASE/api/alerts/$ENC_AID" > "$OUT/alerts/${aid}.json"
  curl -s "$BASE/api/alerts/$ENC_AID/trend" > "$OUT/alerts/${aid}_trend.json"
  curl -s "$BASE/api/alerts/$ENC_AID/feedbacks" > "$OUT/alerts/${aid}_feedbacks.json"
done <<< "$ALERT_IDS"

# Publishers
curl -s "$BASE/api/publishers/top" > "$OUT/publishers_top.json"
echo "  publishers/top → publishers_top.json"

PUB_IDS=$(curl -s "$BASE/api/publishers/top" | python3 -c "import json,sys; [print(p['publisher_id']) for p in json.load(sys.stdin).get('publishers',[])]")
PUB_COUNT=$(echo "$PUB_IDS" | wc -l | tr -d ' ')
echo "  Exporting $PUB_COUNT publisher details..."

# Iterate via `while read` so multi-word publisher_ids (e.g. "Prensa Ibérica",
# "Grupo Godó", "El Español", "Unidad Editorial", "La Razón", "Sociedade
# Vicra Desportiva") stay intact instead of being word-split by `for pid in
# $PUB_IDS`. Filenames keep literal spaces — vercel.json regex routes
# `([^/]+)` URL-decode the path segment so a request for
# `/api/publishers/Prensa%20Ibérica/weekly-kpis` lands on
# `publishers/Prensa Ibérica_weekly-kpis.json` byte-for-byte.
mkdir -p "$OUT/publishers"
while IFS= read -r pid; do
  [ -z "$pid" ] && continue
  ENC_PID=$(urlencode "$pid")
  curl -s "$BASE/api/publishers/$ENC_PID/weekly-kpis" > "$OUT/publishers/${pid}_weekly-kpis.json"
  curl -s "$BASE/api/publishers/$ENC_PID/ecpm-analysis" > "$OUT/publishers/${pid}_ecpm-analysis.json"
  curl -s "$BASE/api/publishers/$ENC_PID/recurring-patterns" > "$OUT/publishers/${pid}_recurring-patterns.json"
  curl -s "$BASE/api/publishers/$ENC_PID/feedback-history" > "$OUT/publishers/${pid}_feedback-history.json"
  curl -s "$BASE/api/publishers/$ENC_PID/interventions" > "$OUT/publishers/${pid}_interventions.json"
done <<< "$PUB_IDS"

# Backtest
curl -s "$BASE/api/backtest" > "$OUT/backtest.json"
echo "  backtest → backtest.json"

# Revenue status 24h — path-param variant (frontend calls /api/metrics/revenue-status-24h/{date}
# when a date is selected). Pre-export each `available_dates` entry returned by the default response
# so date-selector clicks land on a valid JSON instead of the SPA index fallback.
mkdir -p "$OUT/metrics"
DEFAULT_RS24H="$OUT/metrics_revenue-status-24h.json"
if [ -s "$DEFAULT_RS24H" ]; then
  AVAIL_DATES=$(python3 -c "import json; d=json.load(open('$DEFAULT_RS24H')); print('\n'.join(d.get('available_dates',[])))" 2>/dev/null)
  for d in $AVAIL_DATES; do
    curl -s "$BASE/api/metrics/revenue-status-24h/$d" > "$OUT/metrics/revenue-status-24h_${d}.json"
  done
  COUNT=$(echo "$AVAIL_DATES" | wc -l | tr -d ' ')
  echo "  metrics/revenue-status-24h/{date} (${COUNT} dates) → metrics/revenue-status-24h_*.json"
fi

# Network totals — pre-export for default combo (max date in CSV × GOOGLE_ADEX)
# Endpoint requires query params; static deploy serves one canonical combo.
# Probe max date by trying recent dates; fallback to known parquet max.
NT_DATE=$(curl -s "$BASE/api/metrics/network-totals?date=2026-03-23&channel=GOOGLE_ADEX" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('source_date',''))" 2>/dev/null)
if [ -z "$NT_DATE" ]; then NT_DATE="2026-03-23"; fi
curl -s "$BASE/api/metrics/network-totals?date=$NT_DATE&channel=GOOGLE_ADEX" > "$OUT/metrics_network-totals.json"
echo "  metrics/network-totals (date=$NT_DATE, channel=GOOGLE_ADEX) → metrics_network-totals.json"

TOTAL=$(find "$OUT" -name "*.json" | wc -l | tr -d ' ')
echo ""
echo "=== Export complete: $TOTAL JSON files ==="
