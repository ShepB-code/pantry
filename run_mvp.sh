#!/usr/bin/env bash
# Legacy helper — prefer backend/docs/RUNNING.md and scripts/bootstrap-db.sh
#
# Starts API + frontend only. Does NOT seed the database.
# Run ./scripts/bootstrap-db.sh first on a new machine.
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
echo "Pantry MVP — starting API + UI (see backend/docs/RUNNING.md for full setup)"
echo ""

if [[ ! -f "$ROOT/backend/.env" ]]; then
  echo "Warning: backend/.env missing. Copy backend/.env.example and run ./scripts/bootstrap-db.sh"
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Install: https://docs.astral.sh/uv/" >&2
  exit 1
fi

cd "$ROOT/backend"
uv sync
uv run uvicorn app:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!

cd "$ROOT/frontend"
npm install --no-audit --no-fund
npm run dev &
FRONTEND_PID=$!

echo ""
echo "Backend:  http://127.0.0.1:8000"
echo "Frontend: http://localhost:8080 (typical)"
echo "Press Ctrl+C to stop."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
