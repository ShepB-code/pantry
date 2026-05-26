import unittest
from datetime import datetime, timezone

from pantry_engine.db.models import (
    InventoryItemRecord,
    LocationRecord,
    MenuItemRecord,
)
from pantry_engine.db.seed import ensure_default_location
from pantry_engine.db.session import clear_engine_cache, get_session_factory, init_db


class DbSchemaTest(unittest.TestCase):
    def setUp(self) -> None:
        clear_engine_cache()
        self.db_url = "sqlite:///:memory:"
        init_db(self.db_url)

    def test_mvp_tables_and_location_scoped_inventory(self) -> None:
        factory = get_session_factory(self.db_url)
        now = datetime.now(timezone.utc)
        with factory() as session:
            loc_id = ensure_default_location(session, location_id="perilla")
            session.add(
                MenuItemRecord(
                    location_id=loc_id,
                    id="noriko_oyster",
                    name="Noriko Oyster",
                    category="Food",
                    updated_at=now,
                )
            )
            session.add(
                InventoryItemRecord(
                    location_id=loc_id,
                    id="beef_short_rib",
                    name="Short rib",
                    category="Food",
                    unit="lb",
                    on_hand=12.0,
                    par_level=20.0,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.commit()

            item = session.get(
                InventoryItemRecord, {"location_id": loc_id, "id": "beef_short_rib"}
            )
            assert item is not None
            self.assertEqual(item.on_hand, 12.0)
            self.assertEqual(item.par_level, 20.0)

            menu = session.get(
                MenuItemRecord, {"location_id": loc_id, "id": "noriko_oyster"}
            )
            assert menu is not None
            self.assertEqual(menu.name, "Noriko Oyster")

            location = session.get(LocationRecord, loc_id)
            assert location is not None
            self.assertEqual(location.id, "perilla")


if __name__ == "__main__":
    unittest.main()
