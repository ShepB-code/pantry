from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from pantry_engine.db.models import (
    InventoryItemRecord,
    MenuItemRecord,
    PosSalesDailyRecord,
    RecipeLineRecord,
)
from pantry_engine.db.seed import default_location_id
from pantry_engine.db.session import get_session_factory


class RecipeRepository:
    def __init__(
        self,
        *,
        location_id: str | None = None,
        session_factory=None,
    ) -> None:
        self.location_id = location_id or default_location_id()
        self._session_factory = session_factory or get_session_factory()

    def list_menu_items(self, *, search: str | None = None, sold_only: bool = False) -> list[dict]:
        with self._session_factory() as session:
            sales_qty = self._sales_qty_by_menu(session)
            recipe_menu_ids = self._menu_ids_with_recipes(session)
            q = (
                select(MenuItemRecord)
                .where(MenuItemRecord.location_id == self.location_id)
                .order_by(MenuItemRecord.name)
            )
            rows = session.execute(q).scalars().all()
            items: list[dict] = []
            for row in rows:
                if row.menu_group == "Archived":
                    continue
                qty = sales_qty.get(row.id, 0.0)
                if sold_only and qty <= 0:
                    continue
                if search:
                    needle = search.lower()
                    if needle not in row.name.lower() and needle not in row.id.lower():
                        continue
                items.append(
                    {
                        "id": row.id,
                        "name": row.name,
                        "category": row.category,
                        "menuGroup": row.menu_group,
                        "quantitySold": qty,
                        "depletionType": _depletion_type(row, row.id in recipe_menu_ids),
                    }
                )
            items.sort(key=lambda x: (-x["quantitySold"], x["name"].lower()))
            return items

    def list_inventory_options(self) -> list[dict]:
        with self._session_factory() as session:
            rows = session.execute(
                select(InventoryItemRecord)
                .where(InventoryItemRecord.location_id == self.location_id)
                .order_by(InventoryItemRecord.name)
            ).scalars()
            return [
                {
                    "id": row.id,
                    "name": row.name,
                    "inventoryItem": row.catalog_name or row.name,
                    "unit": row.unit or "each",
                    "category": row.category,
                }
                for row in rows
            ]

    def get_recipe(self, menu_item_id: str) -> dict | None:
        with self._session_factory() as session:
            menu = session.get(
                MenuItemRecord,
                {"location_id": self.location_id, "id": menu_item_id},
            )
            if menu is None:
                return None
            lines = session.execute(
                select(RecipeLineRecord, InventoryItemRecord)
                .join(
                    InventoryItemRecord,
                    (RecipeLineRecord.location_id == InventoryItemRecord.location_id)
                    & (
                        RecipeLineRecord.inventory_item_id
                        == InventoryItemRecord.id
                    ),
                )
                .where(
                    RecipeLineRecord.location_id == self.location_id,
                    RecipeLineRecord.menu_item_id == menu_item_id,
                )
                .order_by(InventoryItemRecord.name)
            ).all()
            direct = _direct_to_dict(menu, session, self.location_id)
            return {
                "menuItemId": menu.id,
                "menuItemName": menu.name,
                "category": menu.category,
                "depletionType": _depletion_type(menu, bool(lines)),
                "lines": [_line_to_dict(recipe, inv) for recipe, inv in lines],
                "direct": direct,
            }

    def replace_recipe(
        self,
        menu_item_id: str,
        lines: list[dict],
    ) -> dict:
        with self._session_factory() as session:
            menu = session.get(
                MenuItemRecord,
                {"location_id": self.location_id, "id": menu_item_id},
            )
            if menu is None:
                raise KeyError(menu_item_id)

            validated: list[dict] = []
            seen: set[str] = set()
            for line in lines:
                inv_id = str(line["inventoryItemId"]).strip()
                if not inv_id or inv_id in seen:
                    continue
                qty = float(line["qtyPerServing"])
                if qty <= 0:
                    continue
                seen.add(inv_id)
                inv = session.get(
                    InventoryItemRecord,
                    {"location_id": self.location_id, "id": inv_id},
                )
                if inv is None:
                    raise KeyError(f"inventory item not found: {inv_id}")
                validated.append(
                    {
                        "inventoryItemId": inv_id,
                        "qtyPerServing": qty,
                        "wasteFactor": float(line.get("wasteFactor") or 0.0),
                    }
                )
            if not validated:
                raise ValueError(
                    "At least one ingredient with qty per serving > 0 is required"
                )

            session.execute(
                delete(RecipeLineRecord).where(
                    RecipeLineRecord.location_id == self.location_id,
                    RecipeLineRecord.menu_item_id == menu_item_id,
                )
            )
            menu.direct_inventory_item_id = None
            menu.direct_qty_per_serving = None

            for line in validated:
                session.add(
                    RecipeLineRecord(
                        location_id=self.location_id,
                        menu_item_id=menu_item_id,
                        inventory_item_id=line["inventoryItemId"],
                        qty_per_serving=line["qtyPerServing"],
                        waste_factor=line["wasteFactor"],
                    )
                )
            session.commit()
            return self.get_menu_depletion(menu_item_id)  # type: ignore[return-value]

    def set_direct_depletion(
        self,
        menu_item_id: str,
        *,
        inventory_item_id: str,
        qty_per_serving: float = 1.0,
    ) -> dict:
        with self._session_factory() as session:
            menu = session.get(
                MenuItemRecord,
                {"location_id": self.location_id, "id": menu_item_id},
            )
            if menu is None:
                raise KeyError(menu_item_id)
            inv = session.get(
                InventoryItemRecord,
                {"location_id": self.location_id, "id": inventory_item_id},
            )
            if inv is None:
                raise KeyError(f"inventory item not found: {inventory_item_id}")
            if qty_per_serving <= 0:
                raise ValueError("qty_per_serving must be positive")

            session.execute(
                delete(RecipeLineRecord).where(
                    RecipeLineRecord.location_id == self.location_id,
                    RecipeLineRecord.menu_item_id == menu_item_id,
                )
            )
            menu.direct_inventory_item_id = inventory_item_id
            menu.direct_qty_per_serving = qty_per_serving
            menu.updated_at = datetime.now(timezone.utc)
            session.commit()
            result = self.get_menu_depletion(menu_item_id)
            assert result is not None
            return result

    def clear_direct_depletion(self, menu_item_id: str) -> dict:
        with self._session_factory() as session:
            menu = session.get(
                MenuItemRecord,
                {"location_id": self.location_id, "id": menu_item_id},
            )
            if menu is None:
                raise KeyError(menu_item_id)
            menu.direct_inventory_item_id = None
            menu.direct_qty_per_serving = None
            menu.updated_at = datetime.now(timezone.utc)
            session.commit()
            result = self.get_menu_depletion(menu_item_id)
            assert result is not None
            return result

    def get_menu_depletion(self, menu_item_id: str) -> dict | None:
        with self._session_factory() as session:
            menu = session.get(
                MenuItemRecord,
                {"location_id": self.location_id, "id": menu_item_id},
            )
            if menu is None:
                return None
            lines = session.execute(
                select(RecipeLineRecord, InventoryItemRecord)
                .join(
                    InventoryItemRecord,
                    (RecipeLineRecord.location_id == InventoryItemRecord.location_id)
                    & (
                        RecipeLineRecord.inventory_item_id
                        == InventoryItemRecord.id
                    ),
                )
                .where(
                    RecipeLineRecord.location_id == self.location_id,
                    RecipeLineRecord.menu_item_id == menu_item_id,
                )
                .order_by(InventoryItemRecord.name)
            ).all()
            line_dicts = [_line_to_dict(recipe, inv) for recipe, inv in lines]
            return {
                "menuItemId": menu.id,
                "menuItemName": menu.name,
                "category": menu.category,
                "depletionType": _depletion_type(menu, bool(line_dicts)),
                "lines": line_dicts,
                "direct": _direct_to_dict(menu, session, self.location_id),
            }

    def list_overview(self) -> list[dict]:
        """Menu items that have recipe lines, plus sold items without recipes."""
        with self._session_factory() as session:
            sales_qty = self._sales_qty_by_menu(session)
            recipes_by_menu: dict[str, list[dict]] = defaultdict(list)

            rows = session.execute(
                select(RecipeLineRecord, InventoryItemRecord, MenuItemRecord)
                .join(
                    InventoryItemRecord,
                    (RecipeLineRecord.location_id == InventoryItemRecord.location_id)
                    & (
                        RecipeLineRecord.inventory_item_id
                        == InventoryItemRecord.id
                    ),
                )
                .join(
                    MenuItemRecord,
                    (RecipeLineRecord.location_id == MenuItemRecord.location_id)
                    & (RecipeLineRecord.menu_item_id == MenuItemRecord.id),
                )
                .where(RecipeLineRecord.location_id == self.location_id)
                .order_by(MenuItemRecord.name, InventoryItemRecord.name)
            ).all()

            menu_meta: dict[str, MenuItemRecord] = {}
            for recipe, inv, menu in rows:
                menu_meta[menu.id] = menu
                recipes_by_menu[menu.id].append(_line_to_dict(recipe, inv))

            result: list[dict] = []
            for mid, lines in recipes_by_menu.items():
                menu = menu_meta[mid]
                qty = sales_qty.get(mid, 0.0)
                result.append(_overview_row(menu, lines, qty))

            direct_rows = session.execute(
                select(MenuItemRecord).where(
                    MenuItemRecord.location_id == self.location_id,
                    MenuItemRecord.direct_inventory_item_id.is_not(None),
                )
            ).scalars().all()
            for menu in direct_rows:
                if menu.id in recipes_by_menu:
                    continue
                qty = sales_qty.get(menu.id, 0.0)
                inv = session.get(
                    InventoryItemRecord,
                    {
                        "location_id": self.location_id,
                        "id": menu.direct_inventory_item_id,
                    },
                )
                if inv is None:
                    continue
                result.append(
                    _overview_row_direct(menu, inv, menu.direct_qty_per_serving or 1.0, qty)
                )

            result.sort(key=lambda x: (-x["quantitySold"], x["dish"].lower()))
            return result

    def _menu_ids_with_recipes(self, session: Session) -> set[str]:
        rows = session.execute(
            select(RecipeLineRecord.menu_item_id).where(
                RecipeLineRecord.location_id == self.location_id
            )
        ).scalars()
        return set(rows)

    def _sales_qty_by_menu(self, session: Session) -> dict[str, float]:
        rows = session.execute(
            select(
                PosSalesDailyRecord.menu_item_id,
                func.sum(PosSalesDailyRecord.quantity).label("qty"),
            )
            .where(PosSalesDailyRecord.location_id == self.location_id)
            .group_by(PosSalesDailyRecord.menu_item_id)
        ).all()
        return {row.menu_item_id: float(row.qty or 0) for row in rows}


def _line_to_dict(recipe: RecipeLineRecord, inv: InventoryItemRecord) -> dict:
    return {
        "inventoryItemId": recipe.inventory_item_id,
        "name": inv.name,
        "inventoryItem": inv.catalog_name or inv.name,
        "qtyPerServing": recipe.qty_per_serving,
        "wasteFactor": recipe.waste_factor,
        "unit": inv.unit or "each",
    }


def _depletion_type(menu: MenuItemRecord, has_recipe_lines: bool) -> str:
    if has_recipe_lines:
        return "recipe"
    if menu.direct_inventory_item_id:
        return "direct"
    return "none"


def _direct_to_dict(
    menu: MenuItemRecord, session: Session, location_id: str
) -> dict | None:
    if not menu.direct_inventory_item_id:
        return None
    inv = session.get(
        InventoryItemRecord,
        {"location_id": location_id, "id": menu.direct_inventory_item_id},
    )
    if inv is None:
        return None
    return {
        "inventoryItemId": menu.direct_inventory_item_id,
        "name": inv.name,
        "inventoryItem": inv.catalog_name or inv.name,
        "qtyPerServing": menu.direct_qty_per_serving or 1.0,
        "unit": inv.unit or "each",
    }


def _overview_row(menu: MenuItemRecord, lines: list[dict], quantity_sold: float) -> dict:
    pop, pop_color = _popularity_tier(quantity_sold)
    return {
        "menuItemId": menu.id,
        "dish": menu.name,
        "cat": menu.category or menu.menu_group or "—",
        "quantitySold": quantity_sold,
        "depletionType": "recipe",
        "popularity": pop,
        "popColor": pop_color,
        "ingredientCount": len(lines),
        "ingredients": [
            {
                "id": line["inventoryItemId"],
                "name": line["name"],
                "quantity": str(line["qtyPerServing"]),
                "unit": line["unit"],
                "unitCost": "",
                "cost": "",
            }
            for line in lines
        ],
        "cost": "—",
        "price": "—",
        "margin": 0,
        "totalCost": "—",
    }


def _overview_row_direct(
    menu: MenuItemRecord,
    inv: InventoryItemRecord,
    qty_per_serving: float,
    quantity_sold: float,
) -> dict:
    pop, pop_color = _popularity_tier(quantity_sold)
    return {
        "menuItemId": menu.id,
        "dish": menu.name,
        "cat": menu.category or menu.menu_group or "—",
        "quantitySold": quantity_sold,
        "depletionType": "direct",
        "popularity": pop,
        "popColor": pop_color,
        "ingredientCount": 1,
        "ingredients": [
            {
                "id": inv.id,
                "name": inv.name,
                "quantity": str(qty_per_serving),
                "unit": inv.unit or "each",
                "unitCost": "",
                "cost": "",
            }
        ],
        "cost": "—",
        "price": "—",
        "margin": 0,
        "totalCost": "—",
    }


def _popularity_tier(qty: float) -> tuple[str, str]:
    if qty >= 100:
        return "High", "text-success"
    if qty >= 20:
        return "Medium", "text-info"
    if qty > 0:
        return "Low", "text-warning"
    return "No sales", "text-muted-foreground"
