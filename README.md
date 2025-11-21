This is a cli used to populate budget sheets in ~/Documents/'/Users/nsv/Documents/♥ 2025 ♥ (っ◔◡◔)っ ♥ budget ♥.xlsx'.

usage: cli --workbook-path PATH [OPTIONS] month csv_files

The `--workbook-path` option is now required so you explicitly point at the workbook you intend to update,
and `--yes` skips the confirmation prompt once you are comfortable with a particular workbook/month.

It should ask the user to confirm the budget sheet path and month before making changes.


Some features I'd like to have:
- keep the existing format of the monthly sheets in teh excel document.
- subcommand to generate the pie graph [stretch goal]
- interactively ask the user to classify an expense with a configurable set of categories.
- allow user to specify reocurring expenses and verify that these are satisfied after processing input files
- allow user to indicate that an expense is actually an income source
- allow user to indicate that an expense is miscellaneous (one-off large expense)
- allow use to indicate that an expense is actually a payment and should be excluded.
- sanity check the cells linked in formulas [stretch goal] 
