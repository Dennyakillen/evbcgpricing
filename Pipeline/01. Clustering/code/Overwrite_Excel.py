# pip install xlwings
from pathlib import Path
import pandas as pd
import xlwings as xw

def write_df_preserve_named_range(
    file_path: str | Path,
    df: pd.DataFrame,
    sheet_name: str = "MySheet",
    named_range: str = "MyDataRange",
    start_cell: str = "A1",
    refresh_pivots: bool = True,
    visible: bool = False,      # set True if you want to watch it run
):
    """
    Overwrite data on `sheet_name` starting at `start_cell`, then resize the
    workbook-scoped named range `named_range` to the new block.
    Keeps other sheets/pivots intact by letting Excel do the work (via xlwings).
    """
    file_path = Path(file_path)

    app = xw.App(visible=visible, add_book=False)
    try:
        wb = xw.Book(str(file_path))

        # Ensure the target sheet exists
        try:
            ws = wb.sheets[sheet_name]
        except KeyError:
            ws = wb.sheets.add(name=sheet_name, after=wb.sheets[-1])

        # 1) Clear existing block (only contents) starting from start_cell
        #    `.expand('table')` grabs the current contiguous block.
        rng_start = ws.range(start_cell)
        rng_start.expand('table').clear_contents()

        # 2) Write headers + data
        if not df.empty:
            ws.range(start_cell).value = [df.columns.tolist()] + df.values.tolist()
        else:
            # Write just headers if you want an empty table with headers:
            ws.range(start_cell).value = [df.columns.tolist()]

        # 3) Determine new block to size the named range
        new_block = ws.range(start_cell).expand('table')

        # 4) Ensure the named range exists, then point it to the new block
        try:
            # if name exists, just retarget it
            wb.names[named_range].refers_to = f"='{ws.name}'!{new_block.address}"
        except KeyError:
            # create it if missing (workbook-scoped)
            wb.names.add(name=named_range, refers_to=f"='{ws.name}'!{new_block.address}")

        # 5) Optional: refresh pivots so they pick up new rows immediately
        if refresh_pivots:
            try:
                wb.api.RefreshAll()
            except Exception:
                pass  # safe to ignore if no connections/pivots

        wb.save()
        wb.close()
    finally:
        app.quit()
