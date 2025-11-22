import datetime
import unittest
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import patch

from reconciliations import BudgetSheetConfig, ExpenseRecord, ReconciliationSession

from cli import (
    _check_income_flags,
    _check_recurring_expectations,
)


class CliValidationTest(unittest.TestCase):

    def _build_session(
        self,
        recurring: Optional[Dict[str, float]] = None,
        expenses: Optional[List[ExpenseRecord]] = None,
    ) -> ReconciliationSession:
        config = BudgetSheetConfig(
            workbook_path=Path("budget.xlsx"),
            month="2025-07",
            recurring_expectations=recurring or {},
        )
        return ReconciliationSession(config)

    def test_recurring_validation_prompts_when_missing(self) -> None:
        session = self._build_session(
            recurring={"rent": 100.0},
        )
        session.expenses.append(
            ExpenseRecord(
                date=datetime.date(2025, 7, 1),
                description="Rent",
                amount=50.0,
                recurring_key="rent",
            )
        )

        with patch("cli.click.confirm", return_value=True) as prompt:
            self.assertTrue(_check_recurring_expectations(session))
            prompt.assert_called_once()

    def test_recurring_validation_aborts_when_declined(self) -> None:
        session = self._build_session(
            recurring={"rent": 100.0},
        )
        session.expenses.append(
            ExpenseRecord(
                date=datetime.date(2025, 7, 1),
                description="Rent",
                amount=50.0,
                recurring_key="rent",
            )
        )

        with patch("cli.click.confirm", return_value=False):
            self.assertFalse(_check_recurring_expectations(session))

    def test_recurring_validation_passes_when_satisfied(self) -> None:
        session = self._build_session(
            recurring={"rent": 100.0},
        )
        session.expenses.append(
            ExpenseRecord(
                date=datetime.date(2025, 7, 1),
                description="Rent",
                amount=100.0,
                recurring_key="rent",
            )
        )
        self.assertTrue(_check_recurring_expectations(session))

    def test_income_validation_fails_for_positive_amounts(self) -> None:
        session = self._build_session()
        session.expenses.append(
            ExpenseRecord(
                date=datetime.date(2025, 7, 2),
                description="Refund",
                amount=30.0,
                is_income=True,
            )
        )
        self.assertFalse(_check_income_flags(session))

    def test_income_validation_passes_for_negative_amounts(self) -> None:
        session = self._build_session()
        session.expenses.append(
            ExpenseRecord(
                date=datetime.date(2025, 7, 2),
                description="Refund",
                amount=-30.0,
                is_income=True,
            )
        )
        self.assertTrue(_check_income_flags(session))
