from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.orm import Session

from pantry_engine.db.models import InventoryItemRecord
from pantry_engine.db.name_source import NAME_SOURCE_MANUAL, NAME_SOURCE_XTRACHEF


def _optional_str(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def _row_unit(row: pd.Series) -> str | None:
    return _optional_str(row.get("uom") or row.get("item_uom"))


def _row_category(row: pd.Series) -> str | None:
    return _optional_str(row.get("category_group") or row.get("category"))


def _catalog_rows(xchef: pd.DataFrame) -> pd.DataFrame:
    """Pass through xtraCHEF rows; one row per ``item_key`` (first occurrence)."""
    if xchef.empty or "item_key" not in xchef.columns:
        return xchef.iloc[0:0]
    return xchef.drop_duplicates(subset=["item_key"], keep="first")


def _apply_row_to_record(
    record: InventoryItemRecord,
    row: pd.Series,
    *,
    now: datetime,
) -> None:
    label = _optional_str(row.get("item_description")) or str(row["item_key"])
    record.catalog_name = label
    record.catalog_source = "xtrachef"
    if record.name_source != NAME_SOURCE_MANUAL:
        record.name = label
        record.name_source = NAME_SOURCE_XTRACHEF
    record.category = _row_category(row)
    record.unit = _row_unit(row)
    record.vendor_name = _optional_str(row.get("vendor_name"))
    record.updated_at = now


def upsert_xtrachef_catalog(
    session: Session,
    *,
    location_id: str,
    xchef: pd.DataFrame,
) -> tuple[int, int]:
    """Upsert xtraCHEF rows into inventory_items without transforming source values."""
    rows = _catalog_rows(xchef)
    now = datetime.now(timezone.utc)
    created = 0
    updated = 0
    pending: dict[str, InventoryItemRecord] = {}

    for _, row in rows.iterrows():
        item_id = str(row["item_key"])
        existing = pending.get(item_id) or session.get(
            InventoryItemRecord, {"location_id": location_id, "id": item_id}
        )

        if existing:
            _apply_row_to_record(existing, row, now=now)
            updated += 1
            continue

        label = _optional_str(row.get("item_description")) or item_id
        record = InventoryItemRecord(
            location_id=location_id,
            id=item_id,
            name=label,
            name_source=NAME_SOURCE_XTRACHEF,
            catalog_name=label,
            catalog_source="xtrachef",
            category=_row_category(row),
            unit=_row_unit(row),
            vendor_name=_optional_str(row.get("vendor_name")),
            on_hand=0.0,
            par_level=None,
            last_count_source="uninitialized",
            created_at=now,
            updated_at=now,
        )
        session.add(record)
        pending[item_id] = record
        created += 1

    session.commit()
    return created, updated


def sync_xtrachef_from_exports(session: Session, location_id: str) -> tuple[int, int]:
    from pantry_engine.api.pantry_eda import ensure_pantry_eda_path

    ensure_pantry_eda_path()
    import pantry_eda

    try:
        return upsert_xtrachef_catalog(
            session,
            location_id=location_id,
            xchef=pantry_eda.read_xtrachef_item_library(location_id=location_id),
        )
    except Exception:
        session.rollback()
        raise
