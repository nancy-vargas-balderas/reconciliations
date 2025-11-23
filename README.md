This is a cli used to categorize credit card statements into Excel worksheets. It is interactive and cutomizable.

usage: `cli --workbook-path PATH [OPTIONS] month csv_files`

required:
-`--workbook-path` path to the workbook you intend to update,
-`month` name of the sheet to create and use
-`csv_files` files to ingest and categorize

options:
-`--yes` skips the confirmation prompt once you are comfortable with a particular workbook/month,
-`--config PATH` lets you supply a JSON file that describes available categories and recurring expenses.

The interactive classification flow walks through each CSV row, prompting you to pick a category, mark incomes/misc/payments, and notes recurring expenses if appropriate. Once all records are classified, the CLI totals and writes the monthly summary.


Future work:

Some features I'd like to have:
- subcommand to generate a pie graph
- check that recurring expenses are satisfied
