<img width="722" height="635" alt="Screenshot 2025-11-23 at 2 17 57 AM" src="https://github.com/user-attachments/assets/01288c6d-3525-4bc0-9b7a-2faa5275ee75" />This is a cli used to categorize credit card statements into Excel worksheets. It is interactive and cutomizable.

usage: `cli --workbook-path PATH [OPTIONS] month csv_files`

required:
-`--workbook-path` path to the workbook you intend to update,
-`month` name of the sheet to create and use
-`csv_files` files to ingest and categorize

options:
-`--yes` skips the confirmation prompt once you are comfortable with a particular workbook/month,
-`--config PATH` lets you supply a JSON file that describes available categories and recurring expenses.

The interactive classification flow walks through each CSV row, prompting you to pick a category, mark incomes/misc/payments, and notes recurring expenses if appropriate. Once all records are classified, the CLI totals and writes the monthly summary.

Here is an example flow and the resulting Excel sheet:
<img width="722" height="635" alt="Screenshot 2025-11-23 at 2 17 57 AM" src="https://github.com/user-attachments/assets/556ebb8c-d382-4177-85e7-579e43edcc1c" />
<img width="691" height="139" alt="Screenshot 2025-11-23 at 2 42 03 AM" src="https://github.com/user-attachments/assets/6d2bad2b-6450-46ac-a731-f7a1e8c8fc5e" />


Future work:
- subcommand to generate a pie graph
- check that recurring expenses are satisfied
