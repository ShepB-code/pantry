import sys
import os
import json
from pathlib import Path
from datetime import date, timedelta
import asyncio

from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add data_analysis/notebooks/lib to sys.path
root = Path(__file__).resolve().parent.parent
lib_path = root / "data_analysis" / "notebooks" / "lib"
if str(lib_path) not in sys.path:
    sys.path.append(str(lib_path))

import pantry_eda
from pantry_engine import PantryEngine
from pantry_engine.domain import (
    POSSale,
    WeatherSignal,
    WeatherCondition,
    ReservationDemand,
    EventSignal,
    MenuItem,
    Ingredient,
    RecipeLine,
    SupplierRule,
    OrderRecommendation,
)
from pantry_engine.ingestion import InMemoryDataSource

app = FastAPI(title="Pantry API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_data() -> tuple[PantryEngine, InMemoryDataSource]:
    print("Loading POS data...")
    pos_df = pantry_eda.read_pos_item_selections()
    print("Loading Weather data...")
    weather_df = pantry_eda.read_weather_daily()

    sales = []
    menu_items_dict = {}

    for _, row in pos_df.iterrows():
        mid = row["menu_item_key"]
        mname = row["menu_item"]
        cat = row.get("sales_category")

        if mid not in menu_items_dict:
            menu_items_dict[mid] = MenuItem(id=mid, name=mname, category=cat)

        sales.append(
            POSSale(
                business_date=row["business_date"],
                menu_item_id=mid,
                quantity=row["qty"],
                revenue=row["net_price"],
                source="toast",
                sent_at=row["sent_at"],
                menu_item_name=mname,
                sales_category=cat,
            )
        )

    weather = []
    for _, row in weather_df.iterrows():
        cond = WeatherCondition.CLEAR
        if isinstance(row.get("daily_weather"), str):
            w = row["daily_weather"].lower()
            if "rain" in w:
                cond = WeatherCondition.RAIN
            elif "snow" in w:
                cond = WeatherCondition.SNOW
            elif "cloud" in w:
                cond = WeatherCondition.CLOUDY

        weather.append(
            WeatherSignal(
                business_date=row["business_date"],
                condition=cond,
                high_temp_f=row.get("daily_maximum_dry_bulb_temperature_f"),
                low_temp_f=row.get("daily_minimum_dry_bulb_temperature_f"),
                precipitation_probability=None,
            )
        )

    # For MVP, let's create a dummy ingredient and recipe for the top selling item
    # so we have something to recommend.
    top_item_id = None
    if sales:
        from collections import Counter

        counts = Counter([s.menu_item_id for s in sales])
        top_item_id = counts.most_common(1)[0][0]

    ingredients = [Ingredient(id="beef", name="Ground beef", unit="lb")]
    recipes = []
    if top_item_id:
        recipes.append(
            RecipeLine(menu_item_id=top_item_id, ingredient_id="beef", quantity=0.33)
        )
    else:
        # Fallback if no sales
        menu_items_dict["burger"] = MenuItem(id="burger", name="Burger")
        recipes.append(
            RecipeLine(menu_item_id="burger", ingredient_id="beef", quantity=0.33)
        )

    supplier_rules = [
        SupplierRule(
            ingredient_id="beef", pack_size=10, minimum_order=10, lead_time_days=2
        )
    ]

    engine = PantryEngine(
        menu_items=list(menu_items_dict.values()),
        ingredients=ingredients,
        recipes=recipes,
        supplier_rules=supplier_rules,
    )

    data_source = InMemoryDataSource(
        pos_sales=sales, reservations=[], weather=weather, events=[]
    )

    return engine, data_source


# Global state for MVP
engine = None
data_source = None
inventory_state = {"beef": 12.0}


@app.on_event("startup")
def startup_event():
    global engine, data_source
    engine, data_source = load_data()


@app.get("/api/inventory")
def get_inventory():
    return inventory_state


@app.get("/api/menu")
def get_menu():
    return [
        {"id": m.id, "name": m.name, "category": m.category} for m in engine.menu_items
    ]


@app.get("/api/recommendations")
def get_recommendations(days: int = 7):
    # Determine the max date in the sales to start forecasting from tomorrow
    if not data_source.pos_sales():
        start_date = date.today()
    else:
        # Sort sales and pick the last business date + 1
        last_sale = max(s.business_date for s in data_source.pos_sales())
        start_date = last_sale + timedelta(days=1)

    recs = engine.recommend_orders(
        data_source=data_source, inventory=inventory_state, start=start_date, days=days
    )
    return recs


@app.get("/api/financials/revenue")
def get_revenue():
    from collections import defaultdict

    daily_revenue = defaultdict(float)
    for s in data_source.pos_sales():
        if s.revenue is not None:
            daily_revenue[s.business_date] += s.revenue

    sorted_dates = sorted(daily_revenue.keys())[-7:]

    result = []
    days_of_week = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for d in sorted_dates:
        rev = daily_revenue[d]
        result.append(
            {
                "day": days_of_week[d.weekday()],
                "date": d.isoformat(),
                "revenue": round(rev, 2),
                "cost": round(rev * 0.28, 2),  # Mock 28% food cost for the visual
            }
        )
    return result


@app.get("/api/menu/stats")
def get_menu_stats():
    from collections import defaultdict

    item_stats = defaultdict(
        lambda: {"quantity": 0.0, "revenue": 0.0, "name": "", "category": ""}
    )

    for s in data_source.pos_sales():
        stats = item_stats[s.menu_item_id]
        stats["quantity"] += s.quantity
        if s.revenue is not None:
            stats["revenue"] += s.revenue
        if s.menu_item_name:
            stats["name"] = s.menu_item_name
        if s.sales_category:
            stats["category"] = s.sales_category

    quantities = [s["quantity"] for s in item_stats.values()]
    if not quantities:
        return []

    q_high = sorted(quantities)[int(len(quantities) * 0.75)]
    q_low = sorted(quantities)[int(len(quantities) * 0.25)]

    result = []
    for iid, stats in item_stats.items():
        qty = stats["quantity"]
        rev = stats["revenue"]
        price = (rev / qty) if qty > 0 else 0
        cost = price * 0.28  # Mock cost 28%
        margin = round(((price - cost) / price) * 100) if price > 0 else 0

        pop = "High" if qty >= q_high else "Low" if qty <= q_low else "Medium"
        popColor = (
            "text-success"
            if pop == "High"
            else "text-warning" if pop == "Low" else "text-info"
        )

        result.append(
            {
                "id": iid,
                "dish": stats["name"] or iid,
                "cat": stats["category"] or "Uncategorized",
                "cost": f"${cost:.2f}",
                "price": f"${price:.2f}",
                "margin": margin,
                "popularity": pop,
                "popColor": popColor,
                "ingredients": [],
            }
        )
    return sorted(result, key=lambda x: x["dish"])


@app.get("/api/forecasts/menu")
def get_menu_forecasts(days: int = 7):
    if not data_source.pos_sales():
        start_date = date.today()
    else:
        last_sale = max(s.business_date for s in data_source.pos_sales())
        start_date = last_sale + timedelta(days=1)

    forecasts = engine.forecast_menu_demand(
        data_source=data_source, start=start_date, days=days
    )

    from collections import defaultdict

    demand_by_item = defaultdict(float)
    for f in forecasts:
        demand_by_item[f.menu_item_id] += f.expected_quantity

    result = []
    for iid, qty in demand_by_item.items():
        item = next((m for m in engine.menu_items if m.id == iid), None)
        name = item.name if item else iid
        result.append(
            {
                "item": name,
                "stock": "—",
                "need": f"{qty:.1f} orders",
                "order": "—",
                "unit": "—",
                "total": "—",
            }
        )
    return sorted(result, key=lambda x: float(x["need"].split()[0]), reverse=True)


@app.post("/api/upload/invoice")
async def upload_invoice(file: UploadFile = File(...)):
    print(f"Received file upload: {file.filename}")

    file_bytes = await file.read()

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = """
        You are an AI simulating an invoice parser for a restaurant MVP. 
        Extract the line items from this invoice/receipt image and their current prices (which is the newPrice). 
        Since this is an MVP demo, invent a plausible `oldPrice` (slightly lower) for each item and calculate the `pctChange`. 
        Categorize `severity` as "warning" if pctChange < 8 else "destructive". 
        Output strictly valid JSON matching this exact schema:
        [
          {
            "item": "string",
            "unit": "string",
            "oldPrice": 0.0,
            "newPrice": 0.0,
            "pctChange": 0.0,
            "severity": "warning" | "destructive",
            "affectedDishes": [
              {
                "name": "string",
                "currentCost": 0.0,
                "newCost": 0.0,
                "currentMargin": 0.0,
                "newMargin": 0.0,
                "currentMenuPrice": 0.0
              }
            ]
          }
        ]
        """
        response = model.generate_content(
            [
                prompt,
                {"mime_type": file.content_type or "image/jpeg", "data": file_bytes},
            ],
            generation_config={"response_mime_type": "application/json"},
        )
        return json.loads(response.text)
    except Exception as e:
        print(f"Gemini API error: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse invoice with AI")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
