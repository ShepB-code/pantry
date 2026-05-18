# Pantry

Pantry is an inventory intelligence project for restaurants. This repository contains:
- `backend/`: The core inventory intelligence engine.
- `frontend/`: The web application MVP.
- `data_analysis/`: Exploratory Data Analysis notebooks and pipelines.
- `data/`: Sample datasets and configurations.

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
