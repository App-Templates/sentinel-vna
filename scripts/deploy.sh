#!/bin/bash
# Full deploy pipeline: build → export API → copy config → deploy to Vercel
# Usage: ./scripts/deploy.sh [--skip-backend]
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== SENTINEL Deploy Pipeline ==="

# 1. Clean dist completely for fresh build
rm -rf frontend/dist

# 2. Build frontend
echo "[1/4] Building frontend..."
cd frontend && npx vite build 2>&1 | tail -3
cd "$ROOT"

# 3. Export API JSON (requires backend on port 8000)
if [ "$1" != "--skip-backend" ]; then
  echo "[2/4] Checking backend..."
  if ! curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "  Starting backend..."
    source .venv/bin/activate
    nohup python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > /tmp/sentinel-backend.log 2>&1 &
    BACKEND_PID=$!
    sleep 4
    if ! curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
      echo "  ERROR: Backend failed to start. Check /tmp/sentinel-backend.log"
      exit 1
    fi
    echo "  Backend started (PID $BACKEND_PID)"
  else
    echo "  Backend already running"
  fi
fi

echo "[3/4] Exporting API JSON..."
bash scripts/export_api_json.sh

# 4. Copy vercel.json and deploy
echo "[4/4] Deploying to Vercel..."
cp vercel.json frontend/dist/vercel.json
cd frontend/dist

# Ensure linked to correct project
if [ ! -d .vercel ] || ! grep -q "sentinel-vna" .vercel/project.json 2>/dev/null; then
  npx vercel link --yes --project sentinel-vna
fi

npx vercel --prod --yes 2>&1 | grep -E "Aliased|READY|Error"

# Cleanup backend if we started it
if [ -n "$BACKEND_PID" ]; then
  echo "Stopping backend (PID $BACKEND_PID)..."
  kill $BACKEND_PID 2>/dev/null
fi

echo ""
echo "=== Deploy complete: https://sentinel-vna.vercel.app ==="
