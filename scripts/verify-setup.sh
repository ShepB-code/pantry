#!/usr/bin/env bash
# Quick sanity check before running the UI (files + optional DB).
#
# Usage: ./scripts/verify-setup.sh [location]
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCATION="${1:-${PANTRY_DEFAULT_LOCATION_ID:-perilla}}"

echo "Pantry setup check (location: ${LOCATION})"
echo ""

ok=0
warn=0

check_file() {
  if [[ -f "$1" || -n "$(ls -1 $2 2>/dev/null | head -1)" ]]; then
    echo "  OK   $3"
    ok=$((ok + 1))
  else
    echo "  MISS $3"
    echo "       expected: $2"
    warn=$((warn + 1))
  fi
}

check_file "" "$ROOT/data/toast/xtraCHEF/${LOCATION}/*Item_Detail_Report*.csv" \
  "xtraCHEF Item Detail export"
check_file "" "$ROOT/data/toast/pos/${LOCATION}/MenuItem_Export.csv" \
  "Toast MenuItem_Export.csv (recommended)"
check_file "" "$ROOT/data/toast/pos/${LOCATION}/ItemSelectionDetails*.csv" \
  "Toast ItemSelectionDetails (for POS history)"

if [[ -f "$ROOT/backend/.env" ]]; then
  echo "  OK   backend/.env exists"
else
  echo "  MISS backend/.env (copy from backend/.env.example)"
  warn=$((warn + 1))
fi

if command -v uv >/dev/null 2>&1; then
  echo "  OK   uv installed"
else
  echo "  MISS uv — https://docs.astral.sh/uv/"
  warn=$((warn + 1))
fi

if [[ -f "$ROOT/backend/.env" ]] && grep -q '^DATABASE_URL=' "$ROOT/backend/.env" 2>/dev/null; then
  if curl -sf http://127.0.0.1:8000/api/health/db >/dev/null 2>&1; then
    echo "  OK   API health/db (is backend running?)"
  else
    echo "  —    API not reachable on :8000 (start with: cd backend && uv run uvicorn app:app --reload --port 8000)"
  fi
fi

echo ""
if [[ $warn -eq 0 ]]; then
  echo "Looks good. Run: ./scripts/bootstrap-db.sh ${LOCATION}"
else
  echo "${warn} issue(s) above. See backend/docs/RUNNING.md"
  exit 1
fi
