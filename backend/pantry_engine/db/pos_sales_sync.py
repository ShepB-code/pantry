from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from pantry_engine.db.models import MenuItemRecord, PosSalesDailyRecord
from pantry_engine.db.seed import default_location_id
from pantry_engine.ingestion import ToastItemSelectionDetailsCsvAdapter


def ingest_menu_item_export_file(
    session: Session,
    *,
    csv_path: Path,
    location_id: str | None = None,
) -> dict:
    """Upsert Toast menu items from MenuItem_Export.csv.

    This is the stable menu item database (contains POS Item ID even for items that
    may not appear in a given sales window).
    """
    import pantry_eda

    location_id = location_id or default_location_id()
    df = pantry_eda.read_toast_menu_item_export(csv_path)
    now = datetime.now(timezone.utc)
    upserted = 0
    for _, row in df.iterrows():
        mid = str(row.get("item_id") or "").strip()
        if not mid:
            continue
        name = str(row.get("name") or mid).strip()
        archived = str(row.get("archived") or "").lower() in ("yes", "true", "1")
        # Keep archived items in the DB; they can still be referenced by recipes/history.
        existing = session.get(MenuItemRecord, {"location_id": location_id, "id": mid})
        if existing:
            existing.name = name
            existing.updated_at = now
            existing.category = existing.category  # unchanged (POS export doesn't include sales category)
            existing.menu_group = ("Archived" if archived else None)
        else:
            session.add(
                MenuItemRecord(
                    location_id=location_id,
                    id=mid,
                    name=name,
                    category=None,
                    menu_group=("Archived" if archived else None),
                    updated_at=now,
                )
            )
        upserted += 1
    session.commit()
    return {"menuItemsUpserted": upserted}


def ingest_item_selection_file_all_dates(
    session: Session,
    *,
    csv_path: Path,
    location_id: str | None = None,
) -> dict:
    """Ingest a Toast ItemSelectionDetails export that may contain many days.

    Upserts `menu_items` and writes `pos_sales_daily` for each business_date present in
    the file (overwriting existing rows for those dates).
    """
    location_id = location_id or default_location_id()
    sales = ToastItemSelectionDetailsCsvAdapter(pos_sales_path=csv_path).pos_sales()
    if not sales:
        return {"file": str(csv_path), "days": 0, "menuItems": 0, "salesLines": 0}

    # business_date -> mid -> aggregates
    daily_by_date: dict[date, dict[str, dict]] = defaultdict(
        lambda: defaultdict(lambda: {"quantity": 0.0})
    )
    menu_by_mid: dict[str, dict] = {}

    for sale in sales:
        if sale.business_date is None:
            continue
        mid = sale.menu_item_id
        if mid not in menu_by_mid:
            menu_by_mid[mid] = {
                "name": sale.menu_item_name or mid,
                "category": sale.sales_category,
                "menu_group": sale.menu_group,
            }
        bucket = daily_by_date[sale.business_date][mid]
        bucket["quantity"] += sale.quantity

    now = datetime.now(timezone.utc)
    # Upsert menu items once.
    for mid, info in menu_by_mid.items():
        existing = session.get(MenuItemRecord, {"location_id": location_id, "id": mid})
        if existing:
            existing.name = info["name"]
            existing.category = info["category"]
            existing.menu_group = info["menu_group"]
            existing.updated_at = now
        else:
            session.add(
                MenuItemRecord(
                    location_id=location_id,
                    id=mid,
                    name=info["name"],
                    category=info["category"],
                    menu_group=info["menu_group"],
                    updated_at=now,
                )
            )

    # Overwrite daily rollups for each date present.
    for biz_date, by_mid in daily_by_date.items():
        session.execute(
            delete(PosSalesDailyRecord).where(
                PosSalesDailyRecord.location_id == location_id,
                PosSalesDailyRecord.business_date == biz_date,
            )
        )
        for mid, bucket in by_mid.items():
            session.add(
                PosSalesDailyRecord(
                    location_id=location_id,
                    business_date=biz_date,
                    menu_item_id=mid,
                    quantity=bucket["quantity"],
                    ingested_at=now,
                )
            )

    session.commit()
    return {
        "file": str(csv_path),
        "days": len(daily_by_date),
        "menuItems": len(menu_by_mid),
        "salesLines": len(sales),
        "menuItemsSold": sum(len(m) for m in daily_by_date.values()),
    }


def ingest_item_selection_file(
    session: Session,
    *,
    csv_path: Path,
    business_date: date,
    location_id: str | None = None,
) -> dict:
    """Parse Toast ItemSelectionDetails CSV and upsert menu + daily sales for one day."""
    location_id = location_id or default_location_id()
    sales = [
        s
        for s in ToastItemSelectionDetailsCsvAdapter(pos_sales_path=csv_path).pos_sales()
        if s.business_date == business_date
    ]

    menu_agg: dict[str, dict] = {}
    daily_agg: dict[str, dict] = defaultdict(lambda: {"quantity": 0.0})

    for sale in sales:
        mid = sale.menu_item_id
        if mid not in menu_agg:
            menu_agg[mid] = {
                "name": sale.menu_item_name or mid,
                "category": sale.sales_category,
                "menu_group": sale.menu_group,
            }
        bucket = daily_agg[mid]
        bucket["quantity"] += sale.quantity

    now = datetime.now(timezone.utc)
    for mid, info in menu_agg.items():
        existing = session.get(MenuItemRecord, {"location_id": location_id, "id": mid})
        if existing:
            existing.name = info["name"]
            existing.category = info["category"]
            existing.menu_group = info["menu_group"]
            existing.updated_at = now
        else:
            session.add(
                MenuItemRecord(
                    location_id=location_id,
                    id=mid,
                    name=info["name"],
                    category=info["category"],
                    menu_group=info["menu_group"],
                    updated_at=now,
                )
            )

    session.execute(
        delete(PosSalesDailyRecord).where(
            PosSalesDailyRecord.location_id == location_id,
            PosSalesDailyRecord.business_date == business_date,
        )
    )

    for mid, bucket in daily_agg.items():
        session.add(
            PosSalesDailyRecord(
                location_id=location_id,
                business_date=business_date,
                menu_item_id=mid,
                quantity=bucket["quantity"],
                ingested_at=now,
            )
        )

    session.commit()
    return {
        "businessDate": business_date.isoformat(),
        "menuItems": len(menu_agg),
        "salesLines": len(sales),
        "menuItemsSold": len(daily_agg),
    }
