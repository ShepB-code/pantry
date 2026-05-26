#!/usr/bin/env bash
# Create pantry role + database on local Homebrew PostgreSQL (matches docker-compose credentials).
set -euo pipefail

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
