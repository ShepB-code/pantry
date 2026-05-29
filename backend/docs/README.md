# Pantry backend documentation

| Doc | When to read |
|-----|----------------|
| [RUNNING.md](./RUNNING.md) | **Start here** — install, seed DB, run API + UI |
| [DATA_SOURCES.md](./DATA_SOURCES.md) | **Menu items (Toast) vs ingredients (xtraCHEF)** — read when confused |
| [DATABASE.md](./DATABASE.md) | Postgres (Docker vs Homebrew), migrations, tables |
| [INVENTORY.md](./INVENTORY.md) | Data model, naming, APIs, MVP gaps |

## API layout

| Module | Routes |
|--------|--------|
| `pantry_engine/api/routers/inventory.py` | Stock, quick count, catalog sync |
| `pantry_engine/api/routers/menu.py` | Recipes, menu export sync |
| `pantry_engine/api/routers/ingestion.py` | Toast SFTP pull/apply, run log |
| `pantry_engine/api/routers/demo.py` | Gemini invoice upload demo (Suppliers page) |

All product data routes read/write **Postgres**. Dashboard, Forecasting, and Financials use **mock data in the frontend** only.

## Quick commands (from `backend/`)

```bash
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run python -m pantry_engine.cli db-seed --location perilla
uv run uvicorn app:app --reload --port 8000
```

Use `uv run python -m pantry_engine.cli` (works even when entry points are not installed).
