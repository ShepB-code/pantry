import unittest
from datetime import date, datetime, timezone

from pantry_engine.db.catalog_sync import upsert_xtrachef_catalog
from pantry_engine.db.depletion import apply_sales_depletion
from pantry_engine.db.models import InventoryItemRecord, MenuItemRecord, PosSalesDailyRecord
from pantry_engine.db.recipe_repo import RecipeRepository
from pantry_engine.db.seed import ensure_default_location
from pantry_engine.db.session import clear_engine_cache, get_session_factory, init_db

import pandas as pd


class DepletionResolutionTest(unittest.TestCase):
    def setUp(self) -> None:
        clear_engine_cache()
        self.db_url = "sqlite:///:memory:"
        init_db(self.db_url)
        self.factory = get_session_factory(self.db_url)
        self.loc = "test_loc"
        now = datetime.now(timezone.utc)
        with self.factory() as session:
            ensure_default_location(session, location_id=self.loc)
            upsert_xtrachef_catalog(
                session,
                location_id=self.loc,
                xchef=pd.DataFrame(
                    [
                        {
                            "item_key": "worcestershire sauce",
                            "item_description": "WORCESTERSHIRE SAUCE",
                            "category": "Food",
                            "category_group": "Food",
                            "uom": "each",
                            "item_uom": "each",
                            "weighable": "false",
                            "vendor_name": "V",
                            "item_code": "W1",
                            "last_purchased_price": 5.0,
                            "last_purchased_date": pd.Timestamp("2026-05-01"),
                            "product_s": "",
                        },
                        {
                            "item_key": "scallop",
                            "item_description": "SCALLOP",
                            "category": "Seafood",
                            "category_group": "Seafood",
                            "uom": "each",
                            "item_uom": "each",
                            "weighable": "false",
                            "vendor_name": "V",
                            "item_code": "S1",
                            "last_purchased_price": 3.0,
                            "last_purchased_date": pd.Timestamp("2026-05-01"),
                            "product_s": "",
                        },
                    ]
                ),
            )
            for mid, name in [
                ("dipping_sauce", "Dipping Sauce"),
                ("scallop", "Scallop"),
                ("miso_soup", "Miso Soup"),
                ("gift_card", "Gift Card"),
            ]:
                session.add(
                    MenuItemRecord(
                        location_id=self.loc,
                        id=mid,
                        name=name,
                        category="Food",
                        updated_at=now,
                    )
                )
            session.add(
                PosSalesDailyRecord(
                    location_id=self.loc,
                    business_date=date(2026, 6, 1),
                    menu_item_id="dipping_sauce",
                    quantity=10.0,
                    ingested_at=now,
                )
            )
            session.add(
                PosSalesDailyRecord(
                    location_id=self.loc,
                    business_date=date(2026, 6, 1),
                    menu_item_id="scallop",
                    quantity=4.0,
                    ingested_at=now,
                )
            )
            session.add(
                PosSalesDailyRecord(
                    location_id=self.loc,
                    business_date=date(2026, 6, 1),
                    menu_item_id="gift_card",
                    quantity=1.0,
                    ingested_at=now,
                )
            )
            session.commit()

        self.recipes = RecipeRepository(
            location_id=self.loc, session_factory=self.factory
        )
        with self.factory() as session:
            inv = session.get(
                InventoryItemRecord,
                {"location_id": self.loc, "id": "worcestershire sauce"},
            )
            inv.on_hand = 20.0
            scallop_inv = session.get(
                InventoryItemRecord,
                {"location_id": self.loc, "id": "scallop"},
            )
            scallop_inv.on_hand = 10.0
            session.commit()

    def test_recipe_direct_and_logged_only(self) -> None:
        self.recipes.replace_recipe(
            "dipping_sauce",
            [{"inventoryItemId": "worcestershire sauce", "qtyPerServing": 0.5}],
        )
        self.recipes.set_direct_depletion(
            "scallop",
            inventory_item_id="scallop",
            qty_per_serving=1.0,
        )

        with self.factory() as session:
            result = apply_sales_depletion(
                session, business_date=date(2026, 6, 1), location_id=self.loc
            )

        self.assertTrue(result["applied"])
        self.assertEqual(result["summary"]["recipe"], 1)
        self.assertEqual(result["summary"]["direct"], 1)
        self.assertEqual(result["summary"]["loggedOnly"], 1)

        with self.factory() as session:
            w = session.get(
                InventoryItemRecord,
                {"location_id": self.loc, "id": "worcestershire sauce"},
            )
            s = session.get(
                InventoryItemRecord,
                {"location_id": self.loc, "id": "scallop"},
            )
            assert w is not None and s is not None
            self.assertEqual(w.on_hand, 15.0)  # 20 - 10*0.5
            self.assertEqual(s.on_hand, 6.0)  # 10 - 4*1

    def test_recipe_wins_over_direct_if_both_exist(self) -> None:
        """Recipe lines take precedence; direct link should not apply for same menu item."""
        self.recipes.set_direct_depletion(
            "dipping_sauce",
            inventory_item_id="scallop",
            qty_per_serving=99.0,
        )
        self.recipes.replace_recipe(
            "dipping_sauce",
            [{"inventoryItemId": "worcestershire sauce", "qtyPerServing": 0.5}],
        )

        with self.factory() as session:
            inv = session.get(
                InventoryItemRecord,
                {"location_id": self.loc, "id": "worcestershire sauce"},
            )
            inv.on_hand = 20.0
            session.commit()
        with self.factory() as session:
            apply_sales_depletion(
                session, business_date=date(2026, 6, 1), location_id=self.loc
            )
        with self.factory() as session:
            inv = session.get(
                InventoryItemRecord,
                {"location_id": self.loc, "id": "worcestershire sauce"},
            )
            self.assertEqual(inv.on_hand, 15.0)


if __name__ == "__main__":
    unittest.main()
