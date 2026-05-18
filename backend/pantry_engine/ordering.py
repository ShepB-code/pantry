from __future__ import annotations

import math
from collections import defaultdict

from pantry_engine.domain import (
    IngredientDemand,
    MenuItemForecast,
    OrderRecommendation,
    RecipeLine,
    SupplierRule,
)


def forecast_ingredient_demand(
    *,
    menu_forecasts: list[MenuItemForecast],
    recipes: list[RecipeLine],
) -> list[IngredientDemand]:
    recipes_by_menu_item: dict[str, list[RecipeLine]] = defaultdict(list)
    for recipe in recipes:
        recipes_by_menu_item[recipe.menu_item_id].append(recipe)

    demand: dict[str, float] = defaultdict(float)
    for forecast in menu_forecasts:
        for recipe in recipes_by_menu_item.get(forecast.menu_item_id, []):
            demand[recipe.ingredient_id] += recipe.ingredient_quantity_for(forecast.expected_quantity)

    return [
        IngredientDemand(ingredient_id=ingredient_id, expected_quantity=round(quantity, 2))
        for ingredient_id, quantity in sorted(demand.items())
    ]


def recommend_orders(
    *,
    ingredient_demand: list[IngredientDemand],
    inventory: dict[str, float],
    supplier_rules: list[SupplierRule],
) -> list[OrderRecommendation]:
    rules_by_ingredient = {rule.ingredient_id: rule for rule in supplier_rules}
    recommendations: list[OrderRecommendation] = []

    for demand in ingredient_demand:
        rule = rules_by_ingredient.get(demand.ingredient_id)
        pack_size = rule.pack_size if rule else 1
        minimum_order = rule.minimum_order if rule else 0
        safety_stock = rule.safety_stock if rule else 0
        on_hand = inventory.get(demand.ingredient_id, 0)
        needed = demand.expected_quantity + safety_stock - on_hand

        if needed <= 0:
            quantity = 0
            reason = "On hand inventory covers forecast demand and safety stock."
        else:
            quantity = _round_up_to_pack(max(needed, minimum_order), pack_size)
            reason = "Forecast demand exceeds on hand inventory after safety stock."

        recommendations.append(
            OrderRecommendation(
                ingredient_id=demand.ingredient_id,
                expected_demand=demand.expected_quantity,
                on_hand=on_hand,
                recommended_quantity=quantity,
                pack_size=pack_size,
                reason=reason,
            )
        )

    return recommendations


def _round_up_to_pack(quantity: float, pack_size: float) -> float:
    if pack_size <= 0:
        return quantity
    return math.ceil(quantity / pack_size) * pack_size
