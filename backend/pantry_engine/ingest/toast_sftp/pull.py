from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from pantry_engine.ingest.paths import IngestPaths
from pantry_engine.ingest.runs import IngestionRunStore, RunStatus
from pantry_engine.ingestion import ToastItemSelectionDetailsCsvAdapter

if TYPE_CHECKING:
    from pantry_engine.ingest.toast_sftp.client import SftpDownloader
    from pantry_engine.ingest.toast_sftp.config import ToastSftpConfig

TOAST_SFTP_SOURCE = "toast_sftp"


@dataclass(frozen=True)
class PullResult:
    business_date: date
    status: RunStatus
    local_path: Path | None
    row_count: int | None
    message: str | None = None
    skipped: bool = False


def pull_item_selection(
    *,
    business_date: date,
    downloader: SftpDownloader,
    paths: IngestPaths | None = None,
    store: IngestionRunStore | None = None,
    skip_if_unchanged: bool = True,
    copy_to_canonical: bool = True,
) -> PullResult:
    """Pull one business day of ItemSelectionDetails from Toast SFTP."""
    paths = paths or IngestPaths.from_repo()
    paths.ensure_dirs()
    store = store or IngestionRunStore()

    date_key = business_date.isoformat()
    yyyymmdd = business_date.strftime("%Y%m%d")
    inbox_name = paths.inbox_filename(date_key)
    inbox_path = paths.toast_pos_inbox / inbox_name

    if skip_if_unchanged and store.was_successful(TOAST_SFTP_SOURCE, business_date):
        if inbox_path.is_file():
            return PullResult(
                business_date=business_date,
                status=RunStatus.SKIPPED,
                local_path=inbox_path,
                row_count=store.get_run(TOAST_SFTP_SOURCE, business_date).row_count,
                message="Already ingested; file present in inbox",
                skipped=True,
            )

    staging = paths.toast_pos_inbox / f".staging_{yyyymmdd}.csv"
    try:
        downloader.download_item_selection(business_date, staging)
    except FileNotFoundError as exc:
        store.upsert_run(
            source=TOAST_SFTP_SOURCE,
            business_date=business_date,
            filename=None,
            file_sha256=None,
            status=RunStatus.FAILED,
            error_message=str(exc),
        )
        return PullResult(
            business_date=business_date,
            status=RunStatus.FAILED,
            local_path=None,
            row_count=None,
            message=f"Remote file not found for {yyyymmdd}",
        )
    except OSError as exc:
        store.upsert_run(
            source=TOAST_SFTP_SOURCE,
            business_date=business_date,
            filename=None,
            file_sha256=None,
            status=RunStatus.FAILED,
            error_message=str(exc),
        )
        _move_to_failed(staging, paths, yyyymmdd)
        return PullResult(
            business_date=business_date,
            status=RunStatus.FAILED,
            local_path=None,
            row_count=None,
            message=str(exc),
        )

    file_hash = _sha256(staging)
    existing = store.get_run(TOAST_SFTP_SOURCE, business_date)
    if (
        skip_if_unchanged
        and existing
        and existing.status == RunStatus.SUCCESS
        and existing.file_sha256 == file_hash
        and inbox_path.is_file()
    ):
        staging.unlink(missing_ok=True)
        return PullResult(
            business_date=business_date,
            status=RunStatus.SKIPPED,
            local_path=inbox_path,
            row_count=existing.row_count,
            message="Remote file unchanged",
            skipped=True,
        )

    try:
        row_count = len(
            list(ToastItemSelectionDetailsCsvAdapter(pos_sales_path=staging).pos_sales())
        )
    except Exception as exc:
        store.upsert_run(
            source=TOAST_SFTP_SOURCE,
            business_date=business_date,
            filename=staging.name,
            file_sha256=file_hash,
            status=RunStatus.FAILED,
            error_message=f"Parse error: {exc}",
        )
        _move_to_failed(staging, paths, yyyymmdd)
        return PullResult(
            business_date=business_date,
            status=RunStatus.FAILED,
            local_path=None,
            row_count=None,
            message=f"Parse error: {exc}",
        )

    staging.replace(inbox_path)
    if copy_to_canonical:
        canonical_dir = paths.toast_pos_canonical_dir(
            business_date.year, store.location_id
        )
        canonical_dir.mkdir(parents=True, exist_ok=True)
        canonical_path = canonical_dir / paths.canonical_filename(date_key)
        shutil.copy2(inbox_path, canonical_path)

    archive_dir = paths.toast_pos_archive / yyyymmdd
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / inbox_name
    shutil.copy2(inbox_path, archive_path)

    store.upsert_run(
        source=TOAST_SFTP_SOURCE,
        business_date=business_date,
        filename=inbox_name,
        file_sha256=file_hash,
        status=RunStatus.SUCCESS,
        row_count=row_count,
    )

    return PullResult(
        business_date=business_date,
        status=RunStatus.SUCCESS,
        local_path=inbox_path,
        row_count=row_count,
        message=f"Pulled {row_count} sales rows",
    )


def pull_recent_days(
    *,
    downloader: SftpDownloader,
    days: int = 7,
    end_date: date | None = None,
    paths: IngestPaths | None = None,
    store: IngestionRunStore | None = None,
    skip_if_unchanged: bool = True,
) -> list[PullResult]:
    """Attempt to pull each of the last ``days`` business-date folders on SFTP."""
    end = end_date or (date.today() - timedelta(days=1))
    start = end - timedelta(days=days - 1)
    export_id = getattr(downloader, "export_id", None) or getattr(
        getattr(downloader, "config", None), "export_id", None
    )
    if export_id and hasattr(downloader, "list_business_dates"):
        available = set(downloader.list_business_dates(export_id))
    else:
        available = None

    results: list[PullResult] = []
    current = start
    while current <= end:
        if available is not None and current not in available:
            results.append(
                PullResult(
                    business_date=current,
                    status=RunStatus.SKIPPED,
                    local_path=None,
                    row_count=None,
                    message="Not listed on SFTP (outside 7-day window or not exported)",
                    skipped=True,
                )
            )
        else:
            results.append(
                pull_item_selection(
                    business_date=current,
                    downloader=downloader,
                    paths=paths,
                    store=store,
                    skip_if_unchanged=skip_if_unchanged,
                )
            )
        current += timedelta(days=1)
    return results


def pull_from_config(
    *,
    config: ToastSftpConfig,
    business_date: date | None = None,
    days: int | None = None,
    end_date: date | None = None,
    paths: IngestPaths | None = None,
    skip_if_unchanged: bool = True,
) -> list[PullResult]:
    from pantry_engine.ingest.toast_sftp.downloader import get_toast_downloader

    client = get_toast_downloader(config)
    if business_date is not None:
        return [
            pull_item_selection(
                business_date=business_date,
                downloader=client,
                paths=paths,
                skip_if_unchanged=skip_if_unchanged,
            )
        ]
    return pull_recent_days(
        downloader=client,
        days=days or 7,
        end_date=end_date,
        paths=paths,
        skip_if_unchanged=skip_if_unchanged,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _move_to_failed(staging: Path, paths: IngestPaths, yyyymmdd: str) -> None:
    if not staging.is_file():
        return
    failed_dir = paths.toast_pos_failed / yyyymmdd
    failed_dir.mkdir(parents=True, exist_ok=True)
    dest = failed_dir / staging.name
    shutil.move(str(staging), str(dest))
