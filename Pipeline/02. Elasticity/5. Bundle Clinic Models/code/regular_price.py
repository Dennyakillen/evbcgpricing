import os
import sys
import pandas as pd
import numpy as np
import yaml
from utils import *
from constants import *
from pathlib import Path

# Path to this config file
config_file = Path(__file__).resolve().parent /"src"/ "config.yml"

# Load YAML
with open(config_file, "r") as f:
    config = yaml.safe_load(f)

# Resolve module_path relative to config file location
module_path = (config_file.parent / config["module_path"]).resolve()

print("Module Path:", module_path)

def read_data(path):
    """
    Reads a dataset from the given file path based on its extension.

    Supports reading from:
    - CSV files (with 'cp1252' encoding and error handling)
    - Excel files (.xlsx and .xls using openpyxl engine)

    Parameters:
    ----------
    path : str
        Full path to the data file. Supported formats: .csv, .xlsx, .xls

    Returns:
    -------
    pd.DataFrame
        A pandas DataFrame containing the data from the input file.

    Raises:
    ------
    ValueError
        If the file type is not supported.
    """
    # Extract file extension clearly
    file_extension = os.path.splitext(path)[1].lower()
    
    # Check file type and read accordingly
    if file_extension == ".csv":
        print('Reading CSV file')
        df = pd.read_csv(path, encoding='cp1252', encoding_errors='ignore')
    elif file_extension in [".xlsx", ".xls"]:
        print('Reading Excel file')
        df = pd.read_excel(path, engine='openpyxl')
    else:
        raise ValueError(f"Unsupported file type: {file_extension}")
   

    # Display useful information
    print('Number of Unique Products:', df[Product_Code_var].nunique())
    print('Number of Rows:', df.shape[0])
    print('Columns:', df.columns.to_list())

    return df

### Creating Price Variable (Dollar/Unit)
def get_price(df, level):
    """
    Calculates unit price based on the specified aggregation level.

    If the level is 'volume' (case-insensitive), price is calculated as:
        PRICE = DOLLAR / VOLUME
    Otherwise, price is calculated as:
        PRICE = DOLLAR / UNIT

    Parameters:
    ----------
    df : pd.DataFrame
        The input DataFrame containing transaction data.

    level : str
        Determines the denominator for price calculation. Accepts:
        - "volume" to use VOLUME
        - any other value to use UNIT

    Returns:
    -------
    pd.DataFrame
        The DataFrame with an additional column `PRICE` containing the computed values.

    Prints:
    ------
    Total number of rows in the DataFrame after price calculation.
    """

    if level.lower() == "volume":
        df[PRICE] = df[DOLLAR] / df[VOLUME]
    else:
        df[PRICE] = df[DOLLAR] / df[UNIT]
    print('get price: ', df.shape[0])
    return df

### Saving data at specific path
def save_data(df, path):
    """
    Saves the given DataFrame to a CSV file at the specified path.

    Parameters:
    ----------
    df : pd.DataFrame
        The DataFrame to be saved.

    path : str
        The file path where the CSV should be written.

    Returns:
    -------
    None
    """
    df.to_csv(path, index=False)

### Creating empty rows for missing dates 
def inflate_missing_weeks(df, impute_start_date, impute_end_date, week_ending_day):
    """
    Adds empty rows for missing weeks per KEY between given start and end dates.

    For each unique KEY:
    - Identifies the date range (min to max dates in the data).
    - Creates weekly dates within that range (using Mondays as week ending).
    - Merges those dates with the original data to "inflate" missing weeks.
    - Marks new rows with an 'INFLATED' flag set to 1.

    Parameters:
    ----------
    df : pd.DataFrame
        Input data containing at least DATE and KEY columns.

    impute_start_date : str or datetime
        Start date for generating weekly date range.

    impute_end_date : str or datetime
        End date for generating weekly date range.

    week_ending_day : str
        Expected week-ending day name (e.g., 'Monday') — currently not used, 
        but can be activated for filtering by specific weekday.

    Returns:
    -------
    pd.DataFrame
        DataFrame with added rows for missing weeks and a new column 'INFLATED' 
        indicating whether a row was created (1) or already existed (0).

    Prints:
    ------
    - Shape of generated date range
    - Final DataFrame shape
    - Count of inflated rows
    """
    dates = pd.DataFrame()
    dates[DATE] = pd.date_range(start=impute_start_date, end=impute_end_date, freq='W-MON')
    print(dates.shape)
    dates['Day'] = dates[DATE].dt.day_name()
    print(dates.shape)
    dates.drop('Day', axis=1, inplace=True)
    dates_df_list = []
    for key in df[KEY].unique(): 
        tmp2 = df[df[KEY]==key]
        min_date = tmp2[DATE].min()
        max_date = tmp2[DATE].max()
        tmp = dates.copy()
        tmp = tmp[(tmp[DATE]>=min_date) & (tmp[DATE]<=max_date)] 
        tmp[KEY] = key
        dates_df_list.append(tmp)
        del tmp

    dates = pd.concat(dates_df_list)
    df = df.merge(dates, on=[KEY, DATE], how='outer',
                  indicator=True)
    print(df.shape)
    
    df['INFLATED'] = np.where(df['_merge'] == 'right_only', 1, 0)
    df.drop('_merge', axis=1, inplace=True)
    print(df['INFLATED'].value_counts())
    return df

### Filtering Data for specific dates
def filter_data(df,weeks):
    """
    Filters out KEYs (e.g., sites or products) that have fewer than a specified number of unique weeks.

    Parameters:
    ----------
    df : pd.DataFrame
        Input data containing KEY and DATE columns.

    weeks : int
        Minimum number of unique weeks required for each KEY to be retained.

    Returns:
    -------
    pd.DataFrame
        Filtered DataFrame containing only KEYs with more than the specified number of weeks.
    """
    check=df.groupby(KEY).agg({DATE:'nunique'}).reset_index()
    keys=check[check[DATE]>weeks][KEY].unique()
    df=df[df[KEY].isin(keys)]
    return df

if __name__ == '__main__':
    # Resolve module_path relative to config file location
    module_path = (config_file.parent / config["module_path"]).resolve()
    data_path = config['regular_price']['raw_input_data']
    data_path = os.path.join(module_path, config['regular_price']['raw_input_data'].lstrip("/\\"))
    print(f'Raw Data path: {data_path}')
    price_level = os.path.join(module_path, config['regular_price']['price_level'].lstrip("/\\"))
    save_path = os.path.join(module_path,
                             config['regular_price']['output_data'].lstrip("/\\"))
    print(f"Data is stored at path: {save_path}")
    
    # Read data
    ads = read_data(data_path)
    ads = clean_columns(ads)
    ads=ads[(ads['week_starting_monday']>=START_DATE)&(ads['week_starting_monday']<END_DATE2)]
    ads[DOLLAR]=ads[DOLLAR].astype(float)
    ### Creating Model Group variable
    ads['KEY']= ads[Cluster_Granularity].astype(str)+'-'+ads[Product_Code_var].astype(str)
    print('Before removing 103 weeks min data',ads.shape)
    ### Fitering Data for atleast 104 weeks
    ads=filter_data(ads,103)
    print('After removing 103 weeks min data',ads.shape)
    ### Inflating missing weeks
    ads = inflate_missing_weeks(ads, START_DATE, END_DATE, DATE)
    print('After After adding dummy data',ads.shape)
    ### Calculating Price
    ads = get_price(ads, price_level)
    print(ads.info())

    print(f"ADS Shape Beginning = {ads.shape}")
    print(f"Unique Key Beginning = {ads[KEY].nunique()}")

    # Regular Price
    regular_price = reg_price_calc(ads, PRICE, KEY, DATE, 6, 3, "fwbw", "max")
    

    # Adjusted Regular price to tweak in Excel
    regular_price[ADJUSTED_REGULAR_PRICE] = regular_price[ALGO_REGULAR_PRICE]
    regular_price = regular_price[regular_price['INFLATED']==0]
    print('shape after removing dummy rows.', regular_price.shape)

    print(f"Final data frame Shape = {regular_price.shape}")
    print(f"Unique Key Final data frame = {regular_price[KEY].nunique()}")

    # Save Results
    save_data(regular_price, save_path)