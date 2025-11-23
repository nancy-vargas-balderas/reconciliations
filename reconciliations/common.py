from __future__ import annotations

from dataclasses import dataclass


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