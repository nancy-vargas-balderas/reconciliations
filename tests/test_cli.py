import json
import tempfile
from datetime import date
from pathlib import Path
from typing import List, Optional
from unittest import TestCase
from unittest.mock import patch

import click
from click.testing import CliRunner

import cli as cli_module
from cli import _load_config, InteractiveClassificationSession, cli as reconciliation_cli
from reconciliations.api import BudgetSheetConfig, ReconciliationSession
from reconciliations.common import ExpenseRecord


class CliTests(TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)
        self.runner = CliRunner()
        self.readline_patcher = patch.object(cli_module, "readline", None)
        self.readline_patcher.start()

    def tearDown(self) -> None:
        self.readline_patcher.stop()
        self.tmp_dir.cleanup()

    def _build_session(
        self,
        *,
        categories: Optional[List[str]] = None,
        recurring: Optional[List[str]] = None,
    ) -> ReconciliationSession:
        config = BudgetSheetConfig(
            workbook_path=self.tmp_path / "budget.xlsx",
            month="2024-01",
            categories=categories or [],
            recurring_expenses=recurring or [],
        )
        return ReconciliationSession(config)

    def _write_config(self, payload: dict, name: str = "config.json") -> Path:
        path = self.tmp_path / name
        path.write_text(json.dumps(payload))
        return path

    def test_load_config_trims_values(self) -> None:
        config_path = self._write_config(
            {
                "categories": ["Food", "   "],
                "recurring_expenses": ["Rent", ""],
            }
        )

        categories, recurring = _load_config(config_path)

        self.assertEqual(["Food"], categories)
        self.assertEqual(["Rent"], recurring)

    def test_load_config_rejects_non_list_fields(self) -> None:
        for field in ("categories", "recurring_expenses"):
            with self.subTest(field=field):
                path = self._write_config({"dummy": "value"}, name=f"broken_{field}.json")
                path.write_text(json.dumps({field: "not a list"}))

                with self.assertRaises(click.BadParameter):
                    _load_config(path)

    def test_load_config_rejects_reserved_category(self) -> None:
        path = self._write_config({"categories": ["Income"]}, name="reserved.json")

        with self.assertRaises(click.BadParameter):
            _load_config(path)

    def test_prompt_category_is_case_insensitive(self) -> None:
        session = self._build_session(categories=["Groceries"])
        interactive = InteractiveClassificationSession(session)

        with patch("builtins.input", side_effect=["invalid", "groceries"]):
            self.assertEqual("Groceries", interactive._prompt_category())

    def test_prompt_recurring_key_requires_configuration(self) -> None:
        session = self._build_session()
        interactive = InteractiveClassificationSession(session)

        with self.assertRaises(click.BadParameter):
            interactive._prompt_recurring_key()

    def test_prompt_recurring_key_accepts_choice(self) -> None:
        session = self._build_session(recurring=["Rent"])
        interactive = InteractiveClassificationSession(session)

        with patch("builtins.input", side_effect=["", "rent"]):
            self.assertEqual("Rent", interactive._prompt_recurring_key())

    def test_cli_requires_csv_files(self) -> None:
        result = self.runner.invoke(
            reconciliation_cli,
            ["--workbook-path", str(self.tmp_path / "budget.xlsx"), "2024-01"],
        )

        self.assertEqual(2, result.exit_code)
        self.assertIn("At least one CSV file is required.", result.output)

    def test_classify_sets_flags_and_recurring_key(self) -> None:
        session = self._build_session(categories=["Groceries"], recurring=["Rent"])
        session.expenses = [
            ExpenseRecord(
                date=date(2024, 1, 1),
                description="Groceries",
                amount=10.0,
            ),
            ExpenseRecord(
                date=date(2024, 1, 2),
                description="Salary",
                amount=100.0,
            ),
            ExpenseRecord(
                date=date(2024, 1, 3),
                description="Loan Payment",
                amount=20.0,
            ),
            ExpenseRecord(
                date=date(2024, 1, 4),
                description="Misc Item",
                amount=5.0,
            ),
            ExpenseRecord(
                date=date(2024, 1, 5),
                description="Rent",
                amount=50.0,
            ),
        ]

        interactive = InteractiveClassificationSession(session)

        category_choices = iter(
            ["Groceries", "Income", "Payment", "Miscellaneous", "Recurring"]
        )
        interactive._prompt_category = lambda: next(category_choices)
        interactive._prompt_recurring_key = lambda: "Rent"

        interactive.classify()

        general, income, payment, misc, recurring = session.expenses

        self.assertEqual("Groceries", general.category)
        self.assertFalse(general.is_income)
        self.assertIsNone(general.recurring_key)

        self.assertEqual("Income", income.category)
        self.assertTrue(income.is_income)

        self.assertEqual("Payment", payment.category)
        self.assertTrue(payment.is_payment)

        self.assertEqual("Miscellaneous", misc.category)
        self.assertTrue(misc.is_misc)

        self.assertEqual("Recurring", recurring.category)
        self.assertEqual("Rent", recurring.recurring_key)
