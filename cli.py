from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    import readline
except ImportError:
    readline = None

import click

from reconciliations import BudgetSheetConfig, ExpenseRecord, ReconciliationSession

BASE_RESERVED_CATEGORIES = ["Income", "Miscellaneous", "Payment"]
RECURRING_RESERVED_CATEGORY = "Recurring"


class InteractiveClassificationSession():
    def __init__(self, reconciliation_session: ReconciliationSession):
        self.session = reconciliation_session
        self.config = self.session.config
        self.reserved_categories = BASE_RESERVED_CATEGORIES
        self.recurring_keys = None 

        if bool(self.config.recurring_expenses):
            self.reserved_categories += [RECURRING_RESERVED_CATEGORY]
            self.recurring_keys = self.config.recurring_expenses
        
        self.categories = self.reserved_categories + self.config.categories

    def _decorate_category(
        self,
        category: str,
    ) -> str:
        return f"{category}*" if any(category.lower() == r.lower() for r in self.reserved_categories) else category

    def _install_category_autocomplete(self) -> Optional[Any]:
        """Install a readline completer for the list of categories."""

        if not readline:
            return None

        last_buffer: Optional[str] = None

        def completer(text: str, state: int) -> Optional[str]:
            nonlocal last_buffer
            buffer = readline.get_line_buffer()
            matches = [
                c
                for c in self.categories
                if c.lower().startswith(text.lower())
            ]
            if state == 0:
                last_buffer = buffer
            return matches[state] if state < len(matches) else None

        previous = readline.get_completer()
        readline.set_completer(completer)
        if "libedit" in (getattr(readline, "__doc__", "") or "").lower():
            readline.parse_and_bind("bind ^I rl_complete")
        else:
            readline.parse_and_bind("tab: complete")
        return previous

    def _input_with_default(self, prompt: str, default: str) -> str:
        """Prompt the user with a default value without Click helpers."""

        prompt_text = f"{prompt} [{default}]: " if default else f"{prompt}: "
        return input(prompt_text).strip() or default


    def _prompt_category(
        self,
    ) -> str:
        """Prompt to classify an expense by category with tab completion."""
        previous_completer = self._install_category_autocomplete()
        try:
            while True:
                candidate = self._input_with_default("Category", "")
                match = next(
                    (choice for choice in self.categories if choice.lower() == candidate.lower()),
                    None,
                )
                if match:
                    return match
                click.echo(f"Unrecognized category '{candidate}', try again.")
        finally:
            if readline:
                readline.set_completer(previous_completer)

    def _prompt_recurring_key(self) -> str:
        """Prompt for a specific recurring expense key when needed."""

        if not self.recurring_keys:
            raise click.BadParameter("No recurring items are configured.")

        click.echo("\nRecurring items:")
        for key in self.recurring_keys:
            click.echo(f"  - {key}")

        while True:
            candidate = self._input_with_default("Recurring key", "")
            match = next(
                (key for key in self.recurring_keys if key.lower() == candidate.lower()),
                None,
            )
            if match:
                return match
            click.echo(f"Unrecognized recurring key '{candidate}', try again.")

    def classify(self) -> None:
        # Alert user of available categories
        click.echo("\nAvailable categories:")
        for category in self.reserved_categories:
            click.echo(f"  - {self._decorate_category(category)}")
        if self.config.categories:
            for category in self.config.categories:
                click.echo(f"  - {category}")
        else:
            click.echo("  (none)")
        click.echo("\n*: special categories kept separate from general purchases\n")

        # Begin interactive classification
        total = len(self.session.expenses)
        for idx, record in enumerate(self.session.expenses, start=1):
            progress = click.style(f"({idx}/{total})", fg="green")
            click.echo(f"{progress} {record.date.isoformat()} - {record.description} [{record.amount:.2f}]")
            category = self._prompt_category()
            record.category = category

            if category == "Income":
                record.is_income = True 
            elif category == "Payment":
                record.is_payment = True 
            elif category == "Miscellaneous":
                record.is_misc = True 

            if category.lower() == RECURRING_RESERVED_CATEGORY.lower():
                record.recurring_key = self._prompt_recurring_key()
            else:
                record.recurring_key = None


def _load_config(config_path: Optional[Path]) -> Tuple[List[str], List[str]]:
    """Read the JSON config file describing categories and recurring expectations."""

    if config_path is None:
        return [], {}

    with config_path.open(encoding="utf-8") as fp:
        raw = json.load(fp)

    categories: List[str] = []
    recurring: List[str] = {}

    if "categories" in raw:
        if not isinstance(raw["categories"], list):
            raise click.BadParameter("Config: 'categories' must be a list.")
        categories = [str(item).strip() for item in raw["categories"] if item]

    if "recurring_expenses" in raw:
        if not isinstance(raw["recurring_expenses"], list):
            raise click.BadParameter("Config: 'recurring_expenses' must be a list.")
        recurring = [str(item).strip() for item in raw["recurring_expenses"] if item]

    reserved_for_config = BASE_RESERVED_CATEGORIES + [RECURRING_RESERVED_CATEGORY]
    for name in categories:
        if any(name.lower() == reserved.lower() for reserved in reserved_for_config):
            raise click.BadParameter(f"Config: '{name}' is reserved and cannot be defined.")

    return categories, recurring

@click.command()
@click.option(
    "--workbook-path",
    "-w",
    required=True,
    type=click.Path(path_type=Path),
    help="Path to the master budget workbook.",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip the confirmation prompt before writing.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(exists=True, path_type=Path),
    help="Path to a JSON file describing categories/recurring expectations.",
)
@click.argument("month")
@click.argument("csv_files", nargs=-1, type=click.Path(exists=True, path_type=Path))
def cli(
    workbook_path: Path,
    month: str,
    csv_files: tuple[Path, ...],
    yes: bool,
    config_path: Optional[Path],
) -> None:
    """Reconcile the given CSV files with a monthly budget sheet."""

    if not csv_files:
        raise click.UsageError("At least one CSV file is required.")

    workbook_path = workbook_path.expanduser() 
    categories, recurring_expenses = _load_config(config_path)

    config = BudgetSheetConfig(
        workbook_path=workbook_path,
        month=month,
        categories=categories,
        recurring_expenses=recurring_expenses,
    )

    if not yes and not click.confirm(f"Write changes to {config.workbook_path} for {config.month}?", default=False):
        raise click.Abort()

    session = ReconciliationSession(config)
    session.load_transactions(csv_files)
    classification = InteractiveClassificationSession(session)
    classification.classify()

    target = session.write_budget_sheet()
    click.echo(f"Reconciliation written to {target}")


if __name__ == "__main__":
    cli()
