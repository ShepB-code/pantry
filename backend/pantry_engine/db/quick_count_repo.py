from __future__ import annotations

import json
from datetime import date, datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from pantry_engine.db.models import QuickCountLineRecord, QuickCountSessionRecord
from pantry_engine.db.seed import default_location_id
from pantry_engine.db.session import get_session_factory
from pantry_engine.quick_count import build_quick_count_items


class QuickCountRepository:
    def __init__(
        self,
        *,
        location_id: str | None = None,
        inventory_repo=None,
        session_factory=None,
    ) -> None:
        from pantry_engine.db.inventory_repo import InventoryRepository

        self.location_id = location_id or default_location_id()
        self._session_factory = session_factory or get_session_factory()
        self._inventory = inventory_repo or InventoryRepository(
            location_id=self.location_id,
            session_factory=self._session_factory,
        )

    def build_session_payload(self, *, session_date: date | None = None) -> dict:
        session_date = session_date or date.today()
        with self._session_factory() as session:
            qc_session = self._get_or_create_session(session, session_date)
            lines_by_item = self._lines_map(session, qc_session.id)
            completed_at = qc_session.completed_at
            session.commit()

        items = build_quick_count_items(
            inventory=self._inventory.on_hand_map(),
            par_overrides=self._inventory.par_overrides_map(),
            today=session_date,
        )

        for item in items:
            line = lines_by_item.get(item["id"])
            if line:
                line["name"] = item["name"]
                item["submitted"] = True
                item["actualOnHand"] = line["actual"]
                item["submittedFlags"] = line["flags"]
            else:
                item["submitted"] = False

        submitted = sum(1 for item in items if item.get("submitted"))
        return {
            "sessionDate": session_date.isoformat(),
            "completed": completed_at is not None,
            "completedAt": completed_at.isoformat() if completed_at else None,
            "estimatedMinutes": max(5, min(10, len(items))),
            "itemCount": len(items),
            "submittedCount": submitted,
            "items": items,
            "lines": list(lines_by_item.values()),
        }

    def submit_line(
        self,
        *,
        item_id: str,
        mode: str,
        unit: str,
        name: str,
        expected: float,
        actual: float,
        flagged: bool,
        flags: dict,
        session_date: date | None = None,
    ) -> dict:
        session_date = session_date or date.today()
        now = datetime.now(timezone.utc)
        with self._session_factory() as session:
            qc_session = self._get_or_create_session(session, session_date)
            if qc_session.completed_at is not None:
                raise ValueError("Quick count already completed for today")

            existing = session.execute(
                select(QuickCountLineRecord).where(
                    QuickCountLineRecord.session_id == qc_session.id,
                    QuickCountLineRecord.inventory_item_id == item_id,
                )
            ).scalar_one_or_none()

            flags_json = json.dumps(flags)
            if existing:
                existing.mode = mode
                existing.expected = expected
                existing.actual = actual
                existing.flags = flags_json
                existing.submitted_at = now
            else:
                session.add(
                    QuickCountLineRecord(
                        session_id=qc_session.id,
                        location_id=self.location_id,
                        inventory_item_id=item_id,
                        mode=mode,
                        expected=expected,
                        actual=actual,
                        flags=flags_json,
                        submitted_at=now,
                    )
                )
            session.commit()

        self._inventory.set_on_hand(item_id, actual, source="quick_count")
        line = {
            "itemId": item_id,
            "name": name,
            "mode": mode,
            "unit": unit,
            "expected": expected,
            "actual": actual,
            "flagged": flagged,
            "flags": flags,
            "submittedAt": now.isoformat(),
        }
        return {"line": line, "session": self.build_session_payload(session_date=session_date)}

    def reset_session(self, *, session_date: date | None = None) -> dict:
        session_date = session_date or date.today()
        with self._session_factory() as session:
            qc_session = self._get_or_create_session(session, session_date, force_reset=True)
            session.execute(
                delete(QuickCountLineRecord).where(
                    QuickCountLineRecord.session_id == qc_session.id
                )
            )
            qc_session.completed_at = None
            qc_session.submitted_count = 0
            session.commit()
        return self.build_session_payload(session_date=session_date)

    def complete_session(self, *, session_date: date | None = None) -> dict:
        session_date = session_date or date.today()
        payload = self.build_session_payload(session_date=session_date)
        if payload["submittedCount"] < payload["itemCount"]:
            raise ValueError("Submit all quick count items before completing")

        now = datetime.now(timezone.utc)
        with self._session_factory() as session:
            qc_session = self._get_or_create_session(session, session_date)
            qc_session.completed_at = now
            qc_session.submitted_count = payload["submittedCount"]
            qc_session.item_count = payload["itemCount"]
            session.commit()
        return self.build_session_payload(session_date=session_date)

    def _get_or_create_session(
        self,
        session: Session,
        session_date: date,
        *,
        force_reset: bool = False,
    ) -> QuickCountSessionRecord:
        record = session.execute(
            select(QuickCountSessionRecord).where(
                QuickCountSessionRecord.location_id == self.location_id,
                QuickCountSessionRecord.session_date == session_date,
            )
        ).scalar_one_or_none()

        if record and not force_reset:
            return record

        if record and force_reset:
            record.completed_at = None
            record.submitted_count = 0
            return record

        record = QuickCountSessionRecord(
            location_id=self.location_id,
            session_date=session_date,
            completed_at=None,
            item_count=None,
            submitted_count=0,
        )
        session.add(record)
        session.flush()
        return record

    def _lines_map(self, session: Session, session_id: int) -> dict[str, dict]:
        lines = session.execute(
            select(QuickCountLineRecord).where(
                QuickCountLineRecord.session_id == session_id
            )
        ).scalars()
        result: dict[str, dict] = {}
        for line in lines:
            flags = json.loads(line.flags) if line.flags else {}
            result[line.inventory_item_id] = {
                "itemId": line.inventory_item_id,
                "name": "",
                "mode": line.mode,
                "unit": "",
                "expected": line.expected,
                "actual": line.actual,
                "flagged": flags.get("countMismatch", False),
                "flags": flags,
                "submittedAt": line.submitted_at.isoformat(),
            }
        return result
