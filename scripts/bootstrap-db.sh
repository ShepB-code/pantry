#!/usr/bin/env bash
# First-time (or refresh) database bootstrap from files under data/toast/.
#
# Usage:
#   ./scripts/bootstrap-db.sh
#   ./scripts/bootstrap-db.sh noriko
#   ./scripts/bootstrap-db.sh perilla --skip-pos
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

LOCATION="${PANTRY_DEFAULT_LOCATION_ID:-perilla}"
EXTRA=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-xtrachef|--skip-menu-export|--skip-pos)
      EXTRA+=("$1")
      shift
      ;;
    --pos-file)
      EXTRA+=("$1" "$2")
      shift 2
      ;;
    -h|--help)
      grep '^#' "$0" | head -20
      exit 0
      ;;
    *)
      LOCATION="$1"
      shift
      ;;
  esac
done

if [[ ! -f .env ]]; then
  echo "Creating backend/.env from .env.example ..."
  cp .env.example .env
  echo "Edit backend/.env (DATABASE_URL, PANTRY_DEFAULT_LOCATION_ID) if needed."
fi

export PANTRY_DEFAULT_LOCATION_ID="${LOCATION}"

echo "==> Pantry DB bootstrap (location: ${LOCATION})"
echo "    Repo: ${ROOT}"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Install: https://docs.astral.sh/uv/" >&2
  exit 1
fi

uv sync
uv run alembic upgrade head
uv run python -m pantry_engine.cli db-seed --location "${LOCATION}" "${EXTRA[@]}"

echo ""
echo "Done. Next:"
echo "  cd backend && uv run uvicorn app:app --reload --port 8000"
echo "  cd frontend && npm install && npm run dev"
echo "  Open http://localhost:8080 → Inventory"
