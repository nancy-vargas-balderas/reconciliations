from __future__ import annotations

from pathlib import Path

import click

from reconciliations import BudgetSheetConfig, ReconciliationSession


def _confirm_callback(config: BudgetSheetConfig) -> bool:
    """Prompt the user once before editing the configured workbook."""

    message = f"Write changes to {config.workbook_path} for {config.month}?"
    return click.confirm(message, default=False)


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
@click.argument("month")
@click.argument("csv_files", nargs=-1, type=click.Path(exists=True, path_type=Path))
def cli(
    workbook_path: Path,
    month: str,
    csv_files: tuple[Path, ...],
    yes: bool,
) -> None:
    """Reconcile the given CSV files with a monthly budget sheet."""

    if not csv_files:
        raise click.UsageError("At least one CSV file is required.")

    workbook_path = workbook_path.expanduser()
    config = BudgetSheetConfig(
        workbook_path=workbook_path,
        month=month,
        prompt_user_before_commit=not yes,
    )
    session = ReconciliationSession(config, confirm_callback=_confirm_callback)

    if not session.confirm_budget_sheet():
        click.echo("No changes were made.")
        raise click.Abort()

    session.load_transactions(csv_files)
    target = session.write_budget_sheet()
    click.echo(f"Reconciliation written to {target}")


if __name__ == "__main__":
    cli()
