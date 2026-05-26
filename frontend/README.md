# Pantry frontend

React + Vite app for the restaurant inventory MVP.

## Run

Requires the backend API on port **8000**. See **[../backend/docs/RUNNING.md](../backend/docs/RUNNING.md)** for full setup (Postgres, xtraCHEF data, both terminals).

```bash
npm install
npm run dev
```

Open **http://localhost:8080**. API requests to `/api/*` are proxied to `http://127.0.0.1:8000` (`vite.config.ts`).

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Dev server (port 8080) |
| `npm run build` | Production build |
| `npm run test` | Vitest |

## Key pages

| Path | Component | Data |
|------|-----------|------|
| Inventory | `src/pages/Inventory.tsx` | `GET /api/inventory`, quick count APIs |

Mock data is still used on some Inventory tabs (Expiring Soon, Full Count).
