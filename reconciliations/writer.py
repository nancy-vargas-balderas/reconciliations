from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Tuple

import xlsxwriter


@dataclass
class SheetFormatKeeper:
    """Remembers where the existing budget workbook lives for reuse."""

    workbook_path: Path

    def get_template(self) -> Path:
        """Return the path that will be used when writing updates."""

        return self.workbook_path


SECTION_DEFS = [
    ("Regular", lambda record: not record.is_income and not record.is_misc and not record.recurring_key),
    ("Income", lambda record: record.is_income),
    ("Miscellaneous", lambda record: record.is_misc),
    ("Recurring", lambda record: bool(record.recurring_key)),
]


class BudgetSheetWriter:
    """Lightweight xlsxwriter-backed helper that preserves workbook location."""

    def __init__(self, template_path: Path) -> None:
        self.template_path = template_path
        self.target_path = template_path

    def populate(self, expenses: Sequence["ExpenseRecord"], month: str) -> None:
        """Write the provided expenses into a monthly sheet placeholder."""

        workbook = xlsxwriter.Workbook(str(self.target_path))
        worksheet = workbook.add_worksheet(name=month)

        ROW_HEADERS = ["Date", "Description", "Amount", "Category"]

        current_row = 0
        for section_name, records in self._sectioned_expenses(expenses):
            if not records:
                continue

            worksheet.write(current_row, 0, section_name)
            current_row += 1
            worksheet.write_row(current_row, 0, ROW_HEADERS)
            current_row += 1

            section_total = 0.0
            for record in records:
                worksheet.write_row(
                    current_row,
                    0,
                    [
                        record.date.isoformat(),
                        record.description,
                        record.amount,
                        record.category or "",
                    ],
                )
                section_total += record.amount
                current_row += 1

            worksheet.write_row(
                current_row,
                0,
                ["Total", "", section_total, ""],
            )
            current_row += 1
            current_row += 1  # blank line between sections

        workbook.close()

    def _sectioned_expenses(self, expenses: Sequence["ExpenseRecord"]) -> Sequence[tuple[str, list["ExpenseRecord"]]]:
        remaining = list(expenses)
        sections: list[tuple[str, list["ExpenseRecord"]]] = []

        for name, predicate in SECTION_DEFS:
            section_records = [record for record in remaining if predicate(record)]
            remaining = [record for record in remaining if record not in section_records]
            sections.append((name, section_records))

        return sections
