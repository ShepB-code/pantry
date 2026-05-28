# Pantry frontend

React + Vite app for the restaurant inventory MVP.

## Prerequisites

1. Backend seeded and running — see [../backend/docs/RUNNING.md](../backend/docs/RUNNING.md).
2. From repo root, one-time bootstrap:

```bash
./scripts/bootstrap-db.sh perilla
```

## Run

```bash
npm install
npm run dev
```

Open **http://localhost:8080**. API requests to `/api/*` proxy to `http://127.0.0.1:8000`.

Start the API in another terminal:

```bash
cd ../backend
uv run uvicorn app:app --reload --port 8000
```

## Main screens

| Route / tab | Data source |
|-------------|-------------|
| Inventory → Current Stock | `GET /api/inventory` (database) |
| Inventory → Quick Count | `GET /api/inventory/quick-count` |
| Menu / Recipes | Partially API (`/api/menu/stats`); some mock UI |

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Dev server |
| `npm run build` | Production build |
| `npm run test` | Vitest |
