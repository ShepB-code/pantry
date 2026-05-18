# Pantry EDA Notebooks

These notebooks are for exploring Toast POS exports and external factors before the logic graduates into the production engine.

## Setup

Use a virtual environment if you want to keep notebook dependencies separate:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-eda.txt
jupyter lab notebooks
```

If you are running inside Codex, the bundled Python runtime already includes `pandas`, `numpy`, and `pypdf`, but not a full Jupyter stack.

## Workflow

1. `00_data_catalog.ipynb`: inventory files, shapes, date ranges, and columns.
2. `01_pos_sales_eda.ipynb`: Toast sales trends, category mix, item concentration, daypart patterns, and Jan-Apr Product Mix aggregate review.
3. `02_correlations.ipynb`: day-of-week, weather, category mix, and item-level correlation analysis.

For now, focus on Toast POS and external demand signals. xtraCHEF data can come back once the POS and external-factor workflow is solid.

Note: the current Jan-Apr Product Mix export is aggregate-only. It is useful for overall mix, but daily weather and weekday correlations still require a daily-granular Toast export.

Keep raw exports in `data/`. Put generated charts or derived CSVs in `notebooks/outputs/`.
