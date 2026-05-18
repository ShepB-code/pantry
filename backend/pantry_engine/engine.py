from __future__ import annotations

from datetime import date

from pantry_engine.domain import (
    Ingredient,
    IngredientDemand,
    MenuItem,
    MenuItemForecast,
    OrderRecommendation,
    RecipeLine,
    SupplierRule,
)
from pantry_engine.features import build_daily_features
from pantry_engine.forecasting import BaselineDemandForecaster
from pantry_engine.ingestion import DataSource
from pantry_engine.ordering import forecast_ingredient_demand, recommend_orders


class PantryEngine:
    def __init__(
        self,
        *,
        menu_items: list[MenuItem],
        ingredients: list[Ingredient],
        recipes: list[RecipeLine],
        supplier_rules: list[SupplierRule],
        forecaster: BaselineDemandForecaster | None = None,
    ) -> None:
        self.menu_items = menu_items
        self.ingredients = ingredients
        self.recipes = recipes
        self.supplier_rules = supplier_rules
        self.forecaster = forecaster or BaselineDemandForecaster()

    def forecast_menu_demand(
        self,
        *,
        data_source: DataSource,
        start: date,
        days: int,
    ) -> list[MenuItemForecast]:
        features = build_daily_features(
            reservations=list(data_source.reservations()),
            weather=list(data_source.weather()),
            events=list(data_source.events()),
            start=start,
            days=days,
        )
        return self.forecaster.forecast(
            menu_items=self.menu_items,
            sales_history=list(data_source.pos_sales()),
            features=features,
        )

    def forecast_ingredient_demand(
        self,
        *,
        data_source: DataSource,
        start: date,
        days: int,
    ) -> list[IngredientDemand]:
        menu_forecasts = self.forecast_menu_demand(
            data_source=data_source,
            start=start,
            days=days,
        )
        return forecast_ingredient_demand(
            menu_forecasts=menu_forecasts,
            recipes=self.recipes,
        )

    def recommend_orders(
        self,
        *,
        data_source: DataSource,
        inventory: dict[str, float],
        start: date,
        days: int,
    ) -> list[OrderRecommendation]:
        ingredient_demand = self.forecast_ingredient_demand(
            data_source=data_source,
            start=start,
            days=days,
        )
        return recommend_orders(
            ingredient_demand=ingredient_demand,
            inventory=inventory,
            supplier_rules=self.supplier_rules,
        )
