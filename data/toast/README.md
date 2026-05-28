# Toast & xtraCHEF data layout

Exports on disk are **inputs** for seeding the database. The UI and API read from Postgres (or SQLite), not these files directly.

## Per-restaurant folders

Replace `{location}` with your `PANTRY_DEFAULT_LOCATION_ID` (e.g. `perilla`, `noriko`).

| Path | Purpose |
|------|---------|
| `data/toast/xtraCHEF/{location}/*Item_Detail_Report*.csv` | Inventory catalog (xtraCHEF) |
| `data/toast/pos/{location}/MenuItem_Export.csv` | Toast menu item database (Item ID → name) |
| `data/toast/pos/{location}/ItemSelectionDetails*.csv` | Daily (or range) POS sales exports |

## Bootstrap into the database

From repo root:

```bash
./scripts/bootstrap-db.sh perilla
```

Or see [backend/docs/RUNNING.md](../../backend/docs/RUNNING.md).

## EDA notebooks

`data_analysis/notebooks/` may read the same paths via `pantry_eda.py`; keeping files here supports both notebooks and DB seeding.
