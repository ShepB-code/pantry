# Running Pantry locally

End-to-end guide for the MVP web app (inventory + quick count).

## How it works (read this once)

| Layer | Role |
|-------|------|
| **Files** (`data/toast/…`) | Source exports (xtraCHEF, Toast). Used for **seeding** and notebooks. |
| **Database** | Source of truth for the **API and UI** (`inventory_items`, `menu_items`, `pos_sales_daily`, …). |
| **API** (`uvicorn app:app`) | Serves JSON to the React app. |
| **CLI** (`python -m pantry_engine.cli`) | Ops jobs: seed DB from files, pull Toast SFTP, apply sales/depletion. |

Weather and advanced forecasting still use CSVs in some code paths; the **Inventory** UI is DB-backed.

Folder layout: [data/toast/README.md](../../data/toast/README.md).

---

## First-time setup (checklist)

### 0. Prerequisites

| Tool | Notes |
|------|--------|
| [uv](https://docs.astral.sh/uv/) | Python deps + CLI |
| Node 18+ | Frontend (`npm` or `bun`) |
| PostgreSQL 16 | Recommended — [DATABASE.md](./DATABASE.md) (Docker or Homebrew) |

### 1. Put exports on disk

For location `perilla` (or set `PANTRY_DEFAULT_LOCATION_ID` in `.env`):

```text
data/toast/xtraCHEF/perilla/*Item_Detail_Report*.csv
data/toast/pos/perilla/MenuItem_Export.csv          # optional but recommended
data/toast/pos/perilla/ItemSelectionDetails*.csv  # daily or monthly POS exports
```

### 2. Configure backend

```bash
cd backend
cp .env.example .env
# Edit .env: DATABASE_URL, PANTRY_DEFAULT_LOCATION_ID=perilla
uv sync
```

### 3. Start Postgres (if using it)

```bash
# From repo root — Docker
./scripts/start-postgres.sh

# Or Homebrew — see DATABASE.md
./scripts/setup-postgres-brew.sh
```

### 4. Migrate + seed the database

**One command (from repo root):**

```bash
chmod +x scripts/bootstrap-db.sh   # first time only
./scripts/bootstrap-db.sh perilla
```

**Or manually from `backend/`:**

```bash
uv run alembic upgrade head
uv run python -m pantry_engine.cli db-seed --location perilla
```

`db-seed` will:

- Upsert `MenuItem_Export.csv` → `menu_items` (if present)
- Sync xtraCHEF → `inventory_items` (new rows start at `on_hand = 0`)
- Ingest `ItemSelectionDetails*.csv` → `menu_items` + `pos_sales_daily`

Verify DB:

```bash
curl -s http://127.0.0.1:8000/api/health/db | python3 -m json.tool
# (after API is running)
```

### 5. Start API + UI

**Terminal 1 — API**

```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

On startup the API will also try a light sync (menu export + xtraCHEF) if files are present.

**Terminal 2 — UI**

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:8080** → **Inventory → Current Stock**.

---

## CLI reference (`python -m pantry_engine.cli`)

Run from `backend/` (same as `uv run python -m pantry_engine.cli`):

| Command | Purpose |
|---------|---------|
| `uv run python -m pantry_engine.cli db-seed --location perilla` | Bootstrap DB from `data/toast/` files |
| `uv run python -m pantry_engine.cli db-seed --location perilla --skip-pos` | Catalog + menu only, no POS backfill |
| `uv run python -m pantry_engine.cli toast-pull --date 2026-04-30 --apply` | Pull one day (SFTP or local sim) + ingest + depletion |

Flags for `db-seed`: `--skip-xtrachef`, `--skip-menu-export`, `--skip-pos`, `--pos-file PATH` (repeatable).

### Simulate Toast SFTP (local, no SSH)

```bash
./scripts/simulate-toast-sftp-drop.sh 2026-04-30 /path/to/ItemSelectionDetails.csv
```

Requires `TOAST_SFTP_LOCAL_ROOT` and `TOAST_SFTP_EXPORT_ID` in `.env` (see `.env.example`).

### HTTP equivalents

| Endpoint | Purpose |
|----------|---------|
| `GET /api/health/db` | DB connectivity |
| `GET /api/inventory` | Stock for UI |
| `POST /api/inventory/sync-catalog` | Re-sync xtraCHEF |
| `POST /api/menu/sync-export` | Re-sync `MenuItem_Export.csv` |
| `POST /api/ingestion/toast/pull?days=7` | Toast pull (SFTP) |
| `GET /api/ingestion/runs` | Ingestion history |

More detail: [INVENTORY.md](./INVENTORY.md).

---

## SQLite (quick experiments)

Omit `DATABASE_URL` in `.env`. Tables are created at:

```text
data/ingest/ingestion_runs.db
```

Use Postgres for anything resembling production.

---

## Environment variables

| Variable | Default | Notes |
|----------|---------|--------|
| `DATABASE_URL` | (unset → SQLite) | Postgres connection string |
| `PANTRY_DEFAULT_LOCATION_ID` | `perilla` | Folder slug + `locations.id` |
| `PANTRY_DEFAULT_LOCATION_NAME` | `Perilla` | Display name |
| `PANTRY_DEFAULT_TIMEZONE` | `America/Chicago` | |
| `TOAST_SFTP_*` | — | Nightly Toast pull |
| `TOAST_SFTP_LOCAL_ROOT` | — | Local folder instead of SFTP |
| `PANTRY_REPO_ROOT` | auto | If CLI run outside repo layout |

Template: `backend/.env.example`.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Empty Current Stock | xtraCHEF CSV under `data/toast/xtraCHEF/{location}/`; run `./scripts/bootstrap-db.sh` or `POST /api/inventory/sync-catalog` |
| Wrong restaurant data | `PANTRY_DEFAULT_LOCATION_ID` in `.env` must match folder name |
| UI cannot reach API | API on `:8000`, frontend on `:8080` (Vite proxies `/api`) |
| `relation "inventory_items" does not exist` | `uv run alembic upgrade head` |
| `role "pantry" does not exist` | [DATABASE.md](./DATABASE.md) — Docker vs Homebrew URL |
| Depletion does nothing | Need `recipe_lines` linking menu item → inventory item |

---

## Tests

```bash
cd backend
uv run python -m unittest discover -s tests -q
```

---

## Daily workflow

```text
1. Postgres running
2. Optional: toast-pull --apply for yesterday's sales
3. uv run uvicorn app:app --reload --port 8000
4. npm run dev (frontend)
5. Quick count / par updates in UI
6. New xtraCHEF export → POST sync-catalog or restart API
```
