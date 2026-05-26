from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from pantry_engine.db.models import MenuItemRecord, PosSalesDailyRecord
from pantry_engine.db.seed import default_location_id
from pantry_engine.ingestion import ToastItemSelectionDetailsCsvAdapter


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
    daily_agg: dict[str, dict] = defaultdict(
        lambda: {"quantity": 0.0, "revenue": 0.0, "orders": set()}
    )

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
        if sale.revenue is not None:
            bucket["revenue"] += sale.revenue
        if sale.order_number:
            bucket["orders"].add(sale.order_number)

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
                revenue=bucket["revenue"] or None,
                order_count=len(bucket["orders"]) or None,
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
