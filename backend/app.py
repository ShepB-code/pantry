import sys
import os
import json
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Literal
import asyncio

from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
load_dotenv(Path(__file__).resolve().parent / ".env")
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
from pantry_engine.quick_count import evaluate_submission, resolve_actual_count

app = FastAPI(title="Pantry API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_data() -> tuple[PantryEngine, InMemoryDataSource]:
    from pantry_engine.db.seed import default_location_id

    location_id = default_location_id()
    print(f"Loading POS data for location {location_id}...")
    pos_df = pantry_eda.read_pos_item_selections(location_id=location_id)
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


# Global state for forecasting engine (POS/weather still from CSV exports)
engine = None
data_source = None


def _inventory_repo():
    from pantry_engine.db.inventory_repo import InventoryRepository

    return InventoryRepository()


def _quick_count_repo():
    from pantry_engine.db.quick_count_repo import QuickCountRepository

    return QuickCountRepository(inventory_repo=_inventory_repo())


class QuickCountLineSubmission(BaseModel):
    itemId: str
    mode: Literal["confirm", "numeric", "estimate"]
    value: float | str | None = None
    unit: str | None = None


class ParLevelUpdate(BaseModel):
    parLevel: float


@app.on_event("startup")
def startup_event():
    from pantry_engine.db import init_db
    from pantry_engine.db.catalog_sync import sync_xtrachef_from_exports
    from pantry_engine.db.pos_sales_sync import ingest_menu_item_export_file
    from pantry_engine.db.seed import default_location_id, ensure_default_location
    from pantry_engine.db.session import get_session_factory

    init_db()
    with get_session_factory()() as session:
        loc_id = ensure_default_location(session)
        try:
            menu_export = pantry_eda.pos_location_dir(location_id=loc_id) / "MenuItem_Export.csv"
            if menu_export.exists():
                result = ingest_menu_item_export_file(
                    session, csv_path=menu_export, location_id=loc_id
                )
                print(f"Toast menu export sync: {result.get('menuItemsUpserted', 0)} upserted")
        except Exception as exc:
            session.rollback()
            print(f"Toast menu export sync skipped: {exc}")

        try:
            created, updated = sync_xtrachef_from_exports(session, loc_id)
            print(f"xtraCHEF catalog sync: {created} created, {updated} updated")
        except Exception as exc:
            session.rollback()
            print(f"xtraCHEF catalog sync skipped: {exc}")

    global engine, data_source
    engine, data_source = load_data()


@app.get("/api/health/db")
def health_db():
    from pantry_engine.db import check_connection

    return check_connection()


@app.get("/api/inventory")
def get_inventory():
    repo = _inventory_repo()
    return {
        "locationId": repo.location_id,
        "items": repo.list_items(),
        "onHand": repo.on_hand_map(),
    }


@app.post("/api/inventory/sync-catalog")
def sync_catalog():
    """Re-import xtraCHEF item library into inventory_items."""
    from pantry_engine.db.catalog_sync import sync_xtrachef_from_exports
    from pantry_engine.db.seed import default_location_id
    from pantry_engine.db.session import get_session_factory

    with get_session_factory()() as session:
        created, updated = sync_xtrachef_from_exports(session, default_location_id())
    return {"created": created, "updated": updated}


@app.post("/api/menu/sync-export")
def sync_menu_export():
    """Import Toast MenuItem_Export.csv into menu_items for the default location."""
    from pantry_engine.db.pos_sales_sync import ingest_menu_item_export_file
    from pantry_engine.db.seed import default_location_id
    from pantry_engine.db.session import get_session_factory

    loc_id = default_location_id()
    menu_export = pantry_eda.pos_location_dir(location_id=loc_id) / "MenuItem_Export.csv"
    if not menu_export.exists():
        raise HTTPException(
            status_code=404,
            detail=f"MenuItem_Export.csv not found at {menu_export}",
        )
    with get_session_factory()() as session:
        return ingest_menu_item_export_file(session, csv_path=menu_export, location_id=loc_id)


@app.patch("/api/inventory/{item_id}/par")
def update_inventory_par(item_id: str, body: ParLevelUpdate):
    try:
        return _inventory_repo().set_par_level(item_id, body.parLevel)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Item not found") from exc


@app.get("/api/inventory/quick-count")
def get_quick_count():
    return _quick_count_repo().build_session_payload()


@app.post("/api/inventory/quick-count/lines")
def submit_quick_count_line(body: QuickCountLineSubmission):
    qc = _quick_count_repo()
    payload = qc.build_session_payload()
    if payload["completed"]:
        raise HTTPException(status_code=400, detail="Quick count already completed for today")

    item = next((i for i in payload["items"] if i["id"] == body.itemId), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not in today's quick count list")

    if body.mode == "numeric":
        if body.value is None:
            raise HTTPException(status_code=400, detail="Numeric count requires a value")
        actual = resolve_actual_count(
            expected=item["expectedOnHand"],
            par=item["parLevel"],
            mode="numeric",
            value=float(body.value),
        )
    elif body.mode == "estimate":
        if not isinstance(body.value, str):
            raise HTTPException(status_code=400, detail="Estimate requires low, ok, or high")
        actual = resolve_actual_count(
            expected=item["expectedOnHand"],
            par=item["parLevel"],
            mode="estimate",
            value=body.value,
        )
    else:
        actual = resolve_actual_count(
            expected=item["expectedOnHand"],
            par=item["parLevel"],
            mode="confirm",
        )

    evaluation = evaluate_submission(
        expected=item["expectedOnHand"],
        par=item["parLevel"],
        actual=actual,
        category=item["category"],
    )

    try:
        return qc.submit_line(
            item_id=body.itemId,
            mode=body.mode,
            unit=body.unit or item["defaultCountUnit"],
            name=item["name"],
            expected=item["expectedOnHand"],
            actual=actual,
            flagged=evaluation["flagged"],
            flags=evaluation["flags"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/inventory/quick-count/reset")
def reset_quick_count():
    return _quick_count_repo().reset_session()


@app.post("/api/inventory/quick-count/complete")
def complete_quick_count():
    try:
        return _quick_count_repo().complete_session()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
        data_source=data_source,
        inventory=_inventory_repo().on_hand_map(),
        start=start_date,
        days=days,
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


@app.post("/api/ingestion/toast/apply")
def ingestion_toast_apply(business_date: str):
    """Ingest a pulled inbox CSV and apply recipe-based depletion to on_hand."""
    from pantry_engine.ingest.toast_sftp.apply import apply_pulled_sales

    try:
        parsed = date.fromisoformat(business_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="business_date must be YYYY-MM-DD") from exc
    try:
        return apply_pulled_sales(parsed)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/ingestion/toast/pull")
def ingestion_toast_pull(
    days: int = 7,
    force: bool = False,
    business_date: str | None = None,
    apply_sales: bool = False,
):
    """Pull Toast nightly ItemSelectionDetails exports over SFTP."""
    from pantry_engine.ingest.paths import IngestPaths
    from pantry_engine.ingest.runs import RunStatus
    from pantry_engine.ingest.toast_sftp.config import ToastSftpConfig
    try:
        config = ToastSftpConfig.from_env()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if days < 1 or days > 7:
        raise HTTPException(
            status_code=400,
            detail="days must be between 1 and 7 (Toast SFTP retention window)",
        )

    parsed_date: date | None = None
    if business_date:
        try:
            parsed_date = date.fromisoformat(business_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="business_date must be YYYY-MM-DD",
            ) from exc

    from pantry_engine.ingest.toast_sftp.downloader import get_toast_downloader
    from pantry_engine.ingest.toast_sftp.apply import apply_pulled_sales
    from pantry_engine.ingest.toast_sftp.pull import pull_item_selection, pull_recent_days

    paths = IngestPaths.from_repo(root)
    downloader = get_toast_downloader(config)
    if parsed_date:
        results = [
            pull_item_selection(
                business_date=parsed_date,
                downloader=downloader,
                paths=paths,
                skip_if_unchanged=not force,
            )
        ]
    else:
        end = date.today() - timedelta(days=1)
        results = pull_recent_days(
            downloader=downloader,
            days=days,
            end_date=end,
            paths=paths,
            skip_if_unchanged=not force,
        )

    applied: list[dict] = []
    if apply_sales:
        for result in results:
            if result.status.value != "success" or not result.local_path:
                continue
            try:
                applied.append(apply_pulled_sales(result.business_date, paths=paths))
            except Exception as exc:
                applied.append(
                    {"businessDate": result.business_date.isoformat(), "error": str(exc)}
                )

    return {
        "results": [
            {
                "businessDate": r.business_date.isoformat(),
                "status": r.status.value,
                "rowCount": r.row_count,
                "message": r.message,
                "skipped": r.skipped,
                "path": str(r.local_path) if r.local_path else None,
            }
            for r in results
        ],
        "successCount": sum(1 for r in results if r.status == RunStatus.SUCCESS),
        "failedCount": sum(1 for r in results if r.status == RunStatus.FAILED),
        "applied": applied if apply_sales else None,
    }


@app.get("/api/ingestion/runs")
def ingestion_runs(source: str | None = "toast_sftp", limit: int = 30):
    from pantry_engine.ingest.runs import IngestionRunStore

    store = IngestionRunStore()
    runs = store.list_runs(source=source, limit=limit)
    return [
        {
            "id": run.id,
            "locationId": run.location_id,
            "source": run.source,
            "businessDate": run.business_date.isoformat(),
            "filename": run.filename,
            "status": run.status.value,
            "rowCount": run.row_count,
            "errorMessage": run.error_message,
            "finishedAt": run.finished_at.isoformat() if run.finished_at else None,
        }
        for run in runs
    ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
