#!/usr/bin/env bash
# backup_db.sh — Safe SQLite backup for VNA alerts database
#
# Uses SQLite's .backup command which is safe even during WAL writes.
# Keeps the last 7 backups and removes older ones.
#
# Suggested crontab (every 6 hours):
#   0 */6 * * * /path/to/value-network-alerting/scripts/backup_db.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

DB_PATH="${PROJECT_DIR}/data/vna_alerts.db"
BACKUP_DIR="${PROJECT_DIR}/data/backups"
RETENTION=7

# Verify source database exists
if [ ! -f "$DB_PATH" ]; then
    echo "ERROR: Database not found at ${DB_PATH}" >&2
    exit 1
fi

# Create backup directory if needed
mkdir -p "$BACKUP_DIR"

# Generate timestamped backup filename
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/vna_alerts_${TIMESTAMP}.db"

# Perform backup using SQLite .backup (WAL-safe)
sqlite3 "$DB_PATH" ".backup '${BACKUP_FILE}'"

if [ -f "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "OK: Backup created at ${BACKUP_FILE} (${SIZE})"
else
    echo "ERROR: Backup file was not created" >&2
    exit 1
fi

# Remove old backups beyond retention limit
BACKUP_COUNT=$(ls -1t "$BACKUP_DIR"/vna_alerts_*.db 2>/dev/null | wc -l | tr -d ' ')
if [ "$BACKUP_COUNT" -gt "$RETENTION" ]; then
    REMOVE_COUNT=$((BACKUP_COUNT - RETENTION))
    ls -1t "$BACKUP_DIR"/vna_alerts_*.db | tail -n "$REMOVE_COUNT" | while read -r OLD_BACKUP; do
        rm -f "$OLD_BACKUP"
        echo "Removed old backup: $(basename "$OLD_BACKUP")"
    done
fi

echo "Backups retained: $(ls -1 "$BACKUP_DIR"/vna_alerts_*.db 2>/dev/null | wc -l | tr -d ' ')/${RETENTION}"
