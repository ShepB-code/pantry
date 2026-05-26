#!/usr/bin/env bash
# Start Pantry's local Postgres (Docker). Tries docker-compose, then docker compose.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if command -v docker-compose >/dev/null 2>&1; then
  echo "Using docker-compose ..."
  docker-compose up -d
elif docker compose version >/dev/null 2>&1; then
  echo "Using docker compose ..."
  docker compose up -d
else
  cat <<'EOF' >&2
Docker Compose is not available.

Install one of:

  brew install docker-compose
  # then re-run: ./scripts/start-postgres.sh

  # or install Docker Desktop (includes Compose):
  # https://www.docker.com/products/docker-desktop/

Or skip Docker and use Homebrew Postgres — see backend/docs/DATABASE.md
EOF
  exit 1
fi

echo "Postgres should be on localhost:5432 (user/password/db: pantry/pantry/pantry)"
echo "DATABASE_URL=postgresql+psycopg://pantry:pantry@localhost:5432/pantry"
