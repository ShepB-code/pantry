#!/usr/bin/env bash
# Drop all Pantry database data and re-run bootstrap-db.sh (schema + seed from data/toast/).
#
# Usage:
#   ./scripts/reset-db.sh --yes perilla
#   ./scripts/reset-db.sh --yes --wipe-ingest perilla
#
# Options:
#   --yes           Required — confirms you want to destroy all DB data
#   --wipe-ingest   Also remove data/ingest/inbox, archive, failed CSVs (+ SQLite fallback db)
#   --docker-volume Stop Docker Postgres and delete its volume (only if pantry-postgres exists)
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

YES=0
WIPE_INGEST=0
DOCKER_VOLUME=0
LOCATION="${PANTRY_DEFAULT_LOCATION_ID:-perilla}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes) YES=1; shift ;;
    --wipe-ingest) WIPE_INGEST=1; shift ;;
    --docker-volume) DOCKER_VOLUME=1; shift ;;
    -h|--help)
      grep '^#' "$0" | head -25
      exit 0
      ;;
    *)
      LOCATION="$1"
      shift
      ;;
  esac
done

if [[ "$YES" -ne 1 ]]; then
  echo "This deletes ALL Pantry database data for the configured DATABASE_URL." >&2
  echo "Re-run with: ./scripts/reset-db.sh --yes [$LOCATION]" >&2
  exit 1
fi

if [[ ! -f "$ROOT/backend/.env" ]]; then
  echo "Missing backend/.env — copy from backend/.env.example first." >&2
  exit 1
fi

if [[ "$DOCKER_VOLUME" -eq 1 ]] && docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx pantry-postgres; then
  echo "==> Stopping Docker Postgres and removing volume ..."
  cd "$ROOT"
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose down -v
  else
    docker compose down -v
  fi
  ./scripts/setup-postgres.sh docker
  echo "    Waiting for Postgres ..."
  sleep 3
fi

echo "==> Resetting database ..."
cd "$ROOT/backend"
uv run python - <<PY
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(".env"))
from pantry_engine.db.reset import reset_database

print("   ", reset_database())
PY

if [[ "$WIPE_INGEST" -eq 1 ]]; then
  echo "==> Wiping local ingest artifacts (inbox/archive/failed) ..."
  rm -rf "$ROOT/data/ingest/inbox/toast-pos/"*.csv \
         "$ROOT/data/ingest/archive/toast-pos/"* \
         "$ROOT/data/ingest/failed/toast-pos/"* 2>/dev/null || true
  mkdir -p "$ROOT/data/ingest/inbox/toast-pos" \
           "$ROOT/data/ingest/archive/toast-pos" \
           "$ROOT/data/ingest/failed/toast-pos"
  touch "$ROOT/data/ingest/inbox/toast-pos/.gitkeep" \
        "$ROOT/data/ingest/archive/toast-pos/.gitkeep" \
        "$ROOT/data/ingest/failed/toast-pos/.gitkeep" 2>/dev/null || true
fi

echo "==> Re-bootstrap from data/toast/ ..."
"$ROOT/scripts/bootstrap-db.sh" "$LOCATION"

echo ""
echo "Database reset complete for location: $LOCATION"
