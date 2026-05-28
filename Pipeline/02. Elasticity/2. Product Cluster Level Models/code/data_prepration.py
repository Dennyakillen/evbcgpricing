import os
import sys

import holidays
import pandas as pd
import numpy as np
from pathlib import Path
import yaml
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

### Reading CSV Data
def read_data(path):
    """
    Reads a CSV file into a pandas DataFrame.

    Parameters:
    -----------
    path : str
        Path to the CSV file.

    Returns:
    --------
    pd.DataFrame
        Loaded data.
    """
    df = pd.read_csv(path)
    return df

### Loading Or Creating Transform File
def load_or_create_feature_transform_file(df, file):
    """
    Loads an existing transform control file or creates a new one with feature names.

    Parameters:
    -----------
    df : pd.DataFrame
        The DataFrame whose columns will be used to generate the control file.

    file : str
        Path to the CSV transform control file.

    Returns:
    --------
    pd.DataFrame
        The loaded or newly created transform control DataFrame.
    """
    if (Path(file)).exists():
        print("Feature to Transform File exists")
        trasform_control = pd.read_csv(file)
        return trasform_control
    else:
        print(f"Created Feature to Transform File, please update file at {file}")
        trasform_control = pd.DataFrame({"Feature": df.columns})
        trasform_control["Transform"] = np.nan
        trasform_control.to_csv(file, index=False)

### Transforming Data
def transform_data(df, trasform_control):
    """
    Applies log transformation to specified columns based on a transform control file.

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame to be transformed.

    trasform_control : pd.DataFrame
        DataFrame with columns 'Feature' and 'Transform'. Transformation is applied
        where 'Transform' == 1.

    Returns:
    --------
    pd.DataFrame
        Transformed DataFrame with log-applied columns.
    """

    cols_to_transform = trasform_control[trasform_control["Transform"] == 1]["Feature"].to_list()
    print(f"Number of Cols that will be transformed are {len(cols_to_transform)}")
    print(f"Cols that will be transformed are {cols_to_transform}")
    print(df[cols_to_transform].isnull().sum())
    for col in cols_to_transform:
       
        print(df[col].value_counts())
        df[col] = np.log(df[col])
        df[col] = np.where((df[col] == np.inf) | (df[col] == -np.inf), 0, df[col])
    return df

### Saving Data
def save_data(df, path):
    """
    Saves a pandas DataFrame to a CSV file.

    Parameters:
    -----------
    df : pd.DataFrame
        Data to be saved.

    path : str
        Destination file path.

    Returns:
    --------
    None
    """

    df.to_csv(path, index=False)

### Creating Month End Flag
def get_month_and_year(df, path):
    """
    Extracts year, month, and ISO week from the DATE column in a DataFrame.

    Parameters:
    -----------
    df : pd.DataFrame
        Data containing a DATE column.

    path : str
        Not used in this function (can be removed).

    Returns:
    --------
    pd.DataFrame
        Updated DataFrame with YEAR, MONTH, and WEEK columns.
    """

    
    df[DATE] = pd.to_datetime(df[DATE])
    df[YEAR] = df[DATE].dt.year
    df[MONTH] = df[DATE].dt.month
    df[WEEK] = df[DATE].dt.isocalendar().week
    return df
## creating flag for weeks between 
def creating_negative_media_coverage(df):
    """
    Creates flags for weeks with known negative media coverage periods.

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with a 'week_starting_monday' column.

    Returns:
    --------
    pd.DataFrame
        Updated DataFrame with flags:
        - negative_media_coverage_flag
        - negative_media_coverage_flag_jan25
        - negative_media_coverage_flag_mar24
    """

    # list of special weeks
    special_weeks = SPECIAL_WEEKS
    period_1 = SPECIAL_WEEK_PERIOD_1
    period_2 = SPECIAL_WEEK_PERIOD_2
    # if week_starting_monday is datetime, convert list to datetime as well
    special_weeks = pd.to_datetime(special_weeks)
    period_1 = pd.to_datetime(period_1)
    period_2 = pd.to_datetime(period_2)
    
    # create new flag column (1 if in list, else 0)
    df['negative_media_coverage_flag'] = df['week_starting_monday'].isin(special_weeks).astype(int)
    df['negative_media_coverage_flag_jan25'] = df['week_starting_monday'].isin(period_1).astype(int)
    df['negative_media_coverage_flag_mar24'] = df['week_starting_monday'].isin(period_2).astype(int)
    
    print(f"Negtaive_media_coverage_week: {df['negative_media_coverage_flag'].value_counts()}")
    print(f"Negtaive_media_coverage_week: {df['negative_media_coverage_flag_jan25'].value_counts()}")
    print(f"Negtaive_media_coverage_week: {df['negative_media_coverage_flag_mar24'].value_counts()}")
    
    return df

### Fetching Holiday Data
def holiday_flag(row):
    """
    Returns 1 if the given date is a Swedish holiday, otherwise 0.

    Parameters:
    -----------
    row : pd.Series
        Row containing the DATE field.

    Returns:
    --------
    int
        1 if holiday, 0 otherwise.
    """

    sa_holidays = holidays.Sweden()
    return int(row[DATE] in sa_holidays)

### Fetching Holiday Data
def holiday_name(row):
    """
    Returns the name of the Swedish holiday for a given date, if any.

    Parameters:
    -----------
    row : pd.Series
        Row containing the DATE field.

    Returns:
    --------
    str or None
        Name of the holiday, or None if not a holiday.
    """

    sa_holidays = holidays.Sweden()
    return sa_holidays.get(row[DATE])

### Creating
def get_holiday_flag(df, holiday_start_date=START_DATE, holiday_end_date=END_DATE2):
    """
    Creates holiday flags and merges weekly holiday counts into the main DataFrame.

    Parameters:
    -----------
    df : pd.DataFrame
        Main data to merge with holiday indicators.

    holiday_start_date : str or datetime, optional
        Start date for holiday calendar (default from constants).

    holiday_end_date : str or datetime, optional
        End date for holiday calendar (default from constants).

    Returns:
    --------
    pd.DataFrame
        Data with added weekly holiday count columns:
        - major_holiday_count
        - non_major_holiday_count
    """

    # Build daily calendar
    df_dates = pd.DataFrame({DATE: pd.date_range(holiday_start_date, holiday_end_date)})
    df_dates[HOLIDAY]  = df_dates.apply(holiday_flag, axis=1)          # 1 if holiday else 0
    df_dates[OCCASION] = df_dates.apply(holiday_name, axis=1)          # holiday name (string)

    # Calendar parts
    df_dates[YEAR]  = df_dates[DATE].dt.year
    df_dates[MONTH] = df_dates[DATE].dt.month
    df_dates[WEEK]  = df_dates[DATE].dt.isocalendar().week.astype(int)
    
    # Drop Sundays (and Swedish 'Söndag') if you don’t want them counted
    df_dates = df_dates[~df_dates[OCCASION].str.strip().str.lower().isin(['sunday', 'söndag'])]
    df_dates.to_excel('holiday_check0820.xlsx', index = False)
    # Define "major" holidays
    major_holiday_list = MAJOR_SWEDEN_HOLIDAY_LIST

    # Create per-day indicators (only count if HOLIDAY==1)
    is_major = df_dates[OCCASION].isin(major_holiday_list)
    is_hday  = df_dates[HOLIDAY].astype(int) == 1

    df_dates['major_holiday']     = (is_major & is_hday).astype(int)
    df_dates['non_major_holiday'] = (~is_major & is_hday).astype(int)

    # Weekly counts (sum, DON'T cap)
    weekly_counts = (
        df_dates
        .groupby([YEAR, WEEK], as_index=False)[['major_holiday','non_major_holiday']]
        .sum()
        .rename(columns={'major_holiday': 'major_holiday_count',
                         'non_major_holiday': 'non_major_holiday_count'})
    )



    # Merge back to your modeling df (which should already have YEAR/WEEK)
    df = df.merge(weekly_counts, on=[YEAR, WEEK], how='left')

    # Fill missing (weeks with no holidays)
    for col in ['major_holiday_count','non_major_holiday_count']:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)
    return df

### Creating Month End Flag
def is_month_end_flag(date):
    """
    Checks if a given date falls within the last 7 days of a month.

    Parameters:
    -----------
    date : datetime
        Input date.

    Returns:
    --------
    int
        1 if within last 7 days of the month, else 0.
    """

    next_7_days = pd.date_range(start=date, periods=7)
    return int(any(day.day >= 28 for day in next_7_days))

### Creating Quarter Flag
def get_quarter_flag(df):
    """
    Adds a binary flag indicating if the month is a quarter-end month (Mar, Jun, Sep, Dec).

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame containing a MONTH column.

    Returns:
    --------
    pd.DataFrame
        DataFrame with added 'Quarter_End' column.
    """

    df["Quarter_End"] = np.where(df[MONTH].isin([3, 6, 9, 12]), 1, 0)
    return df


### YOY seasonality
def yoy_seasonality(df):
    """
    Calculates and normalizes YOY seasonality based on UNIT volume per service and group.

    Parameters:
    -----------
    df : pd.DataFrame
        Input data containing WEEK, UNIT, and grouping columns.

    Returns:
    --------
    pd.DataFrame
        Data with added YOY_SEASONALITY column merged back in.
    """

    df.rename(columns = {SERVICE_VAR:'service'}, inplace = True)
	# Calculate mean unit value for each group and week
    group_keys = YOY_SEASONALITY_GROUPBY_COL_NAMES
    print(f'YOY seasonlity is called at {group_keys + [WEEK]} level')
    df_seasonality = df.groupby(group_keys + [WEEK], as_index=False)[UNIT].mean()
    df_seasonality.rename(columns={UNIT: "YOY_SEASONALITY"}, inplace=True)
	#  Calculate total seasonality per group
    total = df_seasonality.groupby(group_keys).agg(total=("YOY_SEASONALITY", 'sum')).reset_index()
    df_seasonality = df_seasonality.merge(total, on=group_keys)
	#  Normalize YOY seasonality
    df_seasonality["YOY_SEASONALITY"] = df_seasonality["YOY_SEASONALITY"] / df_seasonality["total"]
	#  Merge the seasonality data back into original dataframe
    df = df.merge(df_seasonality[group_keys + [WEEK, "YOY_SEASONALITY"]], on=group_keys + [WEEK])
    return df

def create_transform_control_file(df):
    """
    Creates a blank transform control DataFrame with 'Feature' and 'Transform' columns.

    Parameters:
    -----------
    df : pd.DataFrame
        Input data whose columns will be used as features.

    Returns:
    --------
    pd.DataFrame
        Transform control DataFrame with 'Feature' and empty 'Transform' column.
    """

    control = pd.DataFrame({"Feature":df.columns.tolist()})
    control["Transform"] = np.NAN

    return control

### Creating month end flag
def create_month_end_week(ab, start_date=START_DATE, end_date=END_DATE):
    """
    Creates a flag for the last Monday of each month (month-end week).

    Parameters:
    -----------
    ab : pd.DataFrame
        Original DataFrame with a 'week_starting_monday' column.

    start_date : str or datetime
        Start date for generating weeks.

    end_date : str or datetime
        End date for generating weeks.

    Returns:
    --------
    pd.DataFrame
        Updated DataFrame with 'month_end_week' flag.
    """

    # generate all Mondays between start and end
    mondays = pd.date_range(start=start_date, end=end_date, freq='W-MON')
    df = pd.DataFrame({'week_starting_monday': mondays})
    
    # year-month key
    df['year'] = df['week_starting_monday'].dt.year
    df['month'] = df['week_starting_monday'].dt.month

    # find last monday of each month
    last_mondays = df.groupby(['year','month'])['week_starting_monday'].transform('max')
    
    # flag
    df['month_end_week'] = (df['week_starting_monday'] == last_mondays).astype(int)

    df.drop(columns=['year','month'], inplace = True)
    ab = pd.merge(ab, df, on = ['week_starting_monday'], how = 'left')
    ab['month_end_week'].fillna(0, inplace = True)

    return ab

### Creating 1st and 3rd week flag
def week_flag(df):
    """
    Flags the first and third weeks of each month for each KEY.

    Parameters:
    -----------
    df : pd.DataFrame
        Data containing KEY, YEAR, MONTH, DATE columns.

    Returns:
    --------
    pd.DataFrame
        DataFrame with added flags:
        - first_week
        - third_week
    """

    # make sure DATE is sorted so cumcount goes in chronological order
    df = df.sort_values([KEY,YEAR,MONTH,DATE])
    # rank = 1 for the first date in the month, 2 for the second, etc.
    df['week_rank'] = df.groupby([KEY,YEAR,MONTH]).cumcount() + 1
    # flags
    df['first_week'] = (df['week_rank'] == 1).astype(int)
    df['third_week'] = (df['week_rank'] == 3).astype(int)
    return df

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
    
    dates['Day'] = dates[DATE].dt.day_name()
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
    df['INFLATED'] = np.where(df['_merge'] == 'right_only', 1, 0)
    df.drop('_merge', axis=1, inplace=True)

    return df

###filtering data for atleast 104 weeks
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
    raw_data_path = os.path.join( module_path, config['data_preparation']['raw_input_data'].lstrip("/\\"))

    sheet_name = config['data_preparation']['sheet_name']
    transform_control_path = os.path.join(module_path, config['data_preparation']['transform_control'].lstrip("/\\"))
    save_path = os.path.join(module_path, config['data_preparation']['output_data'].lstrip("/\\"))
    save_path_original = os.path.join(module_path, config['data_preparation']['processed_data'].lstrip("/\\"))
    date_to_month_year_path = os.path.join(module_path, config['data_preparation']['date_to_month_year_path'].lstrip("/\\"))
    create_transform_flag = config['data_preparation']['create_transform_control']
    transform_control_path = os.path.join(module_path, config['data_preparation']['transform_control_save_path'].lstrip("/\\"))

    # Read data
    df_raw = read_data(raw_data_path)
    df_raw=filter_data(df_raw,103)
    print(f"Initial dta Shape Beginning = {df_raw.shape}")
    print(f"Unique Key Beginning = {df_raw[KEY].nunique()}")
    print(df_raw.info())
    # Get Year & Month
    df_raw = get_month_and_year(df_raw, date_to_month_year_path)
    df_raw = creating_negative_media_coverage(df_raw)
    # Get Holiday flag
    df_with_features = get_holiday_flag(df_raw)


    df_with_features = create_month_end_week(df_with_features, start_date=START_DATE, end_date=END_DATE)
    df_with_features['unit_temp']=np.where(df_with_features['month_end_week']==1,None,df_with_features[UNIT])
    print(df_with_features.shape)
    df_with_features=inflate_missing_weeks(df_with_features,START_DATE,END_DATE,'Monday')
    
    df_with_features = rolling_seasonality(df_with_features, 'unit_temp', KEY, DATE, 6, 3, "fwbw")
    print(df_with_features.shape)
    df_with_features=df_with_features[df_with_features['INFLATED']==0]
    df_with_features=df_with_features.drop('INFLATED',axis=1)
    print(df_with_features.shape)
    # Quarter Flag
    df_with_features = get_quarter_flag(df_with_features)

    # YOY Seasonality
    df_with_features = yoy_seasonality(df_with_features)

    # Week Flag
    df_with_features = week_flag(df_with_features)

    # Save Data not transformed
    save_data(df_with_features, save_path_original)

    # Feature transform file
    if create_transform_flag:
        transform_control = create_transform_control_file(df_with_features)
        save_data(transform_control, transform_control_path)

    else:
        transform_control = load_or_create_feature_transform_file(df_with_features, transform_control_path)
        # Transform features
        df_for_model = transform_data(df_with_features, transform_control)

        # save
        save_data(df_for_model, save_path)
    print(f"Data for model Shape  = {df_raw.shape}")
    print(f"Unique Key Data for model = {df_raw[KEY].nunique()}")

