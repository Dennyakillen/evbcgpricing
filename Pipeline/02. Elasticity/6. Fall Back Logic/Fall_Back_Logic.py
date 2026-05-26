### Importing Libraries
import pandas as pd
import numpy as np
from datetime import datetime   # for timestamping saved files
import time
import os
# Get pandas default NA values
from pandas._libs.parsers import STR_NA_VALUES
from Constant import *
from pathlib import Path
import xlwings as xw

# Make a copy and remove "NA" and "na"
custom_na_values = set(STR_NA_VALUES) - {"NA", "na"}

### Bundle Level
# Site X Product

# Clinic/Hospital X Product from bundle

# Clinic/Hospital X Product - Individual

# Product across Clinic/Hospital from bundle

# Product across Clinic/Hospital - Individual

# Service within Clinic/Hospital - Individual

# Service across Clinic/Hospital - Individual




# Function: Read Excel Product Data
# -------------------------------------------------------------------
def read_excel_data(path, custom_na_values = None, keep_default_na_values = None):
    """
    Reads and processes a product-level Excel file.

    Steps:
    1. Loads an Excel file into a pandas DataFrame.
    2. Renames columns based on a provided dictionary.
    3. Filters out rows where the 'service' column equals 'Fee'.
    4. Generates a frequency count of combinations of `service` and `Cluster`.

    Parameters
    ----------
    path : str
        Path to the Excel file.
    column_rename_dict : dict
        Dictionary mapping old column names to new column names.

    Returns
    -------
    tuple
        dfproduct : pd.DataFrame
            Processed DataFrame with renamed columns and 'Fee' service rows removed.
        df_selected : pd.Series
            Frequency counts of unique `(service, Cluster)` combinations.
    """
    try:
        dfproduct = pd.read_excel(path, na_values=custom_na_values, keep_default_na=keep_default_na_values)
        print(f"Shape of Product dataframe output from Alteryx: {dfproduct.shape}")
        return dfproduct
    except Exception as error:
        print(f"The error is {error}")
        raise error

# Function: Read Excel Product Data
# -------------------------------------------------------------------
def read_excel(path, column_rename_dict):
    """
    Reads and processes a product-level Excel file.

    Steps:
    1. Loads an Excel file into a pandas DataFrame.
    2. Renames columns based on a provided dictionary.
    3. Filters out rows where the 'service' column equals 'Fee'.
    4. Generates a frequency count of combinations of `service` and `Cluster`.

    Parameters
    ----------
    path : str
        Path to the Excel file.
    column_rename_dict : dict
        Dictionary mapping old column names to new column names.

    Returns
    -------
    tuple
        dfproduct : pd.DataFrame
            Processed DataFrame with renamed columns and 'Fee' service rows removed.
        df_selected : pd.Series
            Frequency counts of unique `(service, Cluster)` combinations.
    """
    try:
        dfproduct = pd.read_excel(path, na_values=custom_na_values, keep_default_na=False)
        print(f"Shape of Product dataframe output from Alteryx: {dfproduct.shape}")
        dfproduct.rename(columns=column_rename_dict, inplace=True)

        print(f"No of missing values: {dfproduct.isnull().sum()}")
        dfproduct = dfproduct[dfproduct['service'] != 'Fee']
        print(f"Shape of Product dataframe After filtering out FEE service: {dfproduct.shape}")

        df_selected = dfproduct[[service, Cluster]].value_counts()
        return dfproduct, df_selected
    except Exception as error:
        print(f"The error is {error}")
        raise error

# ---------------------------------------------------------------------------    
# Function: To Apply Blended Logic to get cluster granularity
# -------------------------------------------------------------------


def aggregate_sales_by_granularity(df):
    """
    Aggregates SalesTotal and SalesTotal_YearEnding25 differently depending 
    on Service_Granularity and special business rules.

    Rules
    -----
    - If Service_Granularity == 'Clinics_CH':
        Group by ['ItemCode','ItemDescription','ProductGroupL4Name','New_Cluster','ID_Department']
    - If Service_Granularity == 'Hospital_CH':
        Group by ['ItemCode','ItemDescription','ProductGroupL4Name','New_Cluster','ID_Department']
    - If Service_Granularity == 'Clinics':
        Group by ['ItemCode','ItemDescription','ProductGroupL4Name','Cluster','ID_Department']
    - If Service_Granularity == 'Hospital':
        Group by ['ItemCode','ItemDescription','ProductGroupL4Name','Cluster','ID_Department']
    - If ProductGroupL4Name == 'Consumables' AND New_Cluster == 'Clinics':
        Group by ['ItemCode','ItemDescription','ProductGroupL4Name','New_Cluster','ID_Department']

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame containing at least:
        ['ItemCode','ItemDescription','ProductGroupL4Name','ID_Department',
         'Cluster','New_Cluster','Service_Granularity','SalesTotal','SalesTotal_YearEnding25']

    Returns
    -------
    pd.DataFrame
        Aggregated DataFrame with summed SalesTotal and SalesTotal_YearEnding25.
    """
    try:
        # --- Split DataFrame by conditions ---
        df_c = df[df['Service_Granularity'] == 'Clinics_CH']
        df_h = df[df['Service_Granularity'] == 'Hospital_CH']
        df_normal_c = df[df['Service_Granularity'] == 'Clinics']
        df_normal_h = df[df['Service_Granularity'] == 'Hospital']

        # --- Grouping for CH types ---
        grouped_c = (
            df_c.groupby(
                [ITEMCODE,ITEMDESCRIPTION,PRODUCTGROUPL4NAME,'New_Cluster',IDDEPARTMENT],
                as_index=False
            )[['SalesTotal','SalesTotal_YearEnding25']].sum()
        )
        grouped_h = (
            df_h.groupby(
                [ITEMCODE,ITEMDESCRIPTION,PRODUCTGROUPL4NAME,'New_Cluster',IDDEPARTMENT],
                as_index=False
            )[['SalesTotal','SalesTotal_YearEnding25']].sum()
        )

        if df["Service_Granularity"].isna().any():
            # take only missing Service_Granularity rows
            df_missing = df[df["Service_Granularity"].isna()]
            print(df_missing[[PRODUCTGROUPL4NAME, 'New_Cluster']].value_counts())

            
            grouped_missing = (
                df_missing.groupby([ITEMCODE,ITEMDESCRIPTION,PRODUCTGROUPL4NAME,'New_Cluster',IDDEPARTMENT],
                as_index=False
            )[['SalesTotal','SalesTotal_YearEnding25']].sum()
        )
        # --- Grouping for normal (non-CH) Clinics and Hospitals ---
        grouped_normal_c = (
            df_normal_c.groupby(
                [ITEMCODE,ITEMDESCRIPTION,PRODUCTGROUPL4NAME,'Cluster',IDDEPARTMENT],
                as_index=False
            )[['SalesTotal','SalesTotal_YearEnding25']].sum()
            .rename(columns={'Cluster': 'New_Cluster'})  # align with CH schema
        )
        grouped_normal_h = (
            df_normal_h.groupby(
                [ITEMCODE,ITEMDESCRIPTION,PRODUCTGROUPL4NAME,'Cluster',IDDEPARTMENT],
                as_index=False
            )[['SalesTotal','SalesTotal_YearEnding25']].sum()
            .rename(columns={'Cluster': 'New_Cluster'})  # align with CH schema
        )

        # --- Debug info (optional) ---
        print("Consumables (Clinics) shape:", grouped_missing.shape)
        print("Row counts (CH + normal):", 
              grouped_c.shape[0] + grouped_h.shape[0] + grouped_normal_c.shape[0] + grouped_normal_h.shape[0], 
              "Consumables:", grouped_missing.shape[0])

        # --- Combine all grouped results ---
        result = pd.concat(
            [grouped_c, grouped_h, grouped_normal_c, grouped_normal_h, grouped_missing], 
            ignore_index=True
        )

        # Replace 0s with NaN in YearEnding25 values (business rule)
        result['SalesTotal_YearEnding25'] = result['SalesTotal_YearEnding25'].replace(0, np.nan)

        print("Final result shape:", result.shape)

        return result

    except Exception as e:
        print(f"Error in aggregation: {e}")
        raise



# -------------------------------------------------------------------
# Function: Read Blended Model Cluster Data
# -------------------------------------------------------------------
def read_blended_model_data(blended_model_path, dfproduct):
    """
    Reads and processes blended model cluster data from an Excel file.

    This function:
    1. Loads a specified sheet from an Excel file.
    2. Renames columns using a predefined dictionary.

    Parameters:
    -----------
    blended_model_path : str
        Path to the blended model Excel file.

    blended_model_sheet_name : str
        Name of the sheet containing the blended model data.
    dfproduct : pd.DataFrame
        Product-level DataFrame used for mapping services.

    Returns:
    --------
    pd.DataFrame
        DataFrame containing the blended model data with renamed columns and service mapping.
    """
    try:
        dfcluster = pd.read_excel(blended_model_path)
        dfcluster.rename(columns=column_rename_dict_df_blended, inplace=True)

        # Map services from product file
        service_map = dfproduct[[ProductKey, service]].drop_duplicates()
        service_map[ProductKey] = service_map[ProductKey].astype(str)
        dfcluster = dfcluster.merge(service_map, on=ProductKey)

        return dfcluster
    except Exception as error:
        print(f"The error is {error}")
        raise error

# -------------------------------------------------------------------
# Function: Read Site-Level Data
# -------------------------------------------------------------------
def reading_site_level_data(path, rename_dict):
    """
    Reads and processes site-level elasticity data from Excel.

    Parameters
    ----------
    path : str
        Path to the site-level Excel file.
    rename_dict : dict
        Dictionary to rename columns.

    Returns
    -------
    pd.DataFrame
        Processed DataFrame with SiteCode and ProductKey extracted from KEY column.
    """
    try:
        dfsite = pd.read_excel(path)
        dfsite.rename(columns=rename_dict, inplace=True)

        # Extract Cluster and ItemCode from composite KEY
        pat = r'^(?P<Clusters>[^-]+)-(?P<ItemCode>.+)$'
        out = dfsite['KEY'].str.extract(pat)

        dfsite[SiteCode]        = out[Cluster]
        dfsite[ProductKey]        = out['ItemCode']
        return dfsite
    except Exception as error:
        print(f"The error is {error}")
        raise error

# -------------------------------------------------------------------
# Function: Read Bundle-Cluster Data
# -------------------------------------------------------------------
def reading_bundle_cluster_level_data(path, rename_column_dict_name):
    """
    Reads and processes bundle-cluster elasticity data.

    Parameters
    ----------
    path : str
        Path to the bundle-level Excel file.
    rename_column_dict_name : dict
        Dictionary to rename columns.

    Returns
    -------
    tuple
        dfbundle : pd.DataFrame
            Processed bundle-level DataFrame.
        dfbundle_exploded : pd.DataFrame
            Exploded DataFrame where multi-product bundles are split into rows.
    """
    try:
        dfbundle=pd.read_excel(path)
        pat = r'^(?P<Cluster>[^-]+)-(?P<Bundle_code>.+)$'
        out = dfbundle['KEY'].str.extract(pat)

        dfbundle[Cluster]        = out['Cluster']
        dfbundle[ProductKey]        = out['Bundle_code']
        dfbundle[ProductKey] = dfbundle["ProductKey"].str.strip()

        dfbundle.rename(columns = rename_column_dict_name, inplace=True)
        dfbundle=df_cleanup(dfbundle,Cluster)
        dfbundle=dfbundle.rename(columns={
	         'significant_Clusters':'significant_bundles',
	         'ELASTICITY_PRICE':ELASTICITY_basket_price})

        # Handle exploded bundles
        dfbundle2 = dfbundle.copy()
        dfbundle2[ProductKey] = dfbundle2["ProductKey"].str.split(",")

        # Step 2: explode the lists into separate rows
        
        dfbundle_exploded = dfbundle2.explode("ProductKey").reset_index(drop=True)
        print(dfbundle_exploded.head())
        return dfbundle, dfbundle_exploded
    except Exception as error:
        print(f"The error is {error}")
        raise error

# -------------------------------------------------------------------
# Function: Mark Significant Models
# -------------------------------------------------------------------
def df_cleanup(dfcluster, level):
    """
    Creates a significance flag column for a given level.

    The function applies the following logic:
    - Marks as significant (1) if:
    - RSQ ≥ 0.5 (rounded to 2 decimals)
    - PVALUE_PRICE ≤ 0.20 (rounded to 2 decimals)
    - ELASTICITY_PRICE between -10 and 0
    - Otherwise, marks as not significant (0).

    Parameters:
    -----------
    dfcluster : pd.DataFrame
        Cluster-level model results with columns: RSQ, PVALUE_PRICE, ELASTICITY_PRICE.

    level : str
        Suffix used to name the significance column (e.g., 'site', 'bundle').

    Returns:
    --------
    pd.DataFrame
        DataFrame with a new column `significant_<level>` added.

    Raises:
    -------
    Exception
        Propagates any exception that occurs while applying the significance logic.
    """

    try:
        dfcluster['significant_{}'.format(level)]=np.where((round(dfcluster['RSQ'],2)>=.5)&(round(dfcluster['PVALUE_PRICE'],2)<=.20)
                                                            &(dfcluster['ELASTICITY_PRICE']<0)&(dfcluster['ELASTICITY_PRICE']>-10),1,0)
        return dfcluster
    except Exception as error:
        print(f"The error is {error}")
        raise error

# -------------------------------------------------------------------
# Function: Significant Cluster Summaries
# -------------------------------------------------------------------
def significant_cluster_summary(dfcluster):
    """
    Builds fallback elasticities at product, service-within-cluster, and service levels.

    Parameters
    ----------
    dfcluster : pd.DataFrame
        Cluster-level results with significance flags.

    Returns
    -------
    tuple
        sig_cluster : pd.DataFrame
            Weighted elasticities at product level.
        sig_cluster_service_within : pd.DataFrame
            Weighted elasticities at service x cluster level.
        sig_cluster_service : pd.DataFrame
            Weighted elasticities at service level.
    """
    try:
        # Product-level fallback
        sig_cluster=dfcluster[dfcluster['significant_Clusters']==1]
        sig_cluster['wt_elas_cluster']=sig_cluster[ELASTICITY_PRICE]*sig_cluster[TotalNet]
        sig_cluster=sig_cluster.groupby(ProductKey).agg({'wt_elas_cluster':'sum',TotalNet:'sum'}).reset_index()
        sig_cluster['wt_elas_cluster']=sig_cluster['wt_elas_cluster']/sig_cluster[TotalNet]
        
        # Service-within-cluster fallback
        sig_cluster_service=dfcluster[dfcluster['significant_Clusters']==1]
        sig_cluster_service['wt_elas_within_cluster_service']=sig_cluster_service[ELASTICITY_PRICE]*sig_cluster_service[TotalNet]
        sig_cluster_service_within=sig_cluster_service.groupby([service,Cluster]).agg({'wt_elas_within_cluster_service':'sum',TotalNet:'sum'}).reset_index()
        sig_cluster_service_within['wt_elas_within_cluster_service']=sig_cluster_service_within['wt_elas_within_cluster_service']/sig_cluster_service_within[TotalNet]
        
        # Service-level fallback
        sig_cluster_service=dfcluster[dfcluster['significant_Clusters']==1]
        sig_cluster_service['wt_elas_cluster_service']=sig_cluster_service[ELASTICITY_PRICE]*sig_cluster_service[TotalNet]
        sig_cluster_service=sig_cluster_service.groupby(service).agg({'wt_elas_cluster_service':'sum',TotalNet:'sum'}).reset_index()
        sig_cluster_service['wt_elas_cluster_service']=sig_cluster_service['wt_elas_cluster_service']/sig_cluster_service[TotalNet]

        return sig_cluster, sig_cluster_service_within, sig_cluster_service
    except Exception as error:
        print(f"The error is {error}")
        raise error

# -------------------------------------------------------------------
# Function: Significant Bundle Summaries
# -------------------------------------------------------------------
def significant_bundle_summary(dfbundle_exploded):
    """
    Builds fallback elasticities for bundles at product-cluster and product level.

    Parameters
    ----------
    dfbundle_exploded : pd.DataFrame
        Exploded bundle DataFrame with significance flags.

    Returns
    -------
    tuple
        sig_cluster_bundle : pd.DataFrame
            Weighted elasticities at product x cluster level.
        sig_bundle : pd.DataFrame
            Weighted elasticities at product level across bundles.
    """
    try:
        # Product-cluster bundle fallback
        sig_cluster_bundle=dfbundle_exploded[dfbundle_exploded['significant_bundles']==1]
        sig_cluster_bundle['wt_elas_cluster_bundle']=sig_cluster_bundle[ELASTICITY_basket_price]*sig_cluster_bundle[Basket_Revenue]
        sig_cluster_bundle=sig_cluster_bundle.groupby([ProductKey,Cluster]).agg({'wt_elas_cluster_bundle':'sum',Basket_Revenue:'sum'}).reset_index()
        sig_cluster_bundle['wt_elas_cluster_bundle']=sig_cluster_bundle['wt_elas_cluster_bundle']/sig_cluster_bundle[Basket_Revenue]
        sig_cluster_bundle[ProductKey]=sig_cluster_bundle[ProductKey].astype(str)

        # Product-bundle fallback
        sig_bundle=dfbundle_exploded[dfbundle_exploded['significant_bundles']==1]
        sig_bundle['wt_elas_bundle']=sig_bundle[ELASTICITY_basket_price]*sig_bundle[Basket_Revenue]
        sig_bundle=sig_bundle.groupby(ProductKey).agg({'wt_elas_bundle':'sum',Basket_Revenue:'sum'}).reset_index()
        sig_bundle['wt_elas_bundle']=sig_bundle['wt_elas_bundle']/sig_bundle[Basket_Revenue]
        sig_bundle[ProductKey]=sig_bundle[ProductKey].astype(str)

        return sig_cluster_bundle, sig_bundle
    except Exception as error:
        print(f"The error is {error}")
        raise error

# -------------------------------------------------------------------
# Function: Merge All Levels into One DataFrame
# -------------------------------------------------------------------
def creating_one_df(dfproduct, dfsite, sig_cluster_bundle, sig_cluster, sig_bundle, sig_cluster_service_within, sig_cluster_service):
    """
    Creates a unified DataFrame merging product, site, cluster, and bundle level elasticities.

    Parameters
    ----------
    dfproduct : pd.DataFrame
        Product-level data.
    dfsite : pd.DataFrame
        Site-level elasticity results.
    sig_cluster_bundle : pd.DataFrame
        Significant product x cluster bundle elasticities.
    sig_cluster : pd.DataFrame
        Significant product-level cluster elasticities.
    sig_bundle : pd.DataFrame
        Significant product-level bundle elasticities.
    sig_cluster_service_within : pd.DataFrame
        Service x cluster fallback elasticities.
    sig_cluster_service : pd.DataFrame
        Service-level fallback elasticities.

    Returns
    -------
    pd.DataFrame
        Final merged fallback DataFrame with chosen elasticity and source level.
    """
    try:
        dv1=dfproduct.merge(dfsite[[SiteCode,ProductKey,ELASTICITY_PRICE,'significant_SiteCode','RSQ','PVALUE_PRICE']],on=[SiteCode,ProductKey],how='left')
        dv2=dv1.merge(dfcluster[[Cluster,ProductKey,ELASTICITY_PRICE,'significant_Clusters','RSQ','PVALUE_PRICE']],on=[Cluster,ProductKey],how='left')
        dv2=dv2.rename(columns={'ELASTICITY_PRICE_x':'ELASTICITY_PRICE_site','ELASTICITY_PRICE_y':'ELASTICITY_PRICE_cluster',
                            'RSQ_x':'RSQ_site','PVALUE_PRICE_x':'PVALUE_PRICE_site','RSQ_y':'RSQ_cluster','PVALUE_PRICE_y':'PVALUE_PRICE_cluster'})
        dv3=dv2.merge(sig_cluster_bundle.drop(Basket_Revenue,axis=1),on=[ProductKey,Cluster],how='left')
        dv4=dv3.merge(sig_cluster.drop(TotalNet,axis=1),on=[ProductKey],how='left')
        dv5=dv4.merge(sig_bundle.drop(Basket_Revenue,axis=1),on=[ProductKey],how='left')
        dv6=dv5.merge(sig_cluster_service_within.drop(TotalNet,axis=1),on=[service,Cluster],how='left')
        dv7=dv6.merge(sig_cluster_service.drop(TotalNet,axis=1),on=[service],how='left')
	# Rename columns and enforce numeric types
        dv7 = dv7.rename(columns=rename_map_merged_dv7)
        dv7[numeric_cols] = dv7[numeric_cols].apply(pd.to_numeric, errors="coerce")
	# Select final elasticity from multiple levels
        dv7["final_elasticity"] = (dv7["F1_site_level"].where(dv7["significant_SiteCode"].eq(1))
                                    .combine_first(dv7["F2_bundle_level"])
                                    .combine_first(dv7["F3_cluster_level"].where(dv7["significant_Clusters"].eq(1)))
                                    .combine_first(dv7["F4_bundle_across_clusters"])
                                    .combine_first(dv7["F5_product_across_clusters"])
                                    .combine_first(dv7["F6_service_within_cluster"])
                                    .combine_first(dv7["F7_service_across_clusters"]))
	# Track elasticity source level
        conditions = [
                        dv7["significant_SiteCode"].eq(1) & dv7["F1_site_level"].notna(),
                        dv7["F2_bundle_level"].notna(),
                        dv7["significant_Clusters"].eq(1) & dv7["F3_cluster_level"].notna(),
                        dv7["F4_bundle_across_clusters"].notna(),
                        dv7["F5_product_across_clusters"].notna(),
                        dv7["F6_service_within_cluster"].notna(),
                        dv7["F7_service_across_clusters"].notna(),
                    ]
        # Use a string default to avoid dtype conflict, then convert blanks to NaN if you prefer
        dv7["elasticity_level"] = np.select(conditions, elasticity_level_labels, default="")  # <- string default
        dv7["elasticity_level"] = dv7["elasticity_level"].replace({"": pd.NA})
        # (Optional) make elasticity_level an ordered categorical
        dv7["elasticity_level"] = pd.Categorical(
            dv7["elasticity_level"],
            categories=elasticity_level_labels,
            ordered=True
        )
        
        dv7['PVALUE_PRICE']=np.where(dv7['elasticity_level'].str.contains('F1'),dv7['PVALUE_PRICE_site'],np.where(dv7['elasticity_level'].str.contains('F2'),dv7['PVALUE_PRICE_cluster'],None))
        dv7['RSQ']=np.where(dv7['elasticity_level'].str.contains('F1'),dv7['RSQ_site'],np.where(dv7['elasticity_level'].str.contains('F2'),dv7['RSQ_cluster'],None))

        dv8=dv7[['ProductKey', 'ProductDescription', 'service', 'Clusters', 'SiteCode',
            'TotalNet', 'year ending 2025 revenue', 'PVALUE_PRICE','RSQ', 'final_elasticity', 'elasticity_level']]
        dv8['Product Granularity']=dv8['elasticity_level'].apply(lambda x:elasticity_to_product_granularity.get(x))
        dv8['site Granularity']=dv8['elasticity_level'].apply(lambda x:elasticity_to_site_granularity.get(x))
        dv8['Weighted Elasticity'] = dv8[TotalNet]*dv8['final_elasticity']
        return dv8
    except Exception as error:
        print(f"The error is {error}")
        raise error

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


# -------------------------------------------------------------------
# Main Script Execution
# -------------------------------------------------------------------
if __name__ == '__main__':
    start_time = time.time()   # start timer
    
    # Read Product Level Excel
    df_allprod = read_excel_data(df_all_product_path, custom_na_values = custom_na_values, keep_default_na_values = False)
    ## Excluding fee services
    base_dir = Path(__file__).resolve().parent.parent
    df_allprod = df_allprod[df_allprod[PRODUCTGROUPL4NAME].str.lower().str.strip() != 'fee']
    # Reading Belnded Output file for cluster granularity
    df_blended_cluster_gran = read_excel_data(os.path.join(base_dir, blended_output_path), custom_na_values = None, keep_default_na_values = None)
    # Merging the above two files
    df_blended_cluster_gran.rename(columns = {'Service':PRODUCTGROUPL4NAME, 'New_cluster':"Service_Granularity", "big_cluster":"New_Cluster"}, inplace = True)
    dff_blended = pd.merge(df_allprod, df_blended_cluster_gran[[PRODUCTGROUPL4NAME, 'Service_Granularity', 'New_Cluster']], on = [PRODUCTGROUPL4NAME, 'New_Cluster'], how = 'left')
    dff_blended_agg = aggregate_sales_by_granularity(dff_blended)
    dff_blended_agg_file = f"Complete_Product_Data_Blended.xlsx"
    dff_blended_agg_file_name_path = os.path.join(output_path, dff_blended_agg_file)
    dff_blended_agg.to_excel(dff_blended_agg_file_name_path, index=False, engine="openpyxl")
    # Read product-level Excel
    dfproduct, df_selected = read_excel(df_product_path, column_rename_dict_df_product)
    
    # Read blended cluster-level data
    dfcluster = read_blended_model_data(os.path.join(base_dir, blended_model_path), dfproduct)
    dfcluster=df_cleanup(dfcluster,Cluster)
    dfcluster = dfcluster[dfcluster_column_order]
    print(f"Significant Cluster Summary: {dfcluster['significant_Clusters'].value_counts()}")
    print(dfcluster.head())

    # Generate cluster summaries
    sig_cluster, sig_cluster_service_within, sig_cluster_service = significant_cluster_summary(dfcluster)
    
    ### Product Site Level Model
    dfsite = reading_site_level_data(os.path.join(base_dir, prod_site_level_path), column_rename_dict_df_site)
    dfsite=df_cleanup(dfsite,SiteCode)
    dfsite_temp = dfsite.groupby(ProductKey).agg(SiteCode_count = (SiteCode,'count'),SigSites_Sum = ('significant_SiteCode','sum')).reset_index()
    dfsite1 = dfsite.merge(dfsite_temp, on='ProductKey',how='left')
    dfsite1['significant_SiteCode_up'] = np.where(dfsite1['SigSites_Sum']>=10,dfsite1['significant_SiteCode'],0)
    dfsite1 = dfsite1.drop('significant_SiteCode',axis=1)
    dfsite = dfsite1.copy()
    dfsite = dfsite.rename({'significant_SiteCode_up':'significant_SiteCode'},axis=1)
    
    ### Bundle Cluster Level Model
    dfbundle, dfbundle_exploded = reading_bundle_cluster_level_data(os.path.join(base_dir, bundle_cluster_level_path), column_rename_dict_df_bundle)
    # dfbundle=df_cleanup(dfbundle,Cluster)
    
    sig_cluster_bundle, sig_bundle = significant_bundle_summary(dfbundle_exploded)
    
    # Ensure correct datatypes
    dfproduct[ProductKey] = dfproduct[ProductKey].astype(str)
    dfproduct[Cluster] = dfproduct[Cluster].astype(str)
    dfproduct[SiteCode] = dfproduct[SiteCode].astype(str)
    dfsite[SiteCode] = dfsite[SiteCode].astype(str)
    dfsite[ProductKey] = dfsite[ProductKey].astype(str)
    
    dv8 = creating_one_df(dfproduct, dfsite, sig_cluster_bundle, sig_cluster, sig_bundle, sig_cluster_service_within, sig_cluster_service)
    dv8.to_excel("Final_Fallback_Data.xlsx", index=False, engine="openpyxl")
    
    # Save final output with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"Final_Fallback_Data_{timestamp}.xlsx"
    product_site_summ_file_name = f'Product_site_check_{timestamp}.csv'
    product_site_summ_file_name_path = os.path.join(output_path, product_site_summ_file_name)
    dfsite_temp.sort_values('SigSites_Sum', ascending=False).to_csv(product_site_summ_file_name_path,index=False)
    output_file_path = os.path.join(output_path, output_file)
    dv8.to_excel(output_file_path, index=False, engine="openpyxl")

    base_dir_output = Path(__file__).resolve().parent.parent
    # Path of template file
    template_path = base_dir_output/"Excel_Outputs/Sweden_Fallback.xlsx"
    write_df_preserve_named_range(
    file_path=template_path,
    df=dv8,
    sheet_name="Raw",
    named_range="raw",
    start_cell="A1",
    refresh_pivots=False,   # keeps slicer state, refreshes pivot caches
    # refresh_all=False,     # set True only if you want to refresh external connections too
    visible=False)
    print(f"Saved final fallback data to {output_file_path}")
    
    # ----------------------------------------------------------------
    # Print total execution time
    # ----------------------------------------------------------------
    end_time = time.time()
    elapsed = end_time - start_time
    mins, secs = divmod(elapsed, 60)
    print(f"Total time taken: {int(mins)} min {secs:.2f} sec")