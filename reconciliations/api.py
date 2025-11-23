from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, MutableMapping, Sequence

import csv

from .writer import BudgetSheetWriter
from .common import ExpenseRecord

@dataclass
class BudgetSheetConfig:
    """Capture the key configuration needed before editing a budget workbook."""

    workbook_path: Path
    month: str
    categories: Sequence[str] = field(default_factory=list)
    recurring_expenses: Sequence[str] = field(default_factory=list)


@dataclass
class RecurringCheckResult:
    """Summarize the state of the configured recurring expenses."""

    missing: MutableMapping[str, float]
    satisfied: MutableMapping[str, float]


class ReconciliationSession:
    """High-level orchestration for collecting and reconciling expenses."""

    def __init__(
        self,
        config: BudgetSheetConfig,
    ) -> None:
        self.config = config
        self.expenses: List[ExpenseRecord] = []

    def load_transactions(self, csv_files: Iterable[Path]) -> None:
        """Read the CSV inputs and expand the session's expense list."""

        for csv_path in csv_files:
            self.expenses.extend(self._parse_csv(csv_path))

    def _parse_csv(self, csv_path: Path) -> List[ExpenseRecord]:
        """Convert each row from the CSV into an expense record."""

        records: List[ExpenseRecord] = []
        with csv_path.open(newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                date_val = row.get("Date", "").strip()
                description = row.get("Description", "").strip()
                amount_val = row.get("Amount", "").strip()

                date_obj = self._parse_date(date_val)
                amount = self._parse_amount(amount_val)

                records.append(
                    ExpenseRecord(
                        date=date_obj,
                        description=description,
                        amount=amount,
                        source_file=csv_path,
                    )
                )

        return records

    @staticmethod
    def _parse_date(value: str) -> datetime.date:
        """Try to parse dates from the CSV (e.g., mm/dd/YYYY)."""

        for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Unable to parse date '{value}'")

    @staticmethod
    def _parse_amount(value: str) -> float:
        """Normalize numeric strings that may include commas or parentheses."""

        normalized = value.replace(",", "")
        if normalized.startswith("(") and normalized.endswith(")"):
            normalized = f"-{normalized[1:-1]}"

        return float(normalized)

    def write_budget_sheet(self) -> Path:
        """Persist the reconciliation results to the workbook."""

        writer = BudgetSheetWriter(self.config.workbook_path)
        writer.populate(self.expenses, self.config.month)
        return self.config.workbook_path


class PieChartBuilder:
    """Utility for constructing the optional pie chart reports."""

    def __init__(self, session: ReconciliationSession) -> None:
        self.session = session

    def generate(self) -> Path:
        """Build the chart data so it can be added to the workbook."""

        raise NotImplementedError("Pie chart generation is a future stretch goal.")
