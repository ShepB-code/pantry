import shutil
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from pantry_engine.db.models import InventoryItemRecord
from pantry_engine.db.seed import ensure_default_location
from pantry_engine.db.session import clear_engine_cache, get_session_factory, init_db
from pantry_engine.demo.depletion import (
    DEMO_BUSINESS_DATE,
    DEMO_CSV,
    DEMO_INVENTORY_ITEM_ID,
    DEMO_STARTING_ON_HAND,
    setup_demo_state,
)
from pantry_engine.ingest.paths import IngestPaths
from pantry_engine.ingest.toast_sftp.apply import apply_pulled_sales


class DemoDepletionTest(unittest.TestCase):
    def setUp(self) -> None:
        clear_engine_cache()
        self.db_url = "sqlite:///:memory:"
        init_db(self.db_url)
        self.factory = get_session_factory(self.db_url)
        with self.factory() as session:
            ensure_default_location(session, location_id="test_loc")
            now = datetime.now(timezone.utc)
            session.add(
                InventoryItemRecord(
                    location_id="test_loc",
                    id=DEMO_INVENTORY_ITEM_ID,
                    name="Worcestershire sauce",
                    catalog_name="WORCESTERSHIRE SAUCE",
                    catalog_source="xtrachef",
                    category="Food",
                    unit="each",
                    on_hand=0.0,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.commit()

    def test_setup_and_apply_reduces_on_hand(self) -> None:
        paths = IngestPaths.from_repo()
        paths.ensure_dirs()
        inbox = paths.toast_pos_inbox / paths.inbox_filename(DEMO_BUSINESS_DATE.isoformat())
        shutil.copy(DEMO_CSV, inbox)

        with self.factory() as session:
            setup = setup_demo_state(session, location_id="test_loc")
        self.assertEqual(setup["expectedOnHandAfter"], 5.0)

        with patch(
            "pantry_engine.ingest.toast_sftp.apply.get_session_factory",
            return_value=self.factory,
        ):
            result = apply_pulled_sales(
                DEMO_BUSINESS_DATE,
                paths=paths,
                location_id="test_loc",
            )
        self.assertTrue(result["depletion"]["applied"])

        with self.factory() as session:
            row = session.get(
                InventoryItemRecord,
                {"location_id": "test_loc", "id": DEMO_INVENTORY_ITEM_ID},
            )
            assert row is not None
            self.assertEqual(row.on_hand, 5.0)
            self.assertEqual(row.last_count_source, "pos_depletion")


if __name__ == "__main__":
    unittest.main()
