from datetime import date
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
from pantry_engine import PantryEngine
from pantry_engine.domain import Ingredient, MenuItem, RecipeLine, SupplierRule
from pantry_engine.ingestion import CsvDataSource


ROOT = Path(__file__).parent


engine = PantryEngine(
    menu_items=[
        MenuItem(id="burger", name="Burger", category="entree"),
        MenuItem(id="salad", name="House Salad", category="entree"),
    ],
    ingredients=[
        Ingredient(id="beef", name="Ground beef", unit="lb", shelf_life_days=3),
        Ingredient(id="bun", name="Burger bun", unit="each", shelf_life_days=5),
        Ingredient(id="greens", name="Mixed greens", unit="lb", shelf_life_days=4),
    ],
    recipes=[
        RecipeLine(menu_item_id="burger", ingredient_id="beef", quantity=0.33, waste_factor=0.04),
        RecipeLine(menu_item_id="burger", ingredient_id="bun", quantity=1),
        RecipeLine(menu_item_id="salad", ingredient_id="greens", quantity=0.18, waste_factor=0.08),
    ],
    supplier_rules=[
        SupplierRule(ingredient_id="beef", pack_size=10, minimum_order=10, safety_stock=8),
        SupplierRule(ingredient_id="bun", pack_size=24, minimum_order=24, safety_stock=24),
        SupplierRule(ingredient_id="greens", pack_size=5, minimum_order=5, safety_stock=4),
    ],
)

data_source = CsvDataSource(
    pos_sales_path=ROOT / "pos_sales.csv",
    reservations_path=ROOT / "reservations.csv",
    weather_path=ROOT / "weather.csv",
    events_path=ROOT / "events.csv",
)

for recommendation in engine.recommend_orders(
    data_source=data_source,
    inventory={"beef": 22, "bun": 96, "greens": 13},
    start=date(2026, 5, 7),
    days=3,
):
    print(recommendation)
