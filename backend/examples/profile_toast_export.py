from collections import Counter, defaultdict
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from pantry_engine.ingestion import ToastItemSelectionDetailsCsvAdapter


ROOT = Path(__file__).resolve().parents[1]
TOAST_DATA = ROOT / "data" / "toast"


sales = list(
    ToastItemSelectionDetailsCsvAdapter(
        pos_sales_path=TOAST_DATA / "pos" / "ItemSelectionDetails_2026_04_01-2026_04_30.csv"
    ).pos_sales()
)

quantity_by_item: Counter[str] = Counter()
revenue_by_item: defaultdict[str, float] = defaultdict(float)
quantity_by_day: defaultdict[object, float] = defaultdict(float)
categories: Counter[str] = Counter()

for sale in sales:
    item_name = sale.menu_item_name or sale.menu_item_id
    quantity_by_item[item_name] += sale.quantity
    revenue_by_item[item_name] += sale.revenue or 0
    quantity_by_day[sale.business_date] += sale.quantity
    if sale.sales_category:
        categories[sale.sales_category] += sale.quantity

dates = sorted(quantity_by_day)
print(f"Rows imported: {len(sales)}")
print(f"Date range: {dates[0]} to {dates[-1]}")
print(f"Unique menu items: {len(quantity_by_item)}")
print(f"Total quantity sold: {sum(quantity_by_item.values()):.2f}")
print()
print("Top 15 items by quantity:")
for item, quantity in quantity_by_item.most_common(15):
    print(f"{quantity:8.2f}  {item}  (${revenue_by_item[item]:.2f})")
print()
print("Sales categories by quantity:")
for category, quantity in categories.most_common():
    print(f"{quantity:8.2f}  {category}")
