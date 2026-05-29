# Inventory data model and naming

This document describes how Pantry represents stock, where names come from, and what is wired in the MVP. It reflects the current codebase (not a future design spec).

**Start here if labels are confusing:** [DATA_SOURCES.md](./DATA_SOURCES.md) (Toast menu items vs xtraCHEF ingredients).

## Data sources

| Source | Export / API | Lands in | Used for |
|--------|----------------|----------|----------|
| **xtraCHEF** | `data/toast/xtraCHEF/{location_id}/*Item_Detail_Report*.csv` | `inventory_items` | Catalog, default on-hand seed, vendor metadata |
| **Toast POS** | `data/toast/pos/{location_id}/ItemSelectionDetails*.csv` (or SFTP inbox) | `menu_items`, `pos_sales_daily` | Sales rollups; depletion when `recipe_lines` exist |
| **Toast menu items** | `data/toast/pos/{location_id}/MenuItem_Export.csv` | `menu_items` | Stable Toast Item ID → name database |
| **Quick count** | `POST /api/inventory/quick-count/lines` | `quick_count_*`, `inventory_items.on_hand` | Physical counts override estimates |
| **Par (manual)** | `PATCH /api/inventory/{id}/par` | `inventory_items.par_level` | Target stock; not overwritten by catalog sync |

Reads and transforms for xtraCHEF/Toast CSVs live in `data_analysis/notebooks/lib/pantry_eda.py`. Catalog upsert logic is in `pantry_engine/db/catalog_sync.py`.

## Two naming layers (do not confuse them)

Pantry deals with **two separate matching problems**:

### 1. Catalog labels (inventory management system → Pantry row)

- **Question:** “What does xtraCHEF call this line, and which DB row is it?”
- **Answer today:** Automatic. `item_key` from xtraCHEF → `inventory_items.id`. Catalog sync stores one row per `item_key` (first CSV row wins). No dedupe or display-name rules on ingest.
- **UI:** **Inventory Item** column (`catalog_name`, source `catalog_source`, usually `xtrachef`).
- **Manual override:** `PATCH /api/inventory/{id}/name` sets `name` with `name_source = manual`; preserved on resync.

### 2. Usage labels (Toast menu → inventory ingredient)

- **Question:** “This dish sold — which ingredient stock moves?”
- **Answer today:** **Manual** `recipe_lines` (menu item id → inventory item id + qty per serving). Quick count may *rank* items using token overlap between POS menu names and xtraCHEF descriptions; that linkage is **not** stored.
- **Toast does not populate** `inventory_items.name` or `catalog_name`.

```text
xtraCHEF CSV ──sync──► inventory_items (id, name, catalog_name, on_hand, par_level)
                              ▲
                              │ recipe_lines (manual)
Toast POS ──sync──► menu_items + pos_sales_daily
```

## `inventory_items` fields (naming)

| Field | API (camelCase) | Meaning today |
|-------|-----------------|---------------|
| `id` | `id` | Stable slug from xtraCHEF `item_description` (`item_key`) |
| `name` | `name` | Same as xtraCHEF `item_description` on sync unless manually edited |
| `name_source` | `nameSource` | `xtrachef` or `manual` |
| `catalog_name` | `inventoryItem` | Raw `item_description` from xtraCHEF |
| `catalog_source` | `catalogSource` | e.g. `xtrachef` |
| `category`, `unit`, `vendor_name` | `category`, `unit`, `vendor` | From xtraCHEF row |
| `on_hand`, `par_level` | `onHand`, `parLevel` | Operational; par via API/UI |

**Current Stock table:** **Ingredient** and **Inventory Item** show the same xtraCHEF text until you edit the ingredient name manually.

## Catalog sync behavior

Triggered on API startup (when DB is available) and via:

```http
POST /api/inventory/sync-catalog
```

- **Creates** new rows from the latest xtraCHEF export (all rows with an `item_key`; no category filter on ingest).
- **Updates** catalog fields from CSV as-is (`name`, `catalog_name`, category, unit, vendor).
- **Does not overwrite** existing `on_hand`, `par_level`, or manually set `name`.
- New rows start at `on_hand = 0` (`last_count_source = uninitialized`).

Data cleaning (food-only filter, dedupe, display names) is deferred — see quick count, which still reads xtraCHEF CSV directly for item selection scoring.

## HTTP API (inventory)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/inventory` | List items + `onHand` map for default location |
| `POST` | `/api/inventory/sync-catalog` | Re-import xtraCHEF into `inventory_items` |
| `PATCH` | `/api/inventory/{item_id}/par` | Body: `{ "parLevel": 20 }` |
| `GET` | `/api/inventory/quick-count` | Today’s quick-count session payload |
| `POST` | `/api/inventory/quick-count/lines` | Submit a count line |
| `POST` | `/api/inventory/quick-count/complete` | Mark session complete |
| `POST` | `/api/inventory/quick-count/reset` | Reset session |

Example `GET /api/inventory` item shape:

```json
{
  "id": "160z usda insp pork porterhouse chop",
  "name": "160Z USDA INSP PORK PORTERHOUSE CHOP PC ...",
  "inventoryItem": "160Z USDA INSP PORK PORTERHOUSE CHOP PC ...",
  "catalogSource": "xtrachef",
  "category": "Food - Meat",
  "unit": "lb",
  "onHand": 12.5,
  "parLevel": 15,
  "status": "Below par",
  "statusColor": "text-warning"
}
```

## Frontend

- **Page:** `frontend/src/pages/Inventory.tsx` — tabs: Current Stock (DB), Expiring Soon / Full Count (mock data only).
- **Quick count:** `frontend/src/components/inventory/QuickCountWizard.tsx`.
- **Types / API:** `frontend/src/types/inventory.ts`, `frontend/src/api/inventory.ts`.

## Schema migration

Revision `002` adds `catalog_name` and `catalog_source` to `inventory_items` and backfills from `name`.

```bash
cd backend
uv run alembic upgrade head
```

Then restart the API or run `POST /api/inventory/sync-catalog` so `catalog_name` matches the latest export.

## MVP gaps (intentional)

| Area | Status |
|------|--------|
| Ingredient name standardization | Not implemented; `name` = xtraCHEF description |
| Catalog alias / matching settings UI | Not implemented |
| Toast → inventory mapping UI | Use DB `recipe_lines` manually |
| POS-driven `on_hand` depletion | Needs recipes + apply path for POS ingest |
| Expiring Soon / Full Count UI | Placeholder data |
| Invoice reconciliation | Not in DB |

## Related docs

- [RUNNING.md](./RUNNING.md) — how to start API + frontend locally
- [DATABASE.md](./DATABASE.md) — Postgres setup, table list, migrations
- [README.md](../../README.md) — Toast SFTP ingestion overview
- [data_analysis/notebooks/README.md](../../data_analysis/notebooks/README.md) — EDA workflow for exports

## Code map

| Concern | Module |
|---------|--------|
| xtraCHEF → DB | `pantry_engine/db/catalog_sync.py` |
| Inventory API rows | `pantry_engine/db/inventory_repo.py` |
| Quick count scoring | `pantry_engine/quick_count.py` |
| ORM | `pantry_engine/db/models.py` |
| Routes | `backend/app.py` |
