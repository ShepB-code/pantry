from datetime import date
import unittest

from pantry_engine import PantryEngine
from pantry_engine.domain import (
    EventSignal,
    Ingredient,
    MenuItem,
    POSSale,
    RecipeLine,
    ReservationDemand,
    SupplierRule,
    WeatherCondition,
    WeatherSignal,
)
from pantry_engine.ingestion import InMemoryDataSource


class PantryEngineTest(unittest.TestCase):
    def test_engine_recommends_orders_from_pos_reservations_weather_and_events(self) -> None:
        engine = PantryEngine(
            menu_items=[MenuItem(id="burger", name="Burger")],
            ingredients=[Ingredient(id="beef", name="Ground beef", unit="lb")],
            recipes=[RecipeLine(menu_item_id="burger", ingredient_id="beef", quantity=0.5)],
            supplier_rules=[
                SupplierRule(ingredient_id="beef", pack_size=10, minimum_order=10, safety_stock=5)
            ],
        )
        data_source = InMemoryDataSource(
            pos_sales=[
                POSSale(business_date=date(2026, 4, 30), menu_item_id="burger", quantity=40),
                POSSale(business_date=date(2026, 5, 7), menu_item_id="burger", quantity=60),
            ],
            reservations=[
                ReservationDemand(business_date=date(2026, 5, 14), covers=100, source="resy")
            ],
            weather=[
                WeatherSignal(
                    business_date=date(2026, 5, 14),
                    condition=WeatherCondition.CLEAR,
                )
            ],
            events=[
                EventSignal(
                    business_date=date(2026, 5, 14),
                    name="Arena show",
                    expected_attendance=1000,
                )
            ],
        )

        recommendations = engine.recommend_orders(
            data_source=data_source,
            inventory={"beef": 12},
            start=date(2026, 5, 14),
            days=1,
        )

        self.assertEqual(len(recommendations), 1)
        recommendation = recommendations[0]
        self.assertEqual(recommendation.ingredient_id, "beef")
        self.assertEqual(recommendation.expected_demand, 30.0)
        self.assertEqual(recommendation.recommended_quantity, 30)

    def test_engine_returns_zero_order_when_inventory_covers_demand(self) -> None:
        engine = PantryEngine(
            menu_items=[MenuItem(id="salad", name="Salad")],
            ingredients=[Ingredient(id="greens", name="Greens", unit="lb")],
            recipes=[RecipeLine(menu_item_id="salad", ingredient_id="greens", quantity=0.25)],
            supplier_rules=[SupplierRule(ingredient_id="greens", pack_size=5, safety_stock=2)],
        )
        data_source = InMemoryDataSource(
            pos_sales=[
                POSSale(business_date=date(2026, 5, 1), menu_item_id="salad", quantity=20),
            ],
            reservations=[],
            weather=[],
            events=[],
        )

        recommendations = engine.recommend_orders(
            data_source=data_source,
            inventory={"greens": 20},
            start=date(2026, 5, 8),
            days=1,
        )

        self.assertEqual(recommendations[0].expected_demand, 5)
        self.assertEqual(recommendations[0].recommended_quantity, 0)


if __name__ == "__main__":
    unittest.main()
