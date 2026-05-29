import unittest
from unittest.mock import patch

from pantry_engine.db.catalog_sync import upsert_xtrachef_catalog
from pantry_engine.db.inventory_repo import InventoryRepository
from pantry_engine.db.models import Base, LocationRecord
from pantry_engine.db.quick_count_repo import QuickCountRepository
from pantry_engine.db.seed import ensure_default_location
from pantry_engine.db.session import clear_engine_cache, get_session_factory, init_db
from pantry_engine.db.name_source import NAME_SOURCE_MANUAL, NAME_SOURCE_XTRACHEF

import pandas as pd


class InventoryDbTest(unittest.TestCase):
    def setUp(self) -> None:
        clear_engine_cache()
        self.db_url = "sqlite:///:memory:"
        init_db(self.db_url)
        self.factory = get_session_factory(self.db_url)
        with self.factory() as session:
            ensure_default_location(session, location_id="test_loc")

        self.inventory = InventoryRepository(
            location_id="test_loc", session_factory=self.factory
        )
        self.quick_count = QuickCountRepository(
            location_id="test_loc",
            inventory_repo=self.inventory,
            session_factory=self.factory,
        )

    def _sample_xchef_row(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "item_key": "salmon_fillet",
                    "item_description": "Salmon fillet",
                    "category": "Food - Seafood",
                    "category_group": "Seafood",
                    "uom": "lb",
                    "item_uom": "lb",
                    "weighable": "true",
                    "vendor_name": "Pacific Seafood",
                    "item_code": "SAL001",
                    "last_purchased_price": 12.5,
                    "last_purchased_date": pd.Timestamp("2026-05-01"),
                    "product_s": "",
                }
            ]
        )

    @patch("pantry_engine.quick_count.pantry_eda.read_pos_item_selections")
    @patch("pantry_engine.quick_count.pantry_eda.read_xtrachef_item_library")
    def test_catalog_upsert_and_quick_count_updates_on_hand(
        self, mock_xchef, mock_pos
    ) -> None:
        mock_xchef.return_value = self._sample_xchef_row()
        mock_pos.return_value = pd.DataFrame()

        with self.factory() as session:
            created, updated = upsert_xtrachef_catalog(
                session, location_id="test_loc", xchef=self._sample_xchef_row()
            )
        self.assertEqual(created, 1)
        self.assertEqual(updated, 0)

        payload = self.quick_count.build_session_payload()
        self.assertEqual(payload["itemCount"], 1)
        item = payload["items"][0]
        item_id = "salmon_fillet"

        result = self.quick_count.submit_line(
            item_id=item_id,
            mode="numeric",
            unit="lb",
            name=item["name"],
            expected=item["expectedOnHand"],
            actual=15.0,
            flagged=False,
            flags=item["flags"],
        )
        self.assertEqual(result["line"]["actual"], 15.0)

        on_hand = self.inventory.on_hand_map()
        self.assertEqual(on_hand[item_id], 15.0)

    def test_catalog_upsert_handles_duplicate_item_keys_in_one_batch(self) -> None:
        df = pd.concat(
            [
                self._sample_xchef_row(),
                self._sample_xchef_row().assign(
                    item_description="Salmon fillet duplicate row",
                    item_code="OTHER",
                ),
            ],
            ignore_index=True,
        )
        with self.factory() as session:
            created, updated = upsert_xtrachef_catalog(
                session, location_id="test_loc", xchef=df
            )
        self.assertEqual(created, 1)
        self.assertEqual(updated, 0)

        with self.factory() as session:
            created2, updated2 = upsert_xtrachef_catalog(
                session, location_id="test_loc", xchef=df
            )
        self.assertEqual(created2, 0)
        self.assertEqual(updated2, 1)

    def test_par_level_update(self) -> None:
        with self.factory() as session:
            upsert_xtrachef_catalog(
                session, location_id="test_loc", xchef=self._sample_xchef_row()
            )
        updated = self.inventory.set_par_level("salmon_fillet", 25.0)
        self.assertEqual(updated["parLevel"], 25.0)
        self.assertIn("salmon_fillet", self.inventory.par_overrides_map())

    def test_catalog_sync_sets_inventory_item_label(self) -> None:
        with self.factory() as session:
            upsert_xtrachef_catalog(
                session, location_id="test_loc", xchef=self._sample_xchef_row()
            )
        row = self.inventory.list_items()[0]
        self.assertEqual(row["name"], "Salmon fillet")
        self.assertEqual(row["inventoryItem"], "Salmon fillet")
        self.assertEqual(row["nameSource"], NAME_SOURCE_XTRACHEF)
        self.assertEqual(row["catalogSource"], "xtrachef")

    def test_catalog_sync_uses_item_description_as_name(self) -> None:
        df = self._sample_xchef_row().assign(
            item_description="ALL PURPOSE FLOUR MEDALLION 2|25 LB BC",
            item_key="all_purpose_flour",
            product_s="Flour, AP",
        )
        with self.factory() as session:
            upsert_xtrachef_catalog(session, location_id="test_loc", xchef=df)
        row = self.inventory.list_items()[0]
        self.assertEqual(row["name"], "ALL PURPOSE FLOUR MEDALLION 2|25 LB BC")
        self.assertEqual(row["inventoryItem"], "ALL PURPOSE FLOUR MEDALLION 2|25 LB BC")
        self.assertEqual(row["nameSource"], NAME_SOURCE_XTRACHEF)

    def test_manual_name_preserved_on_catalog_resync(self) -> None:
        with self.factory() as session:
            upsert_xtrachef_catalog(
                session, location_id="test_loc", xchef=self._sample_xchef_row()
            )
        self.inventory.set_name("salmon_fillet", "Kitchen salmon")
        df = self._sample_xchef_row().assign(
            item_description="SALMON FILLET ATLANTIC 10LB",
            product_s="Salmon, Atlantic",
        )
        with self.factory() as session:
            upsert_xtrachef_catalog(session, location_id="test_loc", xchef=df)
        row = self.inventory.list_items()[0]
        self.assertEqual(row["name"], "Kitchen salmon")
        self.assertEqual(row["nameSource"], NAME_SOURCE_MANUAL)
        self.assertEqual(row["inventoryItem"], "SALMON FILLET ATLANTIC 10LB")

    def test_name_update(self) -> None:
        with self.factory() as session:
            upsert_xtrachef_catalog(
                session, location_id="test_loc", xchef=self._sample_xchef_row()
            )
        updated = self.inventory.set_name("salmon_fillet", "Salmon")
        self.assertEqual(updated["name"], "Salmon")
        self.assertEqual(updated["nameSource"], NAME_SOURCE_MANUAL)


if __name__ == "__main__":
    unittest.main()
