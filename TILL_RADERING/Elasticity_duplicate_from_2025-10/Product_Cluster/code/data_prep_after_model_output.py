import os
import sys

import pandas as pd
import numpy as np
from pathlib import Path
import yaml
import xlwings as xw
    
from utils import *
from constants import *

# Path to this config file
config_file = Path(__file__).resolve().parent /"src"/ "config.yml"

# Load YAML
with open(config_file, "r") as f:
    config = yaml.safe_load(f)

# Resolve module_path relative to config file location
module_path = (config_file.parent / config["module_path"]).resolve()

print("Module Path:", module_path)

### defining Iteration name
itr = config['itr_name']

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

def rank_calc(path):
    """
    Rank products/bundles by revenue or sales.
    - For Product_Site → rank ItemCode by Sum_SalesTotal
    - For Bundle → rank Bundle_code by basket_revenue
    Output: DataFrame with Rank column and saved to CSV.
    """
    df = pd.read_excel(path).drop_duplicates([Product_Code_var,SERVICE_VAR])
    df.rename(columns = {'Sum_SalesTotal':'SalesTotal'}, inplace = True)
    ### Calculating Rank
    df=df.groupby([SERVICE_VAR,Product_Code_var,'ItemDescription English']).agg({'SalesTotal':'sum'}).reset_index()
    df['Index']=1
    df['Rank'] = df.groupby('Index')['SalesTotal'].rank(ascending=False, method='first')
    df.rename(columns = {"ItemDescription English":"Product Description", SERVICE_VAR:SERVICE_OUTPUT_NAME}, inplace=True)
    # df.to_csv(module_path+Path(rf'.\output\rank_{itr}_check.csv'))
    return df

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
    df[KEY] = np.where(df[KEY] == 'Clinics-nan-0', 'Clinics-NA-0', df[KEY])
    # Create Datekey
    df[KEY_WEEK_blended] = df[KEY].astype(str) + "-" + df[DATE].astype(str)
    
    # Extract Cluster + Product/Bundle from KEY
    pattern = rf"^(?P<{Cluster_Granularity}>[^-]+)-(?P<{Product_Code_var}>.+)$"
    out = df[KEY].str.extract(pattern)
    df[Cluster_Granularity] = out[Cluster_Granularity]
    df[Product_Code_var] = out[Product_Code_var]
    # Merge with product/bundle description + Rank
    df1 = pd.merge(df, 
    	           prod_df[[Product_Code_var_data_prep, Product_Code_var, RANK, SERVICE_OUTPUT_NAME]], 
		           on= Product_Code_var, 
                   how = 'left')
    df10 = pd.merge(df1, 
                    df_price[[KEY_WEEK_blended , PRICE ,ALGO_REGULAR_PRICE, NO_OF_SITES]],
    	            on = KEY_WEEK_blended,  how = 'left')
    df2 = df10[FINAL_SUMMARY_COLS]
    df2.rename(columns = {KEY_WEEK_blended:'datekey'}, inplace = True)
    print('---------------------------------------------------------------------------------------')
    return df2

def creating_raw_data(df, prod_df):
    """
    Prepare raw dataset before merging with model results.
    - Builds KEY and Key-week
    - Adds price for Product_Site model
    - Joins with product/bundle description + Rank
    Returns DataFrame with enriched raw data
    """
    
    df[KEY] = df[Cluster_Granularity].astype(str) + "-" + df[Product_Code_var].astype(str)
    df[KEY] = np.where(df[KEY] == 'Clinics-nan-0', 'Clinics-NA-0', df[KEY])
    df[KEY_WEEK_blended] = df[KEY].astype(str)+ '-' +df[DATE].astype(str)
    df1 = pd.merge(df, prod_df, on =[Product_Code_var],  how = 'left')
    return df1

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
    df[KEY] = np.where(df[KEY] == 'Clinics-nan-0', 'Clinics-NA-0', df[KEY])
    
    # Extract Cluster + Product/Bundle from KEY
    pattern = rf"^(?P<{Cluster_Granularity}>[^-]+)-(?P<{Product_Code_var}>.+)$"
    out = df[KEY].str.extract(pattern)
    df[Cluster_Granularity] = out[Cluster_Granularity]
    df[Product_Code_var] = out[Product_Code_var]
    # Base merge columns
    merge_cols = [Product_Code_var, Product_Code_var_data_prep, RANK, SERVICE_OUTPUT_NAME]
    
    # Merge with product/bundle summary
    df1 = pd.merge(df, prod_df[merge_cols], on=Product_Code_var, how="left")
    # Weighted calculations
    df1["Weighted elasticity"] = df1[DOLLAR] * df1[ELASTICITY_COL]
    df1["Weighted  rsq"] = df1[DOLLAR] * df1[RSQ_COL]
    if PVALUE_PREFIX + ALGO_REGULAR_PRICE in df1.columns:
        df1["Weighted Pvalue"] = df1[DOLLAR] * df1[PVALUE_PREFIX + ALGO_REGULAR_PRICE]
        

    # Keep only standardized final columns
    df1['Check'] = np.where((((df[Correl_col] < 0) & (df[ELASTICITY_COL] < 0)) | ((df[Correl_col] > 0) & (df[ELASTICITY_COL] > 0))),1, 0 )
    df1['Significant ?'] = np.where((df[RSQ_COL] >= 0.5) & (df[PVALUE_PREFIX + ALGO_REGULAR_PRICE] <= 0.2), 1,0 )
    df1.rename(columns = {Cluster_Granularity:'Cluster'}, inplace = True)
    return df1

def blended_logic(model_output_df, model_result_1 ):
    """
    Applies blending logic across service-level and cluster-level aggregations to filter and align model results.

    This function:
    1. Maps `Cluster` → `New_cluster` → `big_cluster` in both input DataFrames.
    2. Aggregates `model_output_df` at service and cluster level to compute total net revenue.
    3. Retains the top entry (highest TotalNet) per service and big_cluster where significance is highest.
    4. Merges this filtered `final_model` back into both input DataFrames.

    Parameters:
    -----------
    model_output_df : pd.DataFrame
        DataFrame containing service-level output, cluster assignments, significance flags, and total net revenue.

    model_result_1 : pd.DataFrame
        DataFrame containing additional model results (e.g., prediction outputs) to be aligned with cluster logic.

    Returns:
    --------
    Tuple[pd.DataFrame, pd.DataFrame]
        - model_output_df_1 : Updated model output after blending and filtering by best-performing clusters.
        - model_result_2    : model_result_1 enriched with cluster hierarchy and filtered model logic.

    Notes:
    ------
    - Assumes external mappings: `cluster_h_map`, `clustermap`, and constant `SERVICE_OUTPUT_NAME`.
    - Drops duplicate rows to keep only the most significant and highest TotalNet cluster per service.
    - Columns `TotalNet_y`, `Significant ?_y` are removed post-merge to avoid conflicts.
    """
    # Map Cluster -> New_cluster
    model_output_df['New_cluster']=model_output_df.apply(lambda x: cluster_h_map.get(x.Cluster),axis=1)
    # Map New_cluster -> big_cluster
    model_output_df['big_cluster']=model_output_df.apply(lambda x:clustermap.get(x.New_cluster),axis=1)
    final_model=model_output_df.groupby([SERVICE_OUTPUT_NAME,'big_cluster','New_cluster','Significant ?']).agg({'TotalNet':'sum'}).reset_index()
    final_model=final_model.sort_values(by=['Significant ?','TotalNet'],ascending=[False,False]).drop_duplicates([SERVICE_OUTPUT_NAME,'big_cluster']).sort_values(by=SERVICE_OUTPUT_NAME)
    model_output_df_1 = model_output_df.merge(final_model,on=[SERVICE_OUTPUT_NAME,'big_cluster','New_cluster'])
    if 'TotalNet_y' in model_output_df_1.columns:
        model_output_df_1.drop(columns=['TotalNet_y', 'Significant ?_y'], inplace=True)
        model_output_df_1.rename(columns = {'TotalNet_x':'TotalNet', 'Significant ?_x':'Significant ?'}, inplace = True)
        
    # Map Cluster -> New_cluster  
    model_result_1['New_cluster']=model_result_1.apply(lambda x:cluster_h_map.get(x.Cluster),axis=1)
    # Map New_cluster -> big_cluster
    model_result_1['big_cluster']=model_result_1.apply(lambda x:clustermap.get(x.New_cluster),axis=1)
    model_result_2 = model_result_1.merge(final_model,on=[SERVICE_OUTPUT_NAME,'big_cluster','New_cluster'])
    
    return model_output_df_1, model_result_2, final_model
    
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
    raw_data_path       = os.path.join(module_path, config['regular_price']['output_data'].lstrip("/\\"))
    product_summary_path = os.path.join(module_path, config['output_summary_preparation']['product_description_path'].lstrip("/\\"))
    model_output_path = os.path.join(module_path,config['model']['output_summary_path'].lstrip("/\\"))
    model_summary_path = os.path.join(module_path,config['model']['model_summary_save_path'].lstrip("/\\"))
    rank_source_path = product_summary_path   # item_description.xlsx
    

    # 1) Rank calc
    product_summary = rank_calc(rank_source_path)

    # 2) Raw data
    raw_data = read_data(raw_data_path)
    raw_data1 = creating_raw_data(raw_data, product_summary)
    
    
    # 3) Model result summary
    model_result = read_data(model_result_path)
    model_result_1 = creating_variables_model_summary(model_result, product_summary, raw_data1)
    
    # 4) Model output
    model_out = model_output(model_output_path, product_summary)



    # 6) P-Value summary
    sign_summary = summarize_pvalues(model_summary_path)
    sign_summary.to_excel(rf".\output\significant_variable_summary_{itr}.xlsx", index=False)
    
    # 7 Blended Logic
    model_output_final, model_result_1_final, final_model_df = blended_logic(model_out, model_result_1 )
    # Save consistently here
    model_result_1_final.to_excel(r".\output\model_result_summary_ready.xlsx", index=False)
    model_output_final.to_excel(r".\output\output_summary_ready.xlsx", index=False)
    final_model_df.to_excel(r".\output\final_model_cluster_granularity.xlsx", index=False)
    base_dir_output = Path(__file__).resolve().parent.parent.parent
    # Path of template file
    template_path = base_dir_output/"Excel_Outputs/Sweden_Product_Cluster_Elasticity_Dashboard.xlsx"

    # Writing files to template
    write_df_preserve_named_range(
    file_path=template_path,
    df=model_output_final,
    sheet_name="Model_output",
    named_range="Model_output",
    start_cell="A1",
    refresh_pivots=False,   # keeps slicer state, refreshes pivot caches
    # refresh_all=False,     # set True only if you want to refresh external connections too
    visible=False)

    write_df_preserve_named_range(
    file_path=template_path,
    df=model_result_1_final,
    sheet_name="AvP",
    named_range="AvP",
    start_cell="A1",
    refresh_pivots=False,   # keeps slicer state, refreshes pivot caches
    # refresh_all=False,     # set True only if you want to refresh external connections too
    visible=False)