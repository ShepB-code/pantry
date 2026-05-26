# Database (MVP)

PostgreSQL in production; SQLite fallback when `DATABASE_URL` is unset (local tests).

To start the API and UI after the DB is up, see [RUNNING.md](./RUNNING.md).

## Tables

| Table | Purpose |
|-------|---------|
| `locations` | Restaurants (`id`, `name`, `timezone`) |
| `inventory_items` | xtraCHEF catalog + `on_hand` + `par_level` per location (see [INVENTORY.md](./INVENTORY.md)) |
| `menu_items` | Toast menu items per location |
| `recipe_lines` | Manual menu → inventory qty per serving |
| `pos_sales_daily` | Daily sales rollup per menu item |
| `quick_count_sessions` / `quick_count_lines` | Physical counts |
| `ingestion_runs` | Import audit (SFTP, upload, xtraCHEF) |

All operational data is scoped by `location_id`.

## `inventory_items` (naming columns)

| Column | Role |
|--------|------|
| `id` | Stable key from xtraCHEF `item_description` (`item_key`) |
| `name` | Pantry ingredient label in UI (today: same as xtraCHEF description on sync) |
| `catalog_name` | Raw inventory-system label (xtraCHEF `item_description`) |
| `catalog_source` | e.g. `xtrachef` |

Ingredient vs inventory-system naming and Toast↔inventory matching are documented in [INVENTORY.md](./INVENTORY.md).

## Wired today

- **xtraCHEF** → `POST /api/inventory/sync-catalog` or API startup sync into `inventory_items` (does not overwrite `on_hand` / `par_level` on existing rows).
- **Quick count** → `quick_count_sessions` / `quick_count_lines`; updates `inventory_items.on_hand`.
- **Par** → `PATCH /api/inventory/{item_id}/par` with `{ "parLevel": 20 }`.
- **Stock UI** → `GET /api/inventory` returns `items` (includes `inventoryItem`, `catalogSource`) + `onHand` map.

## Migrations

| Revision | Change |
|----------|--------|
| `001` | MVP tables |
| `002` | `inventory_items.catalog_name`, `catalog_source` |

## Not wired yet

- **Toast POS** → `menu_items`, `pos_sales_daily`; optional depletion via `recipe_lines` (see [INVENTORY.md](./INVENTORY.md)).

## Local PostgreSQL

### Option A — Docker (repo `docker-compose.yml`)

Homebrew’s `docker` formula does **not** include Compose. If you see `docker: unknown command: docker compose`, install Compose separately:

```bash
brew install docker-compose
```

Start the database (from repo root):

```bash
./scripts/start-postgres.sh
# or: docker-compose up -d
```

Connection string for `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg://pantry:pantry@localhost:5432/pantry
```

Connect with `psql`:

```bash
psql postgresql://pantry:pantry@localhost:5432/pantry
```

### Option B — Homebrew Postgres (no Docker)

```bash
brew install postgresql@16
brew services start postgresql@16

# Add CLI to PATH if needed (Apple Silicon):
echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc

Match Docker credentials (recommended if docs use `pantry` / `pantry`):

```bash
./scripts/setup-postgres-brew.sh
psql postgresql://pantry:pantry@127.0.0.1:5432/pantry
```

```env
DATABASE_URL=postgresql+psycopg://pantry:pantry@127.0.0.1:5432/pantry
```

Or use your macOS superuser only (no `pantry` role):

```bash
createdb pantry
```

```env
DATABASE_URL=postgresql+psycopg://YOUR_MAC_USERNAME@localhost:5432/pantry
```

```bash
psql pantry
```

### Migrations and API

```bash
cd backend
cp .env.example .env   # edit DATABASE_URL
uv sync
uv run alembic upgrade head
uv run uvicorn app:app --reload --port 8000
```

Default location is created on API startup (`PANTRY_DEFAULT_LOCATION_ID`, `PANTRY_DEFAULT_LOCATION_NAME`).

Without `DATABASE_URL`, the API uses SQLite at `data/ingest/ingestion_runs.db`.

## Health check

`GET /api/health/db`

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `docker: unknown command: docker compose` | Run `brew install docker-compose`, then `docker-compose up -d` |
| `unable to connect` on 5432 | Container not running: `./scripts/start-postgres.sh` or `brew services list` |
| `role "pantry" does not exist` | Using Docker URL against Homebrew Postgres — switch `DATABASE_URL` to your OS user (Option B) |
| `database "pantry" does not exist` | Run `createdb pantry` (Option B) or start Docker compose (Option A) |
