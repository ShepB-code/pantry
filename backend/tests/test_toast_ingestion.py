from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pantry_engine.ingestion import ToastItemSelectionDetailsCsvAdapter


class ToastItemSelectionDetailsCsvAdapterTest(unittest.TestCase):
    def test_reads_item_selection_details_and_skips_voids(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "item_selection_details.csv"
            path.write_text(
                "\n".join(
                    [
                        "Order #,Sent Date,Menu Item,Menu Group,Menu,Sales Category,Net Price,Qty,Void?",
                        "1,4/1/26 5:02 PM,Mountain Valley Spring,NA BEV,BEV,NA Beverage,10.00,1.0,false",
                        "2,4/1/26 5:04 PM,Noriko Oyster,STARTERS,FOOD,Food,30.00,5.0,true",
                        "3,4/1/26 5:05 PM,Gift Card,,,,100.00,1.0,false",
                    ]
                )
            )

            sales = list(ToastItemSelectionDetailsCsvAdapter(pos_sales_path=path).pos_sales())

        self.assertEqual(len(sales), 1)
        self.assertEqual(sales[0].business_date, date(2026, 4, 1))
        self.assertEqual(sales[0].menu_item_id, "mountain_valley_spring")
        self.assertEqual(sales[0].menu_item_name, "Mountain Valley Spring")
        self.assertEqual(sales[0].menu_group, "NA BEV")
        self.assertEqual(sales[0].quantity, 1.0)
        self.assertEqual(sales[0].revenue, 10.0)

    def test_can_include_uncategorized_rows_when_needed(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "item_selection_details.csv"
            path.write_text(
                "\n".join(
                    [
                        "Order #,Sent Date,Menu Item,Menu Group,Menu,Sales Category,Net Price,Qty,Void?",
                        "3,4/1/26 5:05 PM,Gift Card,,,,100.00,1.0,false",
                    ]
                )
            )

            sales = list(
                ToastItemSelectionDetailsCsvAdapter(
                    pos_sales_path=path,
                    include_uncategorized=True,
                ).pos_sales()
            )

        self.assertEqual(len(sales), 1)
        self.assertEqual(sales[0].menu_item_id, "gift_card")


if __name__ == "__main__":
    unittest.main()
