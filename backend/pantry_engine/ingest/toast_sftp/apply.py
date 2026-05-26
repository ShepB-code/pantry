from __future__ import annotations

from datetime import date
from pathlib import Path

from pantry_engine.db.depletion import apply_sales_depletion
from pantry_engine.db.pos_sales_sync import ingest_item_selection_file
from pantry_engine.db.seed import default_location_id
from pantry_engine.db.session import get_session_factory
from pantry_engine.ingest.paths import IngestPaths


def apply_pulled_sales(
    business_date: date,
    *,
    paths: IngestPaths | None = None,
    location_id: str | None = None,
    apply_depletion: bool = True,
) -> dict:
    """Ingest inbox CSV for a business date and optionally deplete inventory."""
    paths = paths or IngestPaths.from_repo()
    location_id = location_id or default_location_id()
    csv_path = paths.toast_pos_inbox / paths.inbox_filename(business_date.isoformat())
    if not csv_path.is_file():
        raise FileNotFoundError(
            f"No pulled file for {business_date.isoformat()}: expected {csv_path}"
        )

    factory = get_session_factory()
    with factory() as session:
        ingest_result = ingest_item_selection_file(
            session,
            csv_path=csv_path,
            business_date=business_date,
            location_id=location_id,
        )
        depletion_result = None
        if apply_depletion:
            depletion_result = apply_sales_depletion(
                session,
                business_date=business_date,
                location_id=location_id,
            )

    return {
        "ingest": ingest_result,
        "depletion": depletion_result,
        "file": str(csv_path),
    }
