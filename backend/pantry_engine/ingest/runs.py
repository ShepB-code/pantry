from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path

from sqlalchemy import select

from pantry_engine.db.models import IngestionRunRecord
from pantry_engine.db.seed import default_location_id, ensure_default_location
from pantry_engine.db.session import get_session_factory, resolve_database_url


class RunStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class IngestionRun:
    id: int
    location_id: str
    source: str
    business_date: date
    filename: str | None
    file_sha256: str | None
    status: RunStatus
    row_count: int | None
    error_message: str | None
    created_at: datetime
    finished_at: datetime | None


class IngestionRunStore:
    """Persistence for ingestion attempts (PostgreSQL or SQLite)."""

    def __init__(
        self,
        db_target: Path | str | None = None,
        *,
        location_id: str | None = None,
        database_url: str | None = None,
    ) -> None:
        if database_url:
            url = database_url
        elif isinstance(db_target, str):
            url = db_target
        elif isinstance(db_target, Path):
            url = f"sqlite:///{db_target.resolve()}"
        else:
            url = resolve_database_url()

        from pantry_engine.db.session import init_db

        init_db(url)
        self._session_factory = get_session_factory(url)
        self.location_id = location_id or default_location_id()
        with self._session_factory() as session:
            ensure_default_location(session, location_id=self.location_id)

    def upsert_run(
        self,
        *,
        source: str,
        business_date: date,
        filename: str | None,
        file_sha256: str | None,
        status: RunStatus,
        row_count: int | None = None,
        error_message: str | None = None,
    ) -> IngestionRun:
        now = datetime.now(timezone.utc)
        with self._session_factory() as session:
            existing = session.execute(
                select(IngestionRunRecord).where(
                    IngestionRunRecord.location_id == self.location_id,
                    IngestionRunRecord.source == source,
                    IngestionRunRecord.business_date == business_date,
                )
            ).scalar_one_or_none()

            if existing:
                existing.filename = filename
                existing.file_sha256 = file_sha256
                existing.status = status.value
                existing.row_count = row_count
                existing.error_message = error_message
                existing.finished_at = now
                record = existing
            else:
                record = IngestionRunRecord(
                    location_id=self.location_id,
                    source=source,
                    business_date=business_date,
                    filename=filename,
                    file_sha256=file_sha256,
                    status=status.value,
                    row_count=row_count,
                    error_message=error_message,
                    created_at=now,
                    finished_at=now,
                )
                session.add(record)
            session.commit()
            session.refresh(record)
            return self._to_run(record)

    def get_run(self, source: str, business_date: date) -> IngestionRun | None:
        with self._session_factory() as session:
            record = session.execute(
                select(IngestionRunRecord).where(
                    IngestionRunRecord.location_id == self.location_id,
                    IngestionRunRecord.source == source,
                    IngestionRunRecord.business_date == business_date,
                )
            ).scalar_one_or_none()
        return self._to_run(record) if record else None

    def was_successful(self, source: str, business_date: date) -> bool:
        run = self.get_run(source, business_date)
        return run is not None and run.status == RunStatus.SUCCESS

    def list_runs(
        self,
        *,
        source: str | None = None,
        limit: int = 30,
    ) -> list[IngestionRun]:
        with self._session_factory() as session:
            query = (
                select(IngestionRunRecord)
                .where(IngestionRunRecord.location_id == self.location_id)
                .order_by(IngestionRunRecord.business_date.desc())
                .limit(limit)
            )
            if source:
                query = query.where(IngestionRunRecord.source == source)
            records = session.execute(query).scalars().all()
        return [self._to_run(record) for record in records]

    @staticmethod
    def _to_run(record: IngestionRunRecord) -> IngestionRun:
        return IngestionRun(
            id=record.id,
            location_id=record.location_id,
            source=record.source,
            business_date=record.business_date,
            filename=record.filename,
            file_sha256=record.file_sha256,
            status=RunStatus(record.status),
            row_count=record.row_count,
            error_message=record.error_message,
            created_at=record.created_at,
            finished_at=record.finished_at,
        )
