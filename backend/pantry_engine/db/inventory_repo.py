from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from pantry_engine.db.models import InventoryItemRecord
from pantry_engine.db.seed import default_location_id
from pantry_engine.db.session import get_session_factory


class InventoryRepository:
    def __init__(
        self,
        *,
        location_id: str | None = None,
        session_factory=None,
    ) -> None:
        self.location_id = location_id or default_location_id()
        self._session_factory = session_factory or get_session_factory()

    def on_hand_map(self) -> dict[str, float]:
        with self._session_factory() as session:
            rows = session.execute(
                select(InventoryItemRecord).where(
                    InventoryItemRecord.location_id == self.location_id
                )
            ).scalars()
            return {row.id: row.on_hand for row in rows}

    def par_overrides_map(self) -> dict[str, float]:
        """Explicit par levels set in DB (UI or API); quick count uses defaults otherwise."""
        with self._session_factory() as session:
            rows = session.execute(
                select(InventoryItemRecord).where(
                    InventoryItemRecord.location_id == self.location_id,
                    InventoryItemRecord.par_level.is_not(None),
                )
            ).scalars()
            return {row.id: float(row.par_level) for row in rows}

    def list_items(self) -> list[dict]:
        with self._session_factory() as session:
            rows = session.execute(
                select(InventoryItemRecord)
                .where(InventoryItemRecord.location_id == self.location_id)
                .order_by(InventoryItemRecord.name)
            ).scalars()
            return [_item_to_dict(row) for row in rows]

    def get_item(self, item_id: str) -> InventoryItemRecord | None:
        with self._session_factory() as session:
            return session.get(
                InventoryItemRecord,
                {"location_id": self.location_id, "id": item_id},
            )

    def set_on_hand(
        self,
        item_id: str,
        on_hand: float,
        *,
        source: str = "quick_count",
    ) -> None:
        now = datetime.now(timezone.utc)
        with self._session_factory() as session:
            row = session.get(
                InventoryItemRecord,
                {"location_id": self.location_id, "id": item_id},
            )
            if row is None:
                raise KeyError(item_id)
            row.on_hand = on_hand
            row.last_count_source = source
            row.last_counted_at = now
            row.updated_at = now
            session.commit()

    def set_par_level(self, item_id: str, par_level: float) -> dict:
        now = datetime.now(timezone.utc)
        with self._session_factory() as session:
            row = session.get(
                InventoryItemRecord,
                {"location_id": self.location_id, "id": item_id},
            )
            if row is None:
                raise KeyError(item_id)
            row.par_level = par_level
            row.updated_at = now
            session.commit()
            session.refresh(row)
            return _item_to_dict(row)


def _item_to_dict(row: InventoryItemRecord) -> dict:
    par = row.par_level
    on_hand = row.on_hand
    status, status_color = _status_for(on_hand, par)
    return {
        "id": row.id,
        "name": row.name,
        "inventoryItem": row.catalog_name or row.name,
        "catalogSource": row.catalog_source or "xtrachef",
        "category": row.category or "Food",
        "unit": row.unit or "each",
        "vendor": row.vendor_name,
        "onHand": on_hand,
        "parLevel": par,
        "lastCountSource": row.last_count_source,
        "lastCountedAt": row.last_counted_at.isoformat() if row.last_counted_at else None,
        "status": status,
        "statusColor": status_color,
    }


def _status_for(on_hand: float, par: float | None) -> tuple[str, str]:
    if par is None or par <= 0:
        return "Good", "text-success"
    if on_hand < par * 0.5:
        return "Below par", "text-warning"
    if on_hand < par:
        return "Below par", "text-warning"
    if on_hand > par * 1.5:
        return "Overstocked", "text-info"
    return "Good", "text-success"
