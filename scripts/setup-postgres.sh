#!/usr/bin/env bash
# Local Postgres for Pantry — Docker Compose or Homebrew.
#
# Usage:
#   ./scripts/setup-postgres.sh          # Docker (default)
#   ./scripts/setup-postgres.sh docker
#   ./scripts/setup-postgres.sh brew
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-docker}"

setup_docker() {
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
  # then re-run: ./scripts/setup-postgres.sh docker

  # or install Docker Desktop (includes Compose):
  # https://www.docker.com/products/docker-desktop/

Or use Homebrew Postgres instead:
  ./scripts/setup-postgres.sh brew
EOF
    exit 1
  fi

  echo "Postgres should be on localhost:5432 (user/password/db: pantry/pantry/pantry)"
  echo "DATABASE_URL=postgresql+psycopg://pantry:pantry@localhost:5432/pantry"
}

setup_brew() {
  export PATH="/opt/homebrew/opt/postgresql@18/bin:/opt/homebrew/opt/postgresql@16/bin:/opt/homebrew/opt/postgresql/bin:${PATH:-}"

  if ! command -v psql >/dev/null 2>&1; then
    echo "Install Postgres first: brew install postgresql@16 && brew services start postgresql@16" >&2
    exit 1
  fi

  psql postgres -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'pantry') THEN
    CREATE ROLE pantry WITH LOGIN PASSWORD 'pantry' CREATEDB;
  END IF;
END
$$;
SQL

  if ! psql postgres -tAc "SELECT 1 FROM pg_database WHERE datname = 'pantry'" | grep -q 1; then
    createdb -O pantry pantry
  fi

  echo "OK — connect with:"
  echo "  psql postgresql://pantry:pantry@127.0.0.1:5432/pantry"
  echo ""
  echo "backend/.env:"
  echo "  DATABASE_URL=postgresql+psycopg://pantry:pantry@127.0.0.1:5432/pantry"
}

case "$MODE" in
  docker) setup_docker ;;
  brew) setup_brew ;;
  -h|--help)
    grep '^#' "$0" | head -10
    exit 0
    ;;
  *)
    echo "Unknown mode: $MODE (use docker or brew)" >&2
    exit 1
    ;;
esac
