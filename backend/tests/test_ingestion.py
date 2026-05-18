from pathlib import Path
import unittest

from pantry_engine.domain import WeatherCondition
from pantry_engine.ingestion import CsvDataSource


class CsvDataSourceTest(unittest.TestCase):
    def test_csv_data_source_reads_normalized_exports(self) -> None:
        source = CsvDataSource(
            pos_sales_path=Path("examples/pos_sales.csv"),
            reservations_path=Path("examples/reservations.csv"),
            weather_path=Path("examples/weather.csv"),
            events_path=Path("examples/events.csv"),
        )

        self.assertEqual(len(list(source.pos_sales())), 14)
        self.assertEqual(sum(reservation.covers for reservation in source.reservations()), 346)
        self.assertEqual(list(source.weather())[1].condition, WeatherCondition.RAIN)
        self.assertEqual(list(source.events())[0].expected_attendance, 2400)


if __name__ == "__main__":
    unittest.main()
