import unittest

from pantry_engine.db.models import Base, LocationRecord
from pantry_engine.db.reset import reset_database
from pantry_engine.db.seed import ensure_default_location
from pantry_engine.db.session import clear_engine_cache, get_session_factory, init_db


class ResetDatabaseTest(unittest.TestCase):
    def test_reset_file_sqlite(self) -> None:
        import tempfile
        from pathlib import Path

        clear_engine_cache()
        path = Path(tempfile.mkdtemp()) / "test.db"
        url = f"sqlite:///{path}"
        init_db(url)
        factory = get_session_factory(url)
        with factory() as session:
            ensure_default_location(session, location_id="test_loc")

        msg = reset_database(url)
        self.assertIn("deleted SQLite", msg)
        self.assertFalse(path.exists())

        clear_engine_cache()
        init_db(url)
        with get_session_factory(url)() as session:
            self.assertIsNone(session.get(LocationRecord, "test_loc"))


if __name__ == "__main__":
    unittest.main()
