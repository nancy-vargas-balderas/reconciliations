from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import xlsxwriter


@dataclass
class SheetFormatKeeper:
    """Remembers where the existing budget workbook lives for reuse."""

    workbook_path: Path

    def get_template(self) -> Path:
        """Return the path that will be used when writing updates."""

        return self.workbook_path


class BudgetSheetWriter:
    """Lightweight xlsxwriter-backed helper that preserves workbook location."""

    def __init__(self, template_path: Path) -> None:
        self.template_path = template_path
        self.target_path = template_path

    def populate(self, expenses: Sequence["ExpenseRecord"], month: str) -> None:
        """Write the provided expenses into a monthly sheet placeholder."""

        workbook = xlsxwriter.Workbook(str(self.target_path))
        worksheet = workbook.add_worksheet(name=month)

        worksheet.write_row(0, 0, ["Date", "Description", "Amount", "Category"])

        for idx, expense in enumerate(expenses, start=1):
            worksheet.write_row(
                idx,
                0,
                [
                    expense.date.isoformat(),
                    expense.description,
                    expense.amount,
                    expense.category or "Uncategorized",
                ],
            )

        workbook.close()
