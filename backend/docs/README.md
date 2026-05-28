# Pantry backend documentation

| Doc | When to read |
|-----|----------------|
| [RUNNING.md](./RUNNING.md) | **Start here** — install, seed DB, run API + UI |
| [DATABASE.md](./DATABASE.md) | Postgres (Docker vs Homebrew), migrations, tables |
| [INVENTORY.md](./INVENTORY.md) | Data model, naming, APIs, MVP gaps |

## Quick commands (from `backend/`)

```bash
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run python -m pantry_engine.cli db-seed --location perilla
uv run uvicorn app:app --reload --port 8000
```

Use `uv run python -m pantry_engine.cli` (works even when entry points are not installed).
