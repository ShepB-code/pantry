from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from pantry_engine.db.models import LocationRecord


def default_location_id() -> str:
    return os.environ.get("PANTRY_DEFAULT_LOCATION_ID", "default").strip() or "default"


def default_location_name() -> str:
    return os.environ.get("PANTRY_DEFAULT_LOCATION_NAME", "Default Location").strip()


def ensure_default_location(session: Session, *, location_id: str | None = None) -> str:
    """Insert the configured default location if it does not exist."""
    loc_id = location_id or default_location_id()
    existing = session.get(LocationRecord, loc_id)
    if existing:
        return loc_id
    session.add(
        LocationRecord(
            id=loc_id,
            name=default_location_name(),
            timezone=os.environ.get("PANTRY_DEFAULT_TIMEZONE", "America/Chicago"),
        )
    )
    session.commit()
    return loc_id
