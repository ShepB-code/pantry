from __future__ import annotations

from datetime import date, datetime, timezone

import pandas as pd
from sqlalchemy.orm import Session

from pantry_engine.db.models import InventoryItemRecord
from pantry_engine.quick_count import (
    _dedupe_food_items,
    _default_par,
    _is_food_row,
    _normalize_uom,
)


def _parse_purchased_date(value: object) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _prepare_food_catalog(xchef: pd.DataFrame) -> pd.DataFrame:
    food = xchef[xchef.apply(_is_food_row, axis=1)].copy()
    food = _dedupe_food_items(food)
    if "last_purchased_date" in food.columns:
        food = food.sort_values(
            "last_purchased_date", ascending=False, na_position="last"
        )
    # Same item_description → same item_key; keep the newest row only.
    return food.drop_duplicates(subset=["item_key"], keep="first")


def _catalog_label(row: pd.Series) -> str:
    return str(row["item_description"])


def _apply_row_to_record(
    record: InventoryItemRecord,
    row: pd.Series,
    *,
    unit: str,
    now: datetime,
) -> None:
    label = _catalog_label(row)
    record.name = label
    record.catalog_name = label
    record.catalog_source = "xtrachef"
    record.category = str(row.get("category_group") or row.get("category") or "Food")
    record.unit = unit
    vendor = row.get("vendor_name")
    record.vendor_name = str(vendor) if pd.notna(vendor) else None
    record.item_code = str(row["item_code"]) if pd.notna(row.get("item_code")) else None
    price = row.get("last_purchased_price")
    record.last_purchased_price = float(price) if pd.notna(price) else None
    record.last_purchased_date = _parse_purchased_date(row.get("last_purchased_date"))
    record.catalog_updated_at = now
    record.updated_at = now


def upsert_xtrachef_catalog(
    session: Session,
    *,
    location_id: str,
    xchef: pd.DataFrame,
) -> tuple[int, int]:
    """Upsert food items from xtraCHEF. Returns (created, updated) counts."""
    food = _prepare_food_catalog(xchef)
    now = datetime.now(timezone.utc)
    created = 0
    updated = 0
    pending: dict[str, InventoryItemRecord] = {}

    for _, row in food.iterrows():
        item_id = str(row["item_key"])
        unit = _normalize_uom(row.get("uom") or row.get("item_uom"))
        existing = pending.get(item_id) or session.get(
            InventoryItemRecord, {"location_id": location_id, "id": item_id}
        )

        if existing:
            _apply_row_to_record(existing, row, unit=unit, now=now)
            updated += 1
            continue

        default_par = _default_par(row, unit)
        label = _catalog_label(row)
        record = InventoryItemRecord(
            location_id=location_id,
            id=item_id,
            name=label,
            catalog_name=label,
            catalog_source="xtrachef",
            category=str(row.get("category_group") or row.get("category") or "Food"),
            unit=unit,
            vendor_name=str(row["vendor_name"]) if pd.notna(row.get("vendor_name")) else None,
            item_code=str(row["item_code"]) if pd.notna(row.get("item_code")) else None,
            last_purchased_price=(
                float(row["last_purchased_price"])
                if pd.notna(row.get("last_purchased_price"))
                else None
            ),
            last_purchased_date=_parse_purchased_date(row.get("last_purchased_date")),
            on_hand=round(default_par * 0.85, 2),
            par_level=None,
            last_count_source="xtrachef_default",
            catalog_updated_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(record)
        pending[item_id] = record
        created += 1

    session.commit()
    return created, updated


def sync_xtrachef_from_exports(session: Session, location_id: str) -> tuple[int, int]:
    import pantry_eda

    try:
        return upsert_xtrachef_catalog(
            session,
            location_id=location_id,
            xchef=pantry_eda.read_xtrachef_item_library(),
        )
    except Exception:
        session.rollback()
        raise
