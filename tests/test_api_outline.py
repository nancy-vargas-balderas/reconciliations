import datetime
import tempfile
import unittest
from pathlib import Path

from reconciliations import (
    BudgetSheetConfig,
    BudgetSheetWriter,
    ExpenseRecord,
    ReconciliationSession,
)


class ReconciliationSessionTest(unittest.TestCase):

    def test_session_bootstraps(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = BudgetSheetConfig(
                workbook_path=Path(tmpdir) / "budget.xlsx",
                month="2025-05",
            )
            session = ReconciliationSession(config)
            self.assertEqual(session.config.month, "2025-05")
            self.assertEqual(session.expenses, [])

        record = ExpenseRecord(
            date=datetime.date.today(),
            description="Sample expense",
            amount=42.50,
        )
        session.classify_expense(record, "Utilities")
        self.assertEqual(record.category, "Utilities")

    def test_budget_writer_creates_sheet(self) -> None:
        tmp_file = tempfile.NamedTemporaryFile(prefix="budget_", suffix=".xlsx", delete=False)
        tmp_path = Path(tmp_file.name)
        tmp_file.close()

        try:
            writer = BudgetSheetWriter(tmp_path)
            record = ExpenseRecord(
                date=datetime.date(2025, 5, 1),
                description="Rent",
                amount=1500.00,
                category="Housing",
            )
            writer.populate([record], "2025-05")
            self.assertTrue(tmp_path.exists())
        finally:
            tmp_path.unlink(missing_ok=True)
