# Running Pantry locally

End-to-end steps to run the MVP web app (inventory + quick count) against PostgreSQL or SQLite.

## Prerequisites

| Tool | Used for |
|------|----------|
| [uv](https://docs.astral.sh/uv/) | Python deps and CLI (`backend/`) |
| Node 18+ and npm or Bun | React frontend (`frontend/`) |
| PostgreSQL 16 (optional) | Recommended; see [DATABASE.md](./DATABASE.md) |

## 1. Sample data (xtraCHEF)

The API syncs inventory from the **latest** xtraCHEF Item Detail export:

```text
data/toast/xtraCHEF/*Item_Detail_Report*.csv
```

If this folder is empty or missing, the API still starts but catalog sync prints  
`xtraCHEF catalog sync skipped: ...` and **Current Stock** will be empty.

Place a real export there, or copy from your restaurant’s xtraCHEF download path.

Toast POS CSVs (`data/toast/pos/`, SFTP inbox) are optional for the inventory UI; they matter for ingestion, depletion, and quick-count scoring. See [README.md](../../README.md) (Toast SFTP section).

## 2. Database

### PostgreSQL (recommended)

Pick one setup path in [DATABASE.md](./DATABASE.md) (Docker Compose or Homebrew).

```bash
cd backend
cp .env.example .env
# Edit DATABASE_URL — e.g. postgresql+psycopg://pantry:pantry@127.0.0.1:5432/pantry

uv sync
uv run alembic upgrade head
```

`alembic upgrade head` is required on Postgres when the schema changes (e.g. revision `002` for `catalog_name`).  
API startup also calls `init_db()` (`create_all`) for dev convenience; **prefer Alembic** on shared databases.

Check connectivity:

```bash
curl -s http://127.0.0.1:8000/api/health/db | python3 -m json.tool
```

### SQLite (no Postgres)

Omit `DATABASE_URL` in `backend/.env`. Tables are created under:

```text
data/ingest/ingestion_runs.db
```

Fine for unit tests and quick experiments; production-style workflows should use Postgres.

## 3. Start the API

From repo root:

```bash
cd backend
uv sync
uv run uvicorn app:app --reload --port 8000
```

On startup the API will:

1. Ensure default location exists (`PANTRY_DEFAULT_LOCATION_*` in `.env`).
2. Run xtraCHEF catalog sync into `inventory_items` (if export file is present).
3. Load legacy CSV/engine paths for recommendations (stub data may still apply).

Force a catalog re-import without restart:

```bash
curl -X POST http://127.0.0.1:8000/api/inventory/sync-catalog
```

Useful endpoints while developing:

| URL | Purpose |
|-----|---------|
| `GET /api/health/db` | Database connection |
| `GET /api/inventory` | Stock list for UI |
| `GET /api/inventory/quick-count` | Quick count session |

Domain docs: [INVENTORY.md](./INVENTORY.md), [DATABASE.md](./DATABASE.md).

## 4. Start the frontend

In a **second terminal**:

```bash
cd frontend
npm install    # or: bun install
npm run dev    # or: bun run dev
```

- App URL: **http://localhost:8080**
- Vite proxies `/api` → `http://127.0.0.1:8000` (see `frontend/vite.config.ts`)

Open **Inventory → Current Stock** to confirm rows load. **Expiring Soon** and **Full Count** tabs still use placeholder UI data.

## 5. Run tests

```bash
cd backend
uv run python -m unittest discover -s tests -q
```

## Optional: Toast nightly pull

Requires `TOAST_SFTP_*` in `backend/.env` or local simulation — see root [README.md](../../README.md).

```bash
cd backend
uv run pantry-ingest toast-pull --days 7
```

HTTP equivalent: `POST /api/ingestion/toast/pull?days=7`, history at `GET /api/ingestion/runs`.

Applying POS data into `menu_items` / `pos_sales_daily` is a separate step from “run the UI”; see ingestion code under `pantry_engine/ingest/`.

## Environment variables

| Variable | Default | Notes |
|----------|---------|--------|
| `DATABASE_URL` | (unset → SQLite) | Postgres connection string |
| `PANTRY_DEFAULT_LOCATION_ID` | `default` | Single-location MVP |
| `PANTRY_DEFAULT_LOCATION_NAME` | `Default Location` | |
| `PANTRY_DEFAULT_TIMEZONE` | `America/Chicago` | |
| `TOAST_SFTP_*` | — | Only for Toast pull |
| `TOAST_SFTP_LOCAL_ROOT` | — | Local folder instead of SFTP |
| `PANTRY_REPO_ROOT` | auto | Override repo root for CLI |

Full template: `backend/.env.example`.

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| Empty Current Stock | xtraCHEF CSV under `data/toast/xtraCHEF/`; API log for sync skipped; `POST /api/inventory/sync-catalog` |
| UI “Could not load inventory” | API running on 8000; frontend dev server on 8080 |
| `relation "inventory_items" does not exist` | `uv run alembic upgrade head` |
| Column `catalog_name` missing | Migration `002`: `alembic upgrade head`, restart API |
| `role "pantry" does not exist` | [DATABASE.md](./DATABASE.md) — Homebrew vs Docker URL mismatch |
| Duplicate key on startup sync | Rare duplicate `item_key` in one export; fixed in catalog sync — pull latest code |

## Daily workflow (summary)

```text
1. Postgres up (if used)
2. uv run uvicorn app:app --reload --port 8000
3. npm run dev  (frontend)
4. Drop new xtraCHEF export → restart API or POST sync-catalog
5. Optional: toast-pull for POS files
6. Inventory UI: quick count, set par via API PATCH
```
