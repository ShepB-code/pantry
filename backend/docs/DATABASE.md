# Database (MVP)

PostgreSQL in production; SQLite fallback when `DATABASE_URL` is unset (local tests).

To start the API and UI after the DB is up, see [RUNNING.md](./RUNNING.md).

## Schema overview

One Alembic revision (`001`) defines everything the MVP uses today. If you previously ran older multi-step migrations (`002`–`004`), reset the database:

```bash
./scripts/reset-db.sh --yes perilla
```

### Tables (all in use)

| Table | Purpose |
|-------|---------|
| `locations` | Restaurant scope (`id`, `name`) |
| `inventory_items` | xtraCHEF catalog + `on_hand` + `par_level` |
| `menu_items` | Toast menu items; optional direct depletion columns |
| `recipe_lines` | Menu → inventory qty per serving |
| `pos_sales_daily` | Daily units sold per menu item (depletion + recipe UI) |
| `quick_count_sessions` / `quick_count_lines` | Physical counts |
| `ingestion_runs` | SFTP pull audit + dedup (`file_sha256`) |

All operational data is scoped by `location_id`.

### `inventory_items`

| Column | Used for |
|--------|----------|
| `id` | Stable xtraCHEF `item_key` |
| `name`, `name_source` | Kitchen label + provenance (`xtrachef` or `manual`) |
| `catalog_name`, `catalog_source` | Raw vendor description |
| `category`, `unit`, `vendor_name` | Display + quick count (vendor from CSV at runtime) |
| `on_hand`, `par_level` | Stock UI, depletion, quick count |
| `last_count_source`, `last_counted_at` | Count / depletion audit |
| `created_at`, `updated_at` | Row lifecycle |

Not stored in DB (read from xtraCHEF CSV at runtime when needed): `item_code`, purchase price/date — quick count prioritization uses the export file, not persisted catalog metadata.

### `pos_sales_daily`

Stores **quantity only** per menu item per day. Revenue is not persisted yet; Dashboard/Financials show frontend mock data until POS revenue rollups are added.

### `menu_items` direct depletion

| Column | Purpose |
|--------|---------|
| `direct_inventory_item_id` | Singular ingredient link (e.g. scallop) |
| `direct_qty_per_serving` | Units depleted per sale |

## Wired today

- **xtraCHEF** → `inventory_items` via startup sync or `POST /api/inventory/sync-catalog`
- **Toast MenuItem_Export** → `menu_items` via startup or `POST /api/menu/sync-export`
- **Toast ItemSelectionDetails** → `menu_items` + `pos_sales_daily` via `db-seed`, SFTP pull + `--apply`, or `POST /api/ingestion/toast/apply`
- **Recipes** → `recipe_lines` + optional direct depletion on `menu_items`
- **Depletion** → `apply_sales_depletion` after sales ingest
- **Quick count** → updates `on_hand`
- **Par / name** → `PATCH /api/inventory/{id}/par`, `PATCH /api/inventory/{id}/name`

See [DATA_SOURCES.md](./DATA_SOURCES.md) and [INVENTORY.md](./INVENTORY.md).

## Migrations

```bash
cd backend
uv run alembic upgrade head
```

Bootstrap (migrate + seed from files):

```bash
./scripts/bootstrap-db.sh perilla
```

## Local PostgreSQL

### Option A — Docker

```bash
brew install docker-compose   # if needed
./scripts/start-postgres.sh
```

```env
DATABASE_URL=postgresql+psycopg://pantry:pantry@localhost:5432/pantry
```

### Option B — Homebrew Postgres

```bash
./scripts/setup-postgres-brew.sh
```

```env
DATABASE_URL=postgresql+psycopg://pantry:pantry@127.0.0.1:5432/pantry
```

## Health check

`GET /api/health/db`

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Can't locate revision` / migration mismatch | `./scripts/reset-db.sh --yes perilla` |
| `column … does not exist` | Same — schema was squashed into `001` |
| `docker: unknown command: docker compose` | `brew install docker-compose` |
| `role "pantry" does not exist` | Use Homebrew setup script or fix `DATABASE_URL` |

Without `DATABASE_URL`, the API uses SQLite at `data/ingest/ingestion_runs.db`.
