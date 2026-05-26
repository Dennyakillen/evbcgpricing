import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
import yaml
from pandas import ExcelWriter
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


# Global variables
model_group = config['unique_key_var']
date_var = config['date_var']
dep_var = config['dep_var']
train_perc = config['train_perc']


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
        Loaded DataFrame.
    """

    df = pd.read_csv(path)
    return df


def load_or_create_feature_control_file(df, file):
    """
    Loads the feature control file if it exists, else creates one with default settings.

    Parameters:
    -----------
    df : pd.DataFrame
        Input raw data.

    file : str
        File path for the control file.

    Returns:
    --------
    pd.DataFrame
        Loaded or newly created control DataFrame with RUN, TRAIN, and feature columns.
    """

    if (Path(file)).exists():
        print("Model Control File exists")
        control_file = pd.read_excel(file)
        return control_file

    else:
        print(f"Created Model Control File, please update file at {file}")
        control_var_list = [x for x in list(df.columns) if x not in [date_var, dep_var, model_group]]
        control_var_list.insert(0, "TRAIN")
        control_var_list.insert(0, "RUN")

        train = train_perc
        test = 1 - train

        df.sort_values([KEY, DATE], inplace=True)

        control_file = pd.DataFrame(df_raw[model_group].unique(), columns=[model_group])
        for newcol in control_var_list:
            control_file[newcol] = np.nan

        control_file["RUN"] = "YES"
        for x in control_file[model_group]:
            control_file.loc[control_file[model_group] == x, "TRAIN"] = df_raw[df_raw[model_group] == x].tail(
                1 if round(df_raw[df_raw[model_group] == x].shape[0] * test) == 0 else round(
                    df_raw[df_raw[model_group] == x].shape[0] * test))[date_var].iloc[0]

        control_file.to_excel(file, index=False)

def filter_data(df,weeks):
    """
    Filters the DataFrame to only include KEYs with more than the specified number of weeks.

    Parameters:
    -----------
    df : pd.DataFrame
        Input DataFrame containing DATE and KEY columns.

    weeks : int
        Minimum number of unique weeks required.

    Returns:
    --------
    pd.DataFrame
        Filtered DataFrame.
    """

    check=df.groupby(KEY).agg({DATE:'nunique'}).reset_index()
    keys=check[check[DATE]>weeks][KEY].unique()
    df=df[df[KEY].isin(keys)]
    return df


def check_nulls(df, df_control):
    """
    Checks for null values in selected variables (marked with 1) in the control file.

    Parameters:
    -----------
    df : pd.DataFrame
        Input data.

    df_control : pd.DataFrame
        Control file indicating selected variables.

    Returns:
    --------
    None
        Prints a message if nulls are present.
    """

    df_control_t = df_control.melt([model_group, 'RUN', 'TRAIN'], var_name='VARIABLE',
                                   value_name="VALUE").sort_values(by=model_group).reset_index(drop=True)

    null_check_var = (df_control_t[df_control_t['VALUE'] == 1]['VARIABLE']).unique().tolist()
    if df_raw[null_check_var].isnull().sum().sum() == 0:
        print("Varibles contain no-null values")
    else:
        print("Varibles contain null values")


def process_model_results(df, df_avp, df_summary, df_coef):
    """
    Merges AVP, summary, and coefficient data to prepare final model outputs.

    Parameters:
    -----------
    df : pd.DataFrame
        Raw input data.

    df_avp : pd.DataFrame
        Model output (Actual vs Predicted) data.

    df_summary : pd.DataFrame
        Summary stats with R-squared values.

    df_coef : pd.DataFrame
        Regression coefficients with p-values.

    Returns:
    --------
    Tuple[pd.DataFrame, pd.DataFrame]
        model_results: Merged data with AVP, RSQ, and input variables.
        coef_business: Pivoted coefficient table with elasticities.
    """

    model_results = df_avp.merge(df_summary[[model_group, "RSQ", "ADJ_RSQ"]], how="left", left_on=model_group,
                                 right_on=model_group)

    model_results[DATE] = pd.to_datetime(model_results[DATE])
    df[DATE] = pd.to_datetime(df[DATE])

    model_results = model_results.merge(df.drop(columns=[UNIT]), on=["KEY", DATE],
                                        how='left').drop_duplicates()
    coef_business = df_coef.pivot(index=['KEY'], columns=['VARIABLE'], values=['ESTIMATE', 'PVALUE']).reset_index()
    coef_business.columns = [col1 + "_" + col2 for col1, col2 in coef_business.columns]
    coef_business.rename(columns=({"KEY_": 'KEY'}), inplace=True)
    coef_business.columns = coef_business.columns.str.replace('ESTIMATE', "ELASTICITY")

    return model_results, coef_business


def save_model_summary(output_file, df_coef, coef_business, df_avp, df_summary, model_results, df_vif):
    """
    Saves various model summary components into separate sheets of a single Excel file.

    Parameters:
    -----------
    output_file : str
        Path to the output Excel file.

    df_coef : pd.DataFrame
        Raw coefficients.

    coef_business : pd.DataFrame
        Business-readable coefficients.

    df_avp : pd.DataFrame
        Actual vs Predicted data.

    df_summary : pd.DataFrame
        Model performance summary.

    model_results : pd.DataFrame
        Merged model output data.

    df_vif : pd.DataFrame
        Variance inflation factor values.

    Returns:
    --------
    None
    """

    with ExcelWriter(output_file) as writer:
        for n, df_ in enumerate([df_coef, coef_business, df_avp, df_summary, df_vif]):
            try:
                df_.to_excel(writer, 'sheet%s' % n, index=False)
            except:
                df_.to_excel(writer, 'sheet%s' % n)

def compute_corr(group):
    """
    Computes correlation between PRICE and UNIT for a given group.

    Parameters:
    -----------
    group : pd.DataFrame
        Grouped DataFrame.

    Returns:
    --------
    float
        Correlation coefficient.
    """

    return group[PRICE].corr(group[UNIT])

def output_summary(df_raw):
    """
    Generates summary with correlation, total revenue (DOLLAR), and units per KEY.

    Parameters:
    -----------
    df_raw : pd.DataFrame
        Input data.

    Returns:
    --------
    pd.DataFrame
        Summary with DOLLAR, UNIT, and correlation.
    """

    correlation_df = df_raw.groupby(KEY).apply(compute_corr).reset_index()


    correlation_df.columns = [KEY, 'Correl']
    correlation_df.dropna(subset=['Correl'], inplace=True)
    output_summary=df_raw.groupby(KEY).agg({DOLLAR:'sum',UNIT:'sum'}).reset_index().merge(correlation_df,on=KEY,how='left')
    return output_summary

def get_elasticity(df, df_coef):
    """
    Merges elasticity columns from coefficient data into the main DataFrame.

    Parameters:
    -----------
    df : pd.DataFrame
        Main DataFrame.

    df_coef : pd.DataFrame
        Coefficients DataFrame with ELASTICITY columns.

    Returns:
    --------
    pd.DataFrame
        Merged DataFrame with elasticity columns.
    """

    cols_to_keep = [col for col in df_coef.columns if "ELASTICITY" in col.upper()]
    cols_to_keep = [KEY] + cols_to_keep
    df = df.merge(df_coef[cols_to_keep], on=KEY)

    return df


def get_impact(df):
    """
    Computes impact by multiplying input variables with their corresponding elasticity.

    Parameters:
    -----------
    df : pd.DataFrame
        Input DataFrame containing variables and elasticities.

    Returns:
    --------
    pd.DataFrame
        Updated DataFrame with IMPACT columns added.
    """

    driver = df.copy()
    coefs = [col for col in df.columns if "ELASTICITY" in col.upper()]
    iterate_over = [col.replace("ELASTICITY_", "") for col in coefs]
    iterate_over = [col for col in iterate_over if col != 'CONST']
    for col in iterate_over:
        driver[f'IMPACT_{col}'] = driver[col] * driver[f"ELASTICITY_{col}"]
    driver.rename(columns={'Coef_CONST': 'IMPACT_CONST'}, inplace=True)
    impact_cols = [col for col in driver.columns if "IMPACT" in col]
    df = df.merge(driver[['KEY', DATE] + impact_cols], on=['KEY', DATE])

    return df


def save_results(df, file):
    """
    Saves the DataFrame to a CSV file.

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame to save.

    file : str
        Path to output CSV file.

    Returns:
    --------
    None
    """

    df.to_csv(file, index=False)
def save_results_excel(df, file):
    """
    Saves the DataFrame to an Excel file.

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame to save.

    file : str
        Path to output Excel file.

    Returns:
    --------
    None
    """

    df.to_excel(file, index=False)

def get_original_variables(df, path_to_otiginal, cols_to_use):
    """
    Merges the original variables from a CSV file back to the modeled DataFrame.

    Parameters:
    -----------
    df : pd.DataFrame
        Main DataFrame with DATE and KEY.

    path_to_otiginal : str
        Path to the original CSV.

    cols_to_use : list
        List of columns to read from the original file.

    Returns:
    --------
    pd.DataFrame
        DataFrame with original variables merged.
    """

    original = pd.read_csv(path_to_otiginal, usecols=cols_to_use)
    original[DATE] = pd.to_datetime(original[DATE])
    df[DATE] = pd.to_datetime(df[DATE])
    df.merge(original, on=[KEY, DATE])
    return df

def impute_missing(df, config):
    """
    Fills missing values in the DataFrame based on the specified technique.

    Parameters:
    -----------
    df : pd.DataFrame
        Data with missing values.

    config : dict
        Configuration dict with imputation technique and column types.

    Returns:
    --------
    pd.DataFrame
        DataFrame with imputed missing values.
    """

    technique = config['imputation']['technique']
    df = df.copy()
    print(df.info())
    for col in df.drop(UNIT,axis=1).columns:
        df[col] = df[col].astype(config['col_type'][col])
        if config['col_type'][col]!='float64':
            continue
        if col in [HOLIDAY,'rest_holiday']:
            df[col]=df[col].fillna(0)
        n_missing_before = df[col].isnull().sum()
        if n_missing_before:
            if technique == 'mean':
                df[col] = df[col].fillna(df[col].mean())
            elif technique == 'median':
                df[col] = df[col].fillna(df[col].median())
            elif technique == 'zero':
                df[col] = df[col].fillna(0)
            elif technique == 'ffill':
                df[col] = df[col].fillna(method='ffill')
            elif technique == 'bfill':
                df[col] = df[col].fillna(method='bfill')
            n_missing_after = df[col].isnull().sum()

    return df

def get_adjusted_elasticity(df):
    """
    Adjusts elasticity values to fall within reasonable business ranges.

    Rules:
    - REGULAR_PRICE elasticity capped between -5 and 0
    - All others capped between 0 and 6

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame containing elasticity columns.

    Returns:
    --------
    pd.DataFrame
        Adjusted elasticity values.
    """

    elasticity_cols = [col for col in df.columns if "ELASTICITY" in col.upper()]

    for col in elasticity_cols:
        if col == "ELASTICITY_ADJUSTED_REGULAR_PRICE":
            df[col] = np.where(df[col] < -5, -5, df[col])
            df[col] = np.where(df[col] > 0, 0, df[col])
        else:
            df[col] = np.where(df[col] < 0, 0, df[col])
            df[col] = np.where(df[col] > 6, 6, df[col])

    return df


if __name__ == '__main__':
    # Resolve module_path relative to config file location
    module_path = (config_file.parent / config["module_path"]).resolve()
    print(f"Path of Module {module_path}")

    
    # Define the path for the raw input data dynamically based on the model type
    raw_input_data = os.path.join(module_path, config['model']['raw_input_data'].lstrip("/\\"))

    # Define the control file path dynamically based on the model type
    control_file_path = os.path.join(module_path, config['model']['control_file_path'].lstrip("/\\"))

    # Define the model summary save path dynamically based on the model type
    summary_save_path = os.path.join(module_path, config['model']['model_summary_save_path'].lstrip("/\\"))

    # Define the model results save path dynamically based on the model type
    results_save_path = os.path.join(module_path, config['model']['output_path'].lstrip("/\\"))

    # Define the path to the original values used in the modeling process dynamically based on the model type
    original_values_path = os.path.join(module_path, config['model']['original_values'].lstrip("/\\"))

    # Define the output summary path dynamically based on the model type
    output_summary_path = os.path.join(module_path, config['model']['output_summary_path'].lstrip("/\\"))   

    # Read data
    df_raw = read_data(raw_input_data)
    df_raw=df_raw[(df_raw['week_starting_monday']>=START_DATE)&(df_raw['week_starting_monday']<END_DATE2)]
    print(df_raw['week_starting_monday'].unique())

    # df_raw=df_raw.drop('Right_Clusters',axis=1)
    print(df_raw.info())
    # Control file
    control_file = load_or_create_feature_control_file(df_raw, control_file_path)

    # Checking if null in input features
    check_nulls(df_raw, control_file)
    df_raw = df_raw.replace([np.inf, -np.inf], np.nan)
    # df_raw =df_raw.dropna()
    
    df_raw=impute_missing(df_raw,config)
    check_nulls(df_raw, control_file)
    print(f"Shape before week filter = {df_raw.shape}")
    df_raw=filter_data(df_raw,103)

    print(f"Shape after week filter = {df_raw.shape}")
    print(f"Unique KEY after week filter = {df_raw.KEY.nunique()}")

    df_raw=clean_columns(df_raw)


    # Train Model
    df_coef, df_avp, df_summary, df_vif = model(control_file, df_raw, config, scale=False)

    # Saving Results
    model_results, coef_business = process_model_results(df_raw, df_avp, df_summary, df_coef)

    # Save Model Summary
    print( df_coef.shape, coef_business.shape, df_avp.shape, df_summary.shape, model_results.shape, df_vif.shape)
    save_model_summary(summary_save_path, df_coef, coef_business, df_avp, df_summary, model_results, df_vif)
    output_summary_df=output_summary(df_raw).merge(df_summary[[KEY,'RSQ','ADJ_RSQ']],on=KEY).merge(coef_business[[KEY, ELASTICITY_COL, PVALUE_PREFIX + ALGO_REGULAR_PRICE]],on=KEY)    
    save_results_excel(output_summary_df, output_summary_path)

    # Get Elasticity
    model_results = get_elasticity(model_results, coef_business)


    ##check for seasonality

    # Impact of variables
    model_results = get_impact(model_results)

    # Adjust Elasticity
    model_results = get_adjusted_elasticity(model_results)

    # Save Results
    save_results(model_results, results_save_path)
