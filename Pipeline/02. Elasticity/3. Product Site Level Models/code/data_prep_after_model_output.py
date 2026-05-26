import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
import yaml
from constants import *
import xlwings as xw

# Path to this config file
config_file = Path(__file__).resolve().parent /"src"/ "config.yml"

# Load YAML
with open(config_file, "r") as f:
    config = yaml.safe_load(f)

# Resolve module_path relative to config file location
module_path = (config_file.parent / config["module_path"]).resolve()

print("Module Path:", module_path)

itr = config['itr_name']
print(f'Name Of Iteration: {itr}')

### Dyanmic Read Data
def read_data(path, sheet="sheet2"):
    """
    Generic data reader.
    - If file is .csv → read with cp1252 encoding
    - If file is .xlsx/.xls → read Excel (default sheet='sheet2')
    - Returns pandas DataFrame
    """
    print(f"Reading File : {path}")
    ext = os.path.splitext(path)[1].lower()

    if ext == ".csv":
        print("Reading CSV file")
        return pd.read_csv(path, encoding="cp1252", encoding_errors="ignore")

    if ext in [".xlsx", ".xls"]:
        print("Reading Excel file")
        # Let pandas auto-pick engine so both .xlsx and .xls work
        sheet_name = sheet if sheet not in (None, "", False) else 0
        return pd.read_excel(path, sheet_name=sheet_name)

    raise ValueError(f"Unsupported file type: {ext}")
    

### Calculating Rank
def rank_calc(path):
    """
    Rank products/bundles by revenue or sales.
    - For Product_Site → rank ItemCode by Sum_SalesTotal
    - For Bundle → rank Bundle_code by basket_revenue
    Output: DataFrame with Rank column and saved to CSV.
    """
    df = pd.read_excel(path)
    # Rank by sales total
    df[RANK] = df["Sum_SalesTotal"].rank(ascending=False, method="first")
    # Clean up description columns
    df.drop(columns=[DESC_COL_PRODUCT], inplace=True, errors="ignore")
    df.rename(columns={"ItemDescription English": DESC_COL_PRODUCT}, inplace=True)

    # Save rank file for reference
    df.to_csv(rf".\output\rank_{itr}.csv", index=False)
    return df

def creating_raw_data(df, prod_df):
    """
    Prepare raw dataset before merging with model results.
    - Builds KEY and Key-week
    - Adds price for Product_Site model
    - Joins with product/bundle description + Rank
    Returns DataFrame with enriched raw data
    """
    # Create KEY and Key-week
    df[KEY] = df[Cluster_Granularity].astype(str) + "-" + df[Product_Code_var].astype(str)
    df[KEY_WEEK] = df[KEY].astype(str) + "-" + df[DATE].astype(str)

    df[PRICE] = df[DOLLAR] / df[UNIT]

    # Merge with product/bundle summary (Rank + description)
    df1 = pd.merge(df, prod_df[[Product_Code_var, RANK]], on=Product_Code_var, how="left")
    return df1

def creating_variables_model_summary(df, prod_df, df_price):
    """
    Prepare model summary data.
    - Builds Key-week
    - Splits KEY into Cluster + Product/Bundle code
    - Joins with product/bundle summary (description + Rank)
    - Joins with price-related + revenue columns (from constants.PRICE_COLS)
    - Restricts to standardized final column order (from constants.FINAL_SUMMARY_COLS)
    Returns standardized summary DataFrame
    """
    # Create Key-week
    df[KEY_WEEK] = df[KEY].astype(str) + "-" + df[DATE].astype(str)

    # Extract Cluster + Product/Bundle from KEY
    pattern = rf"^(?P<{Cluster_Granularity}>[^-]+)-(?P<{Product_Code_var}>.+)$"
    out = df[KEY].str.extract(pattern)
    df[Cluster_Granularity] = out[Cluster_Granularity]
    df[Product_Code_var] = out[Product_Code_var]

    # Merge with product/bundle description + Rank
    df1 = pd.merge(
        df,
        prod_df[[Product_Code_var, DESC_COL_PRODUCT, RANK]],
        on=Product_Code_var,
        how="left"
    )

    # Merge with price data (defined in constants.py)
    df2 = pd.merge(df1, df_price[PRICE_COLS], on=KEY_WEEK, how="left")

    # Keep only standardized final columns
    final_cols = [c for c in FINAL_SUMMARY_COLS if c in df2.columns]

    df2 = df2[final_cols]
    return df2

def model_output(path, prod_df):
    """
    Prepare final model output.
    - Splits KEY into Cluster + Product/Bundle code
    - Joins with product/bundle summary (description + Rank, service if applicable)
    - Calculates weighted elasticity, R-squared, and P-value
    - Restricts to standardized final column order (constants.FINAL_OUTPUT_COLS)
    Returns standardized output DataFrame
    """
    df = pd.read_excel(path)

    # Extract Cluster + Product/Bundle from KEY
    pattern = rf"^(?P<{Cluster_Granularity}>[^-]+)-(?P<{Product_Code_var}>.+)$"
    out = df[KEY].str.extract(pattern)
    df[Cluster_Granularity] = out[Cluster_Granularity]
    df[Product_Code_var] = out[Product_Code_var]

    # Base merge columns
    merge_cols = [Product_Code_var, DESC_COL_PRODUCT, RANK]

    # Add service column only for Product_Site
    if SERVICE_VAR in prod_df.columns:
        merge_cols.append(SERVICE_VAR)

    # Merge with product/bundle summary
    df1 = pd.merge(df, prod_df[merge_cols], on=Product_Code_var, how="left")

    # Weighted calculations
    df1["Weighted elasticity"] = df1[DOLLAR] * df1[ELASTICITY_COL]
    df1["Weighted  rsq"] = df1[DOLLAR] * df1[RSQ_COL]
    if PVALUE_PREFIX + ALGO_REGULAR_PRICE in df1.columns:
        df1["Weighted PValue"] = df1[DOLLAR] * df1[PVALUE_PREFIX + ALGO_REGULAR_PRICE]

    # Keep only standardized final columns
    final_cols = [c for c in FINAL_OUTPUT_COLS if c in df1.columns]
    df1 = df1[final_cols]
    if SERVICE_VAR in df1.columns and SERVICE_OUTPUT_NAME != SERVICE_VAR:
        df1.rename(columns={SERVICE_VAR: SERVICE_OUTPUT_NAME}, inplace=True)
    df1['Check'] = np.where(( ((df[Correl_col] < 0) & (df[ELASTICITY_COL] < 0)) | ((df[Correl_col] > 0) & (df[ELASTICITY_COL] > 0))),1, 0 )
    df1['Significant ?'] = np.where((df[RSQ_COL].round(1) >= 0.5) & (df[PVALUE_PREFIX + ALGO_REGULAR_PRICE].round(1) <= 0.2), 1,0 )
    return df1

def summarize_pvalues(path, pvalue_prefix=PVALUE_PREFIX, alpha=0.2):
    """
    Summarize statistical significance of model variables.
    - Finds all PVALUE_* columns
    - Counts how many were used in model
    - Counts how many were significant (<= alpha)
    - Computes % significant
    Returns standardized summary DataFrame
    """
    # Read model summary file
    df = pd.read_excel(path, sheet_name="sheet1")

    # Detect PVALUE_* columns
    pval_cols = [c for c in df.columns if c.upper().startswith(pvalue_prefix.upper())]
    if not pval_cols:
        raise ValueError(f"No columns starting with '{pvalue_prefix}' found in {path}")

    results = []
    for col in pval_cols:
        feature_name = col.replace(pvalue_prefix, "").strip()
        vals = pd.to_numeric(df[col], errors="coerce")

        used_count = vals.notna().sum()
        sig_count = (vals.notna() & (vals <= alpha)).sum()
        pct_sig = (sig_count / used_count * 100) if used_count > 0 else 0

        results.append((feature_name, used_count, sig_count, pct_sig))

    # Build DataFrame
    df_out = pd.DataFrame(results, columns=PVALUE_SUMMARY_COLS)

    # Ensure standardized column order
    df_out = df_out[[c for c in PVALUE_SUMMARY_COLS if c in df_out.columns]]

    print(f"P-Value summary prepared with {len(df_out)} features.")
    return df_out

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
    print(file_path)

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
        
if __name__ == "__main__":
    print(f"========== Running pipeline Aggregate data in 1 file ==========")
    # Resolve module_path relative to config file location
    module_path = (config_file.parent / config["module_path"]).resolve()
    model_result_path = os.path.join(module_path,config['output_summary_preparation']['model_result'].lstrip("/\\"))
    raw_data_path       = os.path.join(module_path, config['regular_price']['raw_input_data'].lstrip("/\\"))
    product_summary_path= os.path.join(module_path, config['output_summary_preparation']['product_description_path_Product_Site'].lstrip("/\\"))
    model_output_path = os.path.join(module_path,config['model']['output_summary_path'].lstrip("/\\"))
    model_summary_path = os.path.join(module_path,config['model']['model_summary_save_path'].lstrip("/\\"))
    regular_price_path  = os.path.join(module_path, config['regular_price']['output_data'].lstrip("/\\"))
    rank_source_path = product_summary_path   
    

    # 1) Rank calc
    product_summary = rank_calc(rank_source_path)

    # 2) Raw data
    raw_data = read_data(raw_data_path)
    raw_data1 = creating_raw_data(raw_data, product_summary)

    # 3) Model result summary
    model_result = read_data(model_result_path)
    model_result_1 = creating_variables_model_summary(model_result, product_summary, raw_data1)

    # merge regular price
    regular_price_df = read_data(regular_price_path)
    regular_price_df[KEY_WEEK] = regular_price_df[KEY].astype(str) + "-" + regular_price_df[DATE].astype(str)
    model_result_1 = pd.merge(model_result_1, regular_price_df[[KEY_WEEK, REGULAR_PRICE_COL]], on=KEY_WEEK, how="left")

    # 4) Model output
    model_out = model_output(model_output_path, product_summary)

    # Save consistently here
    model_result_1.to_excel(rf".\output\model_result_summary_ready_{itr}.xlsx", index=False)
    model_out.to_excel(rf".\output\output_summary_ready_{itr}.xlsx", index=False)

    # 6) P-Value summary
    sign_summary = summarize_pvalues(model_summary_path)
    sign_summary.to_excel(rf".\output\significant_variable_summary_{itr}.xlsx", index=False)

    base_dir_output = Path(__file__).resolve().parent.parent.parent
    # Path of template file
    template_path = base_dir_output/"Excel_Outputs/Sweden_Sitecode_level_elasticity_summary.xlsx"

    # Writing files to template
    write_df_preserve_named_range(
    file_path=template_path,
    df=model_out,
    sheet_name="Model_output",
    named_range="Model_output",
    start_cell="A1",
    refresh_pivots=False,   # keeps slicer state, refreshes pivot caches
    # refresh_all=False,     # set True only if you want to refresh external connections too
    visible=False)

    write_df_preserve_named_range(
    file_path=template_path,
    df=model_result_1,
    sheet_name="AvP",
    named_range="AvP",
    start_cell="A1",
    refresh_pivots=False,   # keeps slicer state, refreshes pivot caches
    # refresh_all=False,     # set True only if you want to refresh external connections too
    visible=False)
    print("========== Pipeline Completed ==========")

