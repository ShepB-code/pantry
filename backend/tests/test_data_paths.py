import unittest

from pantry_engine.data_paths import pos_dir, pos_year_dir, xtrachef_dir


class DataPathsTest(unittest.TestCase):
    def test_perilla_paths(self) -> None:
        self.assertEqual(pos_dir("perilla").parts[-2:], ("pos", "perilla"))
        self.assertEqual(pos_year_dir(2026, "perilla").parts[-2:], ("2026", "perilla"))
        self.assertEqual(xtrachef_dir("perilla").parts[-2:], ("xtraCHEF", "perilla"))


if __name__ == "__main__":
    unittest.main()
