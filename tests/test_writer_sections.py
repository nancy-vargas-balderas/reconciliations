import datetime
import tempfile
import unittest
from pathlib import Path

from reconciliations import BudgetSheetWriter, ExpenseRecord


class BudgetSheetWriterSectionsTest(unittest.TestCase):

    def _make_writer(self) -> BudgetSheetWriter:
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        path = Path(tmp.name)
        tmp.close()
        writer = BudgetSheetWriter(path)
        writer.target_path.unlink(missing_ok=True)
        return writer

    def test_sections_split_expenses(self) -> None:
        writer = self._make_writer()

        records = [
            ExpenseRecord(date=datetime.date.today(), description="Regular", amount=10.0),
            ExpenseRecord(
                date=datetime.date.today(), description="Income", amount=-50, is_income=True
            ),
            ExpenseRecord(
                date=datetime.date.today(), description="Misc", amount=5.0, is_misc=True
            ),
            ExpenseRecord(
                date=datetime.date.today(),
                description="Recurring",
                amount=20.0,
                recurring_key="rent",
            ),
        ]

        sections = writer._sectioned_expenses(records)
        self.assertEqual(sections[0][0], "Regular")
        self.assertEqual(len(sections[0][1]), 1)
        self.assertEqual(sections[1][0], "Income")
        self.assertEqual(len(sections[1][1]), 1)
        self.assertEqual(sections[2][0], "Miscellaneous")
        self.assertEqual(len(sections[2][1]), 1)
        self.assertEqual(sections[3][0], "Recurring")
        self.assertEqual(len(sections[3][1]), 1)
