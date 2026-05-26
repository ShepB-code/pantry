from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from pantry_engine.db.models import InventoryItemRecord, PosSalesDailyRecord, RecipeLineRecord
from pantry_engine.db.seed import default_location_id


def apply_sales_depletion(
    session: Session,
    *,
    business_date: date,
    location_id: str | None = None,
) -> dict:
    """Reduce on_hand using recipe_lines × pos_sales_daily for the given day."""
    location_id = location_id or default_location_id()
    recipes = session.execute(
        select(RecipeLineRecord).where(RecipeLineRecord.location_id == location_id)
    ).scalars().all()
    if not recipes:
        return {
            "businessDate": business_date.isoformat(),
            "applied": False,
            "message": "No recipe_lines configured — on_hand unchanged. Add recipes or use Quick Count.",
            "adjustments": [],
        }

    sales = session.execute(
        select(PosSalesDailyRecord).where(
            PosSalesDailyRecord.location_id == location_id,
            PosSalesDailyRecord.business_date == business_date,
        )
    ).scalars().all()
    sales_by_menu = {row.menu_item_id: row.quantity for row in sales}

    now = datetime.now(timezone.utc)
    adjustments: list[dict] = []
    usage_by_ingredient: dict[str, float] = {}

    for recipe in recipes:
        sold = sales_by_menu.get(recipe.menu_item_id, 0.0)
        if sold <= 0:
            continue
        usage = sold * recipe.qty_per_serving * (1.0 + recipe.waste_factor)
        usage_by_ingredient[recipe.inventory_item_id] = (
            usage_by_ingredient.get(recipe.inventory_item_id, 0.0) + usage
        )

    for ingredient_id, usage in usage_by_ingredient.items():
        row = session.get(
            InventoryItemRecord,
            {"location_id": location_id, "id": ingredient_id},
        )
        if row is None:
            continue
        before = row.on_hand
        after = max(0.0, before - usage)
        row.on_hand = round(after, 2)
        row.last_count_source = "pos_depletion"
        row.updated_at = now
        adjustments.append(
            {
                "itemId": ingredient_id,
                "name": row.name,
                "before": before,
                "after": after,
                "used": round(usage, 2),
            }
        )

    session.commit()
    return {
        "businessDate": business_date.isoformat(),
        "applied": bool(adjustments),
        "message": f"Adjusted {len(adjustments)} ingredient(s) from sales.",
        "adjustments": adjustments,
    }
