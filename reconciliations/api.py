from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, List, Mapping, MutableMapping, Optional, Sequence

from .writer import BudgetSheetWriter, SheetFormatKeeper


@dataclass
class BudgetSheetConfig:
    """Capture the key configuration needed before editing a budget workbook."""

    workbook_path: Path
    month: str
    categories: Sequence[str] = field(default_factory=list)
    recurring_expectations: Mapping[str, float] = field(default_factory=dict)
    prompt_user_before_commit: bool = True


@dataclass
class ExpenseRecord:
    """Represents a single transaction that needs reconciliation."""

    date: datetime.date
    description: str
    amount: float
    source_file: Optional[Path] = None
    category: Optional[str] = None
    is_income: bool = False
    is_misc: bool = False
    is_payment: bool = False
    recurring_key: Optional[str] = None


@dataclass
class RecurringCheckResult:
    """Summarize the state of the configured recurring expenses."""

    missing: MutableMapping[str, float]
    satisfied: MutableMapping[str, float]


ConfirmCallback = Callable[["BudgetSheetConfig"], bool]


class ReconciliationSession:
    """High-level orchestration for collecting and reconciling expenses."""

    def __init__(
        self,
        config: BudgetSheetConfig,
        confirm_callback: Optional[ConfirmCallback] = None,
    ) -> None:
        self.config = config
        self.expenses: List[ExpenseRecord] = []
        self.format_keeper = SheetFormatKeeper(config.workbook_path)
        self._confirm_callback = confirm_callback

    def confirm_budget_sheet(self) -> bool:
        """Confirm with the user before mutating the budget workbook."""

        if not self.config.prompt_user_before_commit:
            return True

        if not self._confirm_callback:
            raise RuntimeError(
                "No confirmation callback registered for budget sheet edits."
            )

        return self._confirm_callback(self.config)

    def load_transactions(self, csv_files: Iterable[Path]) -> None:
        """Read the CSV inputs and expand the session's expense list."""

        for csv_path in csv_files:
            self.expenses.append(
                ExpenseRecord(
                    date=datetime.date.today(),
                    description=f"Stub from {csv_path.name}",
                    amount=0.0,
                    source_file=csv_path,
                )
            )

    def classify_expense(self, record: ExpenseRecord, category: str) -> None:
        """Assign a category and track whether additional flags apply."""

        record.category = category

    def mark_as_income(self, record: ExpenseRecord) -> None:
        """Mark an expense that should actually be treated as income."""

        record.is_income = True
        record.is_misc = False
        record.is_payment = False

    def mark_as_miscellaneous(self, record: ExpenseRecord) -> None:
        """Flag high-impact miscellaneous expenses that break the regular pattern."""

        record.is_misc = True

    def mark_as_payment(self, record: ExpenseRecord) -> None:
        """Treat the transaction as a payment that should not affect totals."""

        record.is_payment = True

    def build_recurring_report(self) -> RecurringCheckResult:
        """Compare configured recurring targets with the loaded records."""

        missing: MutableMapping[str, float] = {}
        satisfied: MutableMapping[str, float] = {}
        for key, expected in self.config.recurring_expectations.items():
            satisfied[key] = 0.0
            missing[key] = expected
        return RecurringCheckResult(missing=missing, satisfied=satisfied)

    def write_budget_sheet(self) -> Path:
        """Persist the reconciliation results to the workbook."""

        writer = BudgetSheetWriter(self.format_keeper.get_template())
        writer.populate(self.expenses, self.config.month)
        return writer.target_path


class PieChartBuilder:
    """Utility for constructing the optional pie chart reports."""

    def __init__(self, session: ReconciliationSession) -> None:
        self.session = session

    def generate(self) -> Path:
        """Build the chart data so it can be added to the workbook."""

        raise NotImplementedError("Pie chart generation is a future stretch goal.")
