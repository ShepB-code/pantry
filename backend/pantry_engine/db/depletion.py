from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from pantry_engine.db.models import (
    InventoryItemRecord,
    MenuItemRecord,
    PosSalesDailyRecord,
    RecipeLineRecord,
)
from pantry_engine.db.seed import default_location_id


def apply_sales_depletion(
    session: Session,
    *,
    business_date: date,
    location_id: str | None = None,
) -> dict:
    """Reduce on_hand from POS sales for one business day.

    Resolution per menu_item_id (in order):
    1. recipe_lines — multi-ingredient recipe
    2. menu_items.direct_inventory_item_id — singular ingredient
    3. otherwise — sales already in pos_sales_daily; no stock change
    """
    location_id = location_id or default_location_id()

    sales = session.execute(
        select(PosSalesDailyRecord).where(
            PosSalesDailyRecord.location_id == location_id,
            PosSalesDailyRecord.business_date == business_date,
        )
    ).scalars().all()
    if not sales:
        return {
            "businessDate": business_date.isoformat(),
            "applied": False,
            "message": f"No POS sales for {business_date.isoformat()}.",
            "adjustments": [],
            "summary": {"recipe": 0, "direct": 0, "loggedOnly": 0},
        }

    sales_by_menu = {row.menu_item_id: float(row.quantity) for row in sales}

    recipes = session.execute(
        select(RecipeLineRecord).where(RecipeLineRecord.location_id == location_id)
    ).scalars().all()
    recipes_by_menu: dict[str, list[RecipeLineRecord]] = defaultdict(list)
    for recipe in recipes:
        recipes_by_menu[recipe.menu_item_id].append(recipe)

    direct_menus = session.execute(
        select(MenuItemRecord).where(
            MenuItemRecord.location_id == location_id,
            MenuItemRecord.direct_inventory_item_id.is_not(None),
        )
    ).scalars().all()
    direct_by_menu = {row.id: row for row in direct_menus}

    now = datetime.now(timezone.utc)
    usage_by_ingredient: dict[str, float] = {}
    summary = {"recipe": 0, "direct": 0, "loggedOnly": 0}

    for menu_item_id, sold in sales_by_menu.items():
        if sold <= 0:
            continue

        menu_recipes = recipes_by_menu.get(menu_item_id) or []
        if menu_recipes:
            summary["recipe"] += 1
            for recipe in menu_recipes:
                usage = sold * recipe.qty_per_serving * (1.0 + recipe.waste_factor)
                usage_by_ingredient[recipe.inventory_item_id] = (
                    usage_by_ingredient.get(recipe.inventory_item_id, 0.0) + usage
                )
            continue

        direct_menu = direct_by_menu.get(menu_item_id)
        if direct_menu and direct_menu.direct_inventory_item_id:
            summary["direct"] += 1
            qty_per = direct_menu.direct_qty_per_serving or 1.0
            inv_id = direct_menu.direct_inventory_item_id
            usage_by_ingredient[inv_id] = (
                usage_by_ingredient.get(inv_id, 0.0) + sold * qty_per
            )
            continue

        summary["loggedOnly"] += 1

    adjustments: list[dict] = []
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

    parts: list[str] = []
    if summary["recipe"]:
        parts.append(f"{summary['recipe']} recipe")
    if summary["direct"]:
        parts.append(f"{summary['direct']} direct")
    if summary["loggedOnly"]:
        parts.append(f"{summary['loggedOnly']} logged only")

    message = (
        f"Adjusted {len(adjustments)} ingredient(s) from sales"
        + (f" ({', '.join(parts)})." if parts else ".")
        if adjustments
        else (
            f"No depletion rules matched ({summary['loggedOnly']} sold items logged only)."
            if summary["loggedOnly"]
            else "No stock changes."
        )
    )

    return {
        "businessDate": business_date.isoformat(),
        "applied": bool(adjustments),
        "message": message,
        "adjustments": adjustments,
        "summary": summary,
    }
