from __future__ import annotations

from collections import defaultdict
from statistics import mean

from pantry_engine.domain import DailyFeatures, MenuItem, MenuItemForecast, POSSale, WeatherCondition


class BaselineDemandForecaster:
    """Transparent forecasting model for the first Pantry engine iteration."""

    def forecast(
        self,
        *,
        menu_items: list[MenuItem],
        sales_history: list[POSSale],
        features: list[DailyFeatures],
    ) -> list[MenuItemForecast]:
        averages = _day_of_week_menu_averages(sales_history)
        global_averages = _global_menu_averages(sales_history)

        forecasts: list[MenuItemForecast] = []
        for feature in features:
            for menu_item in menu_items:
                fallback = global_averages.get(menu_item.id, 0)
                baseline = averages.get((menu_item.id, feature.day_of_week), fallback)
                adjustment = _feature_adjustment(feature)
                forecasts.append(
                    MenuItemForecast(
                        business_date=feature.business_date,
                        menu_item_id=menu_item.id,
                        expected_quantity=round(baseline * adjustment, 2),
                        baseline_quantity=round(baseline, 2),
                        adjustment_factor=round(adjustment, 4),
                    )
                )
        return forecasts


def _day_of_week_menu_averages(sales_history: list[POSSale]) -> dict[tuple[str, int], float]:
    quantities: dict[tuple[str, int], list[float]] = defaultdict(list)
    by_date_and_item: dict[tuple[str, object], float] = defaultdict(float)
    for sale in sales_history:
        by_date_and_item[(sale.menu_item_id, sale.business_date)] += sale.quantity

    for (menu_item_id, business_date), quantity in by_date_and_item.items():
        quantities[(menu_item_id, business_date.weekday())].append(quantity)

    return {key: mean(values) for key, values in quantities.items()}


def _global_menu_averages(sales_history: list[POSSale]) -> dict[str, float]:
    quantities: dict[str, list[float]] = defaultdict(list)
    by_date_and_item: dict[tuple[str, object], float] = defaultdict(float)
    for sale in sales_history:
        by_date_and_item[(sale.menu_item_id, sale.business_date)] += sale.quantity

    for (menu_item_id, _business_date), quantity in by_date_and_item.items():
        quantities[menu_item_id].append(quantity)

    return {menu_item_id: mean(values) for menu_item_id, values in quantities.items()}


def _feature_adjustment(feature: DailyFeatures) -> float:
    adjustment = 1.0

    if feature.reservation_covers:
        adjustment += min(feature.reservation_covers / 1000, 0.35)

    if feature.event_attendance:
        adjustment += min(feature.event_attendance / 10000, 0.25)

    if feature.weather_condition in {WeatherCondition.RAIN, WeatherCondition.SNOW, WeatherCondition.STORM}:
        adjustment -= 0.08

    if feature.precipitation_probability and feature.precipitation_probability >= 0.7:
        adjustment -= 0.05

    if feature.weather_condition in {WeatherCondition.EXTREME_HEAT, WeatherCondition.EXTREME_COLD}:
        adjustment -= 0.04

    return max(adjustment, 0.2)
