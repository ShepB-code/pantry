from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class WeatherCondition(str, Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    SNOW = "snow"
    STORM = "storm"
    EXTREME_HEAT = "extreme_heat"
    EXTREME_COLD = "extreme_cold"


@dataclass(frozen=True)
class MenuItem:
    id: str
    name: str
    category: str | None = None


@dataclass(frozen=True)
class Ingredient:
    id: str
    name: str
    unit: str
    shelf_life_days: int | None = None


@dataclass(frozen=True)
class RecipeLine:
    menu_item_id: str
    ingredient_id: str
    quantity: float
    waste_factor: float = 0.0

    def ingredient_quantity_for(self, menu_quantity: float) -> float:
        return menu_quantity * self.quantity * (1 + self.waste_factor)


@dataclass(frozen=True)
class SupplierRule:
    ingredient_id: str
    pack_size: float
    minimum_order: float = 0.0
    lead_time_days: int = 0
    safety_stock: float = 0.0


@dataclass(frozen=True)
class POSSale:
    business_date: date
    menu_item_id: str
    quantity: float
    revenue: float | None = None
    source: str | None = None
    sent_at: datetime | None = None
    order_number: str | None = None
    menu_item_name: str | None = None
    menu_group: str | None = None
    menu: str | None = None
    sales_category: str | None = None


@dataclass(frozen=True)
class ReservationDemand:
    business_date: date
    covers: int
    party_count: int | None = None
    source: str | None = None


@dataclass(frozen=True)
class WeatherSignal:
    business_date: date
    condition: WeatherCondition
    high_temp_f: float | None = None
    low_temp_f: float | None = None
    precipitation_probability: float | None = None


@dataclass(frozen=True)
class EventSignal:
    business_date: date
    name: str
    expected_attendance: int | None = None
    category: str | None = None


@dataclass(frozen=True)
class DailyFeatures:
    business_date: date
    day_of_week: int
    reservation_covers: int = 0
    event_attendance: int = 0
    weather_condition: WeatherCondition | None = None
    precipitation_probability: float | None = None


@dataclass(frozen=True)
class MenuItemForecast:
    business_date: date
    menu_item_id: str
    expected_quantity: float
    baseline_quantity: float
    adjustment_factor: float


@dataclass(frozen=True)
class IngredientDemand:
    ingredient_id: str
    expected_quantity: float


@dataclass(frozen=True)
class OrderRecommendation:
    ingredient_id: str
    expected_demand: float
    on_hand: float
    recommended_quantity: float
    pack_size: float
    reason: str
