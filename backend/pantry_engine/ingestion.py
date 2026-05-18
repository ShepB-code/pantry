from __future__ import annotations

import csv
import re
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from pathlib import Path
from typing import Protocol

from pantry_engine.domain import EventSignal, POSSale, ReservationDemand, WeatherCondition, WeatherSignal


class DataSource(Protocol):
    def pos_sales(self) -> Iterable[POSSale]:
        ...

    def reservations(self) -> Iterable[ReservationDemand]:
        ...

    def weather(self) -> Iterable[WeatherSignal]:
        ...

    def events(self) -> Iterable[EventSignal]:
        ...


class InMemoryDataSource:
    def __init__(
        self,
        *,
        pos_sales: Iterable[POSSale],
        reservations: Iterable[ReservationDemand],
        weather: Iterable[WeatherSignal],
        events: Iterable[EventSignal],
    ) -> None:
        self._pos_sales = list(pos_sales)
        self._reservations = list(reservations)
        self._weather = list(weather)
        self._events = list(events)

    def pos_sales(self) -> Iterable[POSSale]:
        return self._pos_sales

    def reservations(self) -> Iterable[ReservationDemand]:
        return self._reservations

    def weather(self) -> Iterable[WeatherSignal]:
        return self._weather

    def events(self) -> Iterable[EventSignal]:
        return self._events


class CsvDataSource:
    """Reads normalized CSV exports until first-party API adapters exist."""

    def __init__(
        self,
        *,
        pos_sales_path: Path | None = None,
        reservations_path: Path | None = None,
        weather_path: Path | None = None,
        events_path: Path | None = None,
    ) -> None:
        self.pos_sales_path = pos_sales_path
        self.reservations_path = reservations_path
        self.weather_path = weather_path
        self.events_path = events_path

    def pos_sales(self) -> Iterable[POSSale]:
        if not self.pos_sales_path:
            return []
        return [
            POSSale(
                business_date=_parse_date(row["business_date"]),
                menu_item_id=row["menu_item_id"],
                quantity=float(row["quantity"]),
                revenue=_optional_float(row.get("revenue")),
                source=row.get("source"),
            )
            for row in _read_csv(self.pos_sales_path)
        ]

    def reservations(self) -> Iterable[ReservationDemand]:
        if not self.reservations_path:
            return []
        return [
            ReservationDemand(
                business_date=_parse_date(row["business_date"]),
                covers=int(row["covers"]),
                party_count=_optional_int(row.get("party_count")),
                source=row.get("source"),
            )
            for row in _read_csv(self.reservations_path)
        ]

    def weather(self) -> Iterable[WeatherSignal]:
        if not self.weather_path:
            return []
        return [
            WeatherSignal(
                business_date=_parse_date(row["business_date"]),
                condition=WeatherCondition(row["condition"]),
                high_temp_f=_optional_float(row.get("high_temp_f")),
                low_temp_f=_optional_float(row.get("low_temp_f")),
                precipitation_probability=_optional_float(row.get("precipitation_probability")),
            )
            for row in _read_csv(self.weather_path)
        ]

    def events(self) -> Iterable[EventSignal]:
        if not self.events_path:
            return []
        return [
            EventSignal(
                business_date=_parse_date(row["business_date"]),
                name=row["name"],
                expected_attendance=_optional_int(row.get("expected_attendance")),
                category=row.get("category"),
            )
            for row in _read_csv(self.events_path)
        ]


class ToastCsvAdapter(CsvDataSource):
    """Adapter for a simple Toast menu item sales export.

    Expected columns: Date, Menu Item ID, Qty, Gross Sales.
    """

    def pos_sales(self) -> Iterable[POSSale]:
        if not self.pos_sales_path:
            return []
        return [
            POSSale(
                business_date=_parse_date(row["Date"]),
                menu_item_id=row["Menu Item ID"],
                quantity=float(row["Qty"]),
                revenue=_optional_float(row.get("Gross Sales")),
                source="toast",
            )
            for row in _read_csv(self.pos_sales_path)
        ]


class ToastItemSelectionDetailsCsvAdapter(CsvDataSource):
    """Adapter for Toast Item Selection Details exports.

    Expected columns: Order #, Sent Date, Menu Item, Menu Group, Menu,
    Sales Category, Net Price, Qty, Void?.
    """

    def __init__(
        self,
        *,
        pos_sales_path: Path | None = None,
        include_uncategorized: bool = False,
    ) -> None:
        super().__init__(pos_sales_path=pos_sales_path)
        self.include_uncategorized = include_uncategorized

    def pos_sales(self) -> Iterable[POSSale]:
        if not self.pos_sales_path:
            return []

        sales: list[POSSale] = []
        for row in _read_csv(self.pos_sales_path):
            if _is_truthy(row.get("Void?")):
                continue
            if not self.include_uncategorized and not row.get("Sales Category"):
                continue

            sent_at = _parse_toast_datetime(row["Sent Date"])
            menu_item_name = row["Menu Item"].strip()
            quantity = float(row["Qty"])
            revenue = _optional_float(row.get("Net Price"))
            sales.append(
                POSSale(
                    business_date=sent_at.date(),
                    menu_item_id=_stable_id(menu_item_name),
                    quantity=quantity,
                    revenue=revenue,
                    source="toast",
                    sent_at=sent_at,
                    order_number=row.get("Order #"),
                    menu_item_name=menu_item_name,
                    menu_group=_blank_to_none(row.get("Menu Group")),
                    menu=_blank_to_none(row.get("Menu")),
                    sales_category=_blank_to_none(row.get("Sales Category")),
                )
            )

        return sales


class ReservationCsvAdapter(CsvDataSource):
    """Adapter for a simple reservation export.

    Expected columns: Date, Covers, Parties, Source.
    """

    def reservations(self) -> Iterable[ReservationDemand]:
        if not self.reservations_path:
            return []
        return [
            ReservationDemand(
                business_date=_parse_date(row["Date"]),
                covers=int(row["Covers"]),
                party_count=_optional_int(row.get("Parties")),
                source=row.get("Source"),
            )
            for row in _read_csv(self.reservations_path)
        ]


def _read_csv(path: Path) -> list[Mapping[str, str]]:
    with path.open(newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _parse_toast_datetime(value: str) -> datetime:
    for date_format in ("%m/%d/%y %I:%M %p", "%m/%d/%Y %I:%M %p"):
        try:
            return datetime.strptime(value, date_format)
        except ValueError:
            continue
    raise ValueError(f"Unsupported Toast datetime: {value}")


def _optional_float(value: str | None) -> float | None:
    return float(value) if value not in (None, "") else None


def _optional_int(value: str | None) -> int | None:
    return int(value) if value not in (None, "") else None


def _blank_to_none(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    return value


def _is_truthy(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"true", "t", "yes", "y", "1"}


def _stable_id(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return normalized or "unknown_item"
