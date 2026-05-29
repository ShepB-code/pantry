import unittest
from datetime import datetime, timezone

from pantry_engine.db.catalog_sync import upsert_xtrachef_catalog
from pantry_engine.db.models import MenuItemRecord
from pantry_engine.db.recipe_repo import RecipeRepository
from pantry_engine.db.seed import ensure_default_location
from pantry_engine.db.session import clear_engine_cache, get_session_factory, init_db

import pandas as pd


class RecipeRepoTest(unittest.TestCase):
    def setUp(self) -> None:
        clear_engine_cache()
        self.db_url = "sqlite:///:memory:"
        init_db(self.db_url)
        self.factory = get_session_factory(self.db_url)
        with self.factory() as session:
            ensure_default_location(session, location_id="test_loc")
            upsert_xtrachef_catalog(
                session,
                location_id="test_loc",
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
                            "vendor_name": "Vendor",
                            "item_code": "W1",
                            "last_purchased_price": 5.0,
                            "last_purchased_date": pd.Timestamp("2026-05-01"),
                            "product_s": "",
                        }
                    ]
                ),
            )
            now = datetime.now(timezone.utc)
            session.add(
                MenuItemRecord(
                    location_id="test_loc",
                    id="dipping_sauce",
                    name="Dipping Sauce",
                    category="Food",
                    menu_group=None,
                    updated_at=now,
                )
            )
            session.commit()

        self.recipes = RecipeRepository(
            location_id="test_loc", session_factory=self.factory
        )

    def test_replace_and_get_recipe(self) -> None:
        saved = self.recipes.replace_recipe(
            "dipping_sauce",
            [{"inventoryItemId": "worcestershire sauce", "qtyPerServing": 0.5}],
        )
        self.assertEqual(len(saved["lines"]), 1)
        self.assertEqual(saved["lines"][0]["qtyPerServing"], 0.5)

        overview = self.recipes.list_overview()
        self.assertEqual(len(overview), 1)
        self.assertEqual(overview[0]["dish"], "Dipping Sauce")
        self.assertEqual(overview[0]["ingredientCount"], 1)


if __name__ == "__main__":
    unittest.main()
