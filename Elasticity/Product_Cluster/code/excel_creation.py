# Importing Libraries

import pandas as pd
import numpy as np
from pathlib import Path

from pathlib import Path
import pandas as pd
import xlwings as xw
from constants import *

def write_df_preserve_named_range(
    file_path: str | Path,
    df: pd.DataFrame,
    sheet_name: str = "MySheet",
    named_range: str = "MyDataRange",
    start_cell: str = "A1",
    refresh_pivots: bool = True,
    visible: bool = False,
):
    """
    Writes df starting at start_cell on sheet_name, then resizes workbook-scoped
    named_range to the new block. Works with .xlsx or .xlsb files.
    """
    file_path = Path(file_path)
    is_xlsb = file_path.suffix.lower() == ".xlsb"
    FILEFORMAT_XLSB = 50  # Excel Binary Workbook

    app = xw.App(visible=visible, add_book=False)
    try:
        if file_path.exists():
            wb = xw.Book(str(file_path))
        else:
            # Create new workbook, then SaveAs in desired format
            wb = xw.Book()
            # Ensure the sheet exists/has correct name
            ws0 = wb.sheets[0]
            ws0.name = sheet_name
            # Save as xlsb if requested, else default xlsx
            if is_xlsb:
                wb.api.SaveAs(str(file_path), FileFormat=FILEFORMAT_XLSB)
            else:
                wb.save(str(file_path))

        # Ensure the target sheet exists
        try:
            ws = wb.sheets[sheet_name]
        except KeyError:
            ws = wb.sheets.add(name=sheet_name, after=wb.sheets[-1])

        # Clear current block and write data (headers + values)
        anchor = ws.range(start_cell)
        anchor.expand("table").clear_contents()
        if df.empty:
            anchor.value = [df.columns.tolist()]
        else:
            anchor.value = [df.columns.tolist()] + df.values.tolist()

        # Resize (or create) the named range to the new block
        new_block = ws.range(start_cell).expand("table")
        try:
            wb.names[named_range].refers_to = f"='{ws.name}'!{new_block.address}"
        except KeyError:
            wb.names.add(name=named_range, refers_to=f"='{ws.name}'!{new_block.address}")

        # Optional: refresh pivots so slicers see the new rows
        if refresh_pivots:
            try:
                wb.api.RefreshAll()
            except Exception:
                pass

        wb.save()  # keeps existing format (.xlsb or .xlsx)
        wb.close()
    finally:
        app.quit()


if __name__ == '__main__':

    # Get base dir
    base_dir = Path(__file__).resolve().parent.parent
    base_dir_output = Path(__file__).resolve().parent.parent.parent.parent

    model_summary_path = base_dir/"output/model/model_summary.xlsx"
    # read model summary
    model_summary = pd.read_excel(model_summary_path,sheet_name="sheet2")
    print(model_summary.shape)

    # Read raw data
    raw_data_file_path = base_dir/"output/data_original.csv"

    raw_data = pd.read_csv(raw_data_file_path, encoding='latin1', parse_dates=["week_starting_monday"])
    # raw_data = raw_data[raw_data['Data_Sufficiency']==1]
    print(raw_data.shape)

    raw_data['wtprice'] = raw_data['Regular_Price_fwbw_max_6']*raw_data[DOLLAR]

    # Sum revenue per product
    prod_sums = raw_data.groupby("ProductKey", as_index=False)[DOLLAR].sum()

    # Rank products by their total revenue
    prod_sums["Rank"] = prod_sums[DOLLAR].rank(ascending=False, method="first")
    

    # Merge back if you want the rank on every row of raw_data
    raw_data = raw_data.merge(prod_sums[["ProductKey", "Rank"]], on="ProductKey", how="left")
    

    raw_data['ProductKey'] = raw_data['ProductKey'].astype(int).astype(str)
    raw_data['Clusters'] = raw_data['Clusters'].astype(int)
    

    raw_data["Key_Cluster_Product"] = raw_data["Clusters"].astype(str) + "-" + raw_data["ProductKey"].astype(str)
    raw_data["datekey"] = raw_data["Key_Cluster_Product"].astype(str) + "-" + raw_data["week_starting_monday"].dt.strftime("%m/%d/%Y")
    
    raw_data_grouped = raw_data.groupby(["datekey", "ProductDescription","service","Clusters","ProductKey"]).agg({'Regular_Price_fwbw_max_6':"mean", "Rank":"mean"}).reset_index()
    raw_data_grouped['Rank'] = raw_data_grouped['Rank'].astype(int)

    raw_data_output_path = base_dir/"output/model/raw_data_treated.xlsx"
    raw_data.to_excel(raw_data_output_path, index=False)

    model_summary["datekey"] = model_summary["KEY"] + "-" + model_summary["week_starting_monday"].dt.strftime("%m/%d/%Y")
    model_summary = model_summary.merge(raw_data_grouped,on="datekey",how="inner")
    model_summary['Regular_Price_fwbw_max_6'] = model_summary['Regular_Price_fwbw_max_6'].fillna(0)
    model_summary["Qty per site"] = np.exp(model_summary[UNIT])
    model_summary = model_summary.merge(raw_data[['datekey','PRICE']],on="datekey",how="inner")
    model_summary['PRICE'] = model_summary['PRICE'].fillna(0)
    # model_summary = model_summary.rename(columns={"PRICE":"Bundle Price", "Clusters": "Cluster", "ProductDescription": "Bundle Description"})
    # print(model_summary.head())
    model_summary_path_output = base_dir/"output/model/model_summary_treated.xlsx"
    model_summary.to_excel(model_summary_path_output, index=False)

    output_summary_file_path = base_dir/"output/model/output_summary.xlsx"
    output_summary = pd.read_excel(output_summary_file_path)
    print(output_summary.shape)

    output_summary['Weighted elasticity'] = output_summary['ELASTICITY_PRICE'] * output_summary['TotalNet']
    output_summary['Weighted  rsq'] = output_summary['RSQ'] * output_summary['TotalNet']
    output_summary[["Cluster", "ProductKey"]] = output_summary["KEY"].str.split("-", expand=True)
    output_summary["Check"] = (((output_summary["Correl"] < 0) & (output_summary["ELASTICITY_PRICE"] < 0)) | ((output_summary["Correl"] > 0) & (output_summary["ELASTICITY_PRICE"] > 0))).astype(int)
    output_summary["Significant ?"] = ((output_summary["RSQ"].round(2) >= 0.5) & (output_summary["PVALUE_PRICE"].round(2) <= 0.2)).astype(int)
    
    raw_data_grouped.rename(columns={"ProductKey":"ProductKey"},inplace=True)

    output_summary = output_summary.merge(raw_data_grouped[['ProductKey','ProductDescription','service']].drop_duplicates(),on='ProductKey',how='inner')
    output_summary['Weighted  rsq_adj'] = output_summary['ADJ_RSQ'] * output_summary['TotalNet']
    output_summary['Weighted_Pvalue'] = output_summary['PVALUE_PRICE'] * output_summary['TotalNet']

    # output_summary = output_summary.rename(columns={ "ProductDescription": "Bundle Description"})
    output_summary.loc[:, output_summary.columns.str.contains("Weighted", case=False)] = (
    output_summary.loc[:, output_summary.columns.str.contains("Weighted", case=False)].fillna(0))

    output_summary = output_summary[['KEY', 'TotalNet',UNIT, 'Correl', 'RSQ', 'ADJ_RSQ', 'ELASTICITY_PRICE', 'PVALUE_PRICE','Weighted elasticity','Weighted  rsq',
                                     "Cluster", "ProductKey",'Check','Significant ?','ProductDescription','service','Weighted  rsq_adj','Weighted_Pvalue']]
    # print(output_summary.head())
    output_summary_path_output = base_dir/"output/model/output_treated.xlsx"
    output_summary.to_excel(output_summary_path_output, index=False)

    # Path of template file
    template_path = base_dir_output/"Excel_Outputs/UK_Product_Cluster_Elasticity_Dashboard.xlsb"

    # Writing files to template
    write_df_preserve_named_range(
    file_path=template_path,
    df=output_summary,
    sheet_name="Model_output",
    named_range="Model_output",
    start_cell="A1",
    refresh_pivots=False,   # keeps slicer state, refreshes pivot caches
    # refresh_all=False,     # set True only if you want to refresh external connections too
    visible=False)

    write_df_preserve_named_range(
    file_path=template_path,
    df=model_summary,
    sheet_name="AvP",
    named_range="AvP",
    start_cell="A1",
    refresh_pivots=False,   # keeps slicer state, refreshes pivot caches
    # refresh_all=False,     # set True only if you want to refresh external connections too
    visible=False)