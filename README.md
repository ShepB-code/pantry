# Pantry

Pantry is an inventory intelligence project for restaurants. This repository contains:
- `backend/`: The core inventory intelligence engine.
- `frontend/`: The web application MVP.
- `data_analysis/`: Exploratory Data Analysis notebooks and pipelines.
- `data/`: Sample datasets and configurations.

## Run locally (MVP UI)

Full steps (Postgres, API, frontend, sample data, troubleshooting): **[backend/docs/RUNNING.md](backend/docs/RUNNING.md)**.

```bash
# Terminal 1 — API
cd backend && cp .env.example .env   # set DATABASE_URL if using Postgres
uv sync && uv run alembic upgrade head
uv run uvicorn app:app --reload --port 8000

# Terminal 2 — UI (http://localhost:8080, proxies /api → :8000)
cd frontend && npm install && npm run dev
```

Put xtraCHEF `*Item_Detail_Report*.csv` in `data/toast/xtraCHEF/` before expecting rows on **Inventory → Current Stock**.

## Backend Engine

The backend is intentionally small and framework-free:

- Normalize POS, reservation, weather, and event records into one demand dataset.
- Forecast menu item demand over a future planning window.
- Convert menu demand into ingredient demand using recipe mappings.
- Recommend order quantities using on-hand inventory, par levels, lead time, pack size, and safety stock.

### Quick Start

```bash
cd backend
python3 -m unittest discover -s tests
```

### Database (PostgreSQL)

MVP schema: multi-location inventory, daily POS rollups, manual recipes, quick count, ingestion runs.

- [Running locally](backend/docs/RUNNING.md) — start API + frontend, data paths, env, troubleshooting
- [Database setup](backend/docs/DATABASE.md) — Postgres, migrations, tables
- [Inventory & naming](backend/docs/INVENTORY.md) — xtraCHEF vs Toast, Ingredient vs Inventory Item, APIs

```bash
# Postgres via Docker (requires Compose — not bundled with `brew install docker`)
brew install docker-compose   # if `docker compose` is unknown
./scripts/start-postgres.sh   # or: docker-compose up -d

cd backend
cp .env.example .env   # set DATABASE_URL
uv sync
uv run alembic upgrade head
uv run uvicorn app:app --reload --port 8000
```

No Docker? Use Homebrew Postgres instead — [backend/docs/DATABASE.md](backend/docs/DATABASE.md).

Without `DATABASE_URL`, the API falls back to SQLite under `data/ingest/` for development.

### Toast nightly sales exports (SFTP)

Toast can deliver **ItemSelectionDetails.csv** per business day to SFTP after closeout (files kept ~7 days). Pantry pulls these into `data/ingest/inbox/toast-pos/` and logs each run in the database (`ingestion_runs` table).

1. Ask Toast Customer Care to enable **automated nightly data exports** and register your SSH public key (Reports → Settings → SSH Keys / Data Exports).
2. Copy `backend/.env.example` to `backend/.env` and set `TOAST_SFTP_*` variables.
3. Pull yesterday or the last week:

```bash
cd backend
uv sync
uv run pantry-ingest toast-pull              # last 7 days ending yesterday
uv run pantry-ingest toast-pull --date 2026-04-01
uv run pantry-ingest toast-pull --days 3 --force
```

Cron example (daily at 6:00 after Toast closeout export):

```cron
0 6 * * * cd /path/to/Pantry/backend && /path/to/uv run pantry-ingest toast-pull --days 2
```

HTTP trigger (same logic): `POST /api/ingestion/toast/pull?days=7` — see `GET /api/ingestion/runs` for history.

## Exploratory Analysis

The `data_analysis/notebooks/` folder contains an EDA workflow for Toast POS and external demand signals:

```bash
cd data_analysis
pip install -r requirements-eda.txt
jupyter lab notebooks
```

You can also regenerate review CSVs without opening Jupyter:

```bash
cd data_analysis
python3 notebooks/build_correlation_tables.py
```

```python
from datetime import date

from pantry_engine import PantryEngine
from pantry_engine.domain import Ingredient, MenuItem, RecipeLine, SupplierRule
from pantry_engine.ingestion import InMemoryDataSource

engine = PantryEngine(
    menu_items=[MenuItem(id="burger", name="Burger")],
    ingredients=[Ingredient(id="beef", name="Ground beef", unit="lb")],
    recipes=[RecipeLine(menu_item_id="burger", ingredient_id="beef", quantity=0.33)],
    supplier_rules=[SupplierRule(ingredient_id="beef", pack_size=10, minimum_order=10, lead_time_days=2)],
)

recommendations = engine.recommend_orders(
    data_source=InMemoryDataSource(pos_sales=[], reservations=[], weather=[], events=[]),
    inventory={"beef": 12},
    start=date.today(),
    days=7,
)
```
