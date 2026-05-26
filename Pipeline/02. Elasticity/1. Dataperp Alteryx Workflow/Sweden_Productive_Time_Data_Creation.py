### Importing Libraries
import pandas as pd
from datetime import datetime
import numpy as np
import os
from Constants import *
import time


#### -------------------------------------------------Functions --------------------------------
### Reading csv or excel files
def read_data(path, sheetname=None, csv_encoding =None, csv_encoding_errors = None):
    """
    Reads a dataset from the given file path based on its extension.

    Supports reading from:
    - CSV files (with 'cp1252' encoding and error handling)
    - Excel files (.xlsx and .xls using openpyxl engine)

    Parameters:
    ----------
    path : str
        Full path to the data file. Supported formats: .csv, .xlsx, .xls
    sheetname : str, optional
        Name of the sheet to read (only required for Excel files).
    csv_encoding : str, optional
        Encoding of the csv file (only required for CSV files).
    csv_encoding_errors : str, optional
        Parsing Encoding Errors of the csv file (only required for CSV files).

    Returns:
    -------
    pd.DataFrame
        A pandas DataFrame containing the data from the input file.

    Raises:
    ------
    ValueError
        If the file type is not supported.
    """
    try:
        # Extract file extension clearly
        file_extension = os.path.splitext(path)[1].lower()
        
        # Check file type and read accordingly
        if file_extension == ".csv":
            print('Reading CSV file')
            df = pd.read_csv(path, encoding=csv_encoding, encoding_errors=csv_encoding_errors)
        elif file_extension in [".xlsx", ".xls"]:
            print('Reading Excel file')
            df = pd.read_excel(path, sheet_name = sheetname)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        return df
    except Exception as error:
        print(f"The error is in read data function and the error is {error}")
        raise
    
def format_time(seconds):
    """Return formatted string: M min S sec if >= 60s, else S sec"""
    if seconds >= 60:
        mins, secs = divmod(seconds, 60)
        return f"{int(mins)} min {secs:.1f} sec"
    else:
        return f"{seconds:.2f} sec"

### Cleaning Productive time Data
def clean_data(df_latest, col_dict, weeks_to_remove):
    """
    Cleans and preprocesses the productive time DataFrame.

    Steps performed:
    1. Renames columns based on the provided dictionary.
    2. Drops 'CostCenterCode' if present, then renames 'ID_Department' → 'CostCenterCode'.
    3. Removes rows where 'Cluster' is null.
    4. Removes rows for specific (Weeknumber, Year) combinations provided.
    5. Prints shapes of the DataFrame at different stages for validation.

    Parameters
    ----------
    df_latest : pd.DataFrame
        The input DataFrame containing productive time data.
    col_dict : dict
        Dictionary mapping original column names to standardized names.
    weeks_to_remove : list of tuple
        List of (week_number, year) pairs to be removed.
        Example: [(15, 2023), (32, 2024)]

    Returns
    -------
    pd.DataFrame
        Cleaned and preprocessed DataFrame.

    Raises
    ------
    Exception
        If an error occurs during processing.
    """
    try:
        # Standardize column names
        df_latest.rename(columns=col_dict, inplace=True)

        # Drop column only if it exists
        if "CostCenterCode" in df_latest.columns:
            df_latest.drop(columns=["CostCenterCode"], inplace=True)

        # Rename department column
        if "ID_Department" in df_latest.columns:
            df_latest.rename(columns={"ID_Department": "CostCenterCode"}, inplace=True)

        # Drop rows where cluster is missing
        df_latest = df_latest[~df_latest["Cluster"].isnull()]
        print(f"The shape of dataframe is {df_latest.shape}")

        # Remove specified week/year combinations
        for week, year in weeks_to_remove:
            df_latest = df_latest[~((df_latest["Weeknumber"] == week) & (df_latest["Year"] == year))]
            print(f"Removed Week {week}, Year {year}. Current shape: {df_latest.shape}")

        return df_latest

    except Exception as error:
        print(f"The error is in clean_data function and the error is {error}")
        raise


def update_week1_with_prior(df_latest):
    """
    Updates Week 1 rows in the productive time dataset by using the maximum value 
    between Week 1 of the current year and the last available week (52 or 53) 
    from the previous year. Removes Week 53 rows after adjustment.

    Steps:
    1. Copy the input DataFrame and initialize an 'UpdatedSumProductiveTime' column.
    2. For each year having Week 1:
       - Find Week 53 (or fallback to Week 52) of the previous year.
       - Shift these rows to align with Week 1 of the current year.
       - Take the maximum of productive time across the shifted and current Week 1 rows.
    3. Replace Week 1 rows with updated values.
    4. Drop original Week 1 and Week 53 rows.
    5. Append updated Week 1 rows and sort the DataFrame.

    Parameters
    ----------
    df_latest : pd.DataFrame
        Input DataFrame containing at least the following columns (from constants.py):
        YEAR, WEEKNUMBER, COSTCENTERCODE, SUMPRODUCTIVETIME

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame with Week 1 values updated and Week 53 removed.
        Includes an additional column 'UpdatedSumProductiveTime'.

    Raises
    ------
    Exception
        If required columns are missing or if an error occurs in processing.
    """
    try:
        # Step 1: Copy and initialize
        df = df_latest.copy()
        df[UPDATED_SUMPRODUCTIVETIME] = df[SUMPRODUCTIVETIME]

        # Step 2: Identify years with Week 1
        years = df[df[WEEKNUMBER] == 1][YEAR].unique()

        updated_week1_list = []

        for year in years:
            # Week 1 rows
            w1 = df[(df[YEAR] == year) & (df[WEEKNUMBER] == 1)].copy()

            # Prior year Week 53 (or fallback to 52)
            w53 = df[(df[YEAR] == year - 1) & (df[WEEKNUMBER] == 53)].copy()
            if w53.empty:
                prior = df[(df[YEAR] == year - 1) & (df[WEEKNUMBER] == 52)].copy()
            else:
                prior = w53.copy()

            # Shift to Week 1 of current year
            prior[YEAR] += 1
            prior[WEEKNUMBER] = 1

            # Combine and take maximum
            combined = pd.concat([w1, prior])
            max_values = (
                combined.groupby([YEAR, WEEKNUMBER, COSTCENTERCODE], as_index=False)[SUMPRODUCTIVETIME]
                .max()
                .rename(columns={SUMPRODUCTIVETIME: UPDATED_SUMPRODUCTIVETIME})
            )

            # Merge to preserve structure
            updated = pd.merge(
                w1.drop(columns=[UPDATED_SUMPRODUCTIVETIME]),
                max_values,
                on=[YEAR, WEEKNUMBER, COSTCENTERCODE],
                how="left",
            )

            updated_week1_list.append(updated)

        # Step 3: Finalize updated Week 1 rows
        updated_week1 = pd.concat(updated_week1_list, ignore_index=True)

        # Step 4: Drop original Week 1 and Week 53
        df = df[~((df[WEEKNUMBER] == 1) | (df[WEEKNUMBER] == 53))]

        # Step 5: Append updated Week 1 and sort
        df = pd.concat([df, updated_week1], ignore_index=True)
        df = df.sort_values([YEAR, WEEKNUMBER, COSTCENTERCODE]).reset_index(drop=True)
        print(f"Week 1 row count: {df[df[WEEKNUMBER] == 1].shape[0]}")
        print(f"Week 53 still present? {'Yes' if (df[WEEKNUMBER] == 53).any() else 'No'}")
        print(f"Nulls in UpdatedSumProductiveTime: {df[UPDATED_SUMPRODUCTIVETIME].isna().sum()}")

        # Compare values
        changed = df[df[SUMPRODUCTIVETIME] != df[UPDATED_SUMPRODUCTIVETIME]]
        print(f"\n Week 1 rows updated: {len(changed)}")

        return df

    except Exception as error:
        print(f"Error in update_week1_with_prior: {error}")
        raise

# Safe function to get Monday of a valid ISO week, skip invalid (like week 53 in some years)
def get_week_start_safe(year, week):
    try:
        return datetime.fromisocalendar(int(year), int(week), 1)  # 1 = Monday
    except ValueError:
        return pd.NaT  # Return NaT (Not a Time) for invalid week
    

def preprocess_productive_time(df1, df, id_depart_cost_center_code_mapping_df):
    """
    Cleans and standardizes productive time data, applies filtering, 
    and merges with department-cost center mapping.

    Steps performed:
    1. Rename columns using predefined mapping from constants.py.
    2. Filter rows where staff category matches "vets".
    3. Convert 'Date' column to datetime.
    4. Filter rows for specified cost center codes.
    5. Merge with pre-loaded ID-department mapping file.
    6. Replace 'CostCenterCode' with mapped values.
    7. Derive 'week_starting_monday' from 'Date'.
    8. Assign a fixed cluster name (e.g., "Clinics 1").
    9. Keep only relevant columns for modeling.
    10. Drop rows for excluded weeks (e.g., special dates).
    11. Append processed rows to the main DataFrame.

    Parameters
    ----------
    df1 : pd.DataFrame
        OLD Raw productive time DataFrame.
    df : pd.DataFrame
        Base DataFrame to which processed rows will be appended.
    id_depart_cost_center_code_mapping_df : pd.DataFrame
        Mapping DataFrame for CostCenterCode → ID_Department.

    Returns
    -------
    pd.DataFrame
        Updated DataFrame with appended and cleaned productive time rows.
    """
    try:
        # Step 1: Rename columns (mapping defined in constants.py)
        df1.rename(columns=PRODUCTIVE_TIME_RENAME_MAP, inplace=True)

        # Step 2: Filter for staff category "vets"
        df2 = df1[df1[STAFFCATEGORYDESCRIPTION].str.strip().str.lower() == STAFF_CATEGORY_FILTER]
        df2[DATE] = pd.to_datetime(df2[DATE])

        print(f"Date range: {df2[DATE].min()} to {df2[DATE].max()}")

        # Step 3: Keep only specific cost center codes (from constants.py)
        ab = df2[df2[COSTCENTERCODE].isin(COST_CENTER_CODES_FILTER)]

        # Step 4: Merge with mapping DataFrame
        ab = pd.merge(ab, id_depart_cost_center_code_mapping_df, on=COSTCENTERCODE, how="left")
        print("Null check after merging:\n", ab.isnull().sum())

        # Step 5: Replace cost center code with mapped department code
        ab.drop(columns=[COSTCENTERCODE], inplace=True)
        ab.rename(columns={"ID_Department": COSTCENTERCODE}, inplace=True)

        # Step 6: Create week_starting_monday column
        ab[WEEKSTARTINGMONDAY] = ab[DATE] - pd.to_timedelta(ab[DATE].dt.weekday, unit="d")

        # Step 7: Assign fixed cluster name (from constants.py)
        ab[CLUSTER] = DEFAULT_CLUSTER_NAME

        # Step 8: Keep only required columns
        ab = ab[[WEEKSTARTINGMONDAY, COSTCENTERCODE, UPDATED_SUMPRODUCTIVETIME, CLUSTER]]
        print("Shape after filtering:", ab.shape)

        # Step 9: Remove excluded weeks (from constants.py)
        ab = ab[~ab[WEEKSTARTINGMONDAY].isin(EXCLUDED_WEEKS)]
        print("Shape after excluding weeks:", ab.shape)

        # Step 10: Align with final schema and append to main df
        df = df[[WEEKSTARTINGMONDAY, COSTCENTERCODE, UPDATED_SUMPRODUCTIVETIME, CLUSTER]]
        df = pd.concat([df, ab])

        print("Shapes → df1:", df1.shape, "df2:", df2.shape, "final df:", df.shape)
        return df

    except Exception as error:
        print(f"Error in preprocess_productive_time: {error}")
        raise



def interpolate_productive_time(df):
    """
    Aggregates productive time data to weekly sums per cost center,
    fills in missing weeks with interpolation, and flags interpolated values.

    Steps:
    1. Keep only relevant columns and rename UpdatedSumProductiveTime → SumProductiveTime.
    2. Aggregate productive time at [COSTCENTERCODE, WEEK_STARTING_MONDAY].
    3. Build a complete cost center x week grid covering the full date range.
    4. Merge original weekly sums into the full grid.
    5. Add a flag 'WasInterpolated' to indicate missing values before interpolation.
    6. Interpolate missing weekly values within each cost center.
    7. Sort by cost center and week.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame containing at least:
        - COSTCENTERCODE
        - UPDATED_SUMPRODUCTIVETIME
        - WEEK_STARTING_MONDAY

    Returns
    -------
    pd.DataFrame
        Weekly interpolated DataFrame with columns:
        - COSTCENTERCODE
        - WEEK_STARTING_MONDAY
        - SumProductiveTime
        - WasInterpolated
        - SumProductiveTime_Interpolated
    """
    try:
        # Step 1: Keep only relevant columns
        df = df[[COSTCENTERCODE, UPDATED_SUMPRODUCTIVETIME, WEEKSTARTINGMONDAY]].copy()

        # Rename updated productive time column
        df.rename(columns={UPDATED_SUMPRODUCTIVETIME: SUMPRODUCTIVETIME}, inplace=True)

        # Step 2: Aggregate weekly sum
        weekly = df.groupby([COSTCENTERCODE, WEEKSTARTINGMONDAY], as_index=False)[SUMPRODUCTIVETIME].sum()

        # Step 3: Build full cost center × week grid
        costcenters = weekly[COSTCENTERCODE].unique()
        full_weeks = pd.date_range(
            weekly[WEEKSTARTINGMONDAY].min(),
            weekly[WEEKSTARTINGMONDAY].max(),
            freq="W-MON"
        )
        all_combinations = pd.MultiIndex.from_product(
            [costcenters, full_weeks],
            names=[COSTCENTERCODE, WEEKSTARTINGMONDAY]
        ).to_frame(index=False)

        # Step 4: Merge with original weekly sums
        merged = pd.merge(all_combinations, weekly, on=[COSTCENTERCODE, WEEKSTARTINGMONDAY], how="left")

        # Step 5: Add interpolation flag
        merged["WasInterpolated"] = merged[SUMPRODUCTIVETIME].isna()

        # Step 6: Interpolate missing values within each cost center
        merged["SumProductiveTime_Interpolated"] = (
            merged.groupby(COSTCENTERCODE)[SUMPRODUCTIVETIME]
            .transform(lambda x: x.interpolate())
        )

        # Step 7: Sort results
        merged = merged.sort_values([COSTCENTERCODE, WEEKSTARTINGMONDAY]).reset_index(drop=True)
        print(f"Distribution of Interpolated rows: {merged['WasInterpolated'].value_counts()}")

        return merged

    except Exception as error:
        print(f"Error in interpolate_productive_time: {error}")
        raise
    
def fill_missing_sites_with_cluster_mean(df, cutoff_date, cluster_name, missing_sites):
    """
    Fills missing site-level FTE data with cluster-level mean values.

    Business logic:
    ----------------
    Some sites (ID_Departments) do not have data after a certain cutoff date. 
    To ensure continuity, we take the cluster mean FTE_Interpolated values 
    and assign them to these sites for the missing period.

    Steps performed:
    ----------------
    1. Filter data for weeks on/after cutoff_date.
    2. Restrict to the specified cluster (e.g., "Clinics 1").
    3. Aggregate to get cluster mean FTE by [CLUSTER, WEEKSTARTINGMONDAY].
    4. Duplicate this cluster-level mean for each missing site (ID_Department).
    5. Append these duplicated rows back to the original DataFrame.
    6. Save the final DataFrame to Excel.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame containing at least:
        - CLUSTER
        - WEEKSTARTINGMONDAY
        - 'FTE_Interpolated'

    cutoff_date : str or datetime
        Start date from which missing sites are assumed to have no data 
        (e.g., "2025-06-01").

    cluster_name : str
        Cluster name whose mean will be used for imputation (e.g., "Clinics 1").

    missing_sites : list of int
        List of ID_Department values representing sites with missing data 
        (e.g., [115, 8091, 505, 108]).

    Returns
    -------
    pd.DataFrame
        DataFrame containing the original data plus imputed rows for missing sites.
    """
    try:
        # Step 1: Filter for cutoff date
        filtered = df[df[WEEKSTARTINGMONDAY] >= pd.to_datetime(cutoff_date)]

        # Step 2: Restrict to specified cluster
        cluster_df = filtered[filtered[CLUSTER] == cluster_name]

        # Step 3: Compute cluster mean FTE per week
        cluster_means = (
            cluster_df.groupby([CLUSTER, WEEKSTARTINGMONDAY])
            .agg({"FTE_Interpolated": "mean"})
            .reset_index()
        )

        # Step 4: Duplicate cluster mean for each missing site
        duplicates = []
        for site_id in missing_sites:
            temp = cluster_means.copy()
            temp[IDDEPARTMENT] = site_id
            duplicates.append(temp)

        # Step 5: Append duplicates back to original data
        combined = pd.concat([df] + duplicates, ignore_index=True)

        return combined

    except Exception as error:
        print(f"Error in fill_missing_sites_with_cluster_mean: {error}")
        raise
 
if __name__ == '__main__':
    print('----------------------------------------------Sweden Productive Time Data Preperation Started ----------------------------------------------')
    total_start = time.time()
    ### Reading Data Productive Time Data
    df_latest = read_data(productive_time_data_path, sheetname=productive_time_data_sheet_name)
    ### Reading PRevious version of Productive Time Data
    df_old = read_data(old_productive_time_data_path, sheetname="Sheet4")
    ### Id Department Cost Center code Mapping File
    id_depart_cost_center_code_mapping_df = read_data(iddepartment_cost_center_code_mapping_path, sheetname="Sheet1")
    #### Reading Id Department Clsuter mapping Data
    clinic_df = read_data(productive_time_data_path, sheetname=cluster_mapping_sheet_name)
    ### Getting cluster for productive time data
    df_latest = pd.merge(df_latest, clinic_df, on = IDDEPARTMENT, how = 'left')
    ### Cleaning Column names and removing weeks with wrong data
    df_latest = clean_data(df_latest, productive_df_col_rename, weeknumber_year_combination)
    ### Cleanning Productive time data
    df = update_week1_with_prior(df_latest)
    ### Creating Week Starting Monday
    df[WEEKSTARTINGMONDAY] = df.apply(lambda row: get_week_start_safe(row[YEAR], row[WEEKNUMBER]), axis=1)
    ### Updating Productive Time data for Missing Sites
    df = preprocess_productive_time(df_old, df, id_depart_cost_center_code_mapping_df)
    ### Creating Interpolated Data
    df_interpolated  = interpolate_productive_time(df)
    ### Filtering Data for 27 June 2022
    df_interpolated_1 = df_interpolated[df_interpolated[WEEKSTARTINGMONDAY]>=filter_date]
    print(f"Distribution of Interpolated rows: {df_interpolated_1['WasInterpolated'].value_counts()}")
    ### Renaming Columns
    df_interpolated_1.rename(columns = {"SumProductiveTime_Interpolated":'FTE_Interpolated', COSTCENTERCODE:IDDEPARTMENT}, inplace = True)
    ### Getting Clusters for each sites
    df_interpolated_2 = pd.merge(df_interpolated_1, clinic_df, on = IDDEPARTMENT, how = 'left')
    df_interpolated_2 = df_interpolated_2[[CLUSTER, WEEKSTARTINGMONDAY, 'FTE_Interpolated', IDDEPARTMENT]]
    ### If Productive time has missing sites procedd with below else ignore
    ### Interpolating productive time for missing week for missing sites
    df_interpolated_3 = fill_missing_sites_with_cluster_mean(df_interpolated_2, missing_weeks, cluster_name, missing_sites)

    # Step 6: Save to Excel
    df_interpolated_3.to_excel(output_file, index=False)
    print(f"File saved to {output_file}")
    
    total_elapsed = time.time() - total_start
    print("\n Data Preperation completed.")
    print(f"\n Total time taken: {format_time(total_elapsed)}")
    
    
