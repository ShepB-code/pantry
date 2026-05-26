from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pantry_engine.db.session import clear_engine_cache
from pantry_engine.ingest.paths import IngestPaths
from pantry_engine.ingest.runs import IngestionRunStore, RunStatus
from pantry_engine.ingest.toast_sftp.client import LocalSftpDownloader
from pantry_engine.ingest.toast_sftp.pull import TOAST_SFTP_SOURCE, pull_item_selection


SAMPLE_CSV = """\
Order #,Sent Date,Menu Item,Menu Group,Menu,Sales Category,Net Price,Qty,Void?
1,4/1/26 5:02 PM,Mountain Valley Spring,NA BEV,BEV,NA Beverage,10.00,1.0,false
2,4/1/26 5:04 PM,Noriko Oyster,STARTERS,FOOD,Food,30.00,5.0,true
"""


class ToastSftpPullTest(unittest.TestCase):
    def _fixture_downloader(self, root: Path, export_id: str, business_date: date) -> LocalSftpDownloader:
        remote_dir = root / export_id / business_date.strftime("%Y%m%d")
        remote_dir.mkdir(parents=True)
        (remote_dir / "ItemSelectionDetails.csv").write_text(SAMPLE_CSV)
        return LocalSftpDownloader(root, export_id)

    def setUp(self) -> None:
        clear_engine_cache()

    def test_pull_downloads_validates_and_records_run(self) -> None:
        export_id = "loc_test_001"
        business_date = date(2026, 4, 1)

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fixture_root = tmp_path / "sftp"
            ingest_root = tmp_path / "ingest"
            paths = IngestPaths(root=ingest_root)
            paths.ensure_dirs()
            db_url = f"sqlite:///{(ingest_root / 'test.db').resolve()}"
            store = IngestionRunStore(database_url=db_url, location_id="test_loc")
            downloader = self._fixture_downloader(fixture_root, export_id, business_date)

            result = pull_item_selection(
                business_date=business_date,
                downloader=downloader,
                paths=paths,
                store=store,
                skip_if_unchanged=False,
                copy_to_canonical=False,
            )

            self.assertEqual(result.status, RunStatus.SUCCESS)
            self.assertEqual(result.row_count, 1)
            inbox = paths.toast_pos_inbox / paths.inbox_filename("2026-04-01")
            self.assertTrue(inbox.is_file())

            run = store.get_run(TOAST_SFTP_SOURCE, business_date)
            assert run is not None
            self.assertEqual(run.status, RunStatus.SUCCESS)
            self.assertEqual(run.row_count, 1)
            self.assertIsNotNone(run.file_sha256)

    def test_pull_skips_when_already_ingested(self) -> None:
        export_id = "loc_test_002"
        business_date = date(2026, 4, 2)

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            paths = IngestPaths(root=tmp_path / "ingest")
            paths.ensure_dirs()
            db_url = f"sqlite:///{(paths.root / 'test.db').resolve()}"
            store = IngestionRunStore(database_url=db_url, location_id="test_loc")
            downloader = self._fixture_downloader(
                tmp_path / "sftp", export_id, business_date
            )

            first = pull_item_selection(
                business_date=business_date,
                downloader=downloader,
                paths=paths,
                store=store,
            )
            second = pull_item_selection(
                business_date=business_date,
                downloader=downloader,
                paths=paths,
                store=store,
            )

            self.assertEqual(first.status, RunStatus.SUCCESS)
            self.assertTrue(second.skipped)
            self.assertEqual(second.status, RunStatus.SKIPPED)

    def test_pull_fails_when_remote_missing(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            paths = IngestPaths(root=tmp_path / "ingest")
            paths.ensure_dirs()
            db_url = f"sqlite:///{(paths.root / 'test.db').resolve()}"
            store = IngestionRunStore(database_url=db_url, location_id="test_loc")
            downloader = LocalSftpDownloader(tmp_path / "empty", "missing_export")

            result = pull_item_selection(
                business_date=date(2026, 4, 3),
                downloader=downloader,
                paths=paths,
                store=store,
            )

            self.assertEqual(result.status, RunStatus.FAILED)
            run = store.get_run(TOAST_SFTP_SOURCE, date(2026, 4, 3))
            assert run is not None
            self.assertEqual(run.status, RunStatus.FAILED)


if __name__ == "__main__":
    unittest.main()
