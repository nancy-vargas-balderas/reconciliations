from __future__ import annotations

from pathlib import Path
from typing import Sequence

import xlsxwriter
from .common import ExpenseRecord


class BudgetSheetWriter:
    """Lightweight xlsxwriter-backed helper that preserves workbook location."""

    def __init__(self, workbook_path: Path) -> None:
        self.workbook = xlsxwriter.Workbook(str(workbook_path))

    def _apply_template(self, worksheet: xlsxwriter.Worksheet) -> None:
        merge_format = self.workbook.add_format({
            "bold": True,
            "align": "center",
            "border": 1
        })

        #net income
        worksheet.merge_range("B3:C3", "Net Income", merge_format)

        #balance and total spending
        worksheet.write_string("E3", "Balance", merge_format) 
        worksheet.write_string("F3", "Total Spending", merge_format)

        # #recurring expenses
        worksheet.merge_range("B6:C6", "Recurring Expenses", merge_format)

        # #Miscellaneous
        worksheet.merge_range("E6:F6", "Miscellaneous", merge_format)

        # #purchases
        col_name_format = self.workbook.add_format({
            "border": 1
        })
        worksheet.merge_range("I3:L3", "Purchases", merge_format)
        worksheet.write_string("I4", "Date", col_name_format) 
        worksheet.write_string("J4", "Category", col_name_format) 
        worksheet.write_string("K4", "Description", col_name_format)  
        worksheet.write_string("L4", "Amount", col_name_format)

    def populate(self, expenses: Sequence[ExpenseRecord], month: str) -> None:
        """Write the provided expenses into a monthly sheet placeholder."""

        worksheet = self.workbook.add_worksheet(name=month)
        self._apply_template(worksheet)

        total_income_fn = "=0"

        starting_misc_row = 6
        starting_recurring_row = 6
        starting_purchases_row = 4

        misc_row, misc_col = starting_misc_row,4
        recurring_row, recurring_col = starting_recurring_row,1
        purchases_row, purchases_col = starting_purchases_row,8

        row_format = self.workbook.add_format({
            "border": 1
        })
        
        for e in expenses:
            if e.is_payment:
                continue
            
            if e.is_income:
                total_income_fn += f"+{e.amount}"
                continue

            if e.is_misc:
                worksheet.write_row(misc_row, misc_col, (e.description, e.amount), row_format)
                misc_row += 1
                continue

            if e.recurring_key:
                worksheet.write_row(recurring_row, recurring_col, (e.recurring_key, e.amount), row_format)
                recurring_row += 1
                continue 

            worksheet.write_row(
                purchases_row,
                purchases_col,
                [
                    e.date.isoformat(),
                    e.category,
                    e.description,
                    e.amount,
                ],
                row_format
            )
            purchases_row += 1
        
        #add totals
        totals_format = self.workbook.add_format({
            "bold": True,
            "border": 1
        })
        
        worksheet.write("B4", "", totals_format)
        worksheet.write_formula("C4", total_income_fn, totals_format)

        def write_total(row, col, start_row, col_increase_amt):
            worksheet.write(row, col, "total", totals_format)
            col += col_increase_amt
            final_cell = xlsxwriter.utility.xl_rowcol_to_cell(row-1, col) if row != start_row else None
            total_cell = xlsxwriter.utility.xl_rowcol_to_cell(row, col) 
            if final_cell:
                worksheet.write_formula(row, col, f"=SUM({xlsxwriter.utility.xl_rowcol_to_cell(start_row, col)}:{final_cell})", totals_format) 
            else:
                worksheet.write(row, col, 0, totals_format)
            return col, total_cell

        recurring_col, _ = write_total(recurring_row, recurring_col, starting_recurring_row, 1)
        misc_col, misc_total_cell = write_total(misc_row, misc_col, starting_misc_row, 1)
        purchases_col, purchases_total_cell = write_total(purchases_row, purchases_col, starting_purchases_row, 3)
 
        #calculate total spending and balance
        worksheet.write_formula("E4", "=C4-F4", totals_format)
        worksheet.write_formula("F4", f"=SUM({misc_total_cell},{purchases_total_cell})", totals_format)
        self.workbook.close()
