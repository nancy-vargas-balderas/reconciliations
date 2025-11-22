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

RESERVED_CATEGORIES = ["Income", "Miscellaneous", "Payment"]


def _decorate_category(option: str) -> str:
    return f"{option}*" if any(option.lower() == reserved.lower() for reserved in RESERVED_CATEGORIES) else option


def _load_config(config_path: Optional[Path]) -> Tuple[List[str], Dict[str, float]]:
    """Read the JSON config file describing categories and recurring expectations."""

    if config_path is None:
        return [], {}

    with config_path.open(encoding="utf-8") as fp:
        raw = json.load(fp)

    categories: List[str] = []
    recurring: Dict[str, float] = {}

    if "categories" in raw:
        if not isinstance(raw["categories"], list):
            raise click.BadParameter("Config: 'categories' must be a list.")
        categories = [str(item).strip() for item in raw["categories"] if item]
    for name in categories:
        if any(name.lower() == reserved.lower() for reserved in RESERVED_CATEGORIES):
            raise click.BadParameter(f"Config: '{name}' is reserved and cannot be defined.")

    if "recurring_expectations" in raw:
        if not isinstance(raw["recurring_expectations"], dict):
            raise click.BadParameter("Config: 'recurring_expectations' must be a mapping.")
        for key, value in raw["recurring_expectations"].items():
            if not key or not isinstance(key, str):
                raise click.BadParameter("Config: recurring keys must be non-empty strings.")
            try:
                recurring[key] = float(value)
            except (TypeError, ValueError) as exc:
                raise click.BadParameter(f"Config: recurring amount for {key} must be numeric.") from exc

    return categories, recurring


def _print_completion_list(matches: Sequence[str]) -> None:
    click.echo()
    for match in matches:
        click.echo(_decorate_category(match))


def _install_category_autocomplete(
    choices: Sequence[str],
) -> Optional[Any]:
    """Install a readline completer for the list of categories."""

    if not readline:
        return None

    def completer(text: str, state: int) -> Optional[str]:
        buffer = readline.get_line_buffer()
        matches = [
            category
            for category in choices
            if category.lower().startswith(text.lower())
        ]
        if state == 0 and len(matches) > 1:
            _print_completion_list(matches)
        return matches[state] if state < len(matches) else None

    previous = readline.get_completer()
    readline.set_completer(completer)
    if "libedit" in (getattr(readline, "__doc__", "") or "").lower():
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")
    readline.parse_and_bind("set show-all-if-unmodified on")
    readline.parse_and_bind("set show-all-if-ambiguous on")
    return previous


def _input_with_default(prompt: str, default: str) -> str:
    """Prompt the user with a default value without Click helpers."""

    prompt_text = f"{prompt} [{default}]: " if default else f"{prompt}: "
    return input(prompt_text).strip() or default


def _prompt_category(categories: Sequence[str]) -> str:
    """Prompt to classify an expense by category with tab completion."""

    choices: List[str] = list(categories)
    for reserved in RESERVED_CATEGORIES:
        if not any(reserved.lower() == choice.lower() for choice in choices):
            choices.insert(0, reserved)

    previous_completer = _install_category_autocomplete(choices)
    try:
        while True:
            candidate = _input_with_default("Category", "")
            match = next(
                (choice for choice in choices if choice.lower() == candidate.lower()),
                None,
            )
            if match:
                return match
            click.echo(f"Unrecognized category '{candidate}', try again.")
    finally:
        if readline:
            readline.set_completer(previous_completer)


def _interactive_classification(session: ReconciliationSession) -> None:
    """Let the user walk through all records to classify and flag them."""

    click.echo("\nAvailable categories:")
    for category in RESERVED_CATEGORIES:
        click.echo(f"  - {_decorate_category(category)}")
    if session.config.categories:
        for category in session.config.categories:
            click.echo(f"  - {category}")
    else:
        click.echo("  (none)")
    click.echo("\n*: special categories kept separate from general expenses\n")

    total = len(session.expenses)
    for idx, record in enumerate(session.expenses, start=1):
        progress = click.style(f"({idx}/{total})", fg="green")
        click.echo(f"{progress} {record.date.isoformat()} - {record.description} [{record.amount:.2f}]")
        category = _prompt_category(session.config.categories)
        session.classify_expense(record, category)

        normalized = category.strip().lower()
        record.is_income = normalized == "income"
        record.is_misc = normalized == "miscellaneous"
        record.is_payment = normalized == "payment"

        recurring_key = click.prompt("Recurring key (blank to skip)", default="", show_default=False).strip()
        if recurring_key:
            record.recurring_key = recurring_key


def _check_recurring_expectations(session: ReconciliationSession) -> bool:
    """Warn if recurring expectations are not satisfied yet."""

    if not session.config.recurring_expectations:
        return True

    report = session.build_recurring_report()
    missing = {key: value for key, value in report.missing.items() if value > 0.005}
    if not missing:
        return True

    click.echo("\nRecurring expectations not satisfied:")
    for key, value in missing.items():
        click.echo(f"  {key}: missing {value:.2f}")
    return click.confirm("Continue despite missing expectations?", default=False)


def _check_income_flags(session: ReconciliationSession) -> bool:
    """Fail if income flags look inconsistent with amounts."""

    issues = [
        record for record in session.expenses if record.is_income and record.amount >= 0
    ]
    if not issues:
        return True

    click.echo("\nIncome flag validation failed for records with non-negative amounts:")
    for record in issues:
        click.echo(f"  {record.date.isoformat()} {record.description} {record.amount:.2f}")
    return False


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
    categories, recurring_expectations = _load_config(config_path)

    config = BudgetSheetConfig(
        workbook_path=workbook_path,
        month=month,
        categories=categories,
        recurring_expectations=recurring_expectations,
    )

    if not yes and not click.confirm(f"Write changes to {config.workbook_path} for {config.month}?", default=False):
        raise click.Abort()

    session = ReconciliationSession(config)
    session.load_transactions(csv_files)
    _interactive_classification(session)

    if not _check_recurring_expectations(session):
        click.echo("Commit aborted due to recurring expectation validation.")
        raise click.Abort()

    if not _check_income_flags(session):
        click.echo("Commit aborted due to income flag validation.")
        raise click.Abort()

    target = session.write_budget_sheet()
    click.echo(f"Reconciliation written to {target}")


if __name__ == "__main__":
    cli()
