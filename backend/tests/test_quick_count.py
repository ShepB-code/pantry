import unittest
from datetime import date

from pantry_engine.quick_count import (
    build_quick_count_items,
    evaluate_submission,
    resolve_actual_count,
)


class QuickCountTest(unittest.TestCase):
    def test_build_returns_bounded_list(self) -> None:
        items = build_quick_count_items(max_items=8)
        self.assertGreater(len(items), 0)
        self.assertLessEqual(len(items), 8)
        first = items[0]
        self.assertIn("id", first)
        self.assertIn("expectedOnHand", first)
        self.assertIn("countUnits", first)
        self.assertIn("estimate", first["countUnits"])

    def test_evaluate_submission_flags_variance(self) -> None:
        result = evaluate_submission(
            expected=10.0,
            par=12.0,
            actual=20.0,
            category="Produce",
        )
        self.assertTrue(result["flagged"])
        self.assertTrue(result["flags"]["countMismatch"])

    def test_resolve_estimate_modes(self) -> None:
        low = resolve_actual_count(expected=8, par=12, mode="estimate", value="low")
        self.assertAlmostEqual(low, 12 * 0.33)
        ok = resolve_actual_count(expected=8, par=12, mode="estimate", value="ok")
        self.assertAlmostEqual(ok, 12.0)


if __name__ == "__main__":
    unittest.main()
